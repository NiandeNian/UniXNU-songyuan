"""Android boot image: raw or gzip(BootShim + UEFI FD), an optional device tree and ramdisk.

Inputs are a Mu-Silicium checkout (BootShim sources, Resources/Configs/<device>.toml, mkbootimg.py),
the built firmware volume and a compiled device tree. The image is meant for "fastboot boot" only.
The result is verified by unpacking it again; the output is deterministic.
"""
import gzip
import hashlib
import json
import shutil
import struct
import sys
import tempfile
import zlib
from pathlib import Path

from .config import load_toml
from .util import Error, log, run, sha256_file, tool

DEFAULTS = {'header_version': 0, 'base': 0, 'kernel_offset': 0x8000, 'tags_offset': 0x1e00000, 'pagesize': 4096}
MKBOOTIMG_FLAGS = ('base', 'kernel_offset', 'tags_offset', 'pagesize', 'header_version', 'ramdisk_offset', 'second_offset', 'cmdline')


def compile_shim(uefi, base, size, requires_header, scratch, text_offset=None, image_flags=None, screen_log=False):
    clang, objcopy, nm = tool('clang'), tool('llvm-objcopy', 'brew install llvm'), tool('llvm-nm', 'brew install llvm')
    source = uefi / 'BootShim/BootShim.S'
    if not source.is_file():
        raise Error(f'{source} missing: --uefi must be a Mu-Silicium checkout')
    obj = scratch / 'shim.o'
    run([clang, '--target=aarch64-none-elf', '-c', f'-DFD_BASE={base}', f'-DFD_SIZE={size}',
         f'-DREQUIRES_KERNEL_HEADER={int(requires_header)}', f'-DSONGYUAN_SCREEN_LOG={int(screen_log)}',
         source, '-o', obj], capture=True)
    if screen_log:
        console = uefi / 'BootShim/ScreenLog.c'
        linker = uefi / 'BootShim/ScreenLog.ld'
        if not console.is_file() or not linker.is_file():
            raise Error('screen_log requires the songyuan diagnostic BootShim sources')
        console_obj = scratch / 'screen-log.o'
        run([clang, '--target=aarch64-none-elf', '-c', '-Os', '-ffreestanding', '-fno-builtin',
             '-fno-stack-protector', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
             '-mgeneral-regs-only', '-mstrict-align', console, '-o', console_obj], capture=True)
        executable = scratch / 'shim.elf'
        run([tool('ld.lld'), '-T', linker, obj, console_obj, '-o', executable], capture=True)
        obj = executable
    run([objcopy, '-O', 'binary', obj, scratch / 'shim.bin'], capture=True)
    shim = (scratch / 'shim.bin').read_bytes()
    if screen_log and requires_header:
        header = bytearray(shim)
        struct.pack_into('<2Q', header, 8, base, len(shim) + size)
        shim = bytes(header)
    symbols = run([nm, '-n', obj], capture=True)
    offset = next((int(line.split()[0], 16) for line in symbols.splitlines() if line.endswith(' _Payload')), None)
    if offset != len(shim):
        raise Error('a literal pool or padding separates the _Payload label from the appended firmware volume')
    if requires_header and (shim[56:60] != b'ARM\x64' or struct.unpack_from('<QQ', shim, 8) != (base, len(shim) + size)):
        raise Error('the ARM64 image header does not describe the shim plus the firmware volume')
    if text_offset is not None or image_flags is not None:
        if not requires_header:
            raise Error('ARM64 image settings require a kernel header')
        # Linux text_offset describes placement relative to RAM, independently of
        # the FD_BASE address BootShim uses to relocate the firmware.
        header = bytearray(shim)
        if text_offset is not None:
            struct.pack_into('<Q', header, 8, text_offset)
        if image_flags is not None:
            struct.pack_into('<Q', header, 24, image_flags)
        shim = bytes(header)
    return shim


def patch_dtb(dtb, nodes, scratch):
    """Add device-tree nodes the stock bootloader expects (board.toml [[bootimg.dtb_node]])."""
    if not nodes:
        return dtb
    fdtput, fdtget = tool('fdtput', 'brew install dtc'), tool('fdtget', 'brew install dtc')
    work = scratch / 'device.dtb'
    work.write_bytes(dtb)
    for node in nodes:
        run([fdtput, '-c', work, node['path']], capture=True)
        for prop in node.get('props', []):
            values = prop['value'] if isinstance(prop['value'], list) else [prop['value']]
            run([fdtput, '-t', prop.get('type', 's'), work, node['path'], prop['name'], *[str(v) for v in values]], capture=True)
            got = run([fdtget, '-t', prop.get('type', 's'), work, node['path'], prop['name']], capture=True).split()
            kind = prop.get('type', 's')
            if kind in ('x', 'i', 'u') and [int(v, 16 if kind == 'x' else 10) for v in got] != [int(str(v), 0) for v in values]:
                raise Error(f'dtb node {node["path"]} property {prop["name"]} did not round-trip')
    return work.read_bytes()


def settings(ctx, uefi):
    fw = ctx.board.get('firmware', {})
    config = load_toml(uefi / 'Resources/Configs' / f'{fw["config"]}.toml') if fw.get('config') else {}
    values = dict(DEFAULTS)
    values.update(config.get('boot_image', {}))
    values.update(ctx.board.get('bootimg', {}).get('image', {}))
    fd = config.get('uefi_fd', {})
    return values, fd.get('base'), fd.get('size'), config.get('boot_shim', {}).get('requires_kernel_header', True), config


def build(ctx, uefi, fd, dtb, ramdisk=None, output=None):
    log('bootimg')
    image, base, size, requires_header, config = settings(ctx, uefi)
    mkbootimg = uefi / 'Resources/Scripts/mkbootimg.py'
    if not mkbootimg.is_file():
        raise Error(f'{mkbootimg} missing: --uefi must be a Mu-Silicium checkout')
    for path, what in ((fd, 'firmware volume (--fd)'), (dtb, 'device tree (--dtb)')):
        if not path or not Path(path).is_file():
            raise Error(f'{what} not found: {path}')
    firmware = Path(fd).read_bytes()
    if base is None or size is None:
        raise Error('the Mu-Silicium device config has no [uefi_fd] base and size')
    if len(firmware) != size:
        raise Error(f'firmware volume is {len(firmware):#x} bytes, the device config says {size:#x}')
    out = Path(output) if output else ctx.work / 'boot/boot.img'
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='unixnu-bootimg-') as scratch_name:
        scratch = Path(scratch_name)
        shim_config = config.get('boot_shim', {})
        shim = compile_shim(uefi, base, size, requires_header, scratch,
                            shim_config.get('text_offset'), shim_config.get('image_flags'),
                            screen_log=shim_config.get('screen_log', False))
        kernel_config = config.get('boot_image_kernel', {})
        compression = kernel_config.get('kernel_compression', 'gzip')
        append_dtb = kernel_config.get('append_dtb', True)
        if compression not in ('gzip', 'none'):
            raise Error(f'unsupported boot image compression: {compression}')
        tree = Path(dtb).read_bytes()
        if append_dtb:
            tree = patch_dtb(tree, ctx.board.get('bootimg', {}).get('dtb_node', []), scratch)
        if tree[:4] != b'\xd0\x0d\xfe\xed' or struct.unpack_from('>I', tree, 4)[0] != len(tree):
            raise Error('invalid compiled device tree')
        combined = shim + firmware
        kernel = gzip.compress(combined, mtime=0) if compression == 'gzip' else combined
        if append_dtb:
            kernel += tree
        kernel_path = scratch / 'Image.gz-dtb'
        kernel_path.write_bytes(kernel)
        if ramdisk:
            ramdisk_path = Path(ramdisk)
            if not ramdisk_path.is_file():
                raise Error(f'ramdisk not found: {ramdisk_path}')
        else:
            ramdisk_path = scratch / 'ramdisk'
            ramdisk_path.write_bytes(b'')
        command = [sys.executable, mkbootimg, '--kernel', kernel_path, '--ramdisk', ramdisk_path, '-o', out]
        for key in MKBOOTIMG_FLAGS:
            if key in image:
                command += [f'--{key}', str(image[key])]
        run(command, capture=True)
        if image['header_version'] == 4:
            # Mu's pinned mkbootimg emits a zero-filled GKI signature slot
            # without signing keys. Omit that slot for unsigned temporary boot.
            packed = bytearray(out.read_bytes())
            payload_end = 4096 + ((len(kernel) + 4095) // 4096) * 4096
            payload_end += ((ramdisk_path.stat().st_size + 4095) // 4096) * 4096
            signature_size, = struct.unpack_from('<I', packed, 1580)
            if len(packed) != payload_end + signature_size or any(packed[payload_end:]):
                raise Error('unexpected trailing data in an unsigned firmware boot image')
            del packed[payload_end:]
            struct.pack_into('<I', packed, 1580, 0)
            out.write_bytes(packed)
        report = verify(out, combined, tree, ramdisk_path, image, compression, append_dtb)
        if shim_config.get('screen_log', False):
            shutil.copyfile(scratch / 'shim.elf', out.parent / 'BootShim-screen.elf')
    report.update(image_sha256=sha256_file(out), image_bytes=out.stat().st_size, fd_sha256=sha256_file(fd),
                  dtb_sha256=sha256_file(dtb), shim_bytes=len(shim),
                  screen_log=bool(shim_config.get('screen_log', False)), hardware_tested=False)
    (out.parent / 'boot.json').write_text(json.dumps(report, indent=2) + '\n')
    log(f'bootimg: {out} ({out.stat().st_size} bytes)')
    return out


def verify(path, combined, tree, ramdisk_path, image, compression='gzip', append_dtb=True):
    """Unpack the image and compare every part with its input."""
    data = Path(path).read_bytes()
    version, = struct.unpack_from('<I', data, 40)
    if version >= 3:
        kernel_size, ramdisk_size, _, header_bytes = struct.unpack_from('<4I', data, 8)
        if version not in (3, 4) or header_bytes != (1584 if version == 4 else 1580):
            raise Error('invalid Android v3/v4 header size')
        if version == 4 and struct.unpack_from('<I', data, 1580)[0] != 0:
            raise Error('unexpected GKI signature in a temporary firmware boot image')
        kernel_address = tags = None
        second_size, page = 0, 4096
    else:
        kernel_size, kernel_address, ramdisk_size, _, second_size, _, tags, page, version, _ = struct.unpack_from('<10I', data, 8)
    if data[:8] != b'ANDROID!' or second_size or version != image['header_version'] or page != image['pagesize']:
        raise Error('boot image header does not match the requested parameters')
    if version < 3 and (kernel_address != image['base'] + image['kernel_offset'] or tags != image['base'] + image['tags_offset']):
        raise Error('boot image load addresses do not match the requested offsets')
    kernel = data[page:page + kernel_size]
    tail = tree if append_dtb else b''
    if compression == 'gzip':
        unpacker = zlib.decompressobj(16 + zlib.MAX_WBITS)
        if unpacker.decompress(kernel) != combined or not unpacker.eof or unpacker.unused_data != tail:
            raise Error('gzip, firmware and optional device tree do not round-trip')
    elif compression != 'none' or kernel != combined + tail:
        raise Error('raw firmware and optional device tree do not round-trip')
    start = page * (1 + -(-kernel_size // page))
    if data[start:start + ramdisk_size] != Path(ramdisk_path).read_bytes():
        raise Error('ramdisk bytes differ')
    return {'kernel_sha256': hashlib.sha256(kernel).hexdigest(), 'ramdisk_bytes': ramdisk_size,
            'header_version': version, 'kernel_address': hex(kernel_address) if kernel_address is not None else None,
            'tags_address': hex(tags) if tags is not None else None, 'compression': compression, 'appended_dtb': append_dtb,
            'arm64_text_offset': hex(struct.unpack_from('<Q', combined, 8)[0]),
            'arm64_image_flags': hex(struct.unpack_from('<Q', combined, 24)[0])}

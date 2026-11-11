#!/usr/bin/env python3
"""Observe an unmodified generic XNU kernel through real UEFI and GDB.

No guest probe, test process, reset timer, or hardware driver is added.
This fixture intentionally has no root device. A later panic is recorded,
not treated as evidence of userspace or device support.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/qemu-entry'))
from gdb_packets import Packets


def module(path):
    spec = importlib.util.spec_from_file_location('qemu_runner', path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def symbols(data):
    if struct.unpack_from('<I', data)[0] != 0xfeedfacf:
        raise ValueError('Expected a thin Mach-O kernel')
    result, offset = {}, 32
    for _ in range(struct.unpack_from('<I', data, 16)[0]):
        command, size = struct.unpack_from('<II', data, offset)
        if command == 2:
            table, count, strings, length = struct.unpack_from('<4I', data, offset + 8)
            names = data[strings:strings + length]
            for i in range(count):
                index, kind, section, _, address = struct.unpack_from('<IBBHQ', data, table + i * 16)
                if section and not kind & 0xe0 and index < length:
                    name = names[index:names.index(b'\0', index)].decode()
                    result[name] = address
        offset += size
    return result


def parse_adt(data, offset=0):
    count, children = struct.unpack_from('<II', data, offset)
    offset += 8
    properties = []
    for _ in range(count):
        key, length = struct.unpack_from('<32sI', data, offset)
        offset += 36
        properties.append((key.rstrip(b'\0').decode(), data[offset:offset + length]))
        offset += length + (-length % 4)
    kids = []
    for _ in range(children):
        child, offset = parse_adt(data, offset)
        kids.append(child)
    return [properties, kids], offset


def encode_adt(node):
    props, children = node
    result = struct.pack('<II', len(props), len(children))
    for key, value in props:
        result += struct.pack('<32sI', key.encode(), len(value)) + value + bytes(-len(value) % 4)
    return result + b''.join(encode_adt(child) for child in children)


def trim_adt(node):
    props, children = node
    # The upstream fixture contains synthetic UFS test nubs. They are not
    # present on virt and must not enter a normal kernel boot.
    node[1] = [c for c in children if dict(c[0])['name'] not in (b'ufshc\0', b'ufsphy\0')]
    for i, (key, value) in enumerate(props):
        if key == 'compatible' and value == b'arm,cortex-a710\0':
            props[i] = (key, b'arm,armv8\0')
    for child in node[1]:
        trim_adt(child)


def read_registers(packets):
    next_number, values = 0, {}

    def xml(name):
        offset, chunks = 0, []
        while True:
            reply = packets.request(f'qXfer:features:read:{name}:{offset:x},1000')
            if not reply or reply[0] not in 'ml':
                return
            chunks.append(reply[1:])
            offset += len(reply[1:])
            if reply[0] == 'l':
                break
        nonlocal next_number
        for item in ET.fromstring(''.join(chunks)).iter():
            if item.tag.endswith('include'):
                xml(item.attrib['href'])
            elif item.tag == 'reg':
                number = int(item.get('regnum', next_number))
                next_number = number + 1
                name = item.get('name')
                if name in ('pc', 'sp', 'cpsr', 'TCR_EL1', 'SCTLR_EL1', 'TTBR0_EL1', 'TTBR1_EL1', 'CNTFRQ_EL0', 'ESR_EL1', 'FAR_EL1'):
                    raw = packets.request(f'p{number:x}')
                    if raw and not raw.startswith('E') and set(raw) <= set('0123456789abcdef'):
                        values[name] = hex(int.from_bytes(bytes.fromhex(raw), 'little'))
    xml('target.xml')
    return values


def driver_state(packets, names):
    values = {}
    for symbol, size in [('_armdt_platform_configured', 4), ('_armdt_platform_cpu_count', 4),
                         ('_armdt_platform_nvram_proxy', 4), ('_armcpu_registered', 4),
                         ('_armcpu_gic_ready', 4), ('_armcpu_timer_interrupts', 8)]:
        if symbol in names:
            raw = packets.request(f'm{names[symbol]:x},{size:x}')
            if len(raw) == size * 2 and set(raw) <= set('0123456789abcdef'):
                values[symbol] = int.from_bytes(bytes.fromhex(raw), 'little')
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--efi-dir', type=Path, required=True)
    parser.add_argument('--kernel', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=90)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 600:
        parser.error('--timeout must be between 1 and 600 seconds')
    args.out.mkdir(parents=True, exist_ok=True)
    esp = args.out / 'esp'
    payload = esp / 'EFI/UniXNU/Payloads'
    payload.mkdir(parents=True, exist_ok=True)
    boot = esp / 'EFI/BOOT'
    boot.mkdir(parents=True, exist_ok=True)
    for name, destination in [('UniXNU.efi', boot / 'BOOTAA64.EFI'), ('DarwinBoot.efi', payload / 'DarwinBoot.efi')]:
        candidates = list(args.efi_dir.rglob(name))
        if len(candidates) != 1:
            parser.error(f'Expected one {name}, found {len(candidates)}')
        shutil.copyfile(candidates[0], destination)
    shutil.copyfile(args.kernel, payload / 'kernel.macho')
    adt = payload / 'kernel.macho.adt'
    subprocess.run([sys.executable, ROOT / 'scripts/qemu-entry/make-dt.py', '--armvirt', '--armcpu',
                    '--nvram-proxy', '--qemu-vmm-present', '--crypto-hash-method', 'sha2-384',
                    '--osenvironment', 'main', '--dram-size', '0x80000000', '--owned-memory-size', '0x20000000',
                    '--output', adt], check=True)
    tree, end = parse_adt(adt.read_bytes())
    assert end == adt.stat().st_size
    trim_adt(tree)
    adt.write_bytes(encode_adt(tree))
    (esp / 'EFI/UniXNU/unixnu.toml').write_text('''[boot]
default = "xnu"
timeout = 1
[[driver]]
path = "Payloads/DarwinBoot.efi"
[[entry]]
id = "xnu"
title = "QEMU: generic XNU entry"
type = "xnu"
path = "Payloads/kernel.macho"
args = "-v serial=3 debug=0x14e kt_fixed_zones=120"
''')
    runner = module(ROOT / 'package/Scripts/qemu-run.py')
    code, variables = runner.find_firmware(None)
    names = symbols(args.kernel.read_bytes())
    checkpoints = ['_arm_init', '_PE_init_iokit', '_bsd_init']
    missing = [n for n in [*checkpoints, '_panic'] if n not in names]
    if missing:
        parser.error(f'Missing real kernel symbols: {missing}')
    report = {'kernel_sha256': hashlib.sha256(args.kernel.read_bytes()).hexdigest(),
              'adt_sha256': hashlib.sha256(adt.read_bytes()).hexdigest(), 'cpu': 'max', 'memory_mib': 2048,
              'scope': 'generic XNU entry; no root or hardware validation', 'checkpoints': [],
              'registers_or_validation_state_modified': False,
              'firmware_sha256': hashlib.sha256(code.read_bytes()).hexdigest()}
    log = args.out / 'serial.log'
    with tempfile.TemporaryDirectory(prefix='unixnu-entry-') as work:
        work = Path(work)
        with socket.socket() as reserve:
            reserve.bind(('127.0.0.1', 0))
            port = reserve.getsockname()[1]
        command = ['qemu-system-aarch64', '-M', 'virt,virtualization=off,secure=off,gic-version=3',
                   '-accel', 'tcg', '-cpu', 'max', '-m', '2048', '-smp', '1', '-display', 'none',
                   '-no-reboot', '-nic', 'none', '-device', 'ramfb',
                   '-drive', f'if=pflash,format=raw,readonly=on,file={code}',
                   '-drive', f'if=none,id=esp,format=raw,readonly=on,file=fat:{esp.resolve()}',
                   '-device', 'virtio-blk-pci,drive=esp', '-serial', f'file:{log.resolve()}',
                   '-qmp', f'unix:{work}/qmp.sock,server=on,wait=off',
                   '-gdb', f'tcp:127.0.0.1:{port}', '-S']
        if variables:
            shutil.copyfile(variables, work / 'vars.fd')
            command += ['-drive', f'if=pflash,format=raw,file={work}/vars.fd']
        with (args.out / 'qemu.log').open('w') as output:
            proc = subprocess.Popen(command, stdout=output, stderr=output)
            qmp = runner.Qmp(str(work / 'qmp.sock'))
            with socket.create_connection(('127.0.0.1', port), timeout=5) as connection:
                try:
                    packets = Packets(connection)
                    packets.request('qSupported')
                    deadline = time.monotonic() + args.timeout
                    panic = names['_panic']
                    if packets.request(f'Z1,{panic:x},4') != 'OK':
                        raise RuntimeError('Breakpoint refused: _panic')
                    for name in [*checkpoints, '_panic']:
                        address = names[name]
                        if name != '_panic' and packets.request(f'Z1,{address:x},4') != 'OK':
                            raise RuntimeError(f'Breakpoint refused: {name}')
                        connection.settimeout(max(0.1, deadline - time.monotonic()))
                        stop = packets.request('c')
                        connection.settimeout(3)
                        registers = read_registers(packets)
                        pc = int(registers.get('pc', '0'), 16)
                        if pc not in (address, panic):
                            raise RuntimeError(f'Unexpected stop: {stop}, {registers}')
                        if pc == panic:
                            name, address = '_panic', panic
                        report['checkpoints'].append({'symbol': name, 'address': hex(address), 'registers': registers})
                        report['driver_state'] = driver_state(packets, names)
                        print(f'REACHED {name} at {address:#x}', flush=True)
                        packets.request(f'z1,{address:x},4')
                        if name == '_panic':
                            raw = packets.request('g')
                            pointer = int.from_bytes(bytes.fromhex(raw[:16]), 'little')
                            message = packets.request(f'm{pointer:x},100')
                            if not message.startswith('E'):
                                report['panic_format'] = bytes.fromhex(message).split(b'\0')[0].decode(errors='replace')
                            break
                except Exception as exc:
                    report['error'] = str(exc)
                    try:
                        packets.request(None)
                        report['last_registers'] = read_registers(packets)
                        report['driver_state'] = driver_state(packets, names)
                    except Exception:
                        pass
                finally:
                    ppm = work / 'screen.ppm'
                    if 'return' in qmp.command('screendump', filename=str(ppm)):
                        runner.ppm_to_png(ppm, args.out / 'screen.png')
                    qmp.command('quit')
                    proc.wait(timeout=5)
    text = runner.ANSI.sub('', log.read_text(errors='replace'))
    (args.out / 'serial.clean.log').write_text(text)
    report['loader_validated'] = 'inputs validated; exiting boot services' in text
    reached = [c['symbol'] for c in report['checkpoints']]
    report['entry_pass'] = report['loader_validated'] and all(name in reached for name in checkpoints)
    kernel_registers = report['checkpoints'][0]['registers'] if report['checkpoints'] else {}
    tcr = int(kernel_registers.get('TCR_EL1', '0'), 16)
    sctlr = int(kernel_registers.get('SCTLR_EL1', '0'), 16)
    report['native_4k_mmu_observed'] = bool(sctlr & 1) and (tcr >> 14 & 3) == 0 and (tcr >> 30 & 3) == 2
    report['counter_62500000_observed'] = int(kernel_registers.get('CNTFRQ_EL0', '0'), 16) == 62500000
    (args.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['entry_pass'] else 1


if __name__ == '__main__':
    sys.exit(main())

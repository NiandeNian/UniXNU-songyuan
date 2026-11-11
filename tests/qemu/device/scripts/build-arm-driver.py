#!/usr/bin/env python3
"""Build the two generic drivers using the kernel's actual compile record.

Derived from xVanTuring/UniXNU-qemu at
97b75b1f63c6b7e895cd7646029db741d5fe5488, scripts/build-arm-driver.py.
Only ArmDTPlatform and ArmCpu belong to this entry target.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('component', choices=['ArmDTPlatform', 'ArmCpu'])
component = parser.parse_args().component
record_path = ROOT / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json'
record = json.loads(record_path.read_text().strip().rstrip(','))
source = ROOT / 'drivers' / component / (component + '.cpp')
out = ROOT / 'build' / {'ArmDTPlatform': 'armdt-platform', 'ArmCpu': 'armcpu'}[component]
out.mkdir(parents=True, exist_ok=True)
destination = out / (component + '.o')
arguments, command, index = record['arguments'], [], 0
while index < len(arguments):
    value = arguments[index]
    if value == record['file']:
        command.append(str(source))
    elif value == '-o':
        command.extend(['-o', str(destination)])
        index += 1
    elif value == '-Xclang' and arguments[index + 1].startswith('-W'):
        index += 1
    elif not value.startswith('-W'):
        command.append(value)
    index += 1
command.extend(['-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                '-Wno-c99-designator', '-Wno-reorder-init-list', '-Wno-deprecated-enum-enum-conversion',
                '-Wno-unnecessary-virtual-specifier', '-I', str(ROOT / '.cache/xnu-work/osfmk')])
(out / 'compile-command.json').write_text(json.dumps(command, indent=2) + '\n')
result = subprocess.run(command, cwd=record['directory'], stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, text=True)
(out / 'compile.log').write_text(result.stdout)
if result.returncode:
    raise SystemExit(result.stdout[-3500:])
data = destination.read_bytes()
if struct.unpack_from('<4I', data) != (0xfeedfacf, 0x100000c, 0, 1):
    raise SystemExit('Unexpected platform object architecture')
offset, deployment = 32, None
for _ in range(struct.unpack_from('<I', data, 16)[0]):
    cmd, length = struct.unpack_from('<II', data, offset)
    if cmd == 0x32:
        deployment = struct.unpack_from('<II', data, offset + 8)
    offset += length
if deployment != (2, 0x110000):
    raise SystemExit(f'Unexpected platform deployment {deployment}')
archive = out / ('lib' + component + '.a')
archive.unlink(missing_ok=True)
subprocess.run(['xcrun', 'ar', 'rcs', archive, destination], check=True)
print(f'{component}: -Werror build and actual ARM64/iOS 17 object audit passed')

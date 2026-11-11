#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-2-Clause-Patent
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
EDK2=${UNIXNU_EDK2:?Set UNIXNU_EDK2 to a Mu_Basecore checkout}
CLANG_BIN=${CLANG_BIN:-/usr/lib/llvm-14/bin/}
export CLANG_BIN UNIXNU_EDK2
JOBS=${JOBS:-8} bash "$ROOT/package/build.sh"
WORK=$ROOT/out/qemu/darwinboot
mkdir -p "$WORK/Conf"
for item in target tools_def build_rule; do
  cp "$EDK2/BaseTools/Conf/$item.template" "$WORK/Conf/$item.txt"
done
export WORKSPACE=$WORK CONF_PATH=$WORK/Conf
export PACKAGES_PATH=$ROOT/drivers/DarwinBoot:$ROOT/package:$EDK2
export EDK_TOOLS_PATH=$EDK2/BaseTools PYTHON_COMMAND=python3
export PATH=$EDK_TOOLS_PATH/BinWrappers/PosixLike:$EDK_TOOLS_PATH/Source/C/bin:$PATH
build -p DarwinBootPkg/DarwinBoot.dsc -a AARCH64 -b DEBUG -t CLANGPDB -n "${JOBS:-8}"
cp "$WORK/build/DarwinBoot/DEBUG_CLANGPDB/AARCH64/DarwinBoot.efi" "$ROOT/package/Build/Out/AARCH64-DEBUG/"

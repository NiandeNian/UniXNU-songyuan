#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-2-Clause-Patent
# Ubuntu's official newer EDK II fixes custom VirtIO GOP geometry support.
set -euo pipefail
DEST=${1:?Pass an output directory}
mkdir -p "$DEST"
curl -fL https://archive.ubuntu.com/ubuntu/pool/main/e/edk2/qemu-efi-aarch64_2024.02-2ubuntu0.10_all.deb -o "$DEST/aavmf.deb"
echo 'fad8e80e929cd00dae8c5c8e5dd3ec85f37d9a832eea776957e5e2cf86ef2ab5  aavmf.deb' | (cd "$DEST" && sha256sum -c -)
dpkg-deb -x "$DEST/aavmf.deb" "$DEST/extracted"

# Building for Redmi K100 Pro Max

The production board is `songyuan` (SM8850/Canoe). Device parameters and the
A8xx driver are in [songyuan-device](https://github.com/NiandeNian/songyuan-device);
firmware is in [songyuan-uefi](https://github.com/NiandeNian/songyuan-uefi).

## Actions

- **songyuan kernel and graphics** compiles a source-kernel ABI carrier, then
  builds and links FT3683/HID, A840/GMU/HFI, PMGR and display drivers. Its artifact
  is `songyuan-darwin23-graphics`.
- **songyuan production Metal** builds pinned Turnip, the Rust Metal bridge,
  and the production Metal discovery/scanout bundle. Its artifact is
  `songyuan-darwin23-metal`, including the addon and code-directory hashes.
- **songyuan UniXNU menu image** packages UEFI and BootShim into `boot.img`.
  Its artifact is `songyuan-unixnu-menu`. It contains the menu and loader;
  it contains no kernel or OS root payload.

The menu job downloads the `songyuan-uefi` artifact from a successful firmware
run. If that artifact has expired, run the firmware workflow again and supply
its run ID as `uefi_run_id` when dispatching the menu workflow.

These builds do not enable a diagnostic page, probe daemon, GPU self-test worker,
or timed reboot. Device host tests are separate from phone execution.

## Reproducing the driver build

Use macOS with Xcode's iPhoneOS SDK and the tools listed in the kernel workflow.
Keep the pinned submodules, including the device's A8xx override:

```sh
git clone --recurse-submodules https://github.com/NiandeNian/UniXNU-songyuan.git
cd UniXNU-songyuan
git clone --recurse-submodules https://github.com/NiandeNian/songyuan-device.git device
python3 device/scripts/check-songyuan.py
python3 device/scripts/fetch-songyuan-gpu-firmware.py
./unixnu defconfig songyuan_bootstrap_defconfig -D device
./unixnu fetch xnu libplatform libdispatch AvailabilityVersions libpthread corecrypto-2023 IOStorageFamily -D device
./unixnu build kernel -D device
./unixnu defconfig songyuan_graphics_defconfig -D device
./unixnu build kernel -D device
```

The first pass supplies the exact prelinked reference used by the graphics ABI
audits. The default graphics profile excludes the optional full owner-root
pipeline, which additionally needs signed OS/SystemOS policies and a Data seed.

The current kernel and Apple driver ABI are Darwin 23 / ARM64. The inspected
iOS 27.2.1 target uses Darwin 27 / ARM64e and remains incompatible. The build
scope files inside artifacts record this distinction. Physical menu boot,
touch input, accelerated display, and OS startup are not yet validated. The phone
is online; temporary firmware boots currently remain black. The production menu
image uses raw ARM64, Android header v4, text_offset=0 and flags=0xa. The firmware
copy address remains 0xa7100000. Its FD and full image hashes are checked against
the Actions artifact before temporary boot.

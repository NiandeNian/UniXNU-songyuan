<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/logo-light.svg">
    <img alt="UniXNU" src="assets/logo-light.svg" width="200">
  </picture>
</p>

<p align="center">
  <a href="https://unixnu.com"><img alt="Documentation" src="https://img.shields.io/badge/docs-unixnu.com-2A5BD7?logo=readthedocs&logoColor=white"></a>
  <a href="https://t.me/unixnu"><img alt="Telegram" src="https://img.shields.io/badge/Telegram-@unixnu-26A5E4?logo=telegram&logoColor=white"></a>
  <a href="https://qun.qq.com/universal-share/share?ac=1&authKey=Pubz23DOCY76nxjlGuSms2zesk4jRvas4zrXJRYk7omf7CprXbGQigLEI%2BCoYR8D&busi_data=eyJncm91cENvZGUiOiIxMTI2MTE2NzU5IiwidG9rZW4iOiJwSHJsUDN1UnN2Vi8yM210TjJRbzBIcERmcUpyOS9lb0hHVVpadWdvVFdScVpSYUFLT1YzTk5TWC9mN2xWYmtIIiwidWluIjoiMzE1MTEwOTc0MSJ9&data=_cJgr-jX9yJ2-GXwVjRN5FOhDyk5B-HAfIk5LSunbW_XkkmKqNXbpH33wzP93J0p9DI1fbjgBUrUfTVhwDcxjg&svctype=4&tempid=h5_group_info"><img alt="QQ Group" src="https://img.shields.io/badge/QQ%20Group-join-12B7F5?logo=qq&logoColor=white"></a>
  <a href="https://x.com/unixnu"><img alt="X" src="https://img.shields.io/badge/X-@unixnu-000000?logo=x&logoColor=white"></a>
</p>

<p align="center">
  English | <a href="README.zh-CN.md">简体中文</a>
</p>

# UniXNU

## Redmi K100 Pro Max / songyuan

This fork builds the UniXNU menu and SM8850 touch/Adreno 840 port with
[songyuan-uefi](https://github.com/NiandeNian/songyuan-uefi) and
[songyuan-device](https://github.com/NiandeNian/songyuan-device).
Actions builds the menu boot image, the Darwin 23 graphics kernel, and a production
Metal/Turnip bundle without a diagnostic daemon or timed boot reset.

**iOS 27 is not bootable in this port yet.** The inspected iOS 27.2.1 kernel uses
Darwin 27 / ARM64e / MH_FILESET, while the inherited source and driver ABI are
Darwin 23 / ARM64. The matching XNU 13432.42.3 source tag is unavailable.
The phone is currently offline. Temporary menu boots remained black; touch and GPU
execution still require physical validation after the firmware boot chain works.
See the device repository for the captured parameters and exact firmware pins.

Offline work now uses [isolated QEMU tests](tests/qemu/README.zh-CN.md) with AAVMF,
the UniXNU menu, DarwinBoot and a separately built generic kernel. The current
official documentation also provides an experimental iPadOS 27.0.1 ARM64e
profile; adopting that profile requires a separate ABI/PAC migration from this
fork's Darwin 23 build and does not make the inspected iOS 27.2.1 input compatible.

QEMU now passes all six UEFI smoke groups and the real-kernel positive/negative
comparison. After supplying the required AMFI DT policy and the matching pthread
component, the generic kernel initializes its platform, NVRAM, CPU, GIC and real
timer IRQs. It then stops at `Failed to mount root device`: this target supplies
no root volume or userspace. See the linked record for logs and reproducible steps.
[Strict regression 42977412592](https://github.com/NiandeNian/UniXNU-songyuan/actions/runs/42977412592)
passed all three jobs, with 19 real timer IRQs and rejection before BSD in the
missing-AMFI-policy control.

🎉 **News:** The native Metal GPU driver is now fully working on the Xiaomi Pad 6S Pro (sheng). The render server composites the system UI through the Adreno 740, and listed processes get their own Metal devices. See the [Adreno 740 driver documentation](https://unixnu.com/drivers/native-adreno).

An independent project to run iOS and macOS on non-Apple ARM64 hardware through UEFI.

## Documentation

The documentation is at [unixnu.com](https://unixnu.com). It covers the boot chain, the build driver, device porting, driver development, the 4 KiB XNU page patches, boot arguments and per-device notes.

- [Overview](https://unixnu.com/guide/overview)
- [Build](https://unixnu.com/building)
- [Boot the image](https://unixnu.com/guide/boot)
- [Debugging and logs](https://unixnu.com/guide/debugging)
- [Porting](https://unixnu.com/porting/)
- [Drivers](https://unixnu.com/drivers/overview)
- [XNU and 4 KiB pages](https://unixnu.com/xnu/four-k-page-tables)
- [Devices](https://unixnu.com/devices/)

## Repositories

| Repository | Contents |
| --- | --- |
| [UniXNU](https://github.com/UniXNU/UniXNU) | Build driver, UEFI boot manager, module submodules and patches |
| [UniXNU-sheng](https://github.com/UniXNU/UniXNU-sheng) | Device repository for the Xiaomi Pad 6S Pro |
| [uefi-sheng](https://github.com/UniXNU/uefi-sheng) | UEFI firmware port for the Xiaomi Pad 6S Pro |

Drivers and kits are independent public repositories under the UniXNU organization, included as submodules. Clone with `--recurse-submodules`, or run `git submodule update --init --recursive`.

Device repositories use the same layout as this repository. Their modules override modules with the same name, and their `package/` becomes a kit in the build tree.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the repository scope, the development workflow, the commit format and the documentation rules.

## Private blobs

Do not add Apple IPSW files, kernelcaches, disk images, trust caches, Data seeds or vendor firmware to this repository. Keep them in a local cache or external storage.

## License

BSD-2-Clause-Patent. See [LICENSE](LICENSE).

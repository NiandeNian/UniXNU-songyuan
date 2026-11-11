# QEMU 离线调试记录

2026-11-11 已直接读取 [官网移植文档](https://unixnu.com/zh/porting/)，
并核对官方仓库 `848a97bedaf9f4d63155552d113e0f3992368f86` 的同源文件。
参考社区 [UniXNU-qemu](https://github.com/xVanTuring/UniXNU-qemu/tree/97b75b1f63c6b7e895cd7646029db741d5fe5488)。
`device/board.toml` 的 IPSW/预链接选择沿用该项目，运行器和独立内核配置在这里维护。

## 文档核对结果

| 范围 | 对 songyuan 的具体要求 |
| --- | --- |
| 架构与配置 | 当前 fork 为格式 1；新版格式 2 把 ARM64、SoC、OS、板级分开。数组整体替换，组件、归档、补丁必须保留完整依赖。迁移要保存现有 SM8850 参数和社区 A8xx 分支身份。 |
| 固件 | songyuan FD 只用于手机。QEMU 使用 AAVMF，ESP 加载独立 DarwinBoot。菜单、GOP、键盘、文件系统是后续阶段的前提。 |
| 设备树 | FDT 与 XNU ADT 不可混用。ADT 的 reg 为小端 u64 地址/长度，整数 cell 需转换；chosen/cpus/arm-io/defaults/options 和有效 CHRP NVRAM 必须存在。 |
| CPU/内存 | QEMU 使用 GICv3、62.5 MHz 计数器和自己的 RAM。手机仍需验证各核心 PAC、PSCI、GIC、DMA/SMMU 所有权及缓存策略。 |
| 存储 | UFS 要分别确认控制器/PHY/时钟、DMA、命令完成、块数据、根卷及持久 Data。QEMU 只能验证 VirtIO；不能据此确认 SM8850 UFS。 |
| 显示 | GOP 尺寸、stride、像素格式与保留区必须一致。CPU 呈现和 GPU 呈现分别验证；交换完成前保留 IOSurface 与源帧。 |
| 输入 | FT3683 要使用自己的识别、固件、报告协议；不能套 Novatek 矩阵。触点 ID、坐标和数量必须来自同一快照，按下/移动/抬起与面板方向分别验收。 |
| GPU | 官方 A740 接口不能代替 A840。继续使用固定的 A8xx 后端，按 GMU/HFI、SMMU、BO、提交/fence、Metal ABI、实际渲染顺序验证。 |
| 网络/蓝牙/USB | 各自需要板级电源、固件、DMA、中断、OS ABI；设备身份、连接与实际收发分别记录。QEMU 不提供 WCN 和 Qualcomm PHY。 |
| 基带/DSP/音频/电源 | modem 固件与 EFS/NV、苹果 bbfw 是不同输入；GLINK/QRTR、IPA/GSI、DSP 周期缓冲、时基和电源回调需逐层接入。手机离线时不声明完成。 |
| iOS 27 | 官网已有实验性的 `ipados-27.0.1-24A446` arm64e profile（XNU 12377.121.6 加兼容调用）；songyuan 尚不属于其已验证设备。它与之前检查的 iOS 27.2.1 / XNU 13432.42.3 不是同一个目标。 |
| 打包与记录 | 新版固定 package.sh 从 TOML 读取值；私有二进制不入 Git。Data seed 内容身份和 UUID 都要保留。主机构建、QEMU 运行与真机观测分开。 |

阅读范围包括移植步骤、迁移、设备仓库、SoC、arm64e/macOS、设备树、固件、驱动顺序、
平台、UFS、显示、输入、GPU、Wi-Fi、蓝牙、USB、基带、DSP/音频/电源、驱动开发、
双系统分区、打包、bring-up、日志抓取与移植记录，以及 QEMU、调试、故障排查参考。
按用户要求使用正常串口、QMP 和 GDB；文档中的手机探针、诊断页和定时重启不加入本轮载荷。

## 已观察到的结果

- 从此前 Actions 的 UniXNU.efi 启动标准 AAVMF，实际显示 800×600 图形菜单，输入服务存在。
- 本地重建后的默认载荷验证 DT 补丁/overlay、kit 驱动、initrd 和 UEFI 变量，五项通过。
- 下键与 Enter 实际选择第二项并启动；无 GOP/配置时返回固件。
- Ubuntu 22.04 的 2022 AAVMF 把 1080×2400 改为 1280×800，竖屏检查失败。
- 官方 Ubuntu 2024.02 固件在同一 QEMU 6.2 / `max` CPU 上实际支持 1080×2400，竖屏检查通过。
- Ubuntu 2026.05 固件在 QEMU 6.2 下发生同步异常，不用于这个环境。

本地日志在 `out/qemu/` 和 `package/Build/Smoke/`，不会提交生成文件。
Actions 的 `qemu-uefi`、`qemu-kernel`、`qemu-entry-evidence` 保存编译与运行证据。
内核停点和根卷结果应以实际的 `report.json` 为准。

## 重现

在 Linux/WSL 安装 QEMU AArch64、clang/llvm/lld 14、dtc、mtools、uuid-dev、nasm 和构建工具。
Mu_Basecore 固定到 `6f805f26a4366fe56790130dc2f8f3e1b4c2fe28`，初始化三个 BaseTools/MdePkg 子模块。

```sh
export UNIXNU_EDK2=/path/to/Mu_Basecore
export CLANG_BIN=/usr/lib/llvm-14/bin/
bash tests/qemu/fetch-firmware.sh out/qemu/aavmf
export UNIXNU_QEMU_FIRMWARE="$PWD/out/qemu/aavmf/extracted/usr/share/AAVMF/AAVMF_CODE.fd"
export UNIXNU_QEMU_CPU=max
bash tests/qemu/build-uefi.sh
JOBS=8 bash package/Scripts/smoke.sh
```

在带 Xcode 的 macOS 上编译独立内核：

```sh
./unixnu defconfig qemu_entry_defconfig -D tests/qemu/device
./unixnu fetch xnu libplatform libdispatch AvailabilityVersions libpthread corecrypto-2023 IOStorageFamily -D tests/qemu/device
./unixnu build kernel -D tests/qemu/device
```

将它复制到 Linux/WSL 后，在主仓库运行：

```sh
python3 tests/qemu/run-entry.py --efi-dir package/Build/Out/AARCH64-DEBUG \
  --kernel out/qemu/kernel/kernel.macho --out out/qemu/entry
```

独立内核关闭 UFS、触控、Adreno、诊断页、mockfs 和 PMGR；本阶段不提供根设备或用户态。
GDB 使用实际 Mach-O 符号设置硬件停点，并记录 PC、EL1 翻译寄存器和原始 panic 格式。
`entry_pass` 只表示加载器验证并到达内核/IOKit/BSD；后续 panic 是待解决事项。
ESP 与固件 code 只读，NVRAM 使用临时副本。该脚本不访问手机或真实块设备。

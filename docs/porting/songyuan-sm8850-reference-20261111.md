# songyuan 的 SM8850 参考审查（2026-11-11）

对照 [UniXNU 官方设备目录](https://unixnu.com/zh/devices/) 的所有 SM8850 条目，确认 7 个机型组、11 个社区项目。目录是社区项目索引；下表的启动、触摸和 GPU 状态来自维护者文档，未由本项目独立真机复现。源码引用固定到此次读取的提交，避免后续分支更新改变结论。

对 songyuan 最有用的是 Typeun/myron 的 FT3683 和板级交接资料、lafa 的 UniXNU 上屏记录，以及 Pandora 的 Adreno 840 电源/固件/总线代码。它们能指导修复，不构成本机启动或 iOS 27 兼容的证据。

## 全部目录条目

| 机型组 | 项目与固定版本 | 查到的状态 | 对 songyuan 的作用 |
| --- | --- | --- | --- |
| fairlady / 一加 15T | [Osilvfe/UniXNU-fairlady](https://github.com/Osilvfe/UniXNU-fairlady/tree/bb056596ef52dd6982a6109f92cd25d9a053b349) | 源码内核 bring-up，提供 BootProgress S1–S6 诊断；此次所读材料未给出可复核的真机完成记录 | 诊断结构、单核最小配置和标准 UniXNU 打包参考；其面板与内存大小不能直接套用 |
| lafa / realme GT8 Pro | [ky554640/UniXNU-lafa](https://github.com/ky554640/UniXNU-lafa/tree/f7ec5c6d2885fc552f29073e5d4d202c9f9cb925) | 维护者记录 2026-11-01 临时启动到 EFI，UniXNU 提示没有系统；GPU/触摸完成了代码移植，仍有待实测项 | 继承 ABL framebuffer 的 GOP 路线、启动日志和 UFS 几何修正；1440×3136、S3910、IRIS7P 为不同板级条件 |
| myron / Redmi K90 Pro Max、Poco F8 Ultra | [Typeun/myron-device](https://github.com/Typeun/myron-device/tree/d9b6be4d75f5a8169aee65b02bb23cd88968c1eb) | README 记录 iPadOS 17.7.11 SpringBoard、FT3683 触摸、A840 Metal 和 SMP；同一仓库的显示尺寸及存储状态存在互相矛盾的旧记录 | 最接近本机的 FT3683、QUP4 SE0、1200×2608、TLMM、CPU Affinity2 和保留原厂 UFS SMMU 交接参考 |
| myron | [zg7681/UniXNU-myron：myron-next](https://github.com/zg7681/UniXNU-myron/tree/f1a1bfe561226dbb48e2904e0a2e74c67d2485ed) | 核心 UniXNU 派生分支；配套 NativeAdreno 有 a8xx 分支，README 的已运行设备仍写 sheng | 驱动组件 API 和 A8xx 寄存器选择；分支名不能作为 myron 或 songyuan 真机成功证据 |
| pandora / 小米 17 Pro | [ShueiTsuki/data-a-live](https://github.com/ShueiTsuki/data-a-live/tree/d2c7089b0a2e6da2b1e7e843337b503ec032b2c5) | 维护者记录 iOS 16.7.16 主屏、GPU 合成、触摸、8 核；已归档，说明后续由 yechenan 接手 | 最具体的 SM8850 GPU、GPI DMA、RPMh、UFS 交接源码；它的直接 loader、xnu-8796 内建驱动路线与当前 UniXNU 模块路线不同 |
| pma120 / OPPO Find X9 Ultra | [Sunshineix/UniXNU-pma120](https://github.com/Sunshineix/UniXNU-pma120/tree/06d877221ec5f4b613cc8cae59878e9205e06c3a) | README 明确 skeleton，尚不能构建或启动；选择实验性 iPadOS 27 配置 | 固件盘点和配置形式参考；不能据此认定 SM8850 已支持 iOS/iPadOS 27 |
| pudding / 小米 17 | [daisukiKaffuChino/UniXNU-pudding](https://github.com/daisukiKaffuChino/UniXNU-pudding/tree/1c357b4c91865c6d8fcfa7e01e0bdc03b81b5815) | porting.toml 的阶段均为 planned，记录 vendor DTB、p11u-family DTBO 与 Pandora 对照结果 | 1200×2608、FocalTech 接线和 GPU 寄存器交叉核对；文档说明存在多供应商触控，不能仅凭机型决定协议 |
| songyuan / Redmi K100 Pro Max | [aogg2023/songyuan-device](https://github.com/aogg2023/songyuan-device/tree/b489567b58377fe269c70067294df420012c42a1) | 仍保留 myron kit、K90 身份和原 myron 磁盘窗口 | 可对比项目结构；不提供独立的本机硬件验证，尤其不能复制磁盘窗口 |
| songyuan | [NiandeNian/songyuan-device](https://github.com/NiandeNian/songyuan-device/tree/74b7b295eef4346620ebc16e53bcf080789b1ef8) | 本项目基线，已采集 songyuan live FDT、framebuffer 和触控参数；UEFI 真机测试仍黑屏 | 作为本机事实来源，不能计算为另一份独立成功案例 |
| songyuan | [WUKAWL/songyuan-device](https://github.com/WUKAWL/songyuan-device) | 此次 GitHub API 返回 HTTP 404 | 当前无法读取；404 不说明仓库删除还是访问受限 |
| songyuan | [WUKAWL/songyuan-unixnu](https://github.com/WUKAWL/songyuan-unixnu) | 此次 GitHub API 返回 HTTP 404 | 同上；未推断其实现或启动状态 |

## 能直接指导本机工作的信息

### UEFI 与显示交接

[lafa 首次上机记录](https://github.com/ky554640/UniXNU-lafa/blob/f7ec5c6d2885fc552f29073e5d4d202c9f9cb925/docs/首次上机记录.md) 描述 header-v4、gzip BootShim+FD 和原厂 DT 集合，实际出现 EFI 与“没有系统”。这支持在进入 XNU 前先验证完整 UEFI/DXE/GOP 路线。其 [构建脚本](https://github.com/ky554640/UniXNU-lafa/blob/f7ec5c6d2885fc552f29073e5d4d202c9f9cb925/wsl_install/build-uefi.sh) 指定 FD `0xc6900000`，不同于本机的 `0xa7100000`；不能为了模仿上屏结果直接更换地址。

GOP 和早期屏幕日志可以写 ABL 已初始化的 framebuffer，暂时不用重新初始化面板。物理显示仍依赖原厂已运行的 MDSS/DSI/面板链路；这不等于绕过显示硬件，也不能据此断言清空 SMMU 或关闭原厂时钟无害。本机 framebuffer 已采集为 `0xfc800000`、1200×2608、stride 4800。当前继续保留原厂 SMMU 上下文与显示链路。

[Typeun/myron-uefi README](https://github.com/Typeun/myron-uefi/blob/ce8e5e58a522d3d7fbba472ab0d70da735fbe8df/README.md) 记录相同 framebuffer、FT3683 和 QUP4 SE0，但该固定版本明确固件尚未真机启动，仍使用 aston 二进制及 ACPI。它与 myron-device 的后续启动描述不能混为同一份镜像的验证。songyuan 已改用本机固定原厂固件输入，不回退到跨厂商二进制。

### FT3683 与总线

| 项目 | songyuan 已采集值 | 参考及使用方式 |
| --- | --- | --- |
| 触控 IC | FocalTech FT3683 | 优先沿用当前 MyronTouch 的 FocalTech 协议；Pandora 主屏为 Synaptics S3910P，不能复制 TouchComm 解码 |
| SPI 控制器 | QUP4 SE0 `0x01a80000` | myron、Pandora、pudding 均提供同类平台总线参考 |
| GPIO | reset 66、AVDD 117、IRQ 158 | 与 myron/Pandora 接线记录相符；lafa reset159、AVDD66、L4B 不适用 |
| TLMM pin 基址 | 当前驱动使用 `0x0f100000` | [Pandora 触控源码](https://github.com/ShueiTsuki/data-a-live/blob/d2c7089b0a2e6da2b1e7e843337b503ec032b2c5/wsl/pandora_touch.c) 解释 DT `0x0f000000` 还需 pin 表的 `0x100000` 偏移 |
| 分辨率 | 1200×2608 | 以 songyuan live FDT 为准，不能采用 myron README 旧表中的 1220×2656 |

Pandora 的总线代码特别记录 SE FIFO interface disabled，并使用 GPI DMA：GPII1 窗口 `0x01a14000`，GPI SID `0x536`、QUP SID `0x523`，iovdd 资源 `L4I_E0`。这些能用于查明本机总线为何不传输，但仍需核对本机 GENI firmware 状态、GPI 归属和 SMMU stream。当前 MyronTouch 已有 FIFO-disabled/SE DMA 分支；GPI DMA 是待验证的替代路径，不能把另一条路径已成功当成本机当前实现已成功。

### Adreno 840

[Pandora GPU 源码](https://github.com/ShueiTsuki/data-a-live/blob/d2c7089b0a2e6da2b1e7e843337b503ec032b2c5/wsl/pandora_gpu.c) 给出逐级电源/时钟、SCM、GMU SMMU、冷启动、HFI、GX、SQE/CP 到用户接口的实现。最有价值的是访问前检查电源和时钟，以及只接管本驱动拥有的 SMMU stream。GPU/GPUCC/GMU 在未上电时不能靠盲读定位故障。

平台寄存器可以交叉核对：GPU `0x03d00000`、GPUCC `0x03d90000`、GMU `0x03d37000`/`0x68000`、GPU SMMU `0x03da0000`，GMU stream 5。当前本机驱动已有这些地址，重复复制常量不会解决早期 UEFI 黑屏。

[lafa GPU 参数对照](https://github.com/ky554640/UniXNU-lafa/blob/f7ec5c6d2885fc552f29073e5d4d202c9f9cb925/docs/GPU移植对照表.md) 反而说明同 SM8850 也有差异：lafa chipid `0x44050a00`、最高1050 MHz、两档 GMU；Pandora `0x44050a01`、最高1200 MHz、四档 GMU。songyuan 的 OPP、带宽索引、slice 信息和固件版本必须按本机 DT/固件确认，不复制另一台手机的性能表。

[NativeAdreno-myron a8xx 的寄存器表](https://github.com/zg7681/NativeAdreno-myron/blob/5bbeb3b8d049a637a595090319835a49e58a8b56/NativeAdrenoChip.h) 已区分 A7xx/A8xx：例如 SQE base 为 `0x0816`、全局 fence scratch 为 `0x082c`、RBBM interrupt status 为 `0x006a`、CP interrupt status 为 `0x08b5`。这些是 **dword offset**，最终 MMIO 字节地址需乘4；组件默认仍为 A7xx，必须显式传入 A8xx 表。README 的运行状态仍只提 sheng，因此这是代码参考，未认定其完整 A840 冷启动已在本机通过。

### UFS、SMMU 与 CPU

myron-device 的 board.toml 记录 EL1 访问 UFS SMMU context 页面可能 external abort，要求保留原厂映射。当前 songyuan SEC 已移除全局 ArmSmmuDetach，方向与其记录一致。后续驱动接管必须针对所属 stream，不能清空显示和原厂固件仍使用的上下文。

[lafa 的 UFS SMMU 窗口修正](https://github.com/ky554640/UniXNU-lafa/blob/f7ec5c6d2885fc552f29073e5d4d202c9f9cb925/wsl_install/patch-native-ufs-smmu-window.py) 指出 SM8550 的 `0xd0000` 范围不够容纳所记录 SM8850 的128个全局页和81个 context bank，需按本机 DT 的 `0x100000` 映射范围复核。扩大驱动虚拟映射范围与主动读写全部 context bank 是两回事。UFS 还可参考 Pandora 的退出 HIBERN8、WLUN `0xd0` START STOP UNIT 时序；其他设备的 GPT/LBA 窗口不适用。

GIC `0x17000000`/`0x17080000`、redistributor stride `0x40000`、19.2 MHz、prime 核 MPIDR Affinity2 `0x10000/0x10100` 有多份 SM8850 资料相互印证。IPI 使用软件 SPI 的方案仍需本机验证，并成对处理 pending bit 清除，不能仅打开 CPU idle。

## 本轮 QEMU 可复现修复

这两处是运行当前 songyuan 固件发现的源码错误，并非从某个参考仓库推断真机黑屏原因：

1. **内存描述符名称带尾空格。** Mu 用完整 `AsciiStriCmp` 查找；`Display_Reserved` 查找失败后，framebuffer 调用者使用未初始化 descriptor。去掉40个名称的尾空格，并让验证器拒绝名称边缘空白。实际名称修正版 [DEBUG Actions 43012194246](https://github.com/NiandeNian/songyuan-uefi/actions/runs/43012194246) 已在 QEMU 进入 MMU 初始化及 `[14] PlatformPeim`，无需在运行时修改 FD。
2. **XBL 扫描跨越 FD 边界。** 原扫描在保留区最后4字节执行8字节读取，QEMU 的 `FAR_EL1=0xc6aa8000` 恰好为 `0xc6800000+0x2a8000`。修正扫描 lookahead、缺失 RET 时的函数结束边界及 GUID 读取边界；同时按 ADD 的源寄存器解析地址，避免 Rd/Rn 不同导致漏识别。[修复提交](https://github.com/NiandeNian/songyuan-uefi/commit/8063b5d4972d84639163ef009cf0e38ecafc9e51) 的保护页测试覆盖区域末尾、半截签名、缺失 RET、越界 GUID、负 ADRP 和无效区间。原固定版本在空区域扫描时 SIGSEGV，修正版通过。

QEMU 只提供通用 ARM64 CPU/RAM，并加载本机原厂 SEC 的静态 ELF PT_LOAD 字节；没有 SM8850 外设、原厂 scheduler 的运行时数据或真实扫描输出。它可以验证入口、屏幕写入、缓存/MMU及内存访问边界，不能验证触摸、GPU、UEFI 真机菜单或 iOS 27 启动。

[修正版 DEBUG Actions 43013977832](https://github.com/NiandeNian/songyuan-uefi/actions/runs/43013977832) 已成功。下载的实际 FD SHA-256 为 `3e6f30df3b1ce5e6b29912c95c576df3bc2b94916fd38a2dbf55db7d51179447`，与 Actions 日志一致。它在 QEMU 不再触发 `0xc6aa8000` 尾部越界，并调用到原厂 SEC 内的代码；新的停止点为 `ELR_EL1=0xc680955c`、`FAR_EL1=0`、`TPIDR_EL1=0`。该原厂代码先执行 `mrs x19, TPIDR_EL1`，随后在停止点执行 `ldr w1, [x19]`。这符合此静态 QEMU 环境缺少原厂线程上下文的限制，不能据此断言真机也缺少上下文，也未伪造 scheduler 数据来跨过它。仍停留在 `[14]` 阶段，未宣称进入 DXE。

## 后续验证次序

菜单打包工作流已固定到该修复提交和成功的 DEBUG run，继续保留屏幕日志。真机重新在线后，临时启动同一构建的屏幕日志镜像，确定真实停止阶段。完整 UEFI 菜单上屏后，再进入本机 FT3683 总线、A840 冷启动与系统载荷验证。当前没有从这些 SM8850 资料中找到可独立复核的 iOS/iPadOS 27 真机完成案例。

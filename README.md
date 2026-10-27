<div align="center">

# March7thAssistant for macOS（PlayCover iOS 版移植）

**简体中文** | [English](./README_EN.md)

</div>

> [!IMPORTANT]
> 本仓库是 [moesnow/March7thAssistant](https://github.com/moesnow/March7thAssistant)（三月七小助手）的**非官方 macOS 移植版**。
> 原项目由 moesnow 及众多贡献者开发，所有核心功能都来自原项目，本仓库只增加了「在 macOS 上操作 PlayCover 运行的 iOS 版星穹铁道」的适配。
> 遵循原项目的 [GPL-3.0](./LICENSE) 协议发布。macOS 版的问题请在**本仓库**提 Issue，不要打扰原项目。

## 移植了什么

原版通过 Win32 窗口截图 + 键鼠操作 PC 版游戏。macOS 上没有 PC 版，本移植改为操作 [PlayCover](https://github.com/hguandl/PlayCover) 运行的 **iOS 版**：

- **截图 / 触控**：通过 PlayCover（hguandl 分支）内置的 MaaTools 服务（默认端口 1717）在游戏进程内截图、注入多点触控。不需要游戏窗口在前台，也不受窗口位置、Retina 缩放影响
- **键盘 → 触控**：脚本里的按键（W/A/S/D、E、F、Esc、数字键等）转换为对应的屏幕点击 / 摇杆滑动（`module/automation/playcover_input.py`）
- **移动端界面适配**（`module/mobile` + `assets/mobile/`）：iOS 版 UI 布局和 PC 版不同，PC 模板多尺度匹配，匹配不上的换成 iOS 专用模板；识别区域、坐标、滚动方式按移动端重新映射。业务流程基本不改
- **桌面启动图标**：`tools/macos/make_app.sh` 生成「三月七小助手.app」

### 已实测的功能

| 功能 | 状态 |
| --- | --- |
| 启动游戏 / 登录 / 领取奖励 | ✅ |
| 清体力（副本、自动战斗） | ✅ |
| 每日实训（识别、委托、合成、领活跃度礼包） | ✅ |
| 忘却之庭（混沌回忆，支持预设编队） | ✅ |
| 末日幻影 | ✅ |
| 货币战争 | ✅（默认策略） |
| 差分宇宙 | ✅ |
| 虚构叙事 | 🚧 部分适配，未完整验证 |
| 兑换码 | ⛔ iOS 版游戏内没有兑换码入口，自动跳过 |
| 模拟宇宙、锄大地、抽卡记录导出等 | ❌ 未适配 |

## 环境要求

| 项目 | 要求 |
| --- | --- |
| 电脑 | Apple Silicon（M1 及以上）Mac。iOS 应用只能在 Apple Silicon 上运行 |
| 系统 | macOS 14 及以上（开发测试环境：macOS 27 / Apple M4） |
| PlayCover | **hguandl 分支版**（带 MaaTools），测试版本 `4.0.0.maa`：<https://github.com/hguandl/PlayCover/releases>。官方 PlayCover 没有 MaaTools，无法使用 |
| 游戏 | 崩坏：星穹铁道 iOS 版。测试为国际服 `com.HoYoverse.hkrpgoversea`（游戏语言：简体中文）；国服包名为 `com.miHoYo.hkrpg` |
| Python | 3.12 及以上 |
| uv | Python 包管理器：<https://docs.astral.sh/uv/> |
| Git | 用于下载本项目（Xcode Command Line Tools 自带） |

## 部署

### 1. 安装 PlayCover 和星穹铁道

1. 下载并安装 hguandl 分支版 PlayCover（见上表链接）
2. 准备星穹铁道的 iOS 安装包（IPA），拖进 PlayCover 安装。获取 IPA 的方法见 [PlayCover 官方文档](https://docs.playcover.io/)
3. 在 PlayCover 里右键游戏 →「设置」，建议如下（开发时使用的配置）：
   - **MaaTools**：打开，端口 `1717`（**必须**）
   - 显示 → 宽高比：**16:9**；分辨率：4K（3840×2160）下测试通过
   - 键位映射：可保持默认，脚本不依赖 PlayCover 键位
4. 启动一次游戏，登录账号，完成游戏资源下载，把游戏文字语言设为**简体中文**
5. 游戏内建议：「自动战斗」保持记忆开启；关闭会打断操作的弹窗/通知

### 2. 安装 Python 环境

```bash
# 没有 Homebrew 的话先装：https://brew.sh
brew install uv git
```

### 3. 下载本项目并安装依赖

```bash
git clone https://github.com/luoxia001/March7thAssistant-macOS.git
```

```bash
cd March7thAssistant-macOS && uv sync
```

`uv sync` 会自动下载 Python 3.12 并在项目目录创建 `.venv`。

### 4. 生成桌面图标（可选）

```bash
bash tools/macos/make_app.sh
```

桌面会出现「三月七小助手.app」，双击即可打开图形界面。可以传入其他目录作为参数，例如 `bash tools/macos/make_app.sh /Applications`。

> 项目目录移动后需要重新执行一次这个脚本。

## 启动和使用

1. 打开 PlayCover，启动星穹铁道（也可以交给脚本启动），进入游戏主界面
2. 启动小助手（任选其一）：
   - 双击桌面「三月七小助手.app」
   - 命令行：`uv run app.py`（图形界面）
   - 命令行：`uv run main.py`（直接按配置执行一键日常，无界面）
3. macOS 上会**自动启用 PlayCover 模式**（相当于配置里 `playcover_enable: True`），首次运行会从 `assets/config/config.example.yaml` 生成 `config.yaml`
4. 在图形界面里设置要执行的任务，或直接编辑 `config.yaml`。macOS 相关配置项：

   ```yaml
   playcover_bundle_id: com.HoYoverse.hkrpgoversea # 国服改为 com.miHoYo.hkrpg
   playcover_maatools_host: 127.0.0.1
   playcover_maatools_port: 1717
   forgottenhall_team1_preset: 0 # 忘却之庭用游戏内预设编队（0 表示逐个选角色）
   forgottenhall_team2_preset: 0
   ```

5. 脚本运行时**不需要游戏在前台**，可以去做别的事，但不要用鼠标点击游戏窗口，以免干扰操作
6. 日志在 `logs/` 目录

### 常见问题

- **提示 MaaTools 未连接**：确认用的是 hguandl 分支版 PlayCover，游戏设置里已打开 MaaTools，修改设置后需要重启游戏。可以用 `nc -z 127.0.0.1 1717 && echo ok` 检查端口
- **识别不到界面 / 点错位置**：确认宽高比是 16:9、游戏语言是简体中文。移动端模板缩放比例会自动学习并记录到 `assets/mobile/learned_scales.json`
- **调整移动端适配**：区域、坐标、模板阈值都在 `assets/mobile/profile.yaml`，iOS 专用模板放在 `assets/mobile/images/`（与 `assets/images/` 同路径即可覆盖）

## 致谢

- [moesnow/March7thAssistant](https://github.com/moesnow/March7thAssistant) 及其所有贡献者：本项目的全部基础
- [hguandl/PlayCover](https://github.com/hguandl/PlayCover)：提供 MaaTools 截图和触控接口
- [PlayCover](https://github.com/PlayCover/PlayCover)

## 免责声明

本项目仅供学习交流，与 miHoYo / HoYoverse 无关。使用自动化脚本可能违反游戏用户协议，风险由使用者自行承担。

---

<details>
<summary>以下为原项目 README</summary>

<div align="center">
  <h1 align="center">
    <img src="./assets/screenshot/March7th.png" width="200">
    <br/>
    March7thAssistant
  </h1>
  <a href="https://trendshift.io/repositories/3892" target="_blank"><img src="https://trendshift.io/api/badge/repositories/3892" alt="moesnow%2FMarch7thAssistant | Trendshift" style="width: 200px; height: 46px;" width="250" height="46"/></a>
</div>

<br/>

<div align="center">
🌟 点一下右上角的 Star，GitHub 主页就能收到软件更新通知了哦~
</div>

<div align="center">
    <img src="assets/screenshot/star.gif" alt="Star" width="186" height="60">
</div>

<br/>

<div align="center">

**简体中文** | [繁體中文](./README_TW.md) | [English](./README_EN.md) | [日本語](./README_JA.md) | [한국어](./README_KR.md)

快速上手，请访问：[使用教程](https://m7a.top/#/assets/docs/Tutorial)

遇到问题，请在提问前查看：[FAQ](https://m7a.top/#/assets/docs/FAQ)

</div>

## 功能简介

- **日常**：清体力、每日实训、领取奖励、委托、锄大地
- **周常**：历战余响、模拟宇宙、差分宇宙、货币战争、混沌回忆、虚构叙事、末日幻影
- **云·星穹铁道**：支持后台运行、无窗口运行和 [Docker](https://m7a.top/#/assets/docs/Docker) 运行
- **抽卡记录导出**：支持 [UIGF](https://uigf.org/zh/standards/uigf.html)/[SRGF](https://uigf.org/zh/standards/srgf.html) 标准
- **工具箱**：自动对话、解锁帧率、兑换码、触屏模式
- 每日实训等任务的完成情况支持**消息推送**
- 任务刷新或体力恢复到指定值后**自动启动**
- 任务完成后**声音提示、自动关闭游戏或关机等**

详情见图形界面设置或 [配置文件](assets/config/config.example.yaml)｜QQ群 [点击跳转](https://qm.qq.com/q/C3IryUWCQw)｜TG群 [点击跳转](https://t.me/+ZgH5zpvFS8o0NGI1)｜哔哩哔哩 [点击跳转](https://space.bilibili.com/3706960664857075)

## 界面展示

![README](assets/screenshot/README.png)

## 注意事项

- 遇到错误请在 [Issue](https://github.com/moesnow/March7thAssistant/issues) 反馈，提问讨论可以在 [Discussions](https://github.com/moesnow/March7thAssistant/discussions) ，群聊随缘看
- 欢迎 [PR](https://github.com/moesnow/March7thAssistant/pulls)，提交前请先阅读 [贡献指南](CONTRIBUTING.md)

## 下载安装

前往 [Releases](https://github.com/moesnow/March7thAssistant/releases/latest) 下载后解压双击三月七图标的 `March7th Launcher.exe` 打开图形界面

## 源码运行

如果你是完全不懂的小白，请通过上面的方式下载安装，可以不用往下看了。

需要 Python 3.12 或更高版本。

Windows 下如果通过终端启动，建议使用管理员模式打开 PowerShell、Windows Terminal 或 CMD；Windows 11 24H2 及以上也可以按 [Sudo for Windows](https://learn.microsoft.com/zh-cn/windows/advanced-settings/sudo/) 的方式执行。

```cmd
# 安装（推荐使用虚拟环境）
git clone --recurse-submodules https://github.com/moesnow/March7thAssistant
cd March7thAssistant
pip install -r requirements.txt

# 启动图形界面
python app.py

# 执行完整运行（查看全部子命令：python main.py -h）
python main.py

# 更新
git pull
git submodule update --init --recursive
```

如果使用 `uv`，推荐直接使用项目自带的 `pyproject.toml` 工作流：

```cmd
# 安装（使用 uv）
git clone --recurse-submodules https://github.com/moesnow/March7thAssistant
cd March7thAssistant
uv sync

# 启动图形界面
uv run python app.py

# 查看命令行帮助
uv run python main.py -h

# 执行完整运行
uv run python main.py

# 执行每日实训
uv run python main.py daily
```

<details>
<summary>开发相关</summary>

获取 crop 参数表示的裁剪坐标，可以通过小助手工具箱内「游戏截图」卡片的「捕获」功能

</details>

---

如果喜欢本项目，可以微信赞赏送作者一杯咖啡☕

您的支持就是作者开发和维护项目的动力🚀

![sponsor](assets/app/images/sponsor.jpg)

---

## 相关项目

March7thAssistant 离不开以下开源项目和运行时依赖的帮助，感谢所有维护者与贡献者：

- 模拟宇宙自动化 [https://github.com/CHNZYX/Auto_Simulated_Universe](https://github.com/CHNZYX/Auto_Simulated_Universe) ：提供模拟宇宙相关能力
- 锄大地自动化 [https://github.com/linruowuyin/Fhoe-Rail](https://github.com/linruowuyin/Fhoe-Rail) ：提供锄大地相关能力
- OCR 文字识别 [https://github.com/RapidAI/RapidOCR](https://github.com/RapidAI/RapidOCR) ：提供游戏内文字识别能力
- 图形界面组件库 [https://github.com/zhiyiYo/PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) ：提供主要界面组件与交互体验
- Mirror酱 [https://github.com/MirrorChyan/docs](https://github.com/MirrorChyan/docs) ：提供更新检查与下载分发以及 CDN 加速相关能力
- 图像处理与自动化相关依赖 `OpenCV`、`PyAutoGUI` 等：提供截图采集、图像处理与基础自动化能力
- 推理加速相关依赖 `ONNX Runtime`、`OpenVINO` ：为 OCR 和模型推理提供 CPU / GPU 加速支持

此外，`requirements.txt` 中还包含大量底层依赖，在这里不一一列出；同样感谢这些项目对本项目的支持。


## Contributors
<a href="https://github.com/moesnow/March7thAssistant/graphs/contributors">

  <img src="https://contrib.rocks/image?repo=moesnow/March7thAssistant" />

</a>

## Stargazers over time

<a href="https://star-history.dera.page/#moesnow/March7thAssistant">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://star-history.dera.page/svg?repos=moesnow/March7thAssistant&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://star-history.dera.page/svg?repos=moesnow/March7thAssistant" />
   <img alt="Star History Chart" src="https://star-history.dera.page/svg?repos=moesnow/March7thAssistant" />
 </picture>
</a>

</details>

<div align="center">

# March7thAssistant for macOS (PlayCover iOS port)

[简体中文](./README.md) | **English**

</div>

> [!IMPORTANT]
> This repository is an **unofficial macOS port** of [moesnow/March7thAssistant](https://github.com/moesnow/March7thAssistant).
> All core features come from the original project by moesnow and its contributors. This fork only adds support for driving the **iOS version** of Honkai: Star Rail running in PlayCover on macOS.
> Released under the original [GPL-3.0](./LICENSE) license. Please report macOS issues **here**, not to the upstream project.

## What was ported

The original drives the PC client through Win32 screenshots and keyboard/mouse. There is no PC client on macOS, so this port drives the **iOS client** running in [PlayCover](https://github.com/hguandl/PlayCover):

- **Screenshots / touch** via the MaaTools service built into the hguandl fork of PlayCover (default port 1717). The game does not need to be in the foreground.
- **Keys → touches**: key presses used by the scripts (WASD, E, F, Esc, number keys…) are translated into taps and joystick swipes (`module/automation/playcover_input.py`).
- **Mobile UI adaptation** (`module/mobile` + `assets/mobile/`): multi-scale matching of PC templates, iOS-specific templates where needed, and remapped regions / coordinates / scrolling. Task logic is mostly unchanged.
- **Desktop launcher**: `tools/macos/make_app.sh` creates a `三月七小助手.app`.

### Tested features

| Feature | Status |
| --- | --- |
| Launch / login / claim rewards | ✅ |
| Trailblaze Power (calyx, auto battle) | ✅ |
| Daily Training (incl. activity rewards) | ✅ |
| Forgotten Hall / Memory of Chaos (supports team presets) | ✅ |
| Apocalyptic Shadow | ✅ |
| Currency Wars | ✅ (default strategy) |
| Divergent Universe | ✅ |
| Pure Fiction | 🚧 partially adapted |
| Redemption codes | ⛔ no in-game entry on iOS, skipped |
| Simulated Universe, world farming, warp export… | ❌ not adapted |

## Requirements

| Item | Requirement |
| --- | --- |
| Mac | Apple Silicon (M1 or later) |
| macOS | 14 or later (developed on macOS 27 / Apple M4) |
| PlayCover | **hguandl fork** with MaaTools, tested `4.0.0.maa`: <https://github.com/hguandl/PlayCover/releases>. Official PlayCover lacks MaaTools and will not work |
| Game | Honkai: Star Rail iOS. Tested on global `com.HoYoverse.hkrpgoversea` with **Simplified Chinese** game text; CN server is `com.miHoYo.hkrpg` |
| Python | 3.12+ |
| uv | <https://docs.astral.sh/uv/> |
| Git | included in Xcode Command Line Tools |

## Setup

1. Install the hguandl fork of PlayCover, then install the Star Rail IPA into it (see the [PlayCover docs](https://docs.playcover.io/) for obtaining IPAs).
2. In PlayCover, right-click the game → Settings:
   - **MaaTools: on, port `1717` (required)**
   - Aspect ratio **16:9**; tested at 4K (3840×2160)
3. Launch the game once, log in, finish downloading resources, and set the game text language to **Simplified Chinese**.
4. Install tools and the project:

```bash
brew install uv git
```

```bash
git clone https://github.com/luoxia001/March7thAssistant-macOS.git
```

```bash
cd March7thAssistant-macOS && uv sync
```

5. Optional desktop icon:

```bash
bash tools/macos/make_app.sh
```

## Usage

- Double-click `三月七小助手.app`, or run `uv run app.py` (GUI) / `uv run main.py` (headless one-click daily).
- PlayCover mode is enabled automatically on macOS. `config.yaml` is generated from `assets/config/config.example.yaml` on first run. macOS options: `playcover_bundle_id`, `playcover_maatools_host`, `playcover_maatools_port`, `forgottenhall_team1_preset`, `forgottenhall_team2_preset`.
- The game can stay in the background; just don't click inside the game window while a task runs. Logs are in `logs/`.
- Mobile adaptation (regions, coordinates, thresholds) lives in `assets/mobile/profile.yaml`; iOS templates in `assets/mobile/images/` override `assets/images/` at the same path.

## Acknowledgements

- [moesnow/March7thAssistant](https://github.com/moesnow/March7thAssistant) and all its contributors
- [hguandl/PlayCover](https://github.com/hguandl/PlayCover) for MaaTools
- [PlayCover](https://github.com/PlayCover/PlayCover)

## Disclaimer

For learning purposes only; not affiliated with miHoYo / HoYoverse. Automation may violate the game's terms of service — use at your own risk.

---

<details>
<summary>Original upstream README</summary>

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
🌟 Click the Star in the upper-right corner to get update notifications for this project on GitHub.
</div>

<div align="center">
    <img src="assets/screenshot/star.gif" alt="Star" width="186" height="60">
</div>

<br/>

<div align="center">

[简体中文](./README.md) | [繁體中文](./README_TW.md) | **English** | [日本語](./README_JA.md) | [한국어](./README_KR.md)

**This document was translated from the Simplified Chinese version using AI. Last updated: 2026-09-24. If anything differs, the Simplified Chinese version takes precedence.**

**The in-game language currently supports Simplified Chinese only.**

Quick start: [Tutorial](https://m7a.top/#/assets/docs/Tutorial_en_US)

Before asking for help, please check: [FAQ](https://m7a.top/#/assets/docs/FAQ_en_US)

</div>

## Feature Overview

- **Daily**: Spend Trailblaze Power, Daily Training, claim rewards, dispatch, field farming
- **Weekly**: Echo of War, Simulated Universe, Divergent Universe, Currency Wars, Memory of Chaos, Pure Fiction, Apocalyptic Shadow
- **Cloud Honkai: Star Rail**: Supports background execution, headless execution, and [Docker](https://m7a.top/#/assets/docs/Docker) deployment
- **Gacha record export**: Supports the [UIGF](https://uigf.org/zh/standards/uigf.html) / [SRGF](https://uigf.org/zh/standards/srgf.html) standards
- **Toolbox**: Auto dialogue, FPS unlock, redemption codes, touch mode
- Task results such as Daily Training support **push notifications**
- Supports **automatic start** after task refresh or when Trailblaze Power recovers to a specified value
- Supports **sound alerts, automatic game exit, shutdown, and more** after tasks finish

For details, see the GUI settings or the [configuration file](assets/config/config.example.yaml) | QQ group [Join here](https://qm.qq.com/q/C3IryUWCQw) | TG group [Join here](https://t.me/+ZgH5zpvFS8o0NGI1) | Bilibili [Visit here](https://space.bilibili.com/3706960664857075)

## Interface Preview

![README](assets/screenshot/README.png)

## Notes

- If you encounter problems, please report them in [Issues](https://github.com/moesnow/March7thAssistant/issues). Questions and discussions belong in [Discussions](https://github.com/moesnow/March7thAssistant/discussions). Chat groups are checked only occasionally.
- Pull requests are welcome. Please read the [contribution guide](CONTRIBUTING.md) before submitting.

## Download and Installation

Download the latest release from [Releases](https://github.com/moesnow/March7thAssistant/releases/latest), extract it, and double-click `March7th Launcher.exe` with the March 7th icon to open the GUI.

## Running from Source

If you are completely new to this, use the packaged release above. You can ignore the rest of this section.

Python 3.12 or newer is required.

On Windows, if you launch from a terminal, it is recommended to open PowerShell, Windows Terminal, or CMD as Administrator. On Windows 11 24H2 or later, you can also use [Sudo for Windows](https://learn.microsoft.com/zh-cn/windows/advanced-settings/sudo/).

```cmd
# Installation (using venv is recommended)
git clone --recurse-submodules https://github.com/moesnow/March7thAssistant
cd March7thAssistant
pip install -r requirements.txt

# Launch the GUI
python app.py

# Run the full workflow (see all subcommands: python main.py -h)
python main.py

# Update
git pull
git submodule update --init --recursive
```

If you use `uv`, it is recommended to use the built-in `pyproject.toml` workflow directly:

```cmd
# Installation (using uv)
git clone --recurse-submodules https://github.com/moesnow/March7thAssistant
cd March7thAssistant
uv sync

# Launch the GUI
uv run python app.py

# Show CLI help
uv run python main.py -h

# Run the full workflow
uv run python main.py

# Run Daily Training
uv run python main.py daily
```

<details>
<summary>Development Notes</summary>

To obtain the crop coordinates used by crop parameters, use the "Capture" button on the "Game Screenshot" card in the toolbox.

</details>

---

If you like this project, you can support the author with a coffee via WeChat ☕

Your support helps keep the project developed and maintained.

![sponsor](assets/app/images/sponsor.jpg)

---

## Related Projects

March7thAssistant depends on the following open-source projects and runtime dependencies. Thanks to all maintainers and contributors.

- Simulated Universe automation [https://github.com/CHNZYX/Auto_Simulated_Universe](https://github.com/CHNZYX/Auto_Simulated_Universe): provides Simulated Universe related capabilities
- Field farming automation [https://github.com/linruowuyin/Fhoe-Rail](https://github.com/linruowuyin/Fhoe-Rail): provides field farming related capabilities
- OCR text recognition [https://github.com/RapidAI/RapidOCR](https://github.com/RapidAI/RapidOCR): provides in-game text recognition
- GUI component library [https://github.com/zhiyiYo/PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets): provides the main interface components and interaction experience
- MirrorChyan [https://github.com/MirrorChyan/docs](https://github.com/MirrorChyan/docs): provides update checking, download distribution, and CDN acceleration related capabilities
- Image processing and automation related dependencies `OpenCV`, `PyAutoGUI`, and others: provide screenshot capture, image processing, and foundational automation capabilities
- Inference acceleration related dependencies `ONNX Runtime`, `OpenVINO`: provide CPU / GPU acceleration for OCR and model inference

Additionally, `requirements.txt` contains many lower-level dependencies that are not listed one by one here. Thanks as well to those projects for supporting this project.

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

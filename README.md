# WeChatDigestWindows

[中文说明](./README.zh-CN.md) | [Security](./SECURITY.md)

WeChatDigestWindows is a Windows-first local tool for turning WeChat chat history into structured Markdown summaries with either a CLI or a desktop GUI.

## What This Repo Contains

- `digest.py`: main workflow engine and CLI
- `run_gui.py`: desktop app entry point
- `src/wechat_digest_app/backend.py`: thin adapter layer for the GUI
- `src/wechat_digest_app/gui.py`: PySide6 desktop shell
- `src/wechat_digest_app/vendor/wechat_digest/`: vendored helper code for DB detection, decryption, and key scanning
- `tests/`: smoke and regression coverage

## What This Repo Does Not Contain

- decrypted databases
- real chat exports or real summaries
- `.env` files with real values
- `%USERPROFILE%\\.wechat-digest\\*.json`
- local machine paths, chatroom IDs, or keys
- local build output such as `build/` and `dist/`
- local runtime folders such as `output/` and `wetrace-bin`
- historical archive snapshots that are only useful on one machine

## Quick Start

Install dependencies:

```powershell
pip install -r requirements.txt
```

Launch the GUI:

```powershell
python run_gui.py
```

Use the CLI:

```powershell
python digest.py groups
python digest.py groups --dm
python digest.py summarize "Example Group" 2026-04-16
```

## Local Runtime State

Personal runtime state stays outside the repository:

- `%USERPROFILE%\\.wechat-digest\\config.json`
- `%USERPROFILE%\\.wechat-digest\\llm_config.json`
- `%USERPROFILE%\\.wechat-digest\\all_keys.json`
- `%USERPROFILE%\\.wechat-digest\\output\\`

The local companion folder for this machine is:

- `E:\\微信群聊总结.local-state`

## Verification

```powershell
python -m unittest discover -s tests -p "test_*.py"
$env:QT_QPA_PLATFORM="offscreen"
python run_gui.py --smoke-test
```

## Build

```powershell
pip install pyinstaller
pyinstaller --noconfirm app.spec
```

Read [SECURITY.md](./SECURITY.md) before publishing anything.

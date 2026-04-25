# WeChatDigestWindows

[中文说明](./README.zh-CN.md) | [Public Repo Scope](./PUBLIC_REPO_SCOPE.md) | [Architecture](./ARCHITECTURE.md) | [Security](./SECURITY.md) | [Build](./BUILD.md)

Windows-first local tool for turning WeChat chat history into structured Markdown summaries with either a CLI or a desktop GUI.

## What This Repo Includes

- `digest.py`: the main workflow engine and CLI
- `run_gui.py`: desktop app entry point
- `src/wechat_digest_app/backend.py`: thin adapter layer for the GUI
- `src/wechat_digest_app/gui.py`: PySide6 desktop shell
- `src/wechat_digest_app/vendor/wechat_digest/`: vendored helper code for DB detection, decryption, and key scanning

## Public Repo Safety

This repository is intended to be publishable.

It should contain:

- source code
- tests
- sanitized examples
- build and contribution docs
- vendored third-party code with preserved attribution

It should not contain:

- decrypted databases
- generated chat reports from real conversations
- `.env` files with real values
- `%USERPROFILE%\\.wechat-digest\\*.json`
- local inspection dumps or screenshots from private data
- build output folders such as `build/` or `dist/`

Read [SECURITY.md](./SECURITY.md) before pushing anything public.

## Quick Start

### 1. Install dependencies

```powershell
pip install -r requirements.txt
```

### 2. Keep personal runtime config outside the repo

The app stores local state under:

- `%USERPROFILE%\\.wechat-digest\\config.json`
- `%USERPROFILE%\\.wechat-digest\\llm_config.json`
- `%USERPROFILE%\\.wechat-digest\\all_keys.json`
- `%USERPROFILE%\\.wechat-digest\\output\\`

Do not copy those files into this repository.

### 3. Launch the GUI

```powershell
python run_gui.py
```

### 4. Or use the CLI

```powershell
python digest.py groups
python digest.py groups --dm
python digest.py summarize "Example Group" 2026-04-16
python digest.py summarize "Example Group" today --since 14:00
python digest.py batch "Example Group" --last-n 7
```

## GUI Scope

The desktop app focuses on the daily workflow:

- set local DB and output paths
- configure provider, model, and API key
- browse groups and direct messages
- run single-day or multi-day summaries
- review generated reports and logs

## Testing

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

GUI smoke test:

```powershell
$env:QT_QPA_PLATFORM="offscreen"
python run_gui.py --smoke-test
```

## Build

```powershell
pip install pyinstaller
pyinstaller --noconfirm app.spec
```

Build notes live in [BUILD.md](./BUILD.md).

## Notes

- Windows is the primary target.
- The GUI intentionally stays thin and reuses the CLI workflow.
- Historical experiments stay under `scripts/archive/` and should be treated as reference material, not the main product surface.

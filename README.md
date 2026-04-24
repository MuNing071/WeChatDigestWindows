# WeChatDigestWindows

Windows-first tool for turning local WeChat chat history into structured daily summaries.

It supports:

- decrypting local WeChat SQLCipher databases
- listing recent groups and direct messages
- fuzzy session matching
- extracting and compacting chat messages
- generating Markdown summaries with an LLM
- using either a CLI or a desktop GUI

## What Changed In This Refactor

This repo is being turned into a cleaner open-source product repo:

- vendored dependency code instead of a nested Git checkout
- GUI entry point in `run_gui.py`
- reusable app code in `src/wechat_digest_app/`
- local runtime data and personal outputs removed from version control
- Windows desktop packaging under the product name `WeChatDigestWindows`

## Quick Start

### 1. Install dependencies

```powershell
pip install -r requirements.txt
```

### 2. Configure local runtime

The app keeps personal config outside the repo:

- `%USERPROFILE%\.wechat-digest\config.json`
- `%USERPROFILE%\.wechat-digest\llm_config.json`
- `%USERPROFILE%\.wechat-digest\all_keys.json`

### 3. Launch the GUI

```powershell
python run_gui.py
```

The GUI now includes:

- language switcher with Chinese default
- setup help and privacy reminders
- provider presets for Doubao, GLM, DeepSeek, OpenAI, OpenRouter, SiliconFlow, Ollama, and Custom
- group and DM browsing
- single-day and multi-day summary runs

### 4. Or use the CLI

```powershell
python digest.py groups
python digest.py groups --dm
python digest.py summarize "ai 实践" 2026-04-16
python digest.py summarize "ai 实践" today --since 14:00
python digest.py batch "ai 实践" --last-n 7
```

## Main Commands

```powershell
python digest.py groups
python digest.py groups --dm
python digest.py extract "群名" 2026-04-15 --json
python digest.py summarize "群名" 2026-04-15
python digest.py summarize "群名" today --since 14:00
python digest.py summarize "群名" --segment
python digest.py batch "群名" --last-n 7
python digest.py decrypt
python digest.py test-api
python digest.py config --show
```

## GUI Scope

The desktop GUI focuses on the practical daily workflow:

- set local paths and LLM settings
- detect DB directory
- decrypt local databases
- browse groups and DMs by readable names
- run summaries with common options
- summarize a single day or a date range
- inspect reports and logs

## Repo Layout

```text
.
|-- digest.py
|-- run_gui.py
|-- src/
|   `-- wechat_digest_app/
|       |-- backend.py
|       |-- gui.py
|       `-- vendor/
|-- tests/
|-- examples/
|-- ARCHITECTURE.md
|-- BUILD.md
|-- CONTRIBUTING.md
|-- SECURITY.md
`-- OPEN_SOURCE_GUI_REFACTOR_PLAN.md
```

## Privacy And Safety

Do not commit:

- decrypted databases
- personal chat outputs
- `.env` files with keys or machine paths
- `%USERPROFILE%\.wechat-digest\` runtime config files
- screenshots or examples containing private conversations

Read [SECURITY.md](./SECURITY.md) before publishing or contributing.

## Testing

Smoke tests:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

The GUI smoke test uses Qt offscreen mode and does not require personal config.

## Build A Windows App

```powershell
pip install pyinstaller
pyinstaller --noconfirm app.spec
```

Build notes live in [BUILD.md](./BUILD.md).

## Notes

- Windows is the primary target for now.
- The desktop GUI is intentionally a thin wrapper around the same core workflow as the CLI.
- Historical research and archive material remains under `scripts/archive/`.

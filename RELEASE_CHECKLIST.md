# Release Checklist

## Product Name

- App name: `WeChatDigestWindows`
- GUI entry: `python run_gui.py`
- Windows package: `dist/WeChatDigestWindows/WeChatDigestWindows.exe`

## What Was Updated

- GUI now includes a language selector and defaults to Chinese
- Setup includes quick-start guidance and privacy reminders
- Provider presets include Doubao, GLM, DeepSeek, OpenAI, OpenRouter, SiliconFlow, Ollama, and Custom
- Workbench shows readable DM names instead of raw IDs when contact info is available
- Workbench supports both single-day and multi-day summary runs
- Repo docs and build output use the `WeChatDigestWindows` name

## Validation Completed

- `python -m compileall digest.py src run_gui.py`
- `python -m unittest discover -s tests -p "test_*.py"`
- `python digest.py groups --json`
- `python digest.py groups --dm --json`
- `python digest.py test-api`
- `python digest.py summarize "ai 实践" 2026-04-16 -o output\\_product_smoke\\2026-04-16.md`
- backend multi-day summary run for `2026-04-15` to `2026-04-16`
- `pyinstaller --noconfirm app.spec`
- `dist/WeChatDigestWindows/WeChatDigestWindows.exe --smoke-test` in offscreen mode

## Privacy Check Before Publishing

Confirm these are not tracked:

- `output/`
- `wetrace-bin/`
- `wechat-digest/`
- `.workbuddy/`
- any `.env` file
- any decrypted `.db` file
- `%USERPROFILE%\.wechat-digest\*.json`

## Recommended Publish Flow

1. Review `git status`
2. Confirm docs read well:
   - `README.md`
   - `ARCHITECTURE.md`
   - `SECURITY.md`
   - `BUILD.md`
3. Commit the open-source packaging changes on `codex/open-source-gui-packaging`
4. Push branch and open a draft PR
5. Create a GitHub release only after one more manual double-click test of `WeChatDigestWindows.exe`

## Release Assets To Consider

- source code zip from GitHub
- `dist/WeChatDigestWindows/WeChatDigestWindows.exe`
- short release notes highlighting:
  - Windows GUI
  - Chinese-first setup
  - DM name resolution
  - multi-day summaries
  - local-data privacy expectations

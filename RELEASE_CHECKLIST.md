# Release Checklist

## Product Identity

- App name: `WeChatDigestWindows`
- GUI entry: `python run_gui.py`
- Windows package: `dist/WeChatDigestWindows/WeChatDigestWindows.exe`

## Release Readiness

- README has both English and Chinese entry points
- screenshots, if any, are redacted or synthetic
- examples do not contain real names, IDs, or message content
- `SECURITY.md` reflects current publishing rules
- `BUILD.md` still matches the real packaging flow

## Validation

- `python -m compileall digest.py src run_gui.py`
- `python -m unittest discover -s tests -p "test_*.py"`
- `python digest.py groups --json`
- `python digest.py groups --dm --json`
- `python digest.py test-api`
- `python run_gui.py --smoke-test`
- `pyinstaller --noconfirm app.spec`
- `dist/WeChatDigestWindows/WeChatDigestWindows.exe --smoke-test`

Use synthetic names in any manual validation notes, for example `示例群聊` or `Example Group`.

## Privacy Review

Confirm these are not tracked:

- `output/`
- `wetrace-bin/`
- `.workbuddy/`
- any `.env` file
- any decrypted `.db` file
- `%USERPROFILE%\\.wechat-digest\\*.json`
- local inspection dumps such as `scripts/inspect/*.local.txt`

## Suggested Publish Flow

1. Review `git status`.
2. Re-read `README.md`, `README.zh-CN.md`, `SECURITY.md`, and `BUILD.md`.
3. Run the validation commands above.
4. Do one manual open of the GUI build with synthetic or local-only data.
5. Publish only after confirming the repo still contains no user data.

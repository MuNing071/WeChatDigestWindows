# Build

## Local Windows Build

Install dependencies:

```powershell
pip install -r requirements.txt
pip install pyinstaller
```

Build the desktop app:

```powershell
pyinstaller --noconfirm app.spec
```

Expected output:

- `dist/WeChatDigestWindows/WeChatDigestWindows.exe`

## Smoke Test The Built App

```powershell
$env:QT_QPA_PLATFORM="offscreen"
.\dist\WeChatDigestWindows\WeChatDigestWindows.exe --smoke-test
```

## Build Notes

- The build is Windows-first.
- Personal runtime state and default report output live in `%USERPROFILE%\\.wechat-digest\\`.
- `app.spec` resolves files relative to the repository location, not the shell working directory.
- Do not ship private DBs, outputs, `.env` files, or local config JSON files inside release bundles.

## Recommended Release Bundle

- executable folder from `dist/WeChatDigestWindows/`
- README
- SECURITY note
- changelog or release notes

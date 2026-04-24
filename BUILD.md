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

Output:

- `dist/WeChatDigestWindows/WeChatDigestWindows.exe`

## Smoke Test The Built App

```powershell
$env:QT_QPA_PLATFORM="offscreen"
.\dist\WeChatDigestWindows\WeChatDigestWindows.exe --smoke-test
```

## Notes

- The build is Windows-first.
- Personal runtime config still lives in `%USERPROFILE%\.wechat-digest\`.
- Do not bundle private DBs, outputs, or `.env` files into releases.

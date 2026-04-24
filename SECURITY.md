# Security

## Supported Use

This project works with highly sensitive local user data.

That includes:

- private chat history
- local database paths
- decryption keys
- model API keys

## Never Commit These

- `%USERPROFILE%\\.wechat-digest\\all_keys.json`
- `%USERPROFILE%\\.wechat-digest\\config.json` if it contains personal paths you do not want public
- `%USERPROFILE%\\.wechat-digest\\llm_config.json`
- any `.env` file with real values
- any decrypted `.db` file
- generated summaries containing private data
- screenshots of private chats unless intentionally redacted

## Publishing Checklist

Before pushing a branch publicly:

1. Run `git status`
2. Confirm `output/` is not tracked
3. Confirm `wetrace-bin/` runtime data is not tracked
4. Confirm no `.env` file is tracked
5. Confirm no private keys or local machine paths appear in docs or examples

## Disclosure

If you discover a data exposure risk in this repo layout or code path, do not post it with live secrets or live user data. Open a private report with a redacted reproduction.


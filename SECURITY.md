# Security

## Scope

This project works with highly sensitive local data.

That includes:

- private chat history
- local database paths
- database decryption keys
- model API keys
- generated summaries derived from private conversations

## Never Commit These

- `%USERPROFILE%\\.wechat-digest\\all_keys.json`
- `%USERPROFILE%\\.wechat-digest\\config.json`
- `%USERPROFILE%\\.wechat-digest\\llm_config.json`
- any `.env` file with real values
- any decrypted `.db` file
- any report generated from real chats
- local inspection dumps under `scripts/inspect/`
- screenshots that reveal private names, messages, or IDs
- build output folders such as `build/` and `dist/`

## Public Repo Review

Before pushing a branch publicly, check:

1. `git status` is clean except for intentional source changes.
2. No local runtime folders are tracked: `output/`, `wetrace-bin/`, `.workbuddy/`.
3. No machine-local config files are tracked.
4. No docs contain real paths, real chatroom IDs, or copied secrets.
5. Examples and screenshots are synthetic or fully redacted.

## Safer Documentation Practice

- Use `Example Group`, `示例群聊`, or similar placeholder names.
- Use `%USERPROFILE%` or `<your-path>` instead of real local paths.
- Mask keys as `abc123...` only when showing format.
- Do not paste database keys, even in historical handoff notes.

## Reporting

If you discover a privacy or exposure issue, report it privately with redacted evidence.

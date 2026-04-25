# Security

This project works with highly sensitive local data.

## Never Commit

- `%USERPROFILE%\\.wechat-digest\\all_keys.json`
- `%USERPROFILE%\\.wechat-digest\\config.json`
- `%USERPROFILE%\\.wechat-digest\\llm_config.json`
- any `.env` file with real values
- any decrypted `.db` file
- any report generated from real chats
- screenshots that reveal private names, messages, IDs, or paths
- local build and runtime folders such as `build/`, `dist/`, `output/`, and `wetrace-bin`

## Public Repo Rule

If a file is only needed to run on one machine, inspect one private dataset, or
remember one local environment, keep it outside the repository.

## Safer Documentation Practice

- Use `Example Group` or `示例群聊`
- Use `%USERPROFILE%` or `<your-path>` instead of real local paths
- Never paste real database keys
- Never paste real API keys

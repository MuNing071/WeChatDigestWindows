# Public Repo Scope

This repository intentionally separates public source code from local runtime state.

## Keep In The Public Repo

- current product code
- tests
- sanitized examples
- build and security docs
- vendored third-party source with preserved attribution
- archive/reference source snapshots that help explain prior approaches

## Keep Out Of The Public Repo

- local config files
- decrypted databases
- generated summaries from real data
- inspection dumps
- release metadata fetched from upstream APIs
- temporary frontend package manifests that are not part of the tracked archive snapshot
- `__pycache__`, build folders, and other generated artifacts

## Practical Rule

If a file is needed only to run on one machine, to remember one local environment,
or to inspect one private dataset, it should stay outside the public repo.

Recommended local-only companion folder for this checkout:

- `E:\\微信群聊总结.local-state`

## Archive Policy

The `scripts/archive/` folder is reference material only.

- keep source snapshots that are useful for historical context
- do not keep local runtime files beside those snapshots
- do not expand archive folders into active subprojects unless there is a deliberate plan to maintain them

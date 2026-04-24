# Open Source + GUI Refactor Plan

## Goal

Turn this repo into a single-repo, open-source-friendly desktop tool with:

- a clean core pipeline for decrypt -> extract -> summarize
- vendored local dependencies instead of a nested Git dependency
- no tracked private data, keys, or user-specific runtime artifacts
- a GUI layer that wraps the stable core instead of reimplementing logic

## Current Reality

The repo already has a usable product core, but it is still a working project folder rather than a publishable OSS repo.

### What is already good

- `digest.py` is a real unified entry point
- core workflow is already centralized
- config and secrets are mostly designed to live outside the repo
- docs exist and capture a lot of operational knowledge

### What blocks open-source release right now

1. Private runtime data is mixed into the repo
2. `wechat-digest/` is a nested Git dependency
3. `wetrace-bin/` contains machine-specific runtime material
4. historical/archive/reference material is mixed with production code
5. GUI boundaries are not yet explicit in the code structure

## Architecture Read

### Current layers

1. Entry layer
   - `digest.py`

2. Low-level capability layer
   - `wechat-digest/crypto/`
   - selected helper scripts inside `wechat-digest/`

3. Runtime/data/tooling layer
   - `wetrace-bin/`
   - `output/`
   - `scripts/`
   - `.workbuddy/`

### Practical interpretation

The real product is not "all scripts in the repo". The product is:

`digest.py` + decrypt/config helpers + runtime integration + output conventions

That means the GUI should wrap a service boundary derived from `digest.py`, not wrap every old script.

## Decisions For This Refactor

### 1. Vendor to single repo

Adopt `wechat-digest/` into this repo as vendored source code rather than keeping it as a nested Git dependency.

Preferred end state:

- remove nested Git metadata under `wechat-digest/`
- keep source code, license, and attribution
- move only the code we still need into a first-party internal module layout

### 2. Keep `digest.py` behavior stable first

Before GUI work, preserve CLI behavior as the compatibility surface.

Short-term rule:

- CLI remains the reference interface
- GUI calls the same service functions used by CLI

### 3. Separate product code from local runtime artifacts

The published repo should not carry:

- decrypted DBs
- user outputs
- machine paths
- DB keys
- local `.env` with real values

### 4. Keep archive/reference code, but quarantine it

Not everything old must be deleted. Some of it is useful operational memory.

But it should move behind a clear boundary such as:

- `archive/`
- `docs/research/`
- `tools/debug/`

## Target Repo Shape

Proposed target structure:

```text
repo/
├─ app/
│  ├─ cli/
│  │  └─ main.py
│  ├─ core/
│  │  ├─ config_service.py
│  │  ├─ contact_service.py
│  │  ├─ session_service.py
│  │  ├─ extract_service.py
│  │  ├─ summarize_service.py
│  │  └─ output_service.py
│  ├─ providers/
│  │  └─ llm/
│  └─ vendor/
│     └─ wechat_digest/
├─ gui/
│  ├─ desktop/
│  └─ assets/
├─ tools/
│  ├─ debug/
│  ├─ inspect/
│  └─ migration/
├─ docs/
│  ├─ architecture/
│  ├─ security/
│  └─ usage/
├─ examples/
├─ tests/
├─ digest.py
├─ README.md
└─ LICENSE
```

Notes:

- We can keep `digest.py` at repo root during transition and make it a thin compatibility wrapper.
- We do not need to reach this final structure in one jump.

## Refactor Phases

## Phase 0: Safety and repo hygiene

Goal: make the branch safe to continue on.

Tasks:

- expand `.gitignore` to cover local runtime files more completely
- identify tracked sensitive files and remove them from version control
- move or delete real outputs and machine-local runtime artifacts from the repo
- replace real env/config with redacted examples

Important files to review immediately:

- `wetrace-bin/wetrace/.env`
- `output/`
- `wetrace-bin/wetrace/data/`
- any checked-in report, JSON, or cache file with user data

Deliverable:

- a repo that can be pushed without leaking keys or personal data

## Phase 1: Vendor and normalize dependencies

Goal: remove nested-repo coupling.

Tasks:

- copy or adopt required code from `wechat-digest/` into a first-party location
- preserve upstream attribution and original license text
- decide what stays vendored vs what gets rewritten locally
- remove submodule/nested Git dependency behavior

Expected keepers:

- `crypto/config.py`
- `crypto/decrypt.py`
- key scanning code if still needed

Expected optional pieces:

- voice transcription helpers
- article tools
- legacy standalone scripts

Deliverable:

- one repo clone is enough to run core functionality

## Phase 2: Extract service boundaries from `digest.py`

Goal: make GUI integration clean.

Tasks:

- split `digest.py` logic into importable services
- keep command parsing separate from business logic
- standardize return values and error objects
- make long-running operations report progress in a GUI-friendly way

Suggested service split:

- config/bootstrap
- group and contact resolution
- raw row extraction
- message parsing and compaction
- summarization orchestration
- output writing

Deliverable:

- GUI can call Python functions directly without shelling out to ad hoc CLI commands

## Phase 3: Define the GUI MVP

Goal: build the smallest usable desktop experience.

Recommended MVP screens:

1. Setup
   - detect data path
   - configure API key/provider/model
   - verify environment

2. Session browser
   - list groups and DMs
   - fuzzy search
   - recent activity

3. Run summary
   - date picker
   - options: compact/full, segment, since, batch mode
   - output path preview

4. Result view
   - show generated markdown
   - open output folder
   - rerun with same settings

5. Diagnostics
   - config summary
   - dependency checks
   - latest logs/errors

## Phase 4: OSS packaging

Goal: make it understandable and runnable by strangers.

Tasks:

- rewrite README around product use, not project history
- add install/run guide for Windows first
- add `SECURITY.md`
- add `CONTRIBUTING.md`
- add example config/env files
- document legal/privacy expectations clearly

Deliverable:

- public-facing repo with a coherent first-run story

## GUI Technology Direction

Preferred default: Python backend + desktop shell frontend.

Two practical paths:

### Option A: PySide6 / Qt

Pros:

- pure Python stack
- simple packaging for a desktop utility
- easy to call internal services directly

Tradeoff:

- UI polish takes more custom work

### Option B: Tauri + Python backend bridge

Pros:

- modern UI flexibility
- nicer frontend development ergonomics

Tradeoff:

- more moving pieces
- more packaging complexity

Recommendation for this repo now:

- start with PySide6 for the first usable GUI
- only move to a webview-based desktop shell if the product grows beyond utility tooling

## Non-Goals For The First Pass

- no attempt to redesign the summarization logic yet
- no attempt to support every historical script in the GUI
- no cross-platform promise beyond Windows in the first public release
- no deep refactor of Wetrace itself

## Immediate Next Steps

Recommended execution order for the next implementation turn:

1. clean secrets and tracked runtime data
2. tighten `.gitignore`
3. vendor `wechat-digest` into first-party source layout
4. extract `digest.py` into importable services without changing behavior
5. choose GUI stack and scaffold the app shell

## Working Rules For This Branch

- preserve current CLI behavior while refactoring
- do not commit private data even temporarily
- prefer compatibility wrappers over big-bang renames
- treat GUI as a wrapper around stable services, not around shell commands


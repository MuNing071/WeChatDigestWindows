# Architecture

## Product Shape

The product is a local Windows utility with two surfaces:

- CLI: `digest.py`
- desktop GUI: `run_gui.py`

Both are meant to drive the same workflow.

## Core Flow

```text
Local WeChat DB
  -> key discovery / config lookup
  -> SQLCipher decrypt + WAL merge
  -> session lookup
  -> message extraction
  -> noise compression
  -> LLM summary generation
  -> Markdown report output
```

## Main Modules

### `digest.py`

Legacy-compatible orchestrator and CLI entry point.

Key responsibilities:

- config loading
- group resolution
- raw row extraction
- message parsing and compaction
- LLM request orchestration
- file output

### `src/wechat_digest_app/backend.py`

Thin service layer used by the GUI.

It wraps the existing CLI-oriented functions and captures structured results and logs without duplicating workflow logic.

### `src/wechat_digest_app/gui.py`

PySide6 desktop shell for:

- setup
- session browsing
- summary execution
- result/log viewing

### `src/wechat_digest_app/vendor/wechat_digest/`

Vendored dependency code adopted from upstream.

Currently used for:

- DB auto-detection helpers
- SQLCipher decryption
- WAL merge support
- key scanning helpers

## Repo Boundaries

Tracked:

- source code
- tests
- docs
- examples

Ignored:

- personal runtime state
- decrypted data
- `.env`
- generated outputs
- local work memory

## Compatibility Strategy

The refactor keeps `digest.py` as the compatibility surface while moving reusable desktop-facing behavior into importable modules.

That means:

- old command workflows still work
- GUI can evolve without rewriting extraction/summarization logic


import argparse
import contextlib
import datetime as dt
import io
import json
import os
from typing import Any

import digest


APP_NAME = "WeChatDigestWindows"


class BackendError(RuntimeError):
    pass


PROVIDER_PRESETS = {
    "doubao": {
        "label": "豆包 / Doubao",
        "provider": "doubao",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-seed-2-0-lite-260215",
        "recommended": True,
    },
    "glm": {
        "label": "智谱 GLM",
        "provider": "glm",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
        "recommended": False,
    },
    "deepseek": {
        "label": "DeepSeek",
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "recommended": False,
    },
    "openai": {
        "label": "OpenAI",
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "recommended": False,
    },
    "openrouter": {
        "label": "OpenRouter",
        "provider": "openai",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4o-mini",
        "recommended": False,
    },
    "siliconflow": {
        "label": "SiliconFlow",
        "provider": "openai",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "deepseek-ai/DeepSeek-V3",
        "recommended": False,
    },
    "ollama": {
        "label": "Ollama (OpenAI Compatible)",
        "provider": "openai",
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "qwen2.5:latest",
        "recommended": False,
    },
    "custom": {
        "label": "Custom / OpenAI-Compatible",
        "provider": "openai",
        "base_url": "",
        "model": "",
        "recommended": False,
    },
}


def _capture_call(func, *args, **kwargs):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        result = func(*args, **kwargs)
    return result, stdout.getvalue(), stderr.getvalue()


def _load_cfg() -> dict[str, Any]:
    try:
        return digest.load_config()
    except Exception:
        return {}


def _default_output_dir() -> str:
    return os.path.join(digest._SCRIPT_DIR, "output")


def _date_range(start_date: str, end_date: str) -> list[str]:
    start = dt.date.fromisoformat(start_date)
    end = dt.date.fromisoformat(end_date)
    if end < start:
        start, end = end, start
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += dt.timedelta(days=1)
    return dates


def _report_records(output_dir: str, limit: int = 200) -> list[dict[str, Any]]:
    if not output_dir or not os.path.isdir(output_dir):
        return []

    rows: list[dict[str, Any]] = []
    for root, _dirs, files in os.walk(output_dir):
        for name in files:
            if not name.lower().endswith(".md"):
                continue
            path = os.path.join(root, name)
            try:
                stat = os.stat(path)
            except OSError:
                continue
            rows.append(
                {
                    "path": path,
                    "name": name,
                    "title": os.path.splitext(name)[0],
                    "relative_path": os.path.relpath(path, output_dir),
                    "modified_ts": stat.st_mtime,
                    "modified": dt.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "size": stat.st_size,
                }
            )
    rows.sort(key=lambda item: item["modified_ts"], reverse=True)
    return rows[:limit]


def list_provider_presets() -> list[dict[str, Any]]:
    return [{"key": key, **value} for key, value in PROVIDER_PRESETS.items()]


def load_app_state() -> dict[str, Any]:
    cfg = _load_cfg()
    llm_cfg = digest.load_llm_config()
    output_dir = cfg.get("output_dir", _default_output_dir())
    decrypted_dir = cfg.get("decrypted_dir", os.path.join(output_dir, "decrypted"))
    return {
        "app_name": APP_NAME,
        "db_dir": cfg.get("db_dir", ""),
        "decrypted_dir": decrypted_dir,
        "output_dir": output_dir,
        "known_count": len(cfg.get("known", {})),
        "provider": llm_cfg.get("provider", "doubao"),
        "model": llm_cfg.get("model", ""),
        "base_url": llm_cfg.get("base_url", ""),
        "api_key": llm_cfg.get("api_key", ""),
        "batch_endpoint": llm_cfg.get("batch_endpoint", ""),
        "batch_api_key": llm_cfg.get("batch_api_key", ""),
        "language": cfg.get("app", {}).get("language", "zh"),
        "has_decrypted_dir": bool(decrypted_dir and os.path.isdir(decrypted_dir)),
        "report_count": len(_report_records(output_dir, limit=500)),
    }


def detect_db_dir() -> str:
    from wechat_digest_app.vendor.wechat_digest.crypto.config import auto_detect_db_dir

    return auto_detect_db_dir() or ""


def save_app_state(values: dict[str, Any]) -> None:
    cfg = _load_cfg()
    cfg["db_dir"] = values.get("db_dir", "").strip()
    cfg["decrypted_dir"] = values.get("decrypted_dir", "").strip()
    cfg["output_dir"] = values.get("output_dir", "").strip()
    cfg.setdefault("known", {})
    cfg.setdefault("app", {})
    cfg["app"]["language"] = values.get("language", "zh")
    digest.save_config(cfg)

    llm_cfg = digest.load_llm_config()
    llm_cfg.update(
        {
            "provider": values.get("provider", "").strip() or "doubao",
            "model": values.get("model", "").strip(),
            "base_url": values.get("base_url", "").strip(),
            "api_key": values.get("api_key", "").strip(),
            "batch_endpoint": values.get("batch_endpoint", "").strip(),
            "batch_api_key": values.get("batch_api_key", "").strip(),
        }
    )
    os.makedirs(os.path.dirname(digest.LLM_CONFIG_FILE), exist_ok=True)
    with open(digest.LLM_CONFIG_FILE, "w", encoding="utf-8") as fh:
        json.dump(llm_cfg, fh, ensure_ascii=False, indent=2)


def list_sessions(include_dm: bool = False) -> tuple[list[dict[str, Any]], str]:
    args = argparse.Namespace(date=None, json=True, dm=include_dm)
    _, stdout, stderr = _capture_call(digest.cmd_groups, args)
    if not stdout.strip():
        raise BackendError(stderr.strip() or "No session data returned.")
    return json.loads(stdout), stderr


def decrypt_databases() -> tuple[dict[str, Any], str]:
    result, _, stderr = _capture_call(digest.cmd_decrypt, argparse.Namespace())
    return result, stderr


def test_api() -> str:
    _, _, stderr = _capture_call(digest.cmd_test_api, argparse.Namespace())
    return stderr


def output_root() -> str:
    cfg = _load_cfg()
    return cfg.get("output_dir", _default_output_dir())


def list_reports(limit: int = 200) -> list[dict[str, Any]]:
    return _report_records(output_root(), limit=limit)


def read_report(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def preview_output_path(group_name: str, date_str: str, since_text: str = "") -> str:
    cfg = _load_cfg()
    group_username, canonical_name = digest.resolve_group(group_name, db_dir=cfg.get("decrypted_dir", ""))
    if not group_username:
        canonical_name = group_name
    since_min = digest._parse_since(since_text)
    return digest._auto_output_path(canonical_name, date_str, since_min)


def summarize_single(
    group_name: str,
    date_str: str,
    *,
    since_text: str = "",
    segment: bool = False,
    full: bool = False,
    batch_mode: bool = False,
    report_full: bool = False,
    output_path: str | None = None,
) -> dict[str, Any]:
    args = argparse.Namespace(
        group=group_name,
        date=date_str,
        hour_offset=0,
        full=full,
        no_cache=False,
        report_full=report_full,
        prompt=None,
        output=output_path,
        since=since_text or None,
        segment=segment,
        json=False,
        batch_mode=batch_mode,
    )
    summary, stdout, stderr = _capture_call(digest.cmd_summarize, args)
    final_output = output_path or preview_output_path(group_name, date_str, since_text)
    report_body = ""
    if os.path.exists(final_output):
        with open(final_output, "r", encoding="utf-8") as fh:
            report_body = fh.read()
    return {
        "mode": "single",
        "summary": summary if isinstance(summary, str) else stdout,
        "report": report_body,
        "output_path": final_output,
        "log": stderr,
        "generated_files": [final_output],
    }


def summarize_range(
    group_name: str,
    start_date: str,
    end_date: str,
    *,
    segment: bool = False,
    full: bool = False,
    batch_mode: bool = False,
    report_full: bool = False,
) -> dict[str, Any]:
    dates = _date_range(start_date, end_date)
    generated_files: list[str] = []
    logs: list[str] = []
    sections: list[str] = []
    for date_str in dates:
        result = summarize_single(
            group_name,
            date_str,
            segment=segment,
            full=full,
            batch_mode=batch_mode,
            report_full=report_full,
        )
        generated_files.extend(result["generated_files"])
        if result["log"]:
            logs.append(result["log"].strip())
        sections.append(f"## {date_str}\n\n{result['summary'].strip()}")
    return {
        "mode": "range",
        "summary": "\n\n".join(sections),
        "report": "\n\n".join(sections),
        "output_path": os.path.dirname(generated_files[0]) if generated_files else output_root(),
        "log": "\n\n".join(logs),
        "generated_files": generated_files,
    }


def default_summary_date() -> str:
    return (dt.date.today() - dt.timedelta(days=1)).strftime("%Y-%m-%d")

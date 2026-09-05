from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
EXAMPLE_PATH = ROOT / "config.example.json"
LEGACY_KEY = ROOT / "api-key.txt"

DEFAULTS = {
    "api_key": "",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-v4-flash",
    "thinking": None,
    "host": "127.0.0.1",
    "port": 8765,
    "db_path": "data.db",
    "locale": "zh",
}


def _deepseek(url: str) -> bool:
    return "deepseek.com" in (url or "").lower()


def load() -> dict:
    data = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        data.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    if not data.get("api_key") and LEGACY_KEY.exists():
        data["api_key"] = LEGACY_KEY.read_text(encoding="utf-8").strip()
        save(data)
    if data.get("thinking") is None:
        data["thinking"] = _deepseek(data.get("base_url") or "")
    if not Path(data["db_path"]).is_absolute():
        data["db_path_resolved"] = str(ROOT / data["db_path"])
    else:
        data["db_path_resolved"] = data["db_path"]
    return data


def save(data: dict) -> dict:
    out = {k: data.get(k, DEFAULTS[k]) for k in DEFAULTS}
    CONFIG_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return load()


def masked(data: dict | None = None) -> dict:
    data = data or load()
    key = data.get("api_key") or ""
    shown = ""
    if key:
        shown = key[:4] + "…" + key[-4:] if len(key) > 8 else "****"
    return {
        "api_key_set": bool(key),
        "api_key_masked": shown,
        "base_url": data.get("base_url") or "",
        "model": data.get("model") or "",
        "thinking": bool(data.get("thinking")),
        "host": data.get("host"),
        "port": data.get("port"),
        "locale": data.get("locale") or "zh",
    }

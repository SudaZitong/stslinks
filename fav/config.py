from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
LEGACY_KEY = ROOT / "api-key.txt"

DEFAULTS = {
    "active": "",
    "providers": [],
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


def _mask(key: str) -> str:
    key = key or ""
    if not key:
        return ""
    if len(key) > 8:
        return key[:4] + "…" + key[-4:]
    return "****"


def _normalize_providers(data: dict) -> list[dict]:
    providers = []
    seen = set()
    for raw in data.get("providers") or []:
        if not isinstance(raw, dict):
            continue
        name = (raw.get("name") or raw.get("base_url") or "default").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        url = (raw.get("base_url") or "").strip()
        thinking = raw.get("thinking")
        if thinking is None:
            thinking = _deepseek(url)
        providers.append(
            {
                "name": name,
                "base_url": url,
                "model": (raw.get("model") or "").strip(),
                "api_key": (raw.get("api_key") or "").strip(),
                "thinking": bool(thinking),
            }
        )
    if not providers and (data.get("api_key") or data.get("base_url")):
        url = (data.get("base_url") or "").strip()
        providers.append(
            {
                "name": "default",
                "base_url": url or "https://api.deepseek.com",
                "model": data.get("model") or "deepseek-v4-flash",
                "api_key": (data.get("api_key") or "").strip(),
                "thinking": bool(data["thinking"]) if data.get("thinking") is not None else _deepseek(url),
            }
        )
    return providers


def upsert_provider(data: dict, *, name: str, base_url: str, model: str, api_key: str, thinking: bool | None = None) -> dict:
    providers = _normalize_providers(data)
    item = {
        "name": name,
        "base_url": base_url.strip(),
        "model": model.strip(),
        "api_key": api_key.strip(),
        "thinking": _deepseek(base_url) if thinking is None else bool(thinking),
    }
    found = False
    for i, p in enumerate(providers):
        if p["name"] == name:
            if not item["api_key"]:
                item["api_key"] = p.get("api_key") or ""
            providers[i] = item
            found = True
            break
    if not found:
        providers.append(item)
    data["providers"] = providers
    data["active"] = name
    data["api_key"] = item["api_key"]
    data["base_url"] = item["base_url"]
    data["model"] = item["model"]
    data["thinking"] = item["thinking"]
    return data


def load() -> dict:
    data = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        data.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    if not data.get("api_key") and LEGACY_KEY.exists():
        data["api_key"] = LEGACY_KEY.read_text(encoding="utf-8").strip()
    data["providers"] = _normalize_providers(data)
    if data["providers"] and not data.get("active"):
        data["active"] = data["providers"][0]["name"]
    active = active_provider(data)
    if active:
        data["api_key"] = active["api_key"]
        data["base_url"] = active["base_url"]
        data["model"] = active["model"]
        data["thinking"] = active["thinking"]
    elif data.get("thinking") is None:
        data["thinking"] = _deepseek(data.get("base_url") or "")
    if not Path(data["db_path"]).is_absolute():
        data["db_path_resolved"] = str(ROOT / data["db_path"])
    else:
        data["db_path_resolved"] = data["db_path"]
    return data


def active_provider(data: dict | None = None) -> dict | None:
    data = data or load()
    providers = data.get("providers") or []
    name = data.get("active") or ""
    for p in providers:
        if p["name"] == name:
            return p
    return providers[0] if providers else None


def provider_chain(data: dict | None = None) -> list[dict]:
    data = data or load()
    providers = [p for p in (data.get("providers") or []) if p.get("api_key") and p.get("base_url")]
    active = data.get("active") or ""
    providers.sort(key=lambda p: (0 if p["name"] == active else 1, p["name"]))
    return providers


def save(data: dict) -> dict:
    providers = _normalize_providers(data)
    active = data.get("active") or (providers[0]["name"] if providers else "")
    current = None
    for p in providers:
        if p["name"] == active:
            current = p
            break
    if current is None and providers:
        current = providers[0]
        active = current["name"]
    out = {
        "active": active,
        "providers": providers,
        "api_key": (current or {}).get("api_key") or data.get("api_key") or "",
        "base_url": (current or {}).get("base_url") or data.get("base_url") or DEFAULTS["base_url"],
        "model": (current or {}).get("model") or data.get("model") or DEFAULTS["model"],
        "thinking": (current or {}).get("thinking") if current else data.get("thinking"),
        "host": data.get("host", DEFAULTS["host"]),
        "port": data.get("port", DEFAULTS["port"]),
        "db_path": data.get("db_path", DEFAULTS["db_path"]),
        "locale": data.get("locale", DEFAULTS["locale"]),
    }
    CONFIG_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return load()


def masked(data: dict | None = None) -> dict:
    data = data or load()
    providers = []
    for p in data.get("providers") or []:
        providers.append(
            {
                "name": p["name"],
                "base_url": p.get("base_url") or "",
                "model": p.get("model") or "",
                "thinking": bool(p.get("thinking")),
                "api_key_set": bool(p.get("api_key")),
                "api_key_masked": _mask(p.get("api_key") or ""),
            }
        )
    key = data.get("api_key") or ""
    return {
        "active": data.get("active") or "",
        "providers": providers,
        "api_key_set": bool(key),
        "api_key_masked": _mask(key),
        "base_url": data.get("base_url") or "",
        "model": data.get("model") or "",
        "thinking": bool(data.get("thinking")),
        "host": data.get("host"),
        "port": data.get("port"),
        "locale": data.get("locale") or "zh",
    }

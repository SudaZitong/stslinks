from __future__ import annotations

from . import ai, db


def local_search(query: str, tag: str | None = None) -> dict:
    hits = db.keyword_search(query, tag=tag)
    return {
        "ok": bool(hits),
        "mode": "local",
        "msg": f"本地 {len(hits)} 条" if hits else "收藏里对不上。",
        "tags": [tag] if tag else [],
        "items": hits,
        "trace": [],
    }


def _collect(on_event):
    trace: list[dict] = []
    current: dict | None = None

    def handle(ev: dict) -> None:
        nonlocal current
        kind = ev.get("type")
        if kind == "prompt":
            current = {
                "layer": ev.get("layer"),
                "title": ev.get("title"),
                "system": ev.get("system") or "",
                "user": ev.get("user") or "",
                "provider": ev.get("provider") or "",
                "model": ev.get("model") or "",
                "thinking": bool(ev.get("thinking")),
                "base_url": ev.get("base_url") or "",
                "think": "",
                "content": "",
                "total_tokens": None,
            }
            trace.append(current)
        elif kind == "think" and current is not None:
            current["think"] += ev.get("text") or ""
        elif kind == "content" and current is not None:
            current["content"] += ev.get("text") or ""
        elif kind == "usage" and current is not None:
            current["total_tokens"] = ev.get("total_tokens")
        if on_event:
            on_event(ev)

    return trace, handle


def public_result(result: dict) -> dict:
    """给前端的结果：思考保留，提示词和模型 JSON 不带出去。"""
    out = dict(result)
    out["trace"] = [
        {
            "layer": step.get("layer"),
            "title": step.get("title"),
            "provider": step.get("provider"),
            "model": step.get("model"),
            "think": step.get("think") or "",
            "total_tokens": step.get("total_tokens"),
        }
        for step in (result.get("trace") or [])
    ]
    return out


def ai_search(query: str, on_event=None) -> dict:
    """原设计：短标签第一层收窄，长描述第二层筛选。"""
    trace, handle = _collect(on_event)
    tags_res = ai.pick_tags(query, on_event=handle)
    if not tags_res["ok"]:
        return {
            "ok": False,
            "mode": "ai",
            "msg": tags_res.get("msg") or "短标签对不上。",
            "tags": tags_res.get("tags") or [],
            "items": [],
            "trace": trace,
        }
    candidates = db.filter_by_tags(tags_res["tags"], tags_res["mode"])
    ai.emit(
        handle,
        "status",
        layer="tags",
        text=f"标签 {'、'.join(tags_res['tags'])} 命中 {len(candidates)} 条",
    )
    if not candidates:
        return {
            "ok": False,
            "mode": "ai",
            "msg": tags_res.get("msg") or "这几个标签下面是空的。",
            "tags": tags_res["tags"],
            "items": [],
            "trace": trace,
        }
    picked = ai.pick_links(query, candidates, on_event=handle)
    by_id = {c["id"]: c for c in candidates}
    items = [by_id[i] for i in picked["links"] if i in by_id]
    if not items:
        return {
            "ok": False,
            "mode": "ai",
            "msg": picked.get("msg") or "长描述对过一遍，没有真符合的。",
            "tags": tags_res["tags"],
            "items": [],
            "trace": trace,
        }
    return {
        "ok": True,
        "mode": "ai",
        "msg": picked.get("msg") or tags_res.get("msg") or "",
        "tags": tags_res["tags"],
        "tag_mode": tags_res["mode"],
        "items": items,
        "trace": trace,
    }

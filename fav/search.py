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
    }


def ai_search(query: str, on_think=None) -> dict:
    """原设计：短标签第一层收窄，长描述第二层筛选。"""
    tags_res = ai.pick_tags(query, on_think=on_think)
    if not tags_res["ok"]:
        return {
            "ok": False,
            "mode": "ai",
            "msg": tags_res.get("msg") or "短标签对不上。",
            "tags": tags_res.get("tags") or [],
            "items": [],
        }
    candidates = db.filter_by_tags(tags_res["tags"], tags_res["mode"])
    if not candidates:
        return {
            "ok": False,
            "mode": "ai",
            "msg": tags_res.get("msg") or "这几个标签下面是空的。",
            "tags": tags_res["tags"],
            "items": [],
        }
    picked = ai.pick_links(query, candidates, on_think=on_think)
    by_id = {c["id"]: c for c in candidates}
    items = [by_id[i] for i in picked["links"] if i in by_id]
    if not items:
        return {
            "ok": False,
            "mode": "ai",
            "msg": picked.get("msg") or "长描述对过一遍，没有真符合的。",
            "tags": tags_res["tags"],
            "items": [],
        }
    return {
        "ok": True,
        "mode": "ai",
        "msg": picked.get("msg") or tags_res.get("msg") or "",
        "tags": tags_res["tags"],
        "tag_mode": tags_res["mode"],
        "items": items,
    }

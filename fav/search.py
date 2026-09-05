from __future__ import annotations

from . import ai, db


def local_search(query: str, tag: str | None = None) -> dict:
    hits = db.keyword_search(query, tag=tag)
    return {
        "ok": bool(hits),
        "mode": "local",
        "msg": f"本地 {len(hits)} 条" if hits else "收藏里没有类似的。换个说法，或去浏览器搜。",
        "tags": [tag] if tag else [],
        "items": hits,
    }


def ai_search(query: str, on_think=None) -> dict:
    """先本地打分，有额度再让模型从候选里挑。没额度就只出本地结果。"""
    local_hits = db.keyword_search(query)
    try:
        pool = local_hits[:40]
        if len(pool) < 5:
            tags_res = ai.pick_tags(query, on_think=on_think)
            extra = db.filter_by_tags(tags_res.get("tags") or [], tags_res.get("mode") or "or")
            seen = {x["id"] for x in pool}
            for item in extra:
                if item["id"] not in seen:
                    pool.append(item)
                    seen.add(item["id"])
        if not pool:
            return {
                "ok": False,
                "mode": "ai",
                "msg": "收藏里对不上。可以换关键词，或把新站添加进来。",
                "tags": [],
                "items": [],
            }
        picked = ai.pick_links(query, pool, on_think=on_think)
        by_id = {c["id"]: c for c in pool}
        items = [by_id[i] for i in picked["links"] if i in by_id]
        if not items:
            items = pool[:15]
        return {
            "ok": True,
            "mode": "ai",
            "msg": picked.get("msg") or "",
            "tags": [],
            "items": items,
        }
    except ai.AiError as exc:
        return {
            "ok": bool(local_hits),
            "mode": "local-fallback",
            "msg": f"{exc} 先给你本地结果。",
            "tags": [],
            "items": local_hits,
        }

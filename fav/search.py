from __future__ import annotations

from . import ai, db


def local_search(query: str, tag: str | None = None) -> dict:
    hits = db.keyword_search(query, tag=tag)
    return {
        "ok": bool(hits),
        "mode": "local",
        "msg": f"本地命中 {len(hits)} 条" if hits else "本地没有找到，可以试试 AI 搜。",
        "tags": [tag] if tag else [],
        "items": hits,
    }


def ai_search(query: str, on_think=None) -> dict:
    tags_res = ai.pick_tags(query, on_think=on_think)
    if not tags_res["ok"]:
        fallback = db.keyword_search(query)
        if fallback:
            return {
                "ok": True,
                "mode": "local-fallback",
                "msg": tags_res["msg"] or "标签没对上，改用关键词搜了。",
                "tags": [],
                "items": fallback,
            }
        return {
            "ok": False,
            "mode": "ai",
            "msg": tags_res["msg"] or "没有匹配的标签。",
            "tags": [],
            "items": [],
        }
    candidates = db.filter_by_tags(tags_res["tags"], tags_res["mode"])
    if not candidates:
        fallback = db.keyword_search(query)
        return {
            "ok": bool(fallback),
            "mode": "local-fallback",
            "msg": "标签下没有条目，改用关键词搜了。" if fallback else tags_res["msg"],
            "tags": tags_res["tags"],
            "items": fallback,
        }
    links_res = ai.pick_links(query, candidates, on_think=on_think)
    by_id = {c["id"]: c for c in candidates}
    items = [by_id[i] for i in links_res["links"] if i in by_id]
    if not items:
        return {
            "ok": True,
            "mode": "ai-tags",
            "msg": links_res["msg"] or "链接没挑出来，先给你这批标签下的全部条目。",
            "tags": tags_res["tags"],
            "items": candidates,
        }
    return {
        "ok": True,
        "mode": "ai",
        "msg": links_res["msg"] or tags_res["msg"],
        "tags": tags_res["tags"],
        "tag_mode": tags_res["mode"],
        "items": items,
    }

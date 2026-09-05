from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from . import config


def split_tags(raw) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        parts = []
        for item in raw:
            parts.extend(split_tags(item))
        return parts
    text = str(raw).replace(",", "|").replace("，", "|").replace(" ", "|")
    out = []
    seen = set()
    for part in text.split("|"):
        tag = part.strip()
        if tag and tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out


def join_tags(tags) -> str:
    return "|".join(split_tags(tags))


def connect() -> sqlite3.Connection:
    cfg = config.load()
    conn = sqlite3.connect(cfg["db_path_resolved"])
    conn.row_factory = sqlite3.Row
    return conn


def init() -> None:
    with connect() as conn:
        conn.execute(
            """
            create table if not exists links (
                id integer primary key autoincrement not null,
                title text,
                tags text,
                desc text,
                url text
            )
            """
        )
        cols = {row["name"] for row in conn.execute("pragma table_info(links)")}
        if "created_at" not in cols:
            conn.execute("alter table links add column created_at text")
        conn.commit()


def _row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"] or "",
        "tags": split_tags(row["tags"]),
        "desc": row["desc"] or "",
        "url": row["url"] or "",
        "created_at": row["created_at"] if "created_at" in row.keys() else None,
    }


def all_links() -> list[dict]:
    init()
    with connect() as conn:
        rows = conn.execute("select * from links order by id desc").fetchall()
    return [_row(r) for r in rows]


def get_link(link_id: int) -> dict | None:
    init()
    with connect() as conn:
        row = conn.execute("select * from links where id = ?", (link_id,)).fetchone()
    return _row(row) if row else None


def all_tags() -> list[str]:
    tags = []
    seen = set()
    for link in all_links():
        for tag in link["tags"]:
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
    return sorted(tags, key=str.lower)


def add_link(title: str, url: str, tags=None, desc: str = "") -> dict:
    init()
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        cur = conn.execute(
            "insert into links (title, tags, desc, url, created_at) values (?, ?, ?, ?, ?)",
            (title.strip(), join_tags(tags), desc.strip(), url.strip(), now),
        )
        conn.commit()
        link_id = cur.lastrowid
    return get_link(link_id)


def update_link(link_id: int, title=None, url=None, tags=None, desc=None) -> dict | None:
    current = get_link(link_id)
    if not current:
        return None
    if title is not None:
        current["title"] = title
    if url is not None:
        current["url"] = url
    if tags is not None:
        current["tags"] = split_tags(tags)
    if desc is not None:
        current["desc"] = desc
    with connect() as conn:
        conn.execute(
            "update links set title = ?, tags = ?, desc = ?, url = ? where id = ?",
            (
                current["title"].strip(),
                join_tags(current["tags"]),
                current["desc"].strip(),
                current["url"].strip(),
                link_id,
            ),
        )
        conn.commit()
    return get_link(link_id)


def delete_link(link_id: int) -> bool:
    with connect() as conn:
        cur = conn.execute("delete from links where id = ?", (link_id,))
        conn.commit()
        return cur.rowcount > 0


def filter_by_tags(tags: list[str], mode: str = "or") -> list[dict]:
    wanted = split_tags(tags)
    if not wanted:
        return []
    mode = (mode or "or").lower()
    out = []
    for link in all_links():
        have = set(link["tags"])
        ok = have.issuperset(wanted) if mode == "and" else bool(have.intersection(wanted))
        if ok:
            out.append(link)
    return out


def keyword_search(query: str, tag: str | None = None) -> list[dict]:
    q = (query or "").strip().lower()
    tag = (tag or "").strip()
    out = []
    for link in all_links():
        if tag and tag not in link["tags"]:
            continue
        blob = " ".join([link["title"], link["desc"], link["url"], " ".join(link["tags"])]).lower()
        if not q or q in blob:
            out.append(link)
    return out

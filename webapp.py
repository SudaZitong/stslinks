#!/usr/bin/env python3
"""网页：收藏夹搜索引擎。"""
from __future__ import annotations

from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from fav import ai, config, db, search

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"

@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init()
    config.load()
    yield


app = FastAPI(title="TukJiu's Dream", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB), name="static")


class LinkIn(BaseModel):
    title: str
    url: str
    tags: list[str] | str = Field(default_factory=list)
    desc: str = ""


class LinkPatch(BaseModel):
    title: str | None = None
    url: str | None = None
    tags: list[str] | str | None = None
    desc: str | None = None


class SearchIn(BaseModel):
    query: str = ""
    local: bool = False
    tag: str | None = None


class ConfigIn(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    thinking: bool | None = None
    locale: str | None = None


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/links")
def api_links(q: str = "", tag: str = ""):
    return {"items": db.keyword_search(q, tag=tag or None), "tags": db.all_tags()}


@app.post("/api/links")
def api_add(body: LinkIn):
    if not body.title.strip() or not body.url.strip():
        raise HTTPException(400, "标题和网址必填")
    return db.add_link(body.title, body.url, body.tags, body.desc)


@app.put("/api/links/{link_id}")
def api_edit(link_id: int, body: LinkPatch):
    item = db.update_link(link_id, body.title, body.url, body.tags, body.desc)
    if not item:
        raise HTTPException(404, "没有这条")
    return item


@app.delete("/api/links/{link_id}")
def api_delete(link_id: int):
    if not db.delete_link(link_id):
        raise HTTPException(404, "没有这条")
    return {"ok": True}


@app.get("/api/tags")
def api_tags():
    return {"tags": db.all_tags()}


@app.post("/api/search")
def api_search(body: SearchIn):
    if body.local or not body.query.strip():
        return search.local_search(body.query, tag=body.tag)
    try:
        return search.ai_search(body.query)
    except ai.AiError as exc:
        result = search.local_search(body.query, tag=body.tag)
        result["msg"] = f"{exc} 已改用本地搜索。"
        result["mode"] = "local-fallback"
        return result


@app.get("/api/config")
def api_config_get():
    return config.masked()


@app.put("/api/config")
def api_config_put(body: ConfigIn):
    data = config.load()
    payload = body.model_dump(exclude_none=True)
    if payload.get("api_key") == "":
        pass
    elif payload.get("api_key"):
        data["api_key"] = payload["api_key"]
    for key in ("base_url", "model", "thinking", "locale"):
        if key in payload and payload[key] is not None:
            data[key] = payload[key]
    return config.masked(config.save(data))


def main() -> None:
    import uvicorn

    cfg = config.load()
    uvicorn.run(
        "webapp:app",
        host=cfg.get("host") or "127.0.0.1",
        port=int(cfg.get("port") or 8765),
        reload=False,
    )


if __name__ == "__main__":
    main()

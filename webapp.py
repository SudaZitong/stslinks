#!/usr/bin/env python3
"""网页：收藏夹搜索引擎。"""
from __future__ import annotations

import json
import queue
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
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
    name: str | None = None
    active: str | None = None


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
        return search.public_result(search.ai_search(body.query))
    except ai.AiError as exc:
        raise HTTPException(503, ai.scrub(exc)) from exc


def _sse(obj: dict) -> str:
    return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"


def _client_event(ev: dict) -> dict | None:
    kind = ev.get("type")
    if kind == "content":
        return None
    if kind == "prompt":
        return {
            "type": "prompt",
            "layer": ev.get("layer"),
            "title": ev.get("title"),
            "provider": ev.get("provider"),
            "model": ev.get("model"),
        }
    if kind == "done":
        return {"type": "done", "result": search.public_result(ev.get("result") or {})}
    return ev


@app.post("/api/search/stream")
def api_search_stream(body: SearchIn):
    query = (body.query or "").strip()
    if body.local or not query:
        def local_gen():
            yield _sse(_client_event({"type": "done", "result": search.local_search(query, tag=body.tag)}))

        return StreamingResponse(
            local_gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    def gen():
        q: queue.Queue = queue.Queue()

        def on_event(ev: dict) -> None:
            q.put(ev)

        def run() -> None:
            try:
                result = search.ai_search(query, on_event=on_event)
                q.put({"type": "done", "result": result})
            except ai.AiError as exc:
                q.put({"type": "error", "msg": ai.scrub(exc)})
            except Exception as exc:
                q.put({"type": "error", "msg": ai.scrub(exc)})
            finally:
                q.put(None)

        threading.Thread(target=run, daemon=True).start()
        while True:
            try:
                ev = q.get(timeout=1)
            except queue.Empty:
                yield ": ping\n\n"
                continue
            if ev is None:
                break
            pub = _client_event(ev)
            if pub is None:
                continue
            yield _sse(pub)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/config")
def api_config_get():
    return config.masked()


@app.put("/api/config")
def api_config_put(body: ConfigIn):
    data = config.load()
    payload = body.model_dump(exclude_none=True)
    if payload.get("locale"):
        data["locale"] = payload["locale"]
    if payload.get("name") and (payload.get("base_url") or payload.get("model") or payload.get("api_key")):
        current = next((p for p in data.get("providers") or [] if p["name"] == payload["name"]), {})
        data = config.upsert_provider(
            data,
            name=payload["name"],
            base_url=payload.get("base_url") or current.get("base_url") or "",
            model=payload.get("model") or current.get("model") or "",
            api_key=payload.get("api_key") or "",
            thinking=payload.get("thinking"),
        )
    elif payload.get("active"):
        names = {p["name"] for p in data.get("providers") or []}
        if payload["active"] not in names:
            raise HTTPException(400, "没有这一层 API")
        data["active"] = payload["active"]
    else:
        if payload.get("api_key"):
            data["api_key"] = payload["api_key"]
        for key in ("base_url", "model", "thinking"):
            if key in payload:
                data[key] = payload[key]
        if data.get("active"):
            data = config.upsert_provider(
                data,
                name=data["active"],
                base_url=data.get("base_url") or "",
                model=data.get("model") or "",
                api_key=payload.get("api_key") or "",
                thinking=data.get("thinking"),
            )
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

from __future__ import annotations

import json
import re

from openai import OpenAI

from . import config, db

TAG_PROMPT = """你是收藏夹助手「小鲸鱼」。根据用户需求，从给定标签里选出相关标签。
需求模糊时可以多给几个可能有用的标签，并在 msg 里说明偏差。
只输出 JSON，字段：tags（字符串数组）, mode（or 或 and）, ok（true/false）, msg（评价，可调侃）。
tags 为空则 ok 必须为 false。
mode=or 表示命中任一标签；and 表示必须同时包含所有标签。
"""

LINK_PROMPT = """你是收藏夹助手「小鲸鱼」。根据用户需求，从给定条目（id、title、desc）里选出相关链接 id。
需求模糊时可以多给几个，并在 msg 里说明。
只输出 JSON，字段：links（整数 id 数组）, ok（true/false）, msg。
links 为空则 ok 必须为 false。找不到时在 msg 里给搜索关键词建议。
"""


class AiError(Exception):
    pass


def parse_json(text: str) -> dict:
    if not text or not str(text).strip():
        raise AiError("模型返回空内容")
    raw = text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise AiError(f"不是 JSON：{raw[:400]}")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise AiError(f"JSON 解析失败：{exc}") from exc
    if not isinstance(data, dict):
        raise AiError("JSON 根节点必须是对象")
    return data


def _client(cfg: dict) -> OpenAI:
    key = (cfg.get("api_key") or "").strip()
    if not key:
        raise AiError("还没有 API Key。请在网页设置里填写，或编辑 config.json。")
    base = (cfg.get("base_url") or "").strip() or "https://api.deepseek.com"
    return OpenAI(api_key=key, base_url=base)


def complete(system: str, user: str, on_think=None) -> str:
    cfg = config.load()
    client = _client(cfg)
    model = cfg.get("model") or "deepseek-v4-flash"
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    attempts = []
    if cfg.get("thinking"):
        attempts.append({"extra_body": {"thinking": {"type": "enabled"}}, "reasoning_effort": "low"})
    attempts.append({})
    last_err = None
    for extra in attempts:
        try:
            if "extra_body" in extra:
                with client.chat.completions.stream(model=model, messages=messages, **extra) as stream:
                    for event in stream:
                        if event.type == "chunk":
                            delta = event.chunk.choices[0].delta
                            think = getattr(delta, "reasoning_content", None)
                            if think and on_think:
                                on_think(think)
                    completion = stream.get_final_completion()
                return completion.choices[0].message.content or ""
            kwargs = dict(model=model, messages=messages)
            try:
                kwargs["response_format"] = {"type": "json_object"}
                resp = client.chat.completions.create(**kwargs)
            except Exception:
                kwargs.pop("response_format", None)
                resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except Exception as exc:
            last_err = exc
            continue
    raise AiError(f"调用模型失败：{last_err}") from last_err


def pick_tags(query: str, on_think=None) -> dict:
    tags = db.all_tags()
    system = TAG_PROMPT + "\n可选标签：" + json.dumps(tags, ensure_ascii=False)
    data = parse_json(complete(system, query, on_think=on_think))
    picked = [str(t).strip() for t in (data.get("tags") or []) if str(t).strip()]
    known = set(tags)
    picked = [t for t in picked if t in known]
    mode = data.get("mode") if data.get("mode") in ("and", "or") else "or"
    ok = bool(data.get("ok")) and bool(picked)
    return {
        "tags": picked,
        "mode": mode,
        "ok": ok,
        "msg": str(data.get("msg") or ""),
    }


def pick_links(query: str, candidates: list[dict], on_think=None) -> dict:
    slim = [{"id": c["id"], "title": c["title"], "desc": c["desc"]} for c in candidates]
    system = LINK_PROMPT + "\n可选链接：" + json.dumps(slim, ensure_ascii=False)
    data = parse_json(complete(system, query, on_think=on_think))
    ids = []
    for item in data.get("links") or []:
        try:
            ids.append(int(item))
        except (TypeError, ValueError):
            continue
    valid = {c["id"] for c in candidates}
    ids = [i for i in ids if i in valid]
    ok = bool(data.get("ok")) and bool(ids)
    return {
        "links": ids,
        "ok": ok,
        "msg": str(data.get("msg") or ""),
    }

from __future__ import annotations

import json
import re

from openai import OpenAI

from . import config, db

TAG_PROMPT = """你是收藏夹助手「小鲸鱼」。
第一层：只用短标签做快速匹配，从给定标签里选出相关的。标签很粗，宁可 or 多给几个，不要用 and，除非用户明确说必须同时满足。
需求模糊时多给可能用到的标签，在 msg 里说明偏差。
只输出 JSON：tags（字符串数组）, mode（or 或 and）, ok（true/false）, msg（可以调侃）。
tags 为空则 ok=false。
"""

LINK_PROMPT = """你是收藏夹助手「小鲸鱼」。
第二层：下面每条都有认真写的长描述。请根据描述判断是不是用户真要的东西，不要只看标题党，也不要因为标签沾边就全收。
选出相关链接的 id。模糊需求可以多给几个，并在 msg 里说明。
只输出 JSON：links（整数 id 数组）, ok（true/false）, msg。
links 为空则 ok=false。找不到时在 msg 里给浏览器搜索词。
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


def _client(api_key: str, base_url: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url, timeout=60.0)


def _complete_one(prov: dict, system: str, user: str, on_think=None) -> str:
    client = _client(prov["api_key"], prov["base_url"])
    model = prov.get("model") or "gpt-4o-mini"
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    attempts = []
    if prov.get("thinking"):
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
    raise AiError(f"{prov.get('name')}: {last_err}") from last_err


def complete(system: str, user: str, on_think=None) -> str:
    cfg = config.load()
    chain = config.provider_chain(cfg)
    if not chain:
        raise AiError("还没有可用的 API。在设置里加一层 base_url + key + model。")
    errors = []
    for prov in chain:
        try:
            return _complete_one(prov, system, user, on_think=on_think)
        except Exception as exc:
            errors.append(f"{prov.get('name')}: {exc}")
            continue
    raise AiError("上层接口都失败了：" + " | ".join(errors))


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

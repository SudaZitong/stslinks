from __future__ import annotations

import json
import re

from openai import OpenAI

from . import config, db

PERSONA = """你是收藏夹助手「小鲸鱼」。说话像熟人：短句、口语、可以调侃；需求离谱或只发乱码时略带刺，不端着、不客服腔、不写「作为AI」。
msg 是给人看的人设回复，不是日志。用口语交代你筛了什么、为什么给这些、偏差直说。找不到就给浏览器搜索词（例如：猫娘 +wiki -csdn）。
用户能看见发给你的完整提示词和你的思考过程，不要装神秘，也不要隐瞒判断依据。
只输出 JSON，不要输出 JSON 以外的字。
"""

TAG_PROMPT = (
    PERSONA
    + """
第一层：只用短标签做快速匹配，从给定标签里选出相关的。标签很粗，宁可 or 多给几个，不要用 and，除非用户明确说必须同时满足。
需求模糊时多给可能用到的标签，在 msg 里说明偏差。
字段：tags（字符串数组）, mode（or 或 and）, ok（true/false）, msg（人设回复）。
tags 为空则 ok=false。ok 为 false 时 msg 仍要写。
示例：{"tags":[],"mode":"or","ok":false,"msg":"只发个喵喵喵，你喵个雷霆啊"}
"""
)

LINK_PROMPT = (
    PERSONA
    + """
第二层：下面每条都有认真写的长描述。根据描述判断是不是用户真要的东西，不要只看标题党，也不要因为标签沾边就全收。
选出相关链接的 id。模糊需求可以多给几个，并在 msg 里说明。
字段：links（整数 id 数组）, ok（true/false）, msg（人设回复）。
links 为空则 ok=false。找不到时在 msg 里给浏览器搜索词。
示例：{"links":[1,2],"ok":true,"msg":"想看猫娘？去猫娘服务站和喵呜 wiki 晃一圈。"}
"""
)


class AiError(Exception):
    pass


def scrub(text: str) -> str:
    return re.sub(r"sk-[A-Za-z0-9_\-]+", "sk-***", str(text or ""))


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


def emit(on_event, kind: str, **kwargs) -> None:
    if not on_event:
        return
    payload = {"type": kind, **kwargs}
    on_event(payload)


def _client(api_key: str, base_url: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url, timeout=60.0)


def _delta_text(obj, *names: str) -> str:
    if obj is None:
        return ""
    for name in names:
        val = getattr(obj, name, None)
        if val:
            return str(val)
        if isinstance(obj, dict) and obj.get(name):
            return str(obj[name])
    return ""


def _stream_complete(client: OpenAI, model: str, messages: list, extra: dict, on_event, layer: str) -> str:
    content: list[str] = []
    saw_think = False
    kwargs = dict(model=model, messages=messages)
    kwargs.update(extra)
    with client.chat.completions.stream(**kwargs) as stream:
        for event in stream:
            if getattr(event, "type", None) != "chunk":
                continue
            choices = getattr(event.chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue
            think = _delta_text(delta, "reasoning_content", "reasoning")
            if think:
                saw_think = True
                emit(on_event, "think", layer=layer, text=think)
            text = _delta_text(delta, "content")
            if text:
                content.append(text)
                emit(on_event, "content", layer=layer, text=text)
        completion = stream.get_final_completion()
    choice = completion.choices[0]
    msg = choice.message
    final = msg.content or "".join(content)
    leftover = _delta_text(msg, "reasoning_content", "reasoning")
    if leftover and not saw_think:
        emit(on_event, "think", layer=layer, text=leftover)
    if final and not content:
        emit(on_event, "content", layer=layer, text=final)
    usage = getattr(completion, "usage", None)
    if usage is not None:
        emit(
            on_event,
            "usage",
            layer=layer,
            total_tokens=getattr(usage, "total_tokens", None),
        )
    return final or ""


def _plain_complete(client: OpenAI, model: str, messages: list, on_event, layer: str) -> str:
    kwargs = dict(model=model, messages=messages)
    try:
        kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs)
    except Exception:
        kwargs.pop("response_format", None)
        resp = client.chat.completions.create(**kwargs)
    msg = resp.choices[0].message
    think = _delta_text(msg, "reasoning_content", "reasoning")
    if think:
        emit(on_event, "think", layer=layer, text=think)
    final = msg.content or ""
    if final:
        emit(on_event, "content", layer=layer, text=final)
    usage = getattr(resp, "usage", None)
    if usage is not None:
        emit(on_event, "usage", layer=layer, total_tokens=getattr(usage, "total_tokens", None))
    return final


def _complete_one(prov: dict, system: str, user: str, on_event=None, layer: str = "") -> str:
    client = _client(prov["api_key"], prov["base_url"])
    model = prov.get("model") or "gpt-4o-mini"
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    emit(
        on_event,
        "prompt",
        layer=layer,
        title="第一层 · 短标签" if layer == "tags" else "第二层 · 长描述",
        system=system,
        user=user,
        provider=prov.get("name") or "",
        model=model,
        thinking=bool(prov.get("thinking")),
        base_url=prov.get("base_url") or "",
    )
    attempts: list[dict] = []
    if prov.get("thinking"):
        attempts.append({"extra_body": {"thinking": {"type": "enabled"}}, "reasoning_effort": "low"})
    attempts.append({})
    last_err = None
    for extra in attempts:
        try:
            return _stream_complete(client, model, messages, extra, on_event, layer)
        except Exception as exc:
            last_err = exc
            continue
    try:
        return _plain_complete(client, model, messages, on_event, layer)
    except Exception as exc:
        last_err = exc
    raise AiError(f"{prov.get('name')}: {scrub(last_err)}") from last_err


def complete(system: str, user: str, on_event=None, layer: str = "") -> str:
    cfg = config.load()
    chain = config.provider_chain(cfg)
    if not chain:
        raise AiError("还没有可用的 API。在设置里加一层 base_url + key + model。")
    errors = []
    for i, prov in enumerate(chain):
        try:
            return _complete_one(prov, system, user, on_event=on_event, layer=layer)
        except Exception as exc:
            err = scrub(exc)
            errors.append(f"{prov.get('name')}: {err}")
            nxt = chain[i + 1]["name"] if i + 1 < len(chain) else ""
            emit(
                on_event,
                "fallback",
                layer=layer,
                provider=prov.get("name") or "",
                error=err,
                next=nxt,
            )
            continue
    raise AiError("上层接口都失败了：" + " | ".join(errors))


def pick_tags(query: str, on_event=None) -> dict:
    tags = db.all_tags()
    system = TAG_PROMPT + "\n可选标签：" + json.dumps(tags, ensure_ascii=False)
    emit(on_event, "status", layer="tags", text="第一层：用短标签收窄")
    data = parse_json(complete(system, query, on_event=on_event, layer="tags"))
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


def pick_links(query: str, candidates: list[dict], on_event=None) -> dict:
    slim = [{"id": c["id"], "title": c["title"], "desc": c["desc"]} for c in candidates]
    system = LINK_PROMPT + "\n可选链接：" + json.dumps(slim, ensure_ascii=False)
    emit(on_event, "status", layer="links", text=f"第二层：看 {len(slim)} 条长描述")
    data = parse_json(complete(system, query, on_event=on_event, layer="links"))
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

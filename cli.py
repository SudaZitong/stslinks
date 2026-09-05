#!/usr/bin/env python3
"""命令行收藏夹。交互模式沿用原来的小鲸鱼问答。"""
from __future__ import annotations

import argparse
import sys
import time

from fav import ai, config, db, search


def show(content: str) -> None:
    text = str(content) + "\n"
    for ch in text:
        print(ch, end="", flush=True)
        time.sleep(0.004 if ch != "\n" else 0.02)
    time.sleep(0.05)


def think_print(chunk: str) -> None:
    print(chunk, end="", flush=True)


def cmd_search(query: str, local: bool = False) -> int:
    db.init()
    if not query.strip():
        show("请输入需求")
        return 1
    if local:
        result = search.local_search(query)
    else:
        show("===")
        try:
            result = search.ai_search(query, on_think=think_print)
            print()
        except ai.AiError as exc:
            show(str(exc))
            show("改用本地搜索。")
            result = search.local_search(query)
    show(result.get("msg") or "")
    if result.get("tags"):
        show("标签：" + "、".join(result["tags"]))
    if not result.get("items"):
        return 1
    show("[收藏夹] 使用 Ctrl+鼠标左键 打开链接")
    for item in result["items"]:
        show(f"{item['id']}. {item['title']} - {item['url']}")
    return 0


def cmd_add(args) -> int:
    db.init()
    link = db.add_link(args.title, args.url, args.tags, args.desc or "")
    show(f"已添加 #{link['id']} {link['title']}")
    return 0


def cmd_list(tag: str | None) -> int:
    db.init()
    items = db.keyword_search("", tag=tag)
    show(f"共 {len(items)} 条")
    for item in items:
        tags = "|".join(item["tags"])
        show(f"{item['id']}. {item['title']}  [{tags}]  {item['url']}")
    return 0


def cmd_tags() -> int:
    db.init()
    tags = db.all_tags()
    show("、".join(tags) if tags else "还没有标签")
    return 0


def cmd_rm(link_id: int) -> int:
    if db.delete_link(link_id):
        show(f"已删除 #{link_id}")
        return 0
    show("没有这条")
    return 1


def interactive() -> int:
    db.init()
    cfg = config.load()
    show(f"[收藏夹] 模型 {cfg.get('model')} @ {cfg.get('base_url')}")
    show("[收藏夹] Ctrl+C 退出。空行是本地搜，输入需求则走小鲸鱼。")
    while True:
        try:
            show("===")
            print("请输入 >>> ", end="")
            query = input()
        except (EOFError, KeyboardInterrupt):
            print()
            show("再见")
            return 0
        if not query.strip():
            continue
        if query.strip() in ("/tags", "tags"):
            cmd_tags()
            continue
        if query.strip() in ("/list", "list"):
            cmd_list(None)
            continue
        cmd_search(query)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="小鲸鱼收藏夹 CLI")
    sub = parser.add_subparsers(dest="cmd")

    p_s = sub.add_parser("search", help="搜索")
    p_s.add_argument("query")
    p_s.add_argument("--local", action="store_true")

    p_a = sub.add_parser("add", help="添加")
    p_a.add_argument("--title", required=True)
    p_a.add_argument("--url", required=True)
    p_a.add_argument("--tags", default="")
    p_a.add_argument("--desc", default="")

    p_l = sub.add_parser("list", help="列出")
    p_l.add_argument("--tag")

    sub.add_parser("tags", help="列出标签")

    p_r = sub.add_parser("rm", help="删除")
    p_r.add_argument("id", type=int)

    p_c = sub.add_parser("config", help="查看配置（不含完整密钥）")
    sub.add_parser("recat", help="整理标签和空描述（不调模型）")

    args = parser.parse_args(argv)
    if not args.cmd:
        return interactive()
    if args.cmd == "search":
        return cmd_search(args.query, local=args.local)
    if args.cmd == "add":
        return cmd_add(args)
    if args.cmd == "list":
        return cmd_list(args.tag)
    if args.cmd == "tags":
        return cmd_tags()
    if args.cmd == "rm":
        return cmd_rm(args.id)
    if args.cmd == "config":
        show(str(config.masked()))
        return 0
    if args.cmd == "recat":
        from fav.classify import recategorize

        info = recategorize(write=True)
        show(f"更新 {info['changed']} 条，标签 {info['tag_count']} 个")
        show("、".join(info["tags"]))
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

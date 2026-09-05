"""把杂乱标签收成短分类，空描述用标题+网址补上。不调用模型。"""
from __future__ import annotations

from urllib.parse import urlparse

from . import db

CANONICAL = {
    "AI",
    "3D",
    "API",
    "linux",
    "termux",
    "wiki",
    "云",
    "匿名",
    "博客",
    "图像",
    "学习",
    "安卓",
    "工具",
    "开发",
    "心理",
    "我的世界",
    "政府",
    "文件传输",
    "文档",
    "新闻",
    "求职",
    "游戏",
    "物流",
    "生活",
    "硬件",
    "社区",
    "米哈游",
    "系统",
    "网盘",
    "网络",
    "网络安全",
    "翻译",
    "视频",
    "设计",
    "赞助",
    "软件仓库",
    "部署",
    "金融",
    "音频",
    "其他",
}

SYNONYM = {
    "ai": "AI",
    "Linux": "linux",
    "git": "开发",
    "命令": "开发",
    "开发工具": "开发",
    "C语言": "开发",
    "框架": "开发",
    "爬虫": "开发",
    "跨域工具": "开发",
    "termux}开发": "termux",
    "android": "安卓",
    "观看视频": "视频",
    "视频编辑": "视频",
    "视频素材": "视频",
    "直播导播": "视频",
    "动画": "视频",
    "音频编辑": "音频",
    "音频素材": "音频",
    "变声器": "音频",
    "图像编辑": "图像",
    "图像素材": "图像",
    "图像": "图像",
    "教育": "学习",
    "教育工具": "学习",
    "图书": "学习",
    "文献": "学习",
    "竞赛": "学习",
    "考试": "学习",
    "中国政府": "政府",
    "web设计": "设计",
    "设计工具": "设计",
    "文档编辑": "文档",
    "思维导图": "文档",
    "工具集": "工具",
    "书签": "工具",
    "地图": "工具",
    "api平台": "API",
    "找工作": "求职",
    "赞助平台": "赞助",
    "pe系统": "系统",
    "ventoy": "系统",
    "影子系统": "系统",
    "pve": "部署",
    "p2p": "文件传输",
    "反弹shell": "网络安全",
    "单机外挂": "游戏",
    "无线电盒子": "硬件",
    "NFC": "硬件",
    "股票": "金融",
    "人格测试": "心理",
    "国际快递": "物流",
    "海运": "物流",
    "皮肤工具": "我的世界",
    "匿名工具": "匿名",
    "社会工程学": "网络安全",
    "云厂商": "云",
}

HOST_TAGS = {
    "github.com": ["开发"],
    "gitlab.com": ["开发"],
    "wikipedia.org": ["wiki"],
    "fandom.com": ["wiki"],
    "wikihow.com": ["wiki"],
    "minecraft.net": ["我的世界", "游戏"],
    "minecraft.fandom.com": ["我的世界", "游戏", "wiki"],
    "hoyoverse.com": ["米哈游", "游戏"],
    "mihoyo.com": ["米哈游", "游戏"],
    "bilibili.com": ["视频"],
    "youtube.com": ["视频"],
    "deepl.com": ["翻译"],
    "google.com": ["工具"],
    "cloudflare.com": ["网络"],
    "aliyun.com": ["云"],
    "huaweicloud.com": ["云"],
    "tencent.com": ["云"],
    "aws.amazon.com": ["云"],
    "azure.microsoft.com": ["云"],
}

TITLE_HINTS = [
    ("我的世界", ["我的世界", "游戏"]),
    ("minecraft", ["我的世界", "游戏"]),
    ("mcbe", ["我的世界", "游戏"]),
    ("原神", ["米哈游", "游戏"]),
    ("崩坏", ["米哈游", "游戏"]),
    ("星穹", ["米哈游", "游戏"]),
    ("gpt", ["AI"]),
    ("llm", ["AI"]),
    ("ai", ["AI"]),
    ("翻译", ["翻译"]),
    ("wiki", ["wiki"]),
    ("博客", ["博客"]),
    ("漏洞", ["网络安全"]),
    ("渗透", ["网络安全"]),
    ("病毒", ["网络安全"]),
    ("linux", ["linux", "开发"]),
    ("docker", ["部署", "开发"]),
    ("git", ["开发"]),
    ("网盘", ["网盘"]),
    ("云盘", ["网盘"]),
    ("考试", ["学习"]),
    ("课程", ["学习"]),
    ("设计", ["设计"]),
    ("字体", ["设计"]),
    ("音频", ["音频"]),
    ("音乐", ["音频"]),
    ("视频", ["视频"]),
    ("图像", ["图像"]),
    ("图片", ["图像"]),
    ("3d", ["3D"]),
    ("建模", ["3D"]),
    ("招聘", ["求职"]),
    ("工作", ["求职"]),
    ("政府", ["政府"]),
    ("法院", ["政府"]),
    ("铁路", ["生活"]),
    ("文档", ["文档"]),
    ("api", ["API"]),
    ("termux", ["termux", "安卓"]),
]


def _host(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def _looks_like_name(tag: str) -> bool:
    if len(tag) >= 10:
        return True
    for mark in ("导航", "教程", "说明书", "平台", "官网", "[", "]"):
        if mark in tag:
            return True
    return False


def classify_item(title: str, url: str, tags, desc: str = "") -> tuple[list[str], str]:
    leftover = []
    out = []
    seen = set()

    def add(tag: str) -> None:
        tag = (tag or "").strip()
        if not tag or tag in seen:
            return
        seen.add(tag)
        out.append(tag)

    for raw in db.split_tags(tags):
        mapped = SYNONYM.get(raw, raw)
        if mapped not in CANONICAL:
            leftover.append(raw)
            blob = raw.lower()
            for key, vals in TITLE_HINTS:
                if key in blob:
                    for v in vals:
                        add(v)
            continue
        add(mapped)

    host = _host(url)
    blob = f"{title} {url} {desc} {' '.join(leftover)}".lower()
    for suffix, vals in HOST_TAGS.items():
        if host == suffix or host.endswith("." + suffix):
            for v in vals:
                add(v)
    for key, vals in TITLE_HINTS:
        if key in blob:
            for v in vals:
                add(v)
    out = [t for t in out if t in CANONICAL]
    seen = set(out)
    if not out:
        add("其他")

    desc = (desc or "").strip()
    if not desc:
        bits = [title.strip()]
        if host:
            bits.append(host)
        if leftover:
            bits.append("；".join(leftover[:2]))
        desc = " · ".join(x for x in bits if x)

    return out[:6], desc


def recategorize(write: bool = True) -> dict:
    db.init()
    changed = 0
    tag_set = set()
    for link in db.all_links():
        tags, desc = classify_item(link["title"], link["url"], link["tags"], link["desc"])
        tag_set.update(tags)
        if tags != link["tags"] or desc != (link["desc"] or ""):
            changed += 1
            if write:
                db.update_link(link["id"], tags=tags, desc=desc)
    return {"changed": changed, "tag_count": len(tag_set), "tags": sorted(tag_set)}

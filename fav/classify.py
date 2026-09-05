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
    ("内网穿透", ["网络"]),
    ("临时邮箱", ["匿名"]),
    ("接码", ["匿名"]),
    ("题库", ["学习"]),
    ("考公", ["学习"]),
    ("四六级", ["学习"]),
    ("高考", ["学习"]),
    ("作文", ["学习"]),
    ("乐谱", ["音频"]),
    ("钢琴", ["音频"]),
    ("keepass", ["工具", "网络安全"]),
    ("echarts", ["开发"]),
    ("压缩", ["工具"]),
    ("论文", ["学习"]),
    ("mooc", ["学习"]),
    ("建站", ["部署"]),
    ("摄像头", ["网络安全"]),
    ("降重", ["学习"]),
    ("overleaf", ["文档", "学习"]),
    ("caddy", ["部署", "网络"]),
    ("ntlite", ["系统"]),
    ("鸣潮", ["游戏"]),
    ("wuthering", ["游戏"]),
    ("liquidbounce", ["游戏", "我的世界"]),
    ("amulet", ["我的世界", "游戏"]),
    ("gnome", ["linux"]),
    ("简历", ["求职"]),
    ("录屏", ["视频"]),
    ("论坛", ["社区"]),
    ("书苑", ["学习"]),
    ("报刊", ["新闻"]),
    ("虎嗅", ["新闻"]),
    ("果壳", ["学习"]),
    ("营销", ["设计"]),
    ("运营", ["设计"]),
    ("导航", ["工具"]),
    ("绘画", ["设计"]),
    ("舞蹈", ["学习"]),
    ("书签", ["工具"]),
    ("协作", ["文档"]),
    ("frp", ["网络"]),
    ("穿透", ["网络"]),
    ("接码", ["匿名"]),
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

    return out[:6], write_desc(title, url, out, leftover)


def write_desc(title: str, url: str, tags: list[str], leftover: list[str] | None = None) -> str:
    """长描述：给第二层模型看的。语气随便，但要写清楚这站干嘛。"""
    t = (title or "").strip()
    host = _host(url)
    leftover = leftover or []

    if "临时邮箱" in t:
        return f"{t}。一次性邮箱收验证码，用完就扔，别拿来收重要信。"
    if "接码" in t:
        return f"{t}。网上收短信验证码。来路杂，别绑银行卡和主力号。"
    if "内网穿透" in t or t in ("Frp", "OpenFrp", "NATAPP", "cpolar", "飞鸽内网穿透"):
        return f"{t}。把家里或公司内网的服务透到公网。稳不稳、要不要钱自己掂量。"
    if "MC版本库" in t or "MCForWindows" in t:
        return f"{t}。Minecraft 安装包/旧版本仓库，装客户端或翻老版本用。"
    if t.endswith("博客") or (tags == ["博客"] or (len(tags) == 1 and tags[0] == "博客")):
        return f"{t}。个人站，技术笔记和日常想到再翻。"
    if "翻译" in t or host == "deepl.com":
        return f"{t}。在线翻译，语感通常比普通机翻顺，适合对照着改。"
    if t == "Github" or host == "github.com":
        return f"{t}。代码托管，开源仓库、issue、个人主页都在这。"
    if "病毒扫描" in t or host == "virustotal.com":
        return f"{t}。把可疑文件/网址丢上去多家引擎扫一遍。"
    if "漏洞" in t:
        return f"{t}。查公开漏洞和利用信息，偏信安资料库。"
    if t.startswith("googleplay镜像") or "apk" in host:
        return f"{t}。Google Play 安装包镜像，不好下官方商店时用。"
    if "虚拟内网" in t or "zerotier" in t.lower() or t == "Tailscale虚拟内网(udp/p2p)":
        return f"{t}。组虚拟局域网，把分散的机器当同一网段。"
    if "网络空间测绘" in t or host in ("shodan.io", "zoomeye.org"):
        return f"{t}。网上暴露面搜索，查开了什么端口和服务。信安用。"
    if "靶" in t:
        return f"{t}。练习用的靶场/靶机，本地搭了再打，别扫别人。"
    if "Termux" in t:
        return f"{t}。Android 上的 Linux 环境，配置、API 或安装包。"
    if "wiki" in t.lower() or "Wiki" in t:
        return f"{t}。百科资料站，查设定、条目、教程。"
    if "软件仓库" in tags and ("镜像" in t or "软仓" in t):
        return f"{t}。软件下载站，装包、绿色版、仓库导航一类。"
    if t in ("今日热榜",):
        return "各站热搜汇总，刷新闻和风向用。"
    if "慕课" in t or "MOOC" in t or "学堂" in t:
        return f"{t}。网课平台，课程和作业在这。"
    if "题库" in t or "刷题" in t:
        return f"{t}。刷题/搜题，考试前抱佛脚。"
    if "图片素材" in t or "视频素材" in t:
        return f"{t}。免费用的素材库，商用条款自己看一眼。"
    if "压缩" in t:
        return f"{t}。在线压文件或音视频，图方便，隐私要求高就别上传。"
    if "密码" in t:
        return f"{t}。密码生成或常见弱口令列表，自己管密钥用。"
    if tags[:1] == ["赞助"]:
        return f"{t}。打赏/卖货平台，给创作者塞钱或上架小商品。"
    if "云" in tags and ("云" in t or "CDN" in t or "开站" in t):
        return f"{t}。云主机或静态托管，部署站点用。"

    tone = {
        "AI": "AI 向：生成、试模型、当助手。",
        "开发": "开发向：文档、仓库、小工具。",
        "网络安全": "信安向：查洞、扫样本、练靶。别对外乱打。",
        "匿名": "临时身份：邮箱、接码、匿名邮件。",
        "我的世界": "Minecraft 生态：模组、服务端、皮肤、资料。",
        "米哈游": "米哈游游戏相关，官服或社区。",
        "游戏": "游戏相关资源和工具。",
        "学习": "课程、题库或自学资料。",
        "博客": "个人博客，想到再翻。",
        "设计": "设计灵感、模板或配色。",
        "图像": "图片处理或图库。",
        "视频": "视频编辑、解析或素材。",
        "音频": "音频编辑、素材或电台。",
        "网络": "网络工具：测速、穿透、组网、IP。",
        "部署": "部署/运维向，服务端和面板。",
        "政府": "官方站点，查政策、考试或公示。",
        "求职": "找工作、简历或刷题面试。",
        "wiki": "百科，查条目用。",
        "文档": "文档、字体、写作辅助。",
        "工具": "杂项在线工具。",
        "软件仓库": "装软件、下安装包。",
        "API": "模型或数据的 API 入口。",
        "系统": "PE、启动盘、影子系统一类。",
        "linux": "Linux 发行版或命令手册。",
        "termux": "Termux / 安卓终端。",
        "社区": "论坛或问答社区。",
        "云": "云厂商或 CDN。",
        "翻译": "翻译工具。",
        "网盘": "搜盘或网盘入口。",
        "文件传输": "临时传文件，大文件或加密链路。",
        "新闻": "资讯站。",
        "生活": "日常用的小应用。",
        "金融": "行情或盘面。",
        "硬件": "硬件/射频小工具。",
        "心理": "人格测试或量表，当玩。",
        "物流": "货运或快递查询。",
        "赞助": "打赏平台。",
        "3D": "三维建模或生成。",
        "安卓": "安卓开发或 Magisk 一类。",
        "其他": "先收着，用到再点。",
    }
    lead = tone.get(tags[0] if tags else "其他", "先收着，用到再点。")
    extra = leftover[0] if leftover else ""
    if extra and extra not in t:
        return f"{t}。{lead}（原分类备注：{extra}）"
    return f"{t}。{lead}"


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

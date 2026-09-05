# TukJiu's Dream

本地链接收藏夹的自然语言搜索。按需求描述查找已收藏的站点，而不是按分类目录浏览。

数据来源为 [stslinks.pages.dev](https://stslinks.pages.dev/)。本仓库实现命令行与本地网页，不复刻原站的分类导航与活链探测。

## 用途

收藏链接多了之后，标题和分类往往对不上当时的说法。本工具把「要干什么」写成查询，在本地 SQLite 收藏里检索对应网址，适合：

- 个人工具站、文档、镜像、临时邮箱等常用链接的自用检索
- 用口语描述需求（例如「临时邮箱」「对照着改翻译」），由模型在收藏范围内筛选
- 无接口额度或不想调用模型时，改走关键词本地匹配

默认在本机 `127.0.0.1:8765` 运行，密钥与数据库不进入 Git。

## 检索方式

1. **第一层**：用短标签快速收窄候选。
2. **第二层**：根据每条链接的长描述再筛一遍，避免只看标题或标签沾边就全部返回。
3. **仅本地**：关键词匹配，不调用模型。

网页上「搜索」走上述两层模型路径；接口失败不会改成静默本地搜索。「仅本地」才是关键词路径。

模型回复带固定人设（小鲸鱼）。运算过程中展示思考原文，出结果后收起，链接以卡片列出。

## 环境

- Python 3.12（`py -3` 或已加入 PATH 的解释器）
- 依赖见 `requirements.txt`：`openai`、`fastapi`、`uvicorn`

## 运行

```
init.cmd          # 安装依赖
start-web.cmd     # 网页 http://127.0.0.1:8765
start.cmd         # 命令行交互
```

或：

```
py -3 -m pip install -r requirements.txt
py -3 webapp.py
py -3 cli.py
```

常用命令：

```
py -3 cli.py search "翻译"
py -3 cli.py search "翻译" --local
py -3 cli.py add --title DeepL --url https://www.deepl.com --tags "翻译|工具"
py -3 cli.py list
py -3 cli.py tags
py -3 cli.py rm 12
py -3 cli.py config
py -3 cli.py recat
```

`recat` 按规则整理标签并补全空描述，不调用模型。

## 配置

复制 `config.example.json` 为 `config.json`。若存在旧的 `api-key.txt`，首次启动会迁入配置。

可配置多层 OpenAI 兼容接口：`active` 优先，失败后按列表其余有密钥的层回退。

```json
{
  "active": "uuapi",
  "providers": [
    {
      "name": "uuapi",
      "base_url": "https://uuapi.io/v1",
      "model": "gpt-5.6-terra",
      "api_key": "",
      "thinking": false
    },
    {
      "name": "deepseek",
      "base_url": "https://api.deepseek.com",
      "model": "deepseek-v4-flash",
      "api_key": "",
      "thinking": true
    }
  ]
}
```

网页设置中可改当前层、Base URL、密钥、模型，以及是否开启思考过程。中 / EN 可切换界面语言。

下列文件不进入版本库：`config.json`、`api-key.txt`、`data.db`。

## 目录

| 路径 | 说明 |
| --- | --- |
| `cli.py` | 命令行入口 |
| `webapp.py` | 本地网页（FastAPI） |
| `web/` | 前端静态文件 |
| `fav/` | 配置、数据库、两层检索与分类规则 |
| `config.example.json` | 配置样例（不含密钥） |

## 说明

- 本仓库所有者：[SudaZitong](https://github.com/SudaZitong)
- 原始站点与数据：[TukJiu's Dream](https://stslinks.pages.dev/)
- 本仓库的命令行/网页实现由 Grok（xAI）按需求 vibe coding 完成

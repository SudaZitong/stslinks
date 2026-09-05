# TukJiu's Dream

个人链接收藏夹。原站：[stslinks.pages.dev](https://stslinks.pages.dev/)。

按 CLI 原设计做成搜索：短标签第一层快速匹配，长描述第二层筛选。没 token 是现状，不是产品设计。原站 stslinks.pages.dev 只是数据来源，不复刻分类导航。

## 运行

```
init.cmd          # 装依赖
start-web.cmd     # 网页 http://127.0.0.1:8765
start.cmd         # 命令行
```

或：

```
py -3 -m pip install -r requirements.txt
py -3 webapp.py
py -3 cli.py
py -3 cli.py search "翻译"
py -3 cli.py add --title DeepL --url https://www.deepl.com --tags "翻译|工具"
```

## 配置

复制 `config.example.json` 为 `config.json`。旧的 `api-key.txt` 会在首次启动时自动迁进去。

```json
{
  "api_key": "",
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-v4-flash",
  "thinking": true
}
```

换服务商只改这三项，例如 xAI：

```json
{
  "api_key": "",
  "base_url": "https://api.x.ai/v1",
  "model": "grok-4.5",
  "thinking": false
}
```

`config.json`、`api-key.txt`、`data.db` 不进 Git。

## 网页

- 搜索框为主（搜索 = 小鲸鱼，失败自动本地；仅本地不走接口）
- 添加 / 编辑链接
- 设置里改 base_url、key、model
- 中 / EN
- `py -3 cli.py recat` 整理标签和空描述

原站点分类的导航没有复刻。活链探测也没搬。

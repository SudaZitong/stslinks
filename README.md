# TukJiu's Dream

个人链接收藏夹。原站：[stslinks.pages.dev](https://stslinks.pages.dev/)。

分类芯片 + 并且/或者筛选沿用原站；手机和自然语言搜索走小鲸鱼（任意 OpenAI 兼容接口）。网页和 CLI 共用同一份 SQLite。

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

- 点击分类显示链接（并且 / 或者、显示所有 / 隐藏所有）
- 本地搜、小鲸鱼搜
- 添加 / 编辑链接
- 设置里改 base_url、key、model
- 中 / EN

原站「活链探测」依赖已下线的本地端口，网页版没有搬过来。

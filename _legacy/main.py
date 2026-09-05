import time
from tqdm import tqdm
import json
from openai import OpenAI
import sqlite3
import re

# 伪流式输出显示 用来显得这个不咋样的小程序好像有点实力
def show(content):
    content += "\n"
    for text in content:
        if text == "\n":
            time.sleep(0.05)
        print(text, end="", flush=True)
        time.sleep(0.01)
    time.sleep(0.3)

# 获取API密钥
api_key = None
try:
    with open("api-key.txt", 'r', encoding='utf-8') as f:
        api_key = f.read().strip()
except FileNotFoundError:
    show("请将Deepseek API密钥保存在api-key.txt文件中")
    exit()
except Exception as e:
    show(f"获取Deepseek API密钥时出错: {e}")
    exit()
if api_key == None:
    show("请将Deepseek API密钥保存在api-key.txt文件中")
    exit()


# DeepSeek API 暂时不考虑兼容其他baseurl
client = OpenAI(
    api_key=api_key, 
    base_url="https://api.deepseek.com"
)

# 数据准备
all_tags = []
selected_tags = []
all_links = []
def_selected_links = []
agent_selected_links = []

# 获取数据
sqlite_file = "data.db"
conn = sqlite3.connect(sqlite_file)
cursor = conn.cursor()
# 如果表不存在，创建可用链接表
cursor.execute("create table if not exists links (id integer primary key autoincrement not null,title text,tags text, desc text, url text)")
cursor.fetchall()
# 拉取所有tag
cursor.execute("SELECT DISTINCT tags FROM links")
all_tags = cursor.fetchall()
tag_tmp = []
for tag in tqdm(all_tags, desc="收藏夹初始化 - 记录标签", leave=True):
    tag = re.findall(r"\(\s*['\"](.+?)['\"]\s*,?\s*\)", str(tag))
    tmp = []
    for t in tag:
        t = t.split("|")
        tmp += t
    tag = tmp
    tag_tmp += tag
all_tags = list(set(tag_tmp))
# 拉取所有链接
cursor.execute("SELECT * FROM links")
all_links = cursor.fetchall()
all_links = [{"id": link[0], "title": link[1], "tags": link[2], "desc": link[3], "url": link[4]} for link in tqdm(all_links, desc="收藏夹初始化 - 记录链接", leave=True)]
  # 单独对tag进行二次解析
for link in tqdm(all_links, desc="收藏夹初始化 - 记录链接", leave=True):
    link["tags"] = link["tags"].split("|")
    link["tags"] = [tag for tag in link["tags"] if tag != ""]
    link["tags"] = [tag.strip() for tag in link["tags"]]

# print(all_tags)
# print(all_links)
# exit()

def select_link(selected_tags, mode):
    if mode == "and":
        def_selected_links = all_links.copy()
        def_selected_links = [link for link in tqdm(all_links, desc="通过标签筛选链接", leave=True) if all(tag in link["tags"] for tag in selected_tags)]
    elif mode == "or":
        def_selected_links = all_links.copy()
        def_selected_links = [link for link in tqdm(all_links, desc="通过标签筛选链接", leave=True) if any(tag in link["tags"] for tag in selected_tags)]
    def_selected_links = [
    {
        "id": link["id"],
        "title": link["title"],
        "desc": link["desc"]
    }
    for link in tqdm(def_selected_links, desc="准备下一轮输入", leave=True)
    ]
    return def_selected_links

def showlinks(agent_selected_links):
    # 根据agent提供的链接id从所有连接中展示链接
    for li in agent_selected_links:
        link = [link for link in all_links if link["id"] == li][0]
        # print(link)
        # print(link.keys())
        show(f"{link['id']}. {link['title']} - {link['url']}")

# AI判断部分
selectTagPrompt = """
你是一个帮助用户筛选收藏夹链接的deepseek小鲸鱼，负责从给定的收藏夹的分类中根据用户的需求选取相关标签，用户将会访问被标签选中的程序为用户选取的链接。
用户的需求模糊时，推荐可能相关或用得到的标签，但要在msg字段额外说明选择与实际存在的偏差。
你需要以JSON的格式输出三个字段：tags, mode, ok, msg。
tags字段为匹配的标签，以JSON数组形式返回，如果没有匹配的标签，返回空数组。
mode字段为模式，可以有or（并集）或and（交集），用于链接的匹配，or代表链接内包含任一匹配标签就可以被选中，and代表链接需要同时包含所有标签才会被选中。
ok字段为是否匹配成功，可选值有：true，false。此选项将会影响整条消息是否有效，但msg还是可以正常输出。如果tags为空，请返回false。
msg字段写评价，可以是调侃或解释。如果用户的需求不正常，以deepseek小鲸鱼的身份略有攻击力的调侃用户。
示例：
{
    "tags": [],
    "mode": "and",
    "ok": false,
    "msg": "只发个喵喵喵，你喵个雷霆啊"
}

""" + f"可选标签：{json.dumps(all_tags, ensure_ascii=False)}"
selectLinkPrompt = """
你是一个帮助用户筛选收藏夹链接的deepseek小鲸鱼，负责从给定的收藏夹的id title标题和desc描述中根据用户的需求选取相关链接的id，用户将会访问被选中的链接。
用户的需求模糊时，推荐可能相关或用得到的链接，但要在msg字段额外说明选择与实际存在的偏差。
你需要以JSON的格式输出三个字段：links, ok, msg。
links字段为匹配的链接编号，以JSON数组形式返回。如果没有匹配的链接，返回空数组。
ok字段为是否匹配成功，可选值有：true，false。此选项将会影响整条消息是否有效，但msg还是可以正常输出。如果links为空，请返回false。
msg字段写评价，可以是调侃或解释。如果没有匹配的链接，请给出浏览器搜索关键词建议或完整搜索的表达式（例如：猫娘 +wiki -csdn）。
示例：
{
    "links": [1,2],
    "ok": true,
    "msg": "想要看猫娘吗？去看看猫娘服务站和喵呜wiki吧！"
}

"""

def get_tags(prompt):
    show("===")
    answer = None
    with client.chat.completions.stream(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": selectTagPrompt},
            # {"role": "latest_reminder", "content": str(all_tags)},
            {"role": "user","content":prompt}
        ],
        reasoning_effort="low",
        extra_body={"thinking": {"type": "enabled"}}
    )  as stream:
        # 流式输出思考过程
        for event in stream:
            if event.type == "chunk":
                if event.chunk.choices[0].delta.reasoning_content:
                    print(event.chunk.choices[0].delta.reasoning_content, end="", flush=True)
        # 在流式结束后获取完整的结果对象
        completion = stream.get_final_completion()
        # 处理最终结果
        answer = completion.choices[0].message.content
    # 打印花销统计
        show(f"\n本次花销: {completion.usage.total_tokens} tokens")
    return answer

def get_links(prompt):
    show("===")
    answer = None
    with client.chat.completions.stream(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": selectLinkPrompt + f"可选链接：{json.dumps(def_selected_links, ensure_ascii=False)}"},
            # {"role": "latest_reminder", "content": str(def_selected_links)},
            {"role": "user","content":prompt}
        ],
        reasoning_effort="low",
        extra_body={"thinking": {"type": "enabled"}}
    )  as stream:
        # 流式输出思考过程
        for event in stream:
            if event.type == "chunk":
                if event.chunk.choices[0].delta.reasoning_content:
                    print(event.chunk.choices[0].delta.reasoning_content, end="", flush=True)
        # 在流式结束后获取完整的结果对象
        completion = stream.get_final_completion()
        # 处理最终结果
        answer = completion.choices[0].message.content
    # 打印花销统计
        show(f"\n本次花销: {completion.usage.total_tokens} tokens")
    return answer

# 用户交互逻辑

while True:
    show("===")
    show("[收藏夹] 使用Ctrl+C 退出程序")
    show("[收藏夹] 要做什么？")
    print("请输入 >>> ", end="")
    test = input()
    if test.strip() == "":
        show("请输入需求")
        continue
    geted_tags = get_tags(test)
    json_data = None
    try:
        json_data = json.loads(geted_tags)
    except Exception as e:
        show(f"数据异常，可能是偶尔的ai幻觉，请稍后再试：{geted_tags} \n\n {e}")
        continue
    if json_data["ok"] == False: 
        show("小鲸鱼无法做出选择")
        show(json_data["msg"])
        continue
    else:
        selected_tags = json_data["tags"]
        mode = json_data["mode"]
        show(f"小鲸鱼已选择标签：{selected_tags}，搜索模式：{mode}")
        show(json_data["msg"])
        def_selected_links = select_link(selected_tags, mode)
        geted_links = get_links(test)
        try:
            json_data = json.loads(geted_links)
        except Exception as e:
            show(f"数据异常，可能是偶尔的ai幻觉，请稍后再试：{geted_links} \n\n {e}")
            continue
        if json_data["ok"] == False: 
            show("小鲸鱼找不到匹配的链接")
            show(json_data["msg"])
            continue
        else:
            agent_selected_links = json_data["links"]
            show(f"小鲸鱼已选择链接编号：{agent_selected_links}")
            show(json_data["msg"])
            show("===")
            show("[收藏夹] 使用 Ctrl+鼠标左键 调用浏览器")
            show("[收藏夹] 可用的链接列表：")
            showlinks(agent_selected_links)
            continue
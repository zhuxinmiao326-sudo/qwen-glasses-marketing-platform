#!/usr/bin/env python3
"""每日采集全网热点并生成千问 AI 眼镜选题。"""

import json
import os
import re
import datetime
import requests

OUTPUT_DIR = "data"
ARCHIVE_DIR = "archive"
TOPIC_LIMIT = 50

CATEGORY_KEYWORDS = {
    "科技/AI": ["AI", "人工智能", "大模型", "芯片", "机器人", "无人机", "智能", "科技", "算法", "算力", "OpenAI", "千问", "眼镜", "AR", "VR", "Vision"],
    "职场/办公": ["工作", "职场", "办公", "面试", "简历", "PPT", "Excel", "会议", "合同", "薪资", "加班", "领导", "同事", "升职", "裁员"],
    "生活/社会": ["生活", "社会", "家庭", "婚姻", "恋爱", "情感", "教育", "孩子", "养老", "城市", "房价", "租房", "宠物", "美食", "穿搭"],
    "娱乐/影视": ["电影", "电视剧", "综艺", "明星", "演唱会", "娱乐圈", "票房", "剧集", "歌手", "热播", "新剧", "杀青"],
    "旅游/户外": ["旅游", "旅行", "景点", "酒店", "机票", "户外", "露营", "徒步", "登山", "海边", "古镇", "打卡", "攻略"],
    "健康/运动": ["健康", "运动", "健身", "减肥", "跑步", "瑜伽", "睡眠", "体检", "养生", "医疗", "医院", "医生"],
    "财经/商业": ["股市", "基金", "A股", "房价", "经济", "企业", "公司", "财报", "投资", "理财", "消费", "电商", "直播带货"],
}

ANGLE_TEMPLATES = {
    "科技/AI": {
        "angle": "用 AI 眼镜第一视角做体验/评测，语音调用千问多模态能力完成实时识别与总结。",
        "ideas": [
            "POV 开箱：戴上眼镜直击热点科技事件/新品发布",
            "语音实测：让眼镜解读这条科技新闻并给出观点",
            "街头采访：路人如何用 AI 眼镜看懂这件事"
        ]
    },
    "职场/办公": {
        "angle": "把 AI 眼镜变成随身办公助理，解放双手完成记录、翻译、检索。",
        "ideas": [
            "会议 POV：眼镜全程记录并生成会议纪要",
            "合同/文件速读：第一视角让 AI 划出重点与风险",
            "通勤学习：语音让眼镜整理行业热点与邮件摘要"
        ]
    },
    "生活/社会": {
        "angle": "以第一人称视角记录真实生活，AI 自动提炼为可发布的社交内容。",
        "ideas": [
            "热点事件亲历：眼镜视角下的城市生活切片",
            "Vlog 自动生成：出门一天，AI 帮你剪出高光片段",
            "生活小贴士：看到社会话题，让眼镜给出理性解读"
        ]
    },
    "娱乐/影视": {
        "angle": "用 AI 眼镜打造沉浸式观影与追综艺体验，实时字幕、弹幕、语音搜片。",
        "ideas": [
            "影院/居家观影 POV：眼镜里的实时字幕与彩蛋识别",
            "综艺同款挑战：让眼镜识别场景并模仿玩法",
            "明星/剧集二创：第一视角 Reaction + AI 自动字幕"
        ]
    },
    "旅游/户外": {
        "angle": "不掏手机的眼镜导游，导航、识别、翻译、拍照一站完成。",
        "ideas": [
            "景区打卡 POV：眼镜识别建筑/文物并语音讲解",
            "旅行 vlog：边走边拍，AI 自动配字幕与路线",
            "海外出行：实时翻译路牌、菜单、对话"
        ]
    },
    "健康/运动": {
        "angle": "运动场景下解放双手，AI 眼镜记录动作、播报数据、提醒安全。",
        "ideas": [
            "跑步/骑行 POV：实时配速与路线导航",
            "健身跟练：眼镜识别动作并给出纠正建议",
            "户外安全：语音触发紧急联系与位置共享"
        ]
    },
    "财经/商业": {
        "angle": "随身财经资讯助理，语音播报热点、AI 解读数据。",
        "ideas": [
            "晨间财经早报：让眼镜播报今日市场热点",
            "财报速读：AI 提炼关键数字与风险提示",
            "消费洞察：第一视角逛店，眼镜分析商品卖点"
        ]
    },
}

SAMPLE_TOPICS = [
    {"title": "AI 眼镜会成为下一代计算平台吗", "heat": 9800000},
    {"title": "打工人如何用 AI 工具提升效率", "heat": 8500000},
    {"title": "暑期旅游城市热度排行榜出炉", "heat": 7200000},
    {"title": "国产大模型多模态能力再升级", "heat": 6900000},
    {"title": "职场人必备的智能穿戴设备", "heat": 5400000},
    {"title": "年轻人开始用 AI 辅助健身", "heat": 4800000},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch_toutiao():
    url = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = []
    for entry in data.get("data", [])[:TOPIC_LIMIT]:
        title = entry.get("Title", "").strip()
        heat = int(entry.get("HotValue", 0) or 0)
        if title:
            items.append({"title": title, "desc": "", "heat": heat, "source": "头条热榜"})
    return items


def fetch_weibo():
    url = "https://weibo.com/ajax/side/hotSearch"
    headers = {**HEADERS, "Referer": "https://weibo.com/hot/search"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = []
    for entry in data.get("data", {}).get("realtime", [])[:TOPIC_LIMIT]:
        title = entry.get("word", "").strip()
        heat = int(entry.get("num", 0) or 0)
        if title:
            items.append({"title": title, "desc": entry.get("note", ""), "heat": heat, "source": "微博热搜"})
    return items


def fetch_baidu():
    url = "https://top.baidu.com/api/board?platform=wise&tab=realtime"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = []
    cards = data.get("data", {}).get("cards", [])
    if cards and "content" in cards[0] and len(cards[0]["content"]) > 0:
        entries = cards[0]["content"][0].get("content", [])
        total = len(entries)
        for entry in entries[:TOPIC_LIMIT]:
            title = entry.get("word", "").strip()
            idx = entry.get("index", total)
            # 没有热度值时用排名倒序生成相对热度
            heat = (total + 1 - idx) * 100000 if isinstance(idx, int) and idx > 0 else 0
            if title:
                items.append({"title": title, "desc": "", "heat": heat, "source": "百度热搜"})
    return items


def fetch_zhihu():
    url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50"
    headers = {**HEADERS, "Referer": "https://www.zhihu.com/hot"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    items = []
    for entry in data.get("data", [])[:TOPIC_LIMIT]:
        target = entry.get("target", {})
        title = target.get("title", "").strip()
        excerpt = target.get("excerpt", "").strip()
        heat_text = entry.get("detail_text", "0")
        heat = parse_heat(heat_text)
        if title:
            items.append({"title": title, "desc": excerpt, "heat": heat, "source": "知乎热榜"})
    return items


def parse_heat(text):
    if not text:
        return 0
    text = str(text).replace(",", "").strip()
    match = re.search(r"(\d+(\.\d+)?)", text)
    if not match:
        return 0
    value = float(match.group(1))
    if "万" in text:
        value *= 10000
    elif "亿" in text:
        value *= 100000000
    return int(value)


def categorize(title):
    for cat, words in CATEGORY_KEYWORDS.items():
        if any(w.lower() in title.lower() for w in words):
            return cat
    return "其他"


def build_angle_and_ideas(title, category):
    tpl = ANGLE_TEMPLATES.get(category, {
        "angle": "捕捉热点中的可拍摄/可交互场景，用 AI 眼镜第一视角做出差异化内容。",
        "ideas": [
            "热点 POV：戴上眼镜走进这条热点的真实场景",
            "AI 解读：让眼镜语音总结事件并给出独特观点",
            "轻互动挑战：邀请用户用眼镜完成一个与热点相关的小任务"
        ]
    })
    return {
        "glassesAngle": tpl["angle"],
        "contentIdeas": tpl["ideas"]
    }


def collect():
    all_items = []
    sources = []

    fetchers = [
        ("头条热榜", fetch_toutiao),
        ("微博热搜", fetch_weibo),
        ("百度热搜", fetch_baidu),
        ("知乎热榜", fetch_zhihu),
    ]

    for name, fn in fetchers:
        try:
            items = fn()
            all_items.extend(items)
            sources.append({"name": name, "count": len(items)})
        except Exception as e:
            print(f"{name} 采集失败: {e}")

    if not all_items:
        print("使用示例数据兜底")
        for t in SAMPLE_TOPICS:
            all_items.append({"title": t["title"], "desc": "", "heat": t["heat"], "source": "示例数据"})
        sources.append({"name": "示例数据", "count": len(SAMPLE_TOPICS)})

    # 去重：相同标题取最高热度与最早来源
    seen = {}
    for item in all_items:
        key = item["title"]
        if key not in seen or item.get("heat", 0) > seen[key].get("heat", 0):
            seen[key] = item
    unique_items = list(seen.values())
    unique_items.sort(key=lambda x: x.get("heat", 0), reverse=True)

    topics = []
    for idx, item in enumerate(unique_items[:TOPIC_LIMIT], start=1):
        category = categorize(item["title"])
        angle_info = build_angle_and_ideas(item["title"], category)
        topics.append({
            "id": f"{today_str()}-{idx:03d}",
            "rank": idx,
            "title": item["title"],
            "desc": item.get("desc", ""),
            "heat": item.get("heat", 0),
            "source": item.get("source", "未知来源"),
            "category": category,
            **angle_info
        })

    return topics, sources


def today_str():
    tz = datetime.timezone(datetime.timedelta(hours=8))
    return datetime.datetime.now(tz).strftime("%Y-%m-%d")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    topics, sources = collect()
    updated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    result = {
        "date": today_str(),
        "updatedAt": updated_at,
        "sources": sources,
        "topics": topics,
    }

    with open(os.path.join(OUTPUT_DIR, "hot-topics.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    archive_path = os.path.join(ARCHIVE_DIR, f"{today_str()}.json")
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    dates = sorted(
        [f.replace(".json", "") for f in os.listdir(ARCHIVE_DIR) if f.endswith(".json")],
        reverse=True
    )
    history = {"dates": dates, "updatedAt": updated_at}
    with open(os.path.join(OUTPUT_DIR, "history.json"), "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    print(f"✅ 完成：{today_str()}，共 {len(topics)} 条选题，来源：{sources}")


if __name__ == "__main__":
    main()

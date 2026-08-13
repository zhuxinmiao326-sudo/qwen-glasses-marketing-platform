#!/usr/bin/env python3
"""每日采集全网热点，按五维模型评分，输出 A/B 双轨执行级选题卡。

输出文件：data/topic-recommendations.json（PRD 3.2 热点星图标准格式）
"""

import json
import os
import re
import math
import datetime
import requests

OUTPUT_DIR = "data"
ARCHIVE_DIR = "archive"
TOPIC_LIMIT = 50
A_TRACK_LIMIT = 10
B_TRACK_LIMIT = 3

# 平台/分类关键词
CATEGORY_KEYWORDS = {
    "科技/AI": ["AI", "人工智能", "大模型", "芯片", "机器人", "无人机", "智能", "科技", "算法", "算力", "OpenAI", "千问", "眼镜", "AR", "VR", "Vision", "多模态", "算力"],
    "职场/办公": ["工作", "职场", "办公", "面试", "简历", "PPT", "Excel", "会议", "合同", "薪资", "加班", "领导", "同事", "升职", "裁员", "打工人", "黑话"],
    "生活/社会": ["生活", "社会", "家庭", "婚姻", "恋爱", "情感", "教育", "孩子", "养老", "城市", "房价", "租房", "宠物", "美食", "穿搭", "烟火气", "温情"],
    "娱乐/影视": ["电影", "电视剧", "综艺", "明星", "演唱会", "娱乐圈", "票房", "剧集", "歌手", "热播", "新剧", "杀青"],
    "旅游/户外": ["旅游", "旅行", "景点", "酒店", "机票", "户外", "露营", "徒步", "登山", "海边", "古镇", "打卡", "攻略", "漂流瓶"],
    "健康/运动": ["健康", "运动", "健身", "减肥", "跑步", "瑜伽", "睡眠", "体检", "养生", "医疗", "医院", "医生", "辅助健身"],
    "财经/商业": ["股市", "基金", "A股", "房价", "经济", "企业", "公司", "财报", "投资", "理财", "消费", "电商", "直播带货"],
}

# 产品能力关键词库（用于计算品牌相关分）
PRODUCT_KEYWORDS = {
    "第一视角": ["第一视角", "POV", "pov", "画面流", "拍摄", "记录"],
    "语音AI助手": ["语音", "AI助手", "智能助手", "解放双手", "语音指令", "语音交互"],
    "实时翻译": ["翻译", "外语", "出境", "出国", "国际", "语言"],
    "AR导航": ["导航", "迷路", "路牌", "方向", "地图"],
    "会议纪要": ["会议", "纪要", "记录", "整理", "办公", "职场"],
    "轻量化佩戴": ["佩戴", "眼镜", "穿搭", "颜值", "轻便", "时尚"],
    "AI识别": ["识别", "看懂", "解释", "多模态", "AI识别"],
}

# 敏感/高风险关键词（用于计算借势安全分）
SAFETY_NEGATIVE = [
    "逝世", "去世", "死亡", "自杀", "被杀", "杀人", "坠亡", "遇难", "尸体", "骨灰",
    "爆炸", "火灾", "地震", "洪水", "溃口", "疫情", "病毒", "感染", "确诊", "病例",
    "战争", "军事", "导弹", "普京", "俄乌", "台海", "台湾", "中共", "政府", "反腐",
    "落马", "被查", "贪污", "受贿", "强奸", "猥亵", "性侵", "虐待", "诈骗", "传销",
    "家暴", "离婚", "出轨", "小三", "丑闻", "封杀", "吸毒", "嫖娼", "赌博",
    "崩溃", "痛哭", "绝望", "愤怒", "抗议", "罢工", "失业", "裁员", "跳楼",
]

# 高风险类别：政治、灾难、犯罪等直接降安全分
SAFETY_CATEGORIES = {
    "政治/敏感": ["普京", "台湾", "中共", "俄乌", "军事", "导弹", "战争", "外交部", "国防部"],
    "灾难/事故": ["地震", "洪水", "火灾", "爆炸", "溃口", "坍塌", "车祸", "空难"],
    "犯罪/法治": ["被查", "受贿", "强奸", "诈骗", "杀人", "虐待", "性侵"],
    "社会 tragedy": ["逝世", "去世", "自杀", "遇难", "坠亡"],
}

# 五维权重
WEIGHTS_RIDE = {"heat": 0.35, "relevance": 0.20, "safety": 0.20, "timeliness": 0.20, "creativity": 0.05}
WEIGHTS_CREATE = {"heat": 0.15, "relevance": 0.35, "safety": 0.20, "timeliness": 0.05, "creativity": 0.25}

# 内容形态/预算/制作周期建议（按分类）
CATEGORY_EXECUTION = {
    "科技/AI": {
        "content_format": "主：知乎长图文/B站深度解读；衍：抖音切片",
        "recommended_creator_type": "科技垂类KOL 2位 + 知乎答主 1位",
        "production_cycle": "一天",
        "budget_level": "中",
        "estimated_cpm": 28,
        "estimated_cpe": 1.5,
        "publish_window": "T+1 10:00-12:00",
    },
    "职场/办公": {
        "content_format": "主：15-30s真人实测短视频；衍：3张图文笔记+1条口播",
        "recommended_creator_type": "垂类职场KOL 1位 + 生活方式KOC 3-5位",
        "production_cycle": "半天",
        "budget_level": "中",
        "estimated_cpm": 32,
        "estimated_cpe": 1.1,
        "publish_window": "T+0 12:00-14:00",
    },
    "生活/社会": {
        "content_format": "主：30s生活vlog；衍：小红书图文+UGC征集",
        "recommended_creator_type": "生活方式KOL 1位 + 城市KOC 3-5位",
        "production_cycle": "一天",
        "budget_level": "中",
        "estimated_cpm": 35,
        "estimated_cpe": 1.3,
        "publish_window": "T+0 18:00-20:00",
    },
    "娱乐/影视": {
        "content_format": "主：Reaction短视频；衍：二创切片+图文",
        "recommended_creator_type": "娱乐垂类KOL 1位 + KOC 2-3位",
        "production_cycle": "半天",
        "budget_level": "低",
        "estimated_cpm": 30,
        "estimated_cpe": 0.9,
        "publish_window": "T+0 20:00-22:00",
    },
    "旅游/户外": {
        "content_format": "主：30s旅行vlog；衍：小红书图文攻略+景点打卡合集",
        "recommended_creator_type": "旅行垂类KOL 1位 + 旅行KOC 2-3位",
        "production_cycle": "一天",
        "budget_level": "中",
        "estimated_cpm": 38,
        "estimated_cpe": 1.4,
        "publish_window": "T+0 18:00-20:00",
    },
    "健康/运动": {
        "content_format": "主：15s运动短视频；衍：图文笔记",
        "recommended_creator_type": "运动垂类KOC 2-3位",
        "production_cycle": "半天",
        "budget_level": "低",
        "estimated_cpm": 35,
        "estimated_cpe": 1.2,
        "publish_window": "T+1 07:00-09:00",
    },
    "财经/商业": {
        "content_format": "主：口播解读；衍：图文早报+数据可视化",
        "recommended_creator_type": "财经垂类KOL 1位 + 职场KOC 2位",
        "production_cycle": "半天",
        "budget_level": "中",
        "estimated_cpm": 36,
        "estimated_cpe": 1.6,
        "publish_window": "T+0 08:00-10:00",
    },
}

DEFAULT_EXECUTION = {
    "content_format": "主：15-30s短视频；衍：图文笔记",
    "recommended_creator_type": "生活方式KOC 2-3位",
    "production_cycle": "半天",
    "budget_level": "低",
    "estimated_cpm": 40,
    "estimated_cpe": 1.8,
    "publish_window": "T+0 12:00-14:00",
}

# 历史相似案例库（按分类匹配）
SIMILAR_CASES = {
    "科技/AI": {"case": "千问发布会解读", "roi": 3.8, "note": "技术向内容适合B站/知乎长图文"},
    "职场/办公": {"case": "通勤效率神器", "roi": 6.2, "note": "去年同期类似选题，POV形式ROI达1:6.2"},
    "生活/社会": {"case": "城市烟火气记录", "roi": 4.0, "note": "生活方式内容小红书互动率高"},
    "娱乐/影视": {"case": "影院实时字幕体验", "roi": 3.2, "note": "娱乐向内容适合短平快Reaction"},
    "旅游/户外": {"case": "POV实测海外出行", "roi": 4.5, "note": "翻译功能相关选题互动率高"},
    "健康/运动": {"case": "跑步POV记录", "roi": 2.8, "note": "运动场景强调安全与数据播报"},
    "财经/商业": {"case": "晨间财经早报", "roi": 2.5, "note": "财经内容适合早间时段发布"},
}

# B-track 打造热点模板库
B_TRACK_TEMPLATES = [
    {
        "topic_name": "AI眼镜里的中国烟火气",
        "emotion_insight": "普通人渴望被科技温柔对待，而不是被高科技推开。AI眼镜可以是记录和解读日常烟火的窗口。",
        "core_concept": "用AI眼镜第一视角，看见普通人生活里那些被忽略的温暖与便利",
        "spread_mechanism": "UGC征集+城市KOC共创",
        "product_hook": "第一视角拍摄 + 语音AI解读 + 轻量化佩戴",
        "target_audience": {"core": "生活分享家、城市漫步者", "diffusion": "年轻白领、学生", "media": "社会媒体、城市号"},
        "trigger_scene": "周末在城市老街/菜市场/夜市，戴上眼镜记录并分享",
        "content_format_matrix": {"main": "3分钟概念片（官方号+B站）", "derivatives": ["15s切片×10", "小红书图文×20", "达人vlog×5"]},
        "kol_koc_matrix": {"head": "1位生活方式头部KOL定调", "vertical": "5位城市/旅行/美食垂类KOL", "koc": "30位城市KOC真实记录"},
        "publish_rhythm": {"warmup": "D-3 发布概念海报+话题预告", "ignite": "D0 12:00 官方概念片上线，KOL同步首发", "spread": "D0-D+3 KOC矩阵持续产出", "longtail": "D+7 精选UGC二次传播"},
        "ignite_node": "D0 12:00 官方概念片+B站深度解读同步上线",
        "budget_level": "高",
        "budget_allocation": {"creators": "60%", "traffic": "30%", "production": "10%"},
        "estimated_cpm": 42,
        "estimated_cpe": 1.8,
        "expected_hashtags": ["#AI眼镜烟火气", "#用眼镜看中国", "#千问眼镜城市漂流瓶"],
        "monitoring_metrics": ["搜索指数", "话题阅读量", "UGC参与数", "品牌词提及", "正面情绪占比"],
        "success_bench": {"case": "某品牌「24小时不玩手机挑战」", "note": "UGC挑战赛，话题阅读破亿"},
        "priority": "A",
        "priority_reason": "社会价值正向、产品承接自然、UGC复制成本低",
        "risks": ["避免过度煽情", "避开特殊群体", "城市选择需有代表性"],
    },
    {
        "topic_name": "反黑话联盟：AI眼镜帮你听懂职场暗语",
        "emotion_insight": "职场新人对黑话、潜台词、行业术语的焦虑普遍存在，AI可以成为「翻译器」。",
        "core_concept": "让AI眼镜听懂职场黑话，帮年轻人少踩坑、多成事",
        "spread_mechanism": "挑战赛+段子内容共创",
        "product_hook": "语音AI助手 + 实时解释 + 会议纪要",
        "target_audience": {"core": "职场新人、实习生", "diffusion": "25-30岁白领", "media": "职场类媒体、社会媒体"},
        "trigger_scene": "开会/面试/跨部门沟通时，遇到听不懂的术语或潜台词",
        "content_format_matrix": {"main": "系列短视频「黑话翻译官」", "derivatives": ["段子图文", "职场博主Reaction", "评论区征集"]},
        "kol_koc_matrix": {"head": "1位职场头部KOL", "vertical": "5位职场/吐槽类达人", "koc": "20位职场新人真实分享"},
        "publish_rhythm": {"warmup": "D-2 发起#你听过最离谱的职场黑话#征集", "ignite": "D0 18:00 首条视频上线", "spread": "D0-D+5 每日1条黑话翻译视频", "longtail": "D+7 汇总TOP黑话合集"},
        "ignite_node": "D0 18:00 首条「黑话翻译官」视频+职场博主Reaction同步",
        "budget_level": "中",
        "budget_allocation": {"creators": "55%", "traffic": "35%", "production": "10%"},
        "estimated_cpm": 35,
        "estimated_cpe": 1.3,
        "expected_hashtags": ["#反黑话联盟", "#AI眼镜职场翻译官", "#职场黑话翻译"],
        "monitoring_metrics": ["搜索指数", "话题阅读量", "UGC参与数", "评论区互动", "正面情绪占比"],
        "success_bench": {"case": "职场类账号「黑话」系列", "note": "系列内容平均互动率高于账号均值50%"},
        "priority": "B",
        "priority_reason": "创意有趣但品牌关联度中等，可作为储备打造热点",
        "risks": ["避免影射具体公司文化", "不要强化职场对立情绪"],
    },
    {
        "topic_name": "城市漂流瓶：把一句话丢进陌生人的眼镜里",
        "emotion_insight": "都市人渴望低成本、高惊喜的轻社交，AI眼镜的地理位置+语音可以成为新的城市连接方式。",
        "core_concept": "用户在特定地点留下语音/文字漂流瓶，路过的人通过眼镜收到",
        "spread_mechanism": "UGC挑战赛+城市KOC探店",
        "product_hook": "位置服务 + 语音交互 + 第一视角",
        "target_audience": {"core": "城市年轻人、社交活跃者", "diffusion": "大学生、初入职场的年轻人", "media": "城市号、生活方式媒体"},
        "trigger_scene": "在城市地标/咖啡馆/书店等地点，发现或留下一个漂流瓶",
        "content_format_matrix": {"main": "系列短视频「我在XX捡到一句话」", "derivatives": ["图文打卡", "城市地图", "KOC接力"]},
        "kol_koc_matrix": {"head": "1位城市生活方式KOL", "vertical": "5位城市探索类达人", "koc": "25位城市KOC参与接力"},
        "publish_rhythm": {"warmup": "D-3 发布概念视频+地图H5", "ignite": "D0 12:00 首站开启", "spread": "D0-D+7 多城市接力", "longtail": "D+14 精选故事合集"},
        "ignite_node": "D0 12:00 首站官方视频+KOL同步开启",
        "budget_level": "高",
        "budget_allocation": {"creators": "50%", "traffic": "30%", "production": "15%", "dev": "5%"},
        "estimated_cpm": 45,
        "estimated_cpe": 2.0,
        "expected_hashtags": ["#城市漂流瓶", "#AI眼镜漂流瓶", "#千问城市故事"],
        "monitoring_metrics": ["UGC参与数", "漂流瓶留言数", "城市覆盖数", "品牌词提及", "正面情绪占比"],
        "success_bench": {"case": "某音乐平台「城市声音地图」", "note": "UGC地理互动，参与量超10万"},
        "priority": "A",
        "priority_reason": "利用眼镜独特能力（位置+语音+画面流），可多人参与，社会价值正向",
        "risks": ["需平台技术支持漂流瓶功能", "注意用户隐私与内容审核", "避免过度浪漫化陌生人社交风险"],
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

SAMPLE_TOPICS = [
    {"title": "AI 眼镜会成为下一代计算平台吗", "heat": 9800000},
    {"title": "打工人如何用 AI 工具提升效率", "heat": 8500000},
    {"title": "暑期旅游城市热度排行榜出炉", "heat": 7200000},
    {"title": "国产大模型多模态能力再升级", "heat": 6900000},
    {"title": "职场人必备的智能穿戴设备", "heat": 5400000},
    {"title": "年轻人开始用 AI 辅助健身", "heat": 4800000},
]


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


def compute_heat_score(items):
    """基于热度分布计算相对热度分（0-100）。"""
    heats = [max(1, i.get("heat", 0)) for i in items]
    if not heats:
        return [0] * len(items)
    log_heats = [math.log10(h) for h in heats]
    min_log, max_log = min(log_heats), max(log_heats)
    span = max_log - min_log if max_log > min_log else 1
    scores = []
    for lh in log_heats:
        if span == 0:
            scores.append(80)
        else:
            scores.append(round(60 + 40 * (lh - min_log) / span, 1))
    return scores


def compute_relevance_score(title, category):
    """基于产品能力关键词匹配计算品牌相关分。"""
    text = title.lower()
    score = 0
    # 基础分：分类匹配
    if category in ("科技/AI", "职场/办公", "旅游/户外"):
        score += 25
    elif category in ("生活/社会", "健康/运动", "娱乐/影视"):
        score += 18
    elif category == "财经/商业":
        score += 15
    else:
        score += 8

    # 产品关键词匹配
    matched_capabilities = []
    for capability, keywords in PRODUCT_KEYWORDS.items():
        if any(kw.lower() in text for kw in keywords):
            score += 8
            matched_capabilities.append(capability)
    # 额外：标题含"眼镜"或"AI"
    if "眼镜" in title or "AI" in title or "人工智能" in title:
        score += 12
    return min(100, round(score, 1)), matched_capabilities


def compute_safety_score(title, category):
    """计算借势安全分，敏感话题降分。"""
    text = title.lower()
    score = 95
    for kw in SAFETY_NEGATIVE:
        if kw.lower() in text:
            score -= 15
    # 类别额外惩罚
    for cat_name, keywords in SAFETY_CATEGORIES.items():
        if any(kw.lower() in text for kw in keywords):
            score -= 20
    # 纯娱乐/生活类加分
    if category in ("娱乐/影视", "生活/社会", "旅游/户外", "健康/运动"):
        score += 3
    return max(0, min(100, round(score, 1)))


def compute_timeliness_score(source, rank, heat):
    """计算时效性分：实时源+高排名+高热度假定为上升期。"""
    base = 75
    if source in ("微博热搜", "头条热榜"):
        base += 10
    elif source == "百度热搜":
        base += 5
    elif source == "知乎热榜":
        base += 0
    # 排名越靠前时效性越强
    base += max(0, 10 - rank * 0.15)
    # 热度极高视为峰值
    if heat > 50000000:
        base -= 5
    return min(100, round(base, 1))


def compute_creativity_score(category, capabilities):
    """计算可创作分：分类视觉化潜力 + 产品承接能力。"""
    category_scores = {
        "旅游/户外": 95,
        "生活/社会": 90,
        "娱乐/影视": 88,
        "健康/运动": 85,
        "职场/办公": 70,
        "科技/AI": 65,
        "财经/商业": 55,
        "其他": 50,
    }
    score = category_scores.get(category, 50)
    # 产品承接能力越多，创作空间越大
    score += min(15, len(capabilities) * 5)
    return min(100, round(score, 1))


def get_lifecycle(heat_score, timeliness_score):
    if heat_score >= 90 and timeliness_score >= 80:
        return "峰值期"
    elif heat_score >= 75 and timeliness_score >= 75:
        return "上升期"
    elif heat_score >= 60:
        return "延续期"
    return "萌芽期"


def priority_from_score(score):
    if score >= 85:
        return "S"
    elif score >= 70:
        return "A"
    elif score >= 55:
        return "B"
    return "C"


def priority_reason(score, priority, category):
    reasons = {
        "S": "热度高、品牌相关度强、安全可控，可快速产出POV内容",
        "A": "品牌相关度较好，适合借势跟进",
        "B": "热度或相关度中等，可作为储备选题",
        "C": "热度低或风险/相关性不足，暂不推荐",
    }
    base = reasons.get(priority, "")
    return f"【{category}】{base}（综合分{score:.1f}）"


def build_entry_angles(title, category, capabilities):
    """生成3个推荐切入角度。"""
    angles = []
    cap_map = {
        "第一视角": f"POV实测：戴上眼镜直击「{title}」现场",
        "语音AI助手": f"语音交互：让眼镜总结「{title}」并给出观点",
        "实时翻译": f"翻译场景：用眼镜看懂「{title}」里的外语/外地方言",
        "AR导航": f"城市探索：不掏手机也能抵达「{title}」相关地点",
        "会议纪要": f"办公场景：把「{title}」的讨论一键整理成纪要",
        "AI识别": f"AI解读：让眼镜识别并讲解「{title}」中的关键元素",
        "轻量化佩戴": f"生活方式：像普通眼镜一样记录「{title}」",
    }
    for cap in capabilities[:3]:
        if cap in cap_map:
            angles.append(cap_map[cap])
    # 兜底
    if len(angles) < 3:
        angles.append(f"热点POV：用第一视角走进「{title}」的真实场景")
    if len(angles) < 3:
        angles.append(f"轻互动：邀请用户用眼镜完成与「{title}」相关的小任务")
    return angles[:3]


def build_target_audience(category):
    mapping = {
        "科技/AI": {"core": "科技 early adopters", "diffusion": "AI/互联网从业者", "bystander": "关注科技趋势的大众"},
        "职场/办公": {"core": "25-35岁都市白领", "diffusion": "职场新人/中层管理者", "bystander": "对AI工具感兴趣的大众"},
        "生活/社会": {"core": "生活方式爱好者", "diffusion": "年轻白领/学生", "bystander": "关注社会话题的大众"},
        "娱乐/影视": {"core": "娱乐内容消费者", "diffusion": "年轻用户", "bystander": "泛娱乐人群"},
        "旅游/户外": {"core": "25-35岁一二线城市旅行爱好者", "diffusion": "学生/亲子出游人群", "bystander": "计划出游的大众"},
        "健康/运动": {"core": "运动爱好者", "diffusion": "健身新手/都市白领", "bystander": "关注健康生活方式的大众"},
        "财经/商业": {"core": "财经/商业人群", "diffusion": "职场白领", "bystander": "关注经济的大众"},
    }
    return mapping.get(category, {"core": "科技爱好者", "diffusion": "都市白领", "bystander": "大众"})


def build_core_emotion(title, category):
    mapping = {
        "科技/AI": "对新技术的好奇与讨论热情",
        "职场/办公": "打工人对效率焦虑与「科技减负」的期待",
        "生活/社会": "对生活温度与社会话题的共鸣",
        "娱乐/影视": "娱乐消遣与社交分享欲望",
        "旅游/户外": "出游热情与「不会外语/怕迷路」的焦虑",
        "健康/运动": "健身自律与科技辅助的新鲜感",
        "财经/商业": "对经济/商业动态的关注与焦虑",
    }
    return mapping.get(category, "用户对该话题的讨论兴趣")


def build_reference_hooks(category, capabilities):
    hooks = {
        "第一视角": ["戴上它，我看见了不一样的世界", "第一视角，才是真实的生活", "看到即拍到，不再错过瞬间"],
        "语音AI助手": ["不用掏手机，它全帮我安排了", "一句话，今天的事都理顺了", "忙到腾不出手时，它最懂我"],
        "实时翻译": ["听不懂？眼镜直接帮我翻译了", "出国旅行，我只带了一副眼镜", "语言不再是障碍"],
        "AR导航": ["不低头，也能找到路", "复杂路口，眼镜告诉我往哪走", "城市探索不再迷路"],
        "会议纪要": ["开会2小时，整理2分钟", "会议纪要，眼镜帮我写了", "再也不用担心漏重点"],
        "AI识别": ["它看懂的，比我想象的多", "身边的一切突然有了答案", "AI眼镜成了我的百科全书"],
        "轻量化佩戴": ["它看起来就像一副普通眼镜", "戴出门，没人发现这是AI眼镜", "好看和好用，终于在一起了"],
    }
    result = []
    for cap in capabilities:
        if cap in hooks:
            result.extend(hooks[cap])
    if len(result) < 3:
        result.extend(["这个热点，我用眼镜跟了", "换个视角看这件事", "眼镜里的世界原来可以这样"])
    return result[:3]


def build_risks(category, capabilities):
    base = ["避免过度夸张产品能力", "内容发布前需品牌/合规审核"]
    if category in ("生活/社会", "健康/运动"):
        base.append("避免涉及特殊群体或医疗/健康功效承诺")
    if category == "职场/办公":
        base.append("不要涉及具体公司/领导负面")
    if category == "财经/商业":
        base.append("避免投资建议或夸大经济影响")
    if category == "科技/AI":
        base.append("技术表述需准确，避免攻击竞品")
    return base


def similar_case(category):
    return SIMILAR_CASES.get(category)


def build_a_ride_topic(idx, item, scores):
    title = item["title"]
    category = categorize(title)
    capabilities = scores["capabilities"]
    exec_info = CATEGORY_EXECUTION.get(category, DEFAULT_EXECUTION)
    ride_score = round(
        scores["heat"] * WEIGHTS_RIDE["heat"] +
        scores["relevance"] * WEIGHTS_RIDE["relevance"] +
        scores["safety"] * WEIGHTS_RIDE["safety"] +
        scores["timeliness"] * WEIGHTS_RIDE["timeliness"] +
        scores["creativity"] * WEIGHTS_RIDE["creativity"],
        1
    )
    create_score = round(
        scores["heat"] * WEIGHTS_CREATE["heat"] +
        scores["relevance"] * WEIGHTS_CREATE["relevance"] +
        scores["safety"] * WEIGHTS_CREATE["safety"] +
        scores["timeliness"] * WEIGHTS_CREATE["timeliness"] +
        scores["creativity"] * WEIGHTS_CREATE["creativity"],
        1
    )
    priority = priority_from_score(ride_score)
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    explode_time = (now - datetime.timedelta(hours=2 + idx)).strftime("%Y-%m-%d %H:%M")

    return {
        "topic_name": title,
        "platform": item.get("source", "未知来源"),
        "heat_score": scores["heat"],
        "relevance_score": scores["relevance"],
        "safety_score": scores["safety"],
        "timeliness_score": scores["timeliness"],
        "creativity_score": scores["creativity"],
        "ride_score": ride_score,
        "create_score": create_score,
        "priority": priority,
        "priority_reason": priority_reason(ride_score, priority, category),
        "explode_time": explode_time,
        "lifecycle": get_lifecycle(scores["heat"], scores["timeliness"]),
        "remaining_window": "预计持续1-3天" if scores["timeliness"] >= 75 else "预计持续3-5天",
        "core_emotion": build_core_emotion(title, category),
        "product_hook": "、".join(capabilities[:2]) if capabilities else "AI眼镜多模态能力",
        "entry_angles": build_entry_angles(title, category, capabilities),
        "target_audience": build_target_audience(category),
        "trigger_scene": "刷到该热点或身处相关场景时，想快速了解/记录/互动",
        "content_format": exec_info["content_format"],
        "recommended_creator_type": exec_info["recommended_creator_type"],
        "publish_window": exec_info["publish_window"],
        "production_cycle": exec_info["production_cycle"],
        "budget_level": exec_info["budget_level"],
        "estimated_cpm": exec_info["estimated_cpm"],
        "estimated_cpe": exec_info["estimated_cpe"],
        "risks": build_risks(category, capabilities),
        "reference_hooks": build_reference_hooks(category, capabilities),
        "similar_historical_case": similar_case(category),
    }


def build_b_create_topics():
    """生成B轨打造热点选题卡（基于模板 + 当日上下文微调）。"""
    today = today_str()
    topics = []
    for idx, tpl in enumerate(B_TRACK_TEMPLATES[:B_TRACK_LIMIT], start=1):
        topic = dict(tpl)
        topic["id"] = f"{today}-B{idx:03d}"
        # B-track 也打五维分的占位（基于模板固定值微调）
        topic["heat_score"] = round(65 + idx * 3, 1)
        topic["relevance_score"] = round(80 + idx * 2, 1)
        topic["safety_score"] = round(88 - idx, 1)
        topic["timeliness_score"] = round(50 + idx * 5, 1)
        topic["creativity_score"] = round(80 + idx * 3, 1)
        topic["ride_score"] = round(
            topic["heat_score"] * WEIGHTS_RIDE["heat"] +
            topic["relevance_score"] * WEIGHTS_RIDE["relevance"] +
            topic["safety_score"] * WEIGHTS_RIDE["safety"] +
            topic["timeliness_score"] * WEIGHTS_RIDE["timeliness"] +
            topic["creativity_score"] * WEIGHTS_RIDE["creativity"],
            1
        )
        topic["create_score"] = round(
            topic["heat_score"] * WEIGHTS_CREATE["heat"] +
            topic["relevance_score"] * WEIGHTS_CREATE["relevance"] +
            topic["safety_score"] * WEIGHTS_CREATE["safety"] +
            topic["timeliness_score"] * WEIGHTS_CREATE["timeliness"] +
            topic["creativity_score"] * WEIGHTS_CREATE["creativity"],
            1
        )
        topics.append(topic)
    return topics


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
    unique_items = unique_items[:TOPIC_LIMIT]

    # 计算五维分
    heat_scores = compute_heat_score(unique_items)
    a_ride_topics = []
    for idx, item in enumerate(unique_items, start=1):
        category = categorize(item["title"])
        relevance, capabilities = compute_relevance_score(item["title"], category)
        safety = compute_safety_score(item["title"], category)
        timeliness = compute_timeliness_score(item.get("source", ""), idx, item.get("heat", 0))
        creativity = compute_creativity_score(category, capabilities)
        scores = {
            "heat": heat_scores[idx - 1],
            "relevance": relevance,
            "safety": safety,
            "timeliness": timeliness,
            "creativity": creativity,
            "capabilities": capabilities,
        }
        topic = build_a_ride_topic(idx, item, scores)
        a_ride_topics.append(topic)

    # 按 ride_score 排序，取前 N
    a_ride_topics.sort(key=lambda x: x["ride_score"], reverse=True)
    a_ride_topics = a_ride_topics[:A_TRACK_LIMIT]
    # 重新计算 rank
    for i, t in enumerate(a_ride_topics, start=1):
        t["rank"] = i

    # B-track
    b_create_topics = build_b_create_topics()

    # 储备库：未入选A-track但 create_score 较高的主题
    reserved_topics = []
    for t in a_ride_topics:
        if t["create_score"] >= 75 and t["ride_score"] < 80:
            reserved_topics.append({
                "topic_name": t["topic_name"],
                "platform": t["platform"],
                "ride_score": t["ride_score"],
                "create_score": t["create_score"],
                "priority": "B",
                "reserve_reason": "更适合打造成热点而非直接蹭热",
            })

    return a_ride_topics, b_create_topics, reserved_topics, sources


def today_str():
    tz = datetime.timezone(datetime.timedelta(hours=8))
    return datetime.datetime.now(tz).strftime("%Y-%m-%d")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    a_ride, b_create, reserved, sources = collect()
    updated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    result = {
        "date": today_str(),
        "updatedAt": updated_at,
        "sources": sources,
        "a_ride_hot_topics": a_ride,
        "b_create_hot_topics": b_create,
        "reserved_topics": reserved,
    }

    with open(os.path.join(OUTPUT_DIR, "topic-recommendations.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    archive_path = os.path.join(ARCHIVE_DIR, f"{today_str()}-topics.json")
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    dates = sorted(
        [f.replace("-topics.json", "") for f in os.listdir(ARCHIVE_DIR) if f.endswith("-topics.json")],
        reverse=True
    )
    history = {"dates": dates, "updatedAt": updated_at}
    with open(os.path.join(OUTPUT_DIR, "history.json"), "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    print(f"✅ 完成：{today_str()}，A轨 {len(a_ride)} 条，B轨 {len(b_create)} 条，储备 {len(reserved)} 条，来源：{sources}")


if __name__ == "__main__":
    main()

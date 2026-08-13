# 千问 AI 眼镜内容营销平台

基于 GitHub Pages + GitHub Actions 的免费自动化内容营销中台。

## 功能

- **洞察看板**：核心指标、内容矩阵与趋势概览。
- **选题广场**：每日 9:00（北京时间）自动采集全网热点，结合千问 AI 眼镜产品能力输出选题，支持查看历史日期与交互筛选。
- **事件放大**：事件组合、账号矩阵与发布节奏模板。
- **配置中心**：数据源说明、定时任务状态与手动触发入口。

## 在线访问

https://zhuxinmiao326-sudo.github.io/qwen-glasses-marketing-platform/

## 自动更新机制

`.github/workflows/daily-hot-topics.yml` 每日北京时间 9:00 触发：

1. 运行 `scripts/collect_hot_topics.py` 采集热点。
2. 生成 `data/hot-topics.json` 与 `archive/YYYY-MM-DD.json`。
3. 更新 `data/history.json`。
4. 自动提交并推送，GitHub Pages 同步刷新。

## 本地预览

```bash
python -m http.server 8000
# 打开 http://localhost:8000
```

## 技术栈

- GitHub Pages（免费静态托管）
- GitHub Actions（免费定时任务）
- 原生 HTML / CSS / JavaScript
- Python + requests（热点采集）

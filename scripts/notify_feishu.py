"""
飞书推送脚本
读取抓取数据，格式化为飞书卡片消息，通过 Webhook 发送。
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent


def load_data():
    today = datetime.now().strftime("%Y-%m-%d")
    data_path = BASE_DIR / "data" / f"{today}.json"
    if not data_path.exists():
        print(f"未找到今日数据文件: {data_path}")
        print("请先运行 fetch_trending.py")
        sys.exit(1)
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_card(data):
    """构建飞书交互卡片消息。"""
    date = data["date"]
    repos = data["repos"]

    # 项目列表元素
    elements = []

    for i, repo in enumerate(repos, 1):
        stars = f"{repo['stars']:,}"
        desc = repo.get("description_cn") or repo.get("description", "无描述")
        lang = repo.get("language", "未知")
        url = repo["url"]

        elements.append({
            "tag": "markdown",
            "content": f"**{i}. [{repo['name']}]({url})** ⭐ {stars}\n{desc} | {lang}"
        })

        if i < len(repos):
            elements.append({"tag": "hr"})

    # 趋势摘要
    topics = set()
    for repo in repos:
        for t in repo.get("topics", [])[:3]:
            topics.add(t)
    if topics:
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "markdown",
            "content": f"🏷️ 关键词: {', '.join(list(topics)[:8])}"
        })

    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📊 AI 日报 — {date}"
                },
                "template": "blue"
            },
            "elements": elements
        }
    }

    return card


def send_feishu(card):
    """通过飞书 Webhook 发送卡片消息。"""
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")

    if not webhook_url:
        print("错误: 缺少 FEISHU_WEBHOOK_URL")
        print("请在 .env 文件中配置")
        sys.exit(1)

    resp = requests.post(webhook_url, json=card, timeout=30)
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") == 0 or result.get("StatusCode") == 0:
        print("飞书推送成功!")
    else:
        print(f"飞书推送失败: {result}")
        sys.exit(1)


def main():
    data = load_data()
    card = build_card(data)
    print("正在推送到飞书...")
    send_feishu(card)


if __name__ == "__main__":
    main()

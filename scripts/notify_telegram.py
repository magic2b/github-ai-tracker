"""
Telegram 推送脚本
读取抓取数据，格式化为中文消息，通过 Telegram Bot API 发送。
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


def format_message(data):
    """格式化为 Telegram 消息（Markdown）。"""
    date = data["date"]
    repos = data["repos"]

    lines = [
        f"*📊 AI 日报 — {date}*",
        "",
        f"🔥 *今日热门 AI 项目 Top {len(repos)}*",
        "",
    ]

    for i, repo in enumerate(repos, 1):
        stars = f"{repo['stars']:,}"
        desc = repo.get("description_cn") or repo.get("description", "无描述")
        lang = repo.get("language", "未知")
        url = repo["url"]

        lines.append(f"*{i}.* [{repo['name']}]({url}) ⭐ {stars}")
        lines.append(f"   {desc} | {lang}")
        lines.append("")

    # 趋势摘要
    topics = set()
    for repo in repos:
        for t in repo.get("topics", [])[:3]:
            topics.add(t)
    if topics:
        lines.append(f"🏷️ 关键词: {', '.join(list(topics)[:8])}")

    return "\n".join(lines)


def send_telegram(message):
    """通过 Telegram Bot API 发送消息。"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("错误: 缺少 TELEGRAM_BOT_TOKEN 或 TELELEGAM_CHAT_ID")
        print("请在 .env 文件中配置")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()

    if result.get("ok"):
        print("Telegram 推送成功!")
    else:
        print(f"Telegram 推送失败: {result}")
        sys.exit(1)


def main():
    data = load_data()
    message = format_message(data)
    print("正在推送到 Telegram...")
    send_telegram(message)


if __name__ == "__main__":
    main()

"""
Obsidian 写入脚本
读取抓取数据，生成 Markdown 日报文件，写入仓库内 obsidian/ 目录和本地 Vault。
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
OBSIDIAN_REPO_DIR = BASE_DIR / "obsidian" / "AI日报"


def load_data():
    today = datetime.now().strftime("%Y-%m-%d")
    data_path = BASE_DIR / "data" / f"{today}.json"
    if not data_path.exists():
        print(f"未找到今日数据文件: {data_path}")
        print("请先运行 fetch_trending.py")
        sys.exit(1)
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_markdown(data):
    """生成 Obsidian 格式的 Markdown 日报。"""
    date = data["date"]
    repos = data["repos"]

    lines = [
        "---",
        f"date: {date}",
        "tags: [ai-daily, github-trending]",
        "source: github",
        "---",
        "",
        f"# AI 日报 — {date}",
        "",
        f"## 今日热门 Top {len(repos)}",
        "",
        "| # | 项目 | Star | 语言 | 简介 |",
        "|---|------|------|------|------|",
    ]

    for i, repo in enumerate(repos, 1):
        stars = f"{repo['stars']:,}"
        desc = repo.get("description_cn") or repo.get("description", "无描述")
        lang = repo.get("language", "未知")
        # 表格中截断过长描述
        if len(desc) > 50:
            desc = desc[:47] + "..."
        lines.append(f"| {i} | [{repo['name']}]({repo['url']}) | {stars} | {lang} | {desc} |")

    lines.extend(["", "## 项目详情", ""])

    for i, repo in enumerate(repos, 1):
        stars = f"{repo['stars']:,}"
        desc_cn = repo.get("description_cn", "")
        desc_en = repo.get("description", "")
        lang = repo.get("language", "未知")
        topics = repo.get("topics", [])

        lines.append(f"### {i}. {repo['name']}")
        lines.append(f"- **链接**: {repo['url']}")
        lines.append(f"- **Star**: {stars}")
        lines.append(f"- **语言**: {lang}")
        if desc_cn:
            lines.append(f"- **简介**: {desc_cn}")
        if desc_en and desc_cn and desc_en != desc_cn:
            lines.append(f"- **原文**: {desc_en}")
        if topics:
            lines.append(f"- **标签**: {' '.join(f'`{t}`' for t in topics[:6])}")
        lines.append("")

    # 趋势摘要
    topics = set()
    for repo in repos:
        for t in repo.get("topics", [])[:3]:
            topics.add(t)
    if topics:
        lines.extend([
            "## 趋势关键词",
            "",
            ", ".join(f"#{t}" for t in topics),
        ])

    return "\n".join(lines)


def write_to_path(content, date, target_dir):
    """写入 Markdown 文件到指定目录。"""
    target_dir.mkdir(parents=True, exist_ok=True)
    filepath = target_dir / f"{date}.md"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"已写入: {filepath}")
    return filepath


def main():
    data = load_data()
    date = data["date"]
    content = generate_markdown(data)

    # 写入仓库内 obsidian 目录
    write_to_path(content, date, OBSIDIAN_REPO_DIR)

    # 写入本地 Obsidian Vault（如果配置了路径）
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
    if vault_path:
        vault_dir = Path(vault_path) / "AI日报"
        write_to_path(content, date, vault_dir)
    else:
        print("未配置 OBSIDIAN_VAULT_PATH，跳过本地 Vault 写入")

    print("Obsidian 日报生成完毕!")


if __name__ == "__main__":
    main()

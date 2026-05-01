"""
GitHub AI Trending 抓取脚本
从 GitHub API 获取 AI 相关热门仓库，翻译描述为中文，输出结构化 JSON。
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# Windows 控制台 UTF-8 输出
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "keywords.json"
DATA_PATH = BASE_DIR / "data" / f"{datetime.now().strftime('%Y-%m-%d')}.json"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_headers():
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def search_ai_repos(keywords, languages, top_n, min_stars):
    """搜索最近活跃的 AI 相关仓库，按 star 数排序。"""
    one_week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    url = "https://api.github.com/search/repositories"

    seen = set()
    repos = []

    # 分多个查询搜索，每个查询用 topic: 限定，更稳定
    search_keywords = keywords[:6]  # 限制查询次数
    for kw in search_keywords:
        query = f"topic:{kw} stars:>={min_stars} pushed:>{one_week_ago}"
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 10,
        }

        try:
            resp = requests.get(url, headers=get_headers(), params=params, timeout=30)
            if resp.status_code == 422:
                # 某些关键词可能无效，跳过
                continue
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException:
            continue

        for item in data.get("items", []):
            full_name = item["full_name"]
            if full_name in seen:
                continue
            seen.add(full_name)

            lang = item.get("language") or ""
            if languages and lang not in languages:
                continue

            repos.append({
                "name": full_name,
                "url": item["html_url"],
                "description": item.get("description") or "",
                "stars": item["stargazers_count"],
                "language": lang,
                "topics": item.get("topics", []),
                "created_at": item.get("created_at", ""),
                "updated_at": item.get("updated_at", ""),
            })

    # 按 star 数排序，取 top N
    repos.sort(key=lambda r: r["stars"], reverse=True)
    return repos[:top_n]


def translate_to_chinese(text):
    """使用免费翻译 API 将英文翻译为中文。"""
    if not text:
        return ""

    # 尝试 MyMemory API（免费，无需 key）
    try:
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": "en|zh-CN"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        translated = data.get("responseData", {}).get("translatedText", "")
        if translated and translated.lower() != text.lower():
            return translated
    except Exception:
        pass

    # 翻译失败则返回原文
    return text


def enrich_with_chinese(repos):
    """为每个仓库的描述添加中文翻译。"""
    for repo in repos:
        desc = repo.get("description", "")
        if desc:
            repo["description_cn"] = translate_to_chinese(desc)
        else:
            repo["description_cn"] = ""
    return repos


def save_data(repos):
    """保存抓取结果到 JSON 文件。"""
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "count": len(repos),
        "repos": repos,
    }
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"数据已保存到 {DATA_PATH}")
    return output


def main():
    config = load_config()
    print(f"正在抓取 AI 热门仓库...")

    repos = search_ai_repos(
        keywords=config["keywords"],
        languages=config["languages"],
        top_n=config["top_n"],
        min_stars=config["min_stars"],
    )

    print(f"找到 {len(repos)} 个仓库，正在翻译描述...")
    repos = enrich_with_chinese(repos)

    output = save_data(repos)

    # 打印摘要
    print(f"\n=== AI 日报 — {output['date']} ===")
    print(f"共 {output['count']} 个热门项目\n")
    for i, repo in enumerate(repos, 1):
        desc = repo["description_cn"] or repo["description"]
        print(f"{i}. {repo['name']} [{repo['stars']:,} stars]")
        print(f"   {desc} | {repo['language']}")
        print()


if __name__ == "__main__":
    main()

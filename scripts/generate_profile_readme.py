"""
自动生成 ahuteam org 的 profile/README.md

功能:
  - 通过 GitHub API 读取 ahuteam 下的所有 public repo
  - 从 repo description 中提取论文标题和出处
  - 按研究方向自动分类
  - 生成带实时 shields.io 徽章的 Markdown 表格

使用方式:
  1. GitHub Actions 自动执行 (推荐)
  2. 本地执行: python scripts/generate_profile_readme.py
"""

import json
import os
import re
import requests
from pathlib import Path


# ====== 配置区域 ======

ORG_NAME = "ahuteam"
OUTPUT_PATH = Path(__file__).parent.parent / "profile" / "README.md"

# 分类关键词映射 (关键词 -> 分类名)
# 用于从 description 自动判断论文所属领域
CATEGORY_RULES = {
    "🔬 Computer Vision & Image Processing": [
        "CVPR", "ICME", "ICIP", "SPL", "Pattern Recognition",
        "See in the Dark", "RAW Image", "Face Reconstruction",
        "Test-Time Adaptation", "Federated", "Gaussian Splatting",
    ],
    "🏥 Medical Image Analysis": [
        "KDD", "JBHI", "AAAI", "Information Fusion", "Scientific Data",
        "Medical", "Ultrasound", "Fetal", "Segmentation", "UDA",
        "M3-UDA", "eMMamba", "FUSEP", "CertainTTA", "Semiakmm",
        "AHU-Database",
    ],
    "🔐 Biometrics & Security": [
        "IEEE TIM", "IEEE IoT", "IJCB", "Palm", "Biometric",
        "Cryptographic", "Bio-Cryptosystem", "Fingerprint",
        "WiFaKey", "CoLH4Palm", "BioCanCrypto", "PalmRSS",
    ],
}

# 跳过的 repo（不展示在列表中）
SKIP_REPOS = {".github"}


# ====== 核心逻辑 ======

def fetch_repos(org: str) -> list[dict]:
    """通过 GitHub API 获取 org 下所有 public repo"""
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/orgs/{org}/repos?per_page=100&page={page}&sort=updated"
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        repos.extend(data)
        page += 1

    return repos


def classify_repo(repo: dict) -> str:
    """根据 repo description 和名称自动分类"""
    desc = repo.get("description") or ""
    name = repo.get("name") or ""
    text = f"{name} {desc}"

    # 优先匹配：Medical 类关键词
    for category, keywords in CATEGORY_RULES.items():
        if "Medical" in category or "Biometrics" in category:
            for kw in keywords:
                if kw.lower() in text.lower():
                    return category

    # 再匹配 CV 类
    for category, keywords in CATEGORY_RULES.items():
        if "Vision" in category:
            for kw in keywords:
                if kw.lower() in text.lower():
                    return category

    # 默认归类到 CV
    return "🔬 Computer Vision & Image Processing"


def extract_venue_and_title(description: str) -> tuple[str, str]:
    """从 description 中提取出处和论文标题
    
    常见格式:
      [CVPR 2026] Some paper title
      (IEEE TIM) Some paper title
      Source code for CVPR2022 paper "Title"
    """
    if not description:
        return "", ""

    desc = description.strip()

    # 格式1: [Venue] Title
    m = re.match(r'^\[(.+?)\]\s*(.+)$', desc)
    if m:
        return m.group(1).strip(), m.group(2).strip().strip('"')

    # 格式2: (Venue) Title
    m = re.match(r'^\((.+?)\)\s*(.+)$', desc)
    if m:
        return m.group(1).strip(), m.group(2).strip().strip('"')

    # 格式3: Source code for VenueYear paper "Title"
    m = re.match(r'^(?:Source code for|ReImplementation for)\s+(\S+?)[\s:]+(.+)$', desc, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip().strip('"')

    # 无法提取，整个 description 作为标题
    return "", desc


def generate_readme(repos: list[dict]) -> str:
    """生成完整的 profile/README.md 内容"""

    # 过滤并分类
    categorized: dict[str, list] = {}
    for repo in repos:
        name = repo["name"]
        if name in SKIP_REPOS:
            continue
        if repo.get("archived"):
            continue

        category = classify_repo(repo)
        if category not in categorized:
            categorized[category] = []

        venue, title = extract_venue_and_title(repo.get("description") or "")
        categorized[category].append({
            "name": name,
            "html_url": repo["html_url"],
            "description": repo.get("description") or "",
            "venue": venue,
            "title": title,
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
        })

    # 按 stars 降序排列每个分类中的 repo
    for cat in categorized:
        categorized[cat].sort(key=lambda r: r["stars"], reverse=True)

    # 生成 Markdown
    lines = []

    # Header
    lines.append('<h1 align="center">')
    lines.append(f'  <img src="https://avatars.githubusercontent.com/u/310549279?v=4" width="100" height="100" style="border-radius: 50%;" alt="AHU Team Logo"/>')
    lines.append('  <br/>')
    lines.append('  Ahu Team Open Source')
    lines.append('</h1>')
    lines.append('')
    lines.append('<p align="center">')
    lines.append('  <b>We are from an AI research team from Anhui University (安徽大学)</b><br/>')
    lines.append('  Focusing on Computer Vision, Medical Image Analysis, Biometrics, and Test-Time Adaptation')
    lines.append('</p>')
    lines.append('')
    lines.append('<p align="center">')
    lines.append(f'  <a href="https://github.com/{ORG_NAME}"><img src="https://img.shields.io/badge/GitHub-{ORG_NAME}-181717?style=flat-square&logo=github" alt="GitHub"/></a>')
    lines.append('</p>')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## 📚 Publication Repository List')
    lines.append('')
    lines.append('> Below is a curated list of all open-source repositories maintained by our team, along with associated paper information.')
    lines.append('> ')
    lines.append('> Stars and Forks badges are **real-time** via [Shields.io](https://shields.io/).')
    lines.append('')

    # 按固定顺序输出分类
    category_order = [
        "🔬 Computer Vision & Image Processing",
        "🏥 Medical Image Analysis",
        "🔐 Biometrics & Security",
    ]

    idx = 1
    total = sum(len(v) for v in categorized.values())

    for cat in category_order:
        repos_in_cat = categorized.get(cat, [])
        if not repos_in_cat:
            continue

        lines.append(f'### {cat}')
        lines.append('')
        lines.append('| # | Paper Title | Repo | ⭐ Stars | 🍴 Forks |')
        lines.append('|:-:|:---|:---:|:---:|:---:|')

        for r in repos_in_cat:
            venue_prefix = f"**[{r['venue']}]** " if r['venue'] else ""
            title = r['title'] if r['title'] else r['name']
            repo_link = f"[{r['name']}]({r['html_url']})"
            stars_badge = f"![Stars](https://img.shields.io/github/stars/{ORG_NAME}/{r['name']}?style=flat-square&label=)"
            forks_badge = f"![Forks](https://img.shields.io/github/forks/{ORG_NAME}/{r['name']}?style=flat-square&label=)"

            lines.append(f'| {idx} | {venue_prefix}{title} | {repo_link} | {stars_badge} | {forks_badge} |')
            idx += 1

        lines.append('')

    # 处理未归类的 repo（如果有新分类出现）
    for cat, repos_in_cat in categorized.items():
        if cat in category_order:
            continue
        if not repos_in_cat:
            continue

        lines.append(f'### {cat}')
        lines.append('')
        lines.append('| # | Paper Title | Repo | ⭐ Stars | 🍴 Forks |')
        lines.append('|:-:|:---|:---:|:---:|:---:|')

        for r in repos_in_cat:
            venue_prefix = f"**[{r['venue']}]** " if r['venue'] else ""
            title = r['title'] if r['title'] else r['name']
            repo_link = f"[{r['name']}]({r['html_url']})"
            stars_badge = f"![Stars](https://img.shields.io/github/stars/{ORG_NAME}/{r['name']}?style=flat-square&label=)"
            forks_badge = f"![Forks](https://img.shields.io/github/forks/{ORG_NAME}/{r['name']}?style=flat-square&label=)"

            lines.append(f'| {idx} | {venue_prefix}{title} | {repo_link} | {stars_badge} | {forks_badge} |')
            idx += 1

        lines.append('')

    # Footer
    lines.append('---')
    lines.append('')
    lines.append('<p align="center">')
    lines.append(f'  <i>📊 Total Repositories: {total} (excluding .github) &nbsp;|&nbsp; Auto-generated by GitHub Actions</i>')
    lines.append('</p>')
    lines.append('')
    lines.append('<p align="center">')
    lines.append('  <i>If you find our work useful, please consider giving a ⭐ star!</i>')
    lines.append('</p>')

    return '\n'.join(lines) + '\n'


def main():
    print(f"Fetching repos for org: {ORG_NAME}...")
    repos = fetch_repos(ORG_NAME)
    print(f"Found {len(repos)} repos")

    readme_content = generate_readme(repos)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(readme_content, encoding="utf-8")
    print(f"Profile README written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""每周GitHub高星项目搜索脚本
    
搜索过去7天内创建的高星项目，生成Markdown报告。
同时生成一个供Codex读取的状态文件。
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone

# 配置
MIN_STARS = int(os.getenv("MIN_STARS", "50"))
TOP_N = int(os.getenv("TOP_N", "20"))
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
DAYS_BACK = 7

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


def search_trending_repos():
    """搜索最近创建的GitHub高星项目"""
    since_date = (datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)).strftime("%Y-%m-%d")
    
    # 搜索最近创建的高星项目
    query = f"created:>={since_date} stars:>={MIN_STARS}"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": TOP_N,
    }
    
    url = "https://api.github.com/search/repositories"
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    
    if resp.status_code != 200:
        print(f"[ERROR] GitHub API returned {resp.status_code}: {resp.text}")
        return []
    
    data = resp.json()
    repos = data.get("items", [])
    
    results = []
    for repo in repos:
        results.append({
            "name": repo["full_name"],
            "url": repo["html_url"],
            "stars": repo["stargazers_count"],
            "forks": repo["forks_count"],
            "language": repo.get("language", "N/A"),
            "description": repo.get("description", "无描述"),
            "topics": repo.get("topics", []),
            "created_at": repo["created_at"],
            "open_issues": repo["open_issues_count"],
        })
    
    return results


def also_search_trending_weekly():
    """额外搜索本周最热项目（不限创建时间，按本周新增star排序）"""
    # GitHub trending 没有直接的API，使用变通方法：
    # 搜索最近更新的热门项目作为补充
    since_date = (datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)).strftime("%Y-%m-%d")
    
    # 搜索最近有活动且star数高的项目（补充老项目本周爆发的情况）
    query = f"pushed:>={since_date} stars:>={MIN_STARS * 2}"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": 10,
    }
    
    url = "https://api.github.com/search/repositories"
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    
    if resp.status_code != 200:
        return []
    
    data = resp.json()
    repos = data.get("items", [])
    
    results = []
    for repo in repos:
        results.append({
            "name": repo["full_name"],
            "url": repo["html_url"],
            "stars": repo["stargazers_count"],
            "forks": repo["forks_count"],
            "language": repo.get("language", "N/A"),
            "description": repo.get("description", "无描述"),
            "topics": repo.get("topics", []),
            "created_at": repo["created_at"],
            "open_issues": repo["open_issues_count"],
        })
    
    return results


def generate_markdown(new_repos, trending_repos, report_date):
    """生成Markdown报告"""
    lines = []
    lines.append(f"# 📊 GitHub 高星项目周报")
    lines.append(f"")
    lines.append(f"**报告日期**：{report_date}")
    lines.append(f"**统计周期**：过去 7 天")
    lines.append(f"**最低星数阈值**：{MIN_STARS}⭐")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    
    # 新增高星项目
    lines.append(f"## 🆕 本周新晋高星项目（Top {min(TOP_N, len(new_repos))}）")
    lines.append(f"")
    
    if not new_repos:
        lines.append(f"> 本周暂无超过 {MIN_STARS} 星的新项目。")
    else:
        lines.append(f"| # | 项目 | 语言 | ⭐ Stars | Forks | Issues |")
        lines.append(f"|---|------|------|---------|-------|--------|")
        
        for i, repo in enumerate(new_repos, 1):
            name = repo["name"]
            url = repo["url"]
            lang = repo["language"] or "N/A"
            stars = repo["stars"]
            forks = repo["forks"]
            issues = repo["open_issues"]
            desc = (repo["description"] or "无描述")[:60]
            lines.append(f"| {i} | [{name}]({url})<br/>{desc} | {lang} | {stars} | {forks} | {issues} |")
    
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    
    # 热门活跃项目
    lines.append(f"## 🔥 本周热门活跃项目（持续火爆的老项目）")
    lines.append(f"")
    
    if not trending_repos:
        lines.append(f"> 未找到符合条件的活跃项目。")
    else:
        lines.append(f"| # | 项目 | 语言 | ⭐ Stars | Forks |")
        lines.append(f"|---|------|------|---------|-------|")
        
        for i, repo in enumerate(trending_repos, 1):
            name = repo["name"]
            url = repo["url"]
            lang = repo["language"] or "N/A"
            stars = repo["stars"]
            forks = repo["forks"]
            desc = (repo["description"] or "无描述")[:60]
            lines.append(f"| {i} | [{name}]({url})<br/>{desc} | {lang} | {stars} | {forks} |")
    
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"📌 *本报告由 GitHub Actions 自动生成，每周日 08:00（北京时间）更新。*")
    lines.append(f"")
    
    return "\n".join(lines)


def main():
    report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    print(f"[INFO] 搜索过去 {DAYS_BACK} 天内创建的高星项目（>= {MIN_STARS}⭐）...")
    new_repos = search_trending_repos()
    print(f"[INFO] 找到 {len(new_repos)} 个新晋高星项目")
    
    print(f"[INFO] 搜索本周热门活跃项目...")
    trending_repos = also_search_trending_weekly()
    print(f"[INFO] 找到 {len(trending_repos)} 个热门活跃项目")
    
    # 去重
    new_names = {r["name"] for r in new_repos}
    trending_repos = [r for r in trending_repos if r["name"] not in new_names][:5]
    
    # 生成报告
    markdown = generate_markdown(new_repos, trending_repos, report_date)
    
    with open("trending-report.md", "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"[INFO] 报告已写入 trending-report.md")
    
    # 生成JSON摘要（供Codex读取）
    summary = {
        "report_date": report_date,
        "new_high_star_repos": new_repos[:TOP_N],
        "trending_active_repos": trending_repos,
        "total_new": len(new_repos),
        "note": "Codex可读取trending-report.md获取完整报告"
    }
    with open("trending-summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[INFO] 摘要已写入 trending-summary.json")
    
    # 打印预览
    print("\n" + "=" * 60)
    print(f"📊 本周 {report_date} 高星项目快览")
    print("=" * 60)
    for repo in new_repos[:5]:
        print(f"  ⭐ {repo['stars']:>6}  [{repo['name']}]({repo['url']})")
        print(f"          {repo['description'][:80] if repo['description'] else '无描述'}")
    print(f"  ... 共 {len(new_repos)} 个项目")
    print("=" * 60)


if __name__ == "__main__":
    main()
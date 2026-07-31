#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习工作台数据同步脚本
扫描各分类文件夹 + 打卡总表 + 书单，生成：
  1. data.js（供 dashboard.html 通过本地服务器使用）
  2. 学习工作台.html（自包含 HTML，内嵌数据，双击直接打开即可用）

用法：
    python3 sync_data.py

自动化任务生成完每日内容后，运行本脚本即可刷新网页数据。
打开 学习工作台.html 即可直接使用，无需启动服务器。
"""
import os, re, json, glob, datetime

BASE = os.path.dirname(os.path.abspath(__file__))

# 分类定义（与 工作台首页.md 对应）
CATEGORIES = [
    {"id":"tongshi","name":"中国通史","folder":"中国通史","icon":"🏛","schedule":"每日",
     "desc":"历史典故、各朝代大事记、社交谈资积累。每日时序递进更新，无重复史实，配套名人典故、朝代脉络，每周自动生成思维导图汇总。"},
    {"id":"jindai","name":"中外近现代史","folder":"中外近代史","icon":"🌍","schedule":"每日",
     "desc":"分国家梳理近代重大事件、人物、因果脉络。中外对照学习，理清国内外近代发展脉络，补齐知识空白，每周复盘汇总导图。"},
    {"id":"zixun","name":"每日资讯简报","folder":"每日资讯简报","icon":"📰","schedule":"每日",
     "desc":"前一日国内外时政、外交、金融资讯+多方观点。每日更新前日重磅资讯，不止罗列事件，附带客观评析，适配碎片阅读。"},
    {"id":"kouyu","name":"日常英语口语","folder":"英语口语","icon":"💬","schedule":"每日",
     "desc":"简单交流实用短句。每日5句高频短句，带音标、场景释义，适合日常口语交流，每日内容完全去重。"},
    {"id":"shuji","name":"每周书籍精读","folder":"书籍精读","icon":"📖","schedule":"每周",
     "desc":"书籍框架大纲、核心观点、经典金句。周一至周六分段拆解、周日全局复盘，支持自定义书单，每周生成书籍思维导图。"},
    {"id":"daotu","name":"每周思维导图汇总","folder":"每周思维导图汇总","icon":"🗺","schedule":"每周",
     "desc":"全板块周度复盘归档。通史、近代史、资讯、书籍每周自动整合，结构化梳理知识点，方便长期回顾记忆。"},
]

FOLDER_README = {
    "中国通史": "# 中国通史\n\n每日时序递进更新，无重复史实。\n\n## 命名规范\n- 每日文件：`YYYY-MM-DD.md`\n- 示例：`2026-07-30.md`\n- 周导图：`YYYY-WXX周导图.md`\n\n自动化任务生成内容后，运行 `python3 sync_data.py` 即可在网页查看。",
    "中外近代史": "# 中外近代史\n\n分国家梳理近代重大事件、人物、因果脉络。\n\n## 命名规范\n- 每日文件：`YYYY-MM-DD.md`\n- 示例：`2026-07-30.md`\n\n自动化任务生成内容后，运行 `python3 sync_data.py` 即可在网页查看。",
    "每日资讯简报": "# 每日资讯简报\n\n前一日国内外时政、外交、金融资讯+多方观点。\n\n## 命名规范\n- 每日文件：`YYYY-MM-DD.md`\n- 示例：`2026-07-30.md`\n\n自动化任务生成内容后，运行 `python3 sync_data.py` 即可在网页查看。",
    "英语口语": "# 日常英语口语\n\n每日5句高频短句，带音标、场景释义。\n\n## 命名规范\n- 每日文件：`YYYY-MM-DD.md`\n- 示例：`2026-07-30.md`\n\n自动化任务生成内容后，运行 `python3 sync_data.py` 即可在网页查看。",
    "书籍精读": "# 每周书籍精读\n\n周一至周六分段拆解、周日全局复盘。\n\n## 命名规范\n- 按书名建子文件夹：`书籍精读/万历十五年/`\n- 每日文件：`书籍精读/万历十五年/YYYY-MM-DD.md`\n- 周复盘：`书籍精读/万历十五年/周复盘.md`\n\n自动化任务生成内容后，运行 `python3 sync_data.py` 即可在网页查看。",
    "每周思维导图汇总": "# 每周思维导图汇总\n\n全板块周度复盘归档。\n\n## 命名规范\n- 每周文件：`YYYY-WXX.md`（如 `2026-W31.md`）\n- 涵盖通史、近代史、资讯、书籍周度整合\n\n自动化任务生成内容后，运行 `python3 sync_data.py` 即可在网页查看。",
}

DATE_RE = re.compile(r'(20\d{2})[-_]?(\d{1,2})[-_]?(\d{1,2})')
WEEK_RE = re.compile(r'(20\d{2})[-_]?W(\d{1,2})', re.I)

def ensure_folders():
    """创建分类文件夹骨架 + README"""
    created = []
    for cat in CATEGORIES:
        fdir = os.path.join(BASE, cat["folder"])
        if not os.path.isdir(fdir):
            os.makedirs(fdir)
            created.append(cat["folder"])
        readme = os.path.join(fdir, "README.md")
        if not os.path.exists(readme):
            with open(readme, "w", encoding="utf-8") as f:
                f.write(FOLDER_README.get(cat["folder"], "# "+cat["name"]))
    return created

def parse_date_from_name(name):
    m = DATE_RE.search(name)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return "%04d-%02d-%02d" % (y, mo, d), datetime.date(y, mo, d)
        except ValueError:
            return None, None
    return None, None

def parse_article(filepath, cat):
    """解析单个 markdown 文章"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = f.read()
    except Exception:
        return None
    fname = os.path.basename(filepath)
    rel = os.path.relpath(filepath, BASE)
    # 日期
    date_str, date_obj = parse_date_from_name(fname)
    if not date_str:
        # 从内容首行找
        for line in raw.splitlines()[:5]:
            d, _ = parse_date_from_name(line)
            if d:
                date_str = d
                break
    if not date_str:
        date_str = datetime.date.today().isoformat()
    # 标题：首个 # 标题 或 文件名
    title = None
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("# "):
            title = s[2:].strip()
            break
    if not title:
        title = os.path.splitext(fname)[0]
    # 摘要：首个非空非标题段落
    summary = ""
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith(">") or s.startswith("---"):
            continue
        summary = s
        break
    if len(summary) > 80:
        summary = summary[:80] + "…"
    # 书籍子目录：提取书名
    book = None
    if cat["id"] == "shuji":
        sub = os.path.relpath(filepath, os.path.join(BASE, cat["folder"]))
        top = sub.split(os.sep)[0]
        if top and top != os.path.basename(filepath):
            book = top
    # 周导图
    is_weekly = False
    mw = WEEK_RE.search(fname)
    if mw:
        is_weekly = True
        date_str = "%s-W%s" % (mw.group(1), mw.group(2).zfill(2))
    return {
        "id": re.sub(r'[^a-zA-Z0-9]', '_', rel)[:80],
        "category": cat["id"],
        "catName": cat["name"],
        "icon": cat["icon"],
        "date": date_str,
        "title": title,
        "summary": summary,
        "content": raw,
        "path": rel.replace(os.sep, "/"),
        "book": book,
        "weekly": is_weekly,
    }

def scan_articles():
    """扫描所有分类文件夹的文章，同分类同日期自动去重（保留内容最丰富的）"""
    articles = []
    for cat in CATEGORIES:
        fdir = os.path.join(BASE, cat["folder"])
        if not os.path.isdir(fdir):
            continue
        for root, dirs, files in os.walk(fdir):
            for fn in files:
                if not fn.lower().endswith(".md"):
                    continue
                if fn.lower() == "readme.md":
                    continue
                fp = os.path.join(root, fn)
                art = parse_article(fp, cat)
                if art:
                    articles.append(art)
    # 去重：同分类同日期，保留 content 最长的
    seen = {}
    for a in articles:
        key = (a["category"], a["date"])
        if key not in seen:
            seen[key] = a
        else:
            if len(a["content"]) > len(seen[key]["content"]):
                seen[key] = a
    articles = list(seen.values())
    # 按日期倒序
    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles

def read_books():
    """解析书单自定义库.md"""
    path = os.path.join(BASE, "书单自定义库.md")
    current = ""
    to_read = []
    finished = []
    if not os.path.exists(path):
        return {"current": current, "toRead": to_read, "finished": finished}
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    section = None
    for line in lines:
        s = line.strip()
        if "当前本周在读" in s:
            section = "current"; continue
        if "待读列表" in s:
            section = "toread"; continue
        if "已读完归档" in s:
            section = "finished"; continue
        if not s or s.startswith("#") or s.startswith(">"):
            continue
        # 提取书名（去掉序号）
        m = re.match(r'^\d+\.\s*(.+)', s)
        name = m.group(1).strip() if m else s
        if name.startswith("《") or name:
            if section == "current" and s:
                current = s
            elif section == "toread":
                to_read.append(name)
            elif section == "finished":
                finished.append(name)
    return {"current": current, "toRead": to_read, "finished": finished}

def read_checkin(articles):
    """解析学习进度打卡总表.md 的 ✅/⭕ 状态，返回 {title: done}"""
    path = os.path.join(BASE, "学习进度打卡总表.md")
    done_map = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if "✅" in s:
                    # 取标题部分
                    t = re.sub(r'^\d+\.\s*', '', s)
                    t = t.replace("✅", "").replace("已完成", "").strip()
                    if t:
                        done_map[t] = True
    return done_map

def compute_stats(articles, done_count):
    today = datetime.date.today().isoformat()
    today_updates = sum(1 for a in articles if a["date"] == today)
    total = len(articles)
    pending = total - done_count if total > done_count else 0
    # 本周完成
    now = datetime.date.today()
    week_start = now - datetime.timedelta(days=now.weekday())
    week_completed = 0  # 由前端 localStorage 主导，这里给初始值
    # 连续天数：统计有文章的连续日期（简化为最近有内容的连续天数）
    dates_with_content = sorted(set(a["date"][:10] for a in articles if not a["weekly"]), reverse=True)
    streak = 0
    if dates_with_content:
        d = datetime.date.today()
        while True:
            ds = d.isoformat()
            if ds in dates_with_content:
                streak += 1
                d -= datetime.timedelta(days=1)
            else:
                # 允许今天还没更新
                if d == datetime.date.today():
                    d -= datetime.timedelta(days=1)
                    continue
                break
    return {
        "todayUpdates": today_updates,
        "pending": pending,
        "weekCompleted": week_completed,
        "streakDays": streak,
        "total": total,
    }

def generate_self_contained_html(data):
    """读取 dashboard.html 模板，内嵌数据，生成自包含 HTML（双击可直接打开）"""
    template_path = os.path.join(BASE, "dashboard.html")
    if not os.path.exists(template_path):
        print("⚠️ 未找到 dashboard.html 模板，跳过生成自包含 HTML")
        return False
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    # 将 <script src="data.js"></script> 替换为内联数据
    data_json = json.dumps(data, ensure_ascii=False, indent=2)
    inline_script = (
        '<script>\n'
        '/* 内嵌数据 - 由 sync_data.py 自动生成 - 请勿手动编辑 */\n'
        '/* 生成时间: ' + data["meta"]["generatedAt"] + ' */\n'
        'var WORKBENCH_DATA = ' + data_json + ';\n'
        '</script>'
    )
    html = html.replace('<script src="data.js"></script>', inline_script)
    out = os.path.join(BASE, "学习工作台.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return True

def main():
    created = ensure_folders()
    articles = scan_articles()
    books = read_books()
    done_map = read_checkin(articles)
    # 标记文章初始完成状态
    for a in articles:
        a["done"] = bool(done_map.get(a["title"]))
    done_count = sum(1 for a in articles if a["done"])
    stats = compute_stats(articles, done_count)

    data = {
        "meta": {
            "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "version": 2,
            "note": "由 sync_data.py 自动生成，请勿手动编辑。自动化任务生成内容后运行 sync_data.py 刷新。",
        },
        "categories": CATEGORIES,
        "articles": articles,
        "books": books,
        "stats": stats,
    }

    out = os.path.join(BASE, "data.js")
    with open(out, "w", encoding="utf-8") as f:
        f.write("/* 学习工作台数据文件 - 由 sync_data.py 自动生成 - 请勿手动编辑 */\n")
        f.write("/* 生成时间: %s */\n" % data["meta"]["generatedAt"])
        f.write("var WORKBENCH_DATA = ")
        f.write(json.dumps(data, ensure_ascii=False, indent=2))
        f.write(";\n")

    # 生成自包含 HTML（双击直接打开）
    html_ok = generate_self_contained_html(data)

    print("=" * 50)
    print("✅ 同步完成")
    print("   生成时间: %s" % data["meta"]["generatedAt"])
    print("   文章总数: %d" % len(articles))
    print("   今日更新: %d" % stats["todayUpdates"])
    print("   连续天数: %d" % stats["streakDays"])
    print("   在读: %s" % books["current"])
    print("   待读: %d 本" % len(books["toRead"]))
    if html_ok:
        print("   📄 学习工作台.html 已生成（双击直接打开）")
    if created:
        print("   新建文件夹: %s" % "、".join(created))
    print("=" * 50)

if __name__ == "__main__":
    main()

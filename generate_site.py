#!/usr/bin/env python3
"""
Website Generator for Auto-Research Pipeline
=============================================
Reads papers.json + insights.json and generates a single-file,
GitHub Pages-deployable HTML research dashboard.

Design: modern academic, clean typography, responsive cards,
interactive filtering, bilingual (EN/ZH) labeling.
"""

import json, os, sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PAPERS_JSON = os.path.join(SCRIPT_DIR, "papers.json")
INSIGHTS_JSON = os.path.join(SCRIPT_DIR, "insights.json")
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "index.html")


def load_data():
    with open(PAPERS_JSON, "r", encoding="utf-8") as f:
        papers_data = json.load(f)
    papers = papers_data.get("papers", papers_data if isinstance(papers_data, list) else [])

    insights = {}
    if os.path.exists(INSIGHTS_JSON):
        with open(INSIGHTS_JSON, "r", encoding="utf-8") as f:
            insights = json.load(f)

    return papers, insights


def topic_label(topic_key):
    labels = {
        "agent_evaluation": ("Agent Evaluation", "Agent 评测"),
        "function_calling": ("Function Calling", "函数调用"),
        "car_agent": ("Car Agent", "车载 Agent"),
        "eval_methodology": ("Methodology", "评测方法论"),
        "chinese_agent": ("Chinese Agent", "中文 Agent"),
    }
    en, zh = labels.get(topic_key, (topic_key, topic_key))
    return en, zh


def topic_color(topic_key):
    colors = {
        "agent_evaluation": "#3b82f6",
        "function_calling": "#10b981",
        "car_agent": "#f59e0b",
        "eval_methodology": "#8b5cf6",
        "chinese_agent": "#ef4444",
    }
    return colors.get(topic_key, "#64748b")


def score_stars(score):
    return "★" * score + "☆" * (5 - score)


def generate_html(papers, insights):
    # Stats
    total_papers = len(papers)
    topics = {}
    for p in papers:
        t = p.get("topic", "unknown")
        topics[t] = topics.get(t, 0) + 1
    curated = sum(1 for p in papers if p.get("car_control_score", 0) >= 4)
    total_citations = sum(p.get("citations", 0) for p in papers)

    # Topic filter buttons
    topic_buttons = ""
    for t_key in ["agent_evaluation", "function_calling", "car_agent", "eval_methodology", "chinese_agent"]:
        if t_key in topics:
            en, zh = topic_label(t_key)
            color = topic_color(t_key)
            topic_buttons += f'<button class="topic-btn" data-topic="{t_key}" style="--tc:{color}">{zh}<span class="count">{topics[t_key]}</span></button>\n'

    # Paper cards
    paper_cards = ""
    for i, p in enumerate(papers):
        tid = p.get("topic", "")
        en_t, zh_t = topic_label(tid)
        color = topic_color(tid)
        score = p.get("car_control_score", 0)
        stars = score_stars(score) if score > 0 else ""

        tags_html = ""
        for tag in p.get("tags", [])[:6]:
            tags_html += f'<span class="tag">{tag}</span>'

        findings_html = ""
        for f in p.get("key_findings", []):
            findings_html += f'<li>{f}</li>'

        car_insight = p.get("car_control_insight", "")
        insight_html = ""
        if car_insight:
            insight_html = f'''
            <div class="car-insight">
              <span class="ci-label">🚗 车控启示</span>
              <p>{car_insight}</p>
              {f'<span class="stars">{stars}</span>' if stars else ''}
            </div>'''

        methodology = p.get("methodology", "")
        citations = p.get("citations", 0)
        venue = p.get("venue", "")
        year = p.get("year", "")
        authors = ", ".join(p.get("authors", [])[:4])
        if len(p.get("authors", [])) > 4:
            authors += " et al."

        # Pre-compute details HTML to avoid nested f-string escaping issues
        details_html = ""
        if findings_html:
            meth_html = f'<p class="methodology"><strong>Methodology:</strong> {methodology}</p>' if methodology else ""
            details_html = f'<details class="pc-details"><summary>📋 Key Findings & Methodology</summary><ul class="findings">{findings_html}</ul>{meth_html}</details>'

        paper_cards += f'''
        <div class="paper-card" data-topic="{tid}" data-year="{year}" data-score="{score}">
          <div class="pc-header">
            <span class="pc-topic" style="background:{color}">{zh_t}</span>
            {f'<span class="pc-venue">{venue}</span>' if venue else ''}
            <span class="pc-year">{year}</span>
            {f'<span class="pc-citations" title="Citations">{citations}+ citations</span>' if citations else ''}
          </div>
          <h3 class="pc-title"><a href="{p.get("url", "#")}" target="_blank" rel="noopener">{p["title"]}</a></h3>
          <p class="pc-authors">{authors}</p>
          <p class="pc-abstract">{p.get("abstract", "")[:400]}{"..." if len(p.get("abstract", "")) > 400 else ""}</p>
          {f'<div class="pc-tags">{tags_html}</div>' if tags_html else ''}
          {details_html}
          {insight_html}
        </div>'''

    # Insight cards
    insight_cards = ""
    for theme in insights.get("cross_cutting_themes", []):
        papers_ref = ", ".join(theme.get("papers", [])[:4])
        insight_cards += f'''
        <div class="insight-card">
          <div class="ic-header">
            <h3>{theme.get("theme_zh", theme.get("theme", ""))}</h3>
            <span class="ic-theme">{theme.get("theme", "")}</span>
          </div>
          <p class="ic-desc">{theme.get("description", "")}</p>
          <div class="ic-action">
            <strong>🎯 车控行动项:</strong> {theme.get("car_control_action", "")}
          </div>
          {f'<div class="ic-papers">📄 来源: {papers_ref}</div>' if papers_ref else ''}
        </div>'''

    # Gap analysis
    gap_html = ""
    if insights.get("gap_analysis"):
        ga = insights["gap_analysis"]
        have_items = "".join(f"<li>{item}</li>" for item in ga.get("what_we_have", []))
        missing_items = "".join(f"<li>{item}</li>" for item in ga.get("what_benchmarks_have_that_we_dont", []))
        unique_items = "".join(f"<li>{item}</li>" for item in ga.get("what_we_have_that_benchmarks_dont", []))
        gap_html = f'''
        <div class="gap-grid">
          <div class="gap-col have">
            <h4>✅ 我们已有的</h4>
            <ul>{have_items}</ul>
          </div>
          <div class="gap-col missing">
            <h4>🔧 业界有而我们缺的</h4>
            <ul>{missing_items}</ul>
          </div>
          <div class="gap-col unique">
            <h4>💎 我们有而业界缺的</h4>
            <ul>{unique_items}</ul>
          </div>
        </div>'''

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Auto-Eval Research | 车控 Agent 评测研究门户</title>
<meta name="description" content="Automated research pipeline for LLM Agent evaluation in car-control scenarios. Papers, insights, and gap analysis.">
<style>
/* ===== RESET & BASE ===== */
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth;font-size:16px}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;background:#f8fafc;color:#1e293b;line-height:1.6}}
a{{color:#2563eb;text-decoration:none}}a:hover{{text-decoration:underline}}
.container{{max-width:1280px;margin:0 auto;padding:0 24px}}

/* ===== NAV ===== */
nav{{background:#fff;border-bottom:1px solid #e2e8f0;position:sticky;top:0;z-index:100;backdrop-filter:blur(8px)}}
.nav-inner{{max-width:1280px;margin:0 auto;padding:12px 24px;display:flex;align-items:center;gap:24px;flex-wrap:wrap}}
.nav-logo{{font-weight:800;font-size:18px;color:#0f172a;white-space:nowrap}}
.nav-logo span{{color:#3b82f6}}
.nav-links{{display:flex;gap:16px;flex-wrap:wrap;font-size:14px}}
.nav-links a{{color:#64748b;padding:4px 0;border-bottom:2px solid transparent;transition:all .15s}}
.nav-links a:hover{{color:#0f172a;border-bottom-color:#3b82f6;text-decoration:none}}

/* ===== HERO ===== */
.hero{{background:linear-gradient(135deg,#0f172a 0%,#1e293b 50%,#1e3a5f 100%);color:#fff;padding:60px 24px;text-align:center}}
.hero h1{{font-size:clamp(28px,5vw,44px);font-weight:800;margin-bottom:12px;letter-spacing:-0.5px}}
.hero h1 span{{background:linear-gradient(135deg,#3b82f6,#10b981);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.hero p{{font-size:18px;color:#94a3b8;max-width:700px;margin:0 auto 24px}}
.hero-stats{{display:flex;gap:24px;justify-content:center;flex-wrap:wrap;margin-top:24px}}
.hero-stat{{text-align:center;min-width:100px}}
.hero-stat .hs-num{{font-size:36px;font-weight:800;color:#fff}}
.hero-stat .hs-label{{font-size:13px;color:#94a3b8;margin-top:4px}}

/* ===== SECTION HEADERS ===== */
.section{{padding:48px 0}}
.section-header{{margin-bottom:32px}}
.section-header h2{{font-size:26px;font-weight:700;color:#0f172a;margin-bottom:4px}}
.section-header p{{color:#64748b;font-size:15px}}

/* ===== FILTER BAR ===== */
.filter-bar{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:24px;padding:16px;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);position:sticky;top:57px;z-index:50}}
.filter-bar input{{padding:8px 16px;border:1px solid #e2e8f0;border-radius:8px;font-size:14px;min-width:240px;outline:none;transition:border-color .15s}}
.filter-bar input:focus{{border-color:#3b82f6}}
.topic-btn{{padding:6px 14px;border:1.5px solid #e2e8f0;background:#fff;border-radius:8px;cursor:pointer;font-size:13px;font-weight:500;transition:all .15s;display:flex;align-items:center;gap:6px;white-space:nowrap}}
.topic-btn:hover{{border-color:var(--tc);background:#f8fafc}}
.topic-btn.active{{background:var(--tc);color:#fff;border-color:var(--tc)}}
.topic-btn .count{{font-size:11px;background:rgba(0,0,0,.08);padding:1px 6px;border-radius:10px}}
.topic-btn.active .count{{background:rgba(255,255,255,.25)}}
.filter-bar .clear-btn{{padding:6px 14px;border:1px solid #fecaca;background:#fef2f2;color:#991b1b;border-radius:8px;cursor:pointer;font-size:13px;margin-left:auto}}
.sort-select{{padding:6px 12px;border:1px solid #e2e8f0;border-radius:8px;font-size:13px;background:#fff;cursor:pointer}}

/* ===== PAPER CARDS ===== */
.papers-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:20px}}
.paper-card{{background:#fff;border-radius:12px;padding:20px 24px;box-shadow:0 1px 3px rgba(0,0,0,.06);border:1px solid #f1f5f9;transition:all .2s;display:flex;flex-direction:column}}
.paper-card:hover{{box-shadow:0 4px 12px rgba(0,0,0,.1);transform:translateY(-2px)}}
.pc-header{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px}}
.pc-topic{{font-size:11px;font-weight:600;color:#fff;padding:3px 10px;border-radius:4px;white-space:nowrap}}
.pc-venue{{font-size:11px;color:#64748b;background:#f1f5f9;padding:3px 8px;border-radius:4px}}
.pc-year{{font-size:11px;color:#94a3b8;font-weight:500}}
.pc-citations{{font-size:11px;color:#64748b;margin-left:auto}}
.pc-title{{font-size:17px;font-weight:700;line-height:1.3;margin-bottom:6px}}
.pc-title a{{color:#0f172a}}
.pc-title a:hover{{color:#2563eb}}
.pc-authors{{font-size:13px;color:#64748b;margin-bottom:8px}}
.pc-abstract{{font-size:13px;color:#475569;line-height:1.5;margin-bottom:10px;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}}
.pc-tags{{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:10px}}
.tag{{font-size:10px;background:#eff6ff;color:#2563eb;padding:2px 8px;border-radius:3px;font-weight:500}}
.pc-details{{margin-top:auto;font-size:13px}}
.pc-details summary{{cursor:pointer;color:#3b82f6;font-weight:500;padding:6px 0}}
.pc-details summary:hover{{color:#1d4ed8}}
.findings{{margin:8px 0 0 20px;color:#475569;font-size:12px;line-height:1.6}}
.findings li{{margin-bottom:3px}}
.methodology{{font-size:12px;color:#64748b;margin-top:8px;font-style:italic}}

.car-insight{{margin-top:12px;padding:12px 16px;background:linear-gradient(135deg,#fffbeb,#fef3c7);border-left:3px solid #f59e0b;border-radius:0 8px 8px 0;font-size:12px}}
.ci-label{{font-weight:700;color:#92400e;font-size:11px;display:block;margin-bottom:4px}}
.car-insight p{{color:#78350f;line-height:1.5}}
.stars{{color:#f59e0b;font-size:14px;letter-spacing:2px}}
.hidden{{display:none!important}}

/* ===== INSIGHT CARDS ===== */
.insights-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:20px}}
.insight-card{{background:#fff;border-radius:12px;padding:20px 24px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-top:4px solid #3b82f6}}
.insight-card:nth-child(1){{border-top-color:#3b82f6}}
.insight-card:nth-child(2){{border-top-color:#10b981}}
.insight-card:nth-child(3){{border-top-color:#f59e0b}}
.insight-card:nth-child(4){{border-top-color:#ef4444}}
.insight-card:nth-child(5){{border-top-color:#8b5cf6}}
.insight-card:nth-child(6){{border-top-color:#ec4899}}
.ic-header{{margin-bottom:10px}}
.ic-header h3{{font-size:17px;font-weight:700;color:#0f172a}}
.ic-theme{{font-size:11px;color:#64748b;display:block;margin-top:2px}}
.ic-desc{{font-size:13px;color:#475569;line-height:1.6;margin-bottom:12px}}
.ic-action{{font-size:13px;color:#0f172a;background:#f1f5f9;padding:10px 14px;border-radius:8px;line-height:1.5}}
.ic-papers{{font-size:11px;color:#94a3b8;margin-top:8px}}

/* ===== GAP ANALYSIS ===== */
.gap-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;margin-top:24px}}
.gap-col{{background:#fff;border-radius:12px;padding:20px 24px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.gap-col h4{{font-size:15px;font-weight:700;margin-bottom:12px}}
.gap-col ul{{list-style:none;font-size:13px;line-height:1.8;color:#475569}}
.gap-col ul li::before{{margin-right:8px}}
.gap-col.have{{border-left:4px solid #10b981}}
.gap-col.have ul li::before{{content:'✅'}}
.gap-col.missing{{border-left:4px solid #f59e0b}}
.gap-col.missing ul li::before{{content:'🔧'}}
.gap-col.unique{{border-left:4px solid #8b5cf6}}
.gap-col.unique ul li::before{{content:'💎'}}

/* ===== ABOUT SECTION ===== */
.about{{background:#0f172a;color:#e2e8f0;padding:48px 24px;margin-top:48px}}
.about-inner{{max-width:1280px;margin:0 auto}}
.about h2{{font-size:22px;color:#fff;margin-bottom:16px}}
.about p{{font-size:14px;color:#94a3b8;line-height:1.8;max-width:800px}}
.about code{{background:#1e293b;padding:2px 8px;border-radius:4px;font-size:13px;color:#10b981}}
.about a{{color:#60a5fa}}

/* ===== FOOTER ===== */
footer{{background:#0f172a;border-top:1px solid #1e293b;padding:24px;text-align:center;font-size:12px;color:#64748b}}
footer a{{color:#94a3b8}}

@media(max-width:768px){{
  .papers-grid,.insights-grid{{grid-template-columns:1fr}}
  .hero-stats{{gap:12px}}
  .hero-stat .hs-num{{font-size:28px}}
  .filter-bar{{flex-direction:column;align-items:stretch}}
  .filter-bar input{{min-width:0}}
}}

/* ===== SCROLL-TO-TOP ===== */
.scroll-top{{position:fixed;bottom:24px;right:24px;width:44px;height:44px;background:#0f172a;color:#fff;border:none;border-radius:50%;font-size:20px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.2);opacity:0;transition:opacity .3s;z-index:200}}
.scroll-top.visible{{opacity:1}}
</style>
</head>
<body>

<nav>
  <div class="nav-inner">
    <div class="nav-logo">🔬 <span>Auto-Eval</span> Research</div>
    <div class="nav-links">
      <a href="#papers">📄 论文</a>
      <a href="#insights">💡 洞察</a>
      <a href="#gap">📊 差距分析</a>
      <a href="#about">ℹ️ 关于</a>
    </div>
  </div>
</nav>

<section class="hero">
  <div class="container">
    <h1>车控 Agent 评测<br><span>自动化研究门户</span></h1>
    <p>基于 Semantic Scholar + arXiv API 的论文自动检索、摘要与洞察提取。
    聚焦 LLM Agent 评测、函数调用基准、车载 Agent 评测方法。</p>
    <div class="hero-stats">
      <div class="hero-stat"><div class="hs-num">{total_papers}</div><div class="hs-label">收录论文</div></div>
      <div class="hero-stat"><div class="hs-num">{len(topics)}</div><div class="hs-label">研究方向</div></div>
      <div class="hero-stat"><div class="hs-num">{curated}</div><div class="hs-label">车控高度相关</div></div>
      <div class="hero-stat"><div class="hs-num">{total_citations:,}</div><div class="hs-label">累计引用</div></div>
      <div class="hero-stat"><div class="hs-num">{len(insights.get('cross_cutting_themes', []))}</div><div class="hs-label">跨领域洞察</div></div>
    </div>
  </div>
</section>

<section class="section" id="papers">
  <div class="container">
    <div class="section-header">
      <h2>📄 论文数据库</h2>
      <p>收录 LLM Agent 评测、函数调用基准、车载 Agent 评估等方向的代表性论文和框架</p>
    </div>

    <div class="filter-bar">
      <input type="text" placeholder="🔍 搜索论文标题、作者、摘要..." id="searchInput" oninput="filterPapers()">
      <button class="topic-btn active" data-topic="all" onclick="filterTopic('all', this)">全部<span class="count">{total_papers}</span></button>
      {topic_buttons}
      <select class="sort-select" onchange="sortPapers(this.value)">
        <option value="relevance">按车控相关度</option>
        <option value="citations">按引用数</option>
        <option value="year">按年份</option>
      </select>
      <button class="clear-btn" onclick="clearFilters()">重置筛选</button>
    </div>

    <div class="papers-grid" id="papersGrid">
      {paper_cards}
    </div>
  </div>
</section>

<section class="section" id="insights" style="background:#f1f5f9">
  <div class="container">
    <div class="section-header">
      <h2>💡 跨论文洞察</h2>
      <p>从 {total_papers} 篇论文中提取的 6 个跨领域共识，并映射到车控评测改进方向</p>
    </div>
    <div class="insights-grid">
      {insight_cards}
    </div>
  </div>
</section>

<section class="section" id="gap">
  <div class="container">
    <div class="section-header">
      <h2>📊 差距分析: 我们的评测 vs 业界基准</h2>
      <p>将现有车控评测集（207 条用例，48 Tags，6 维金标准）与业界主流评测框架进行系统对比</p>
    </div>
    {gap_html}
  </div>
</section>

<section class="about" id="about">
  <div class="about-inner">
    <h2>ℹ️ 关于 Auto-Eval Research</h2>
    <p>
      本项目是一个<b>自动化评测研究流水线</b>（Auto-Research Pipeline），旨在自动检索、筛选、摘要和综合
      LLM Agent 评测领域的学术论文与工业框架，并将研究成果系统性地应用到
      <b>车控场景的 Agent 评测集设计</b>中。
    </p>
    <p style="margin-top:12px">
      <strong>数据源:</strong> Semantic Scholar API, arXiv API, 论文官方仓库<br>
      <strong>更新频率:</strong> 运行 <code>python3 auto_research.py --api</code> 即可拉取最新论文<br>
      <strong>方法论:</strong> 多源检索 → 去重合并 → 结构化摘要 → 跨论文洞察 → 车控映射<br>
      <strong>生成时间:</strong> {now}<br>
      <strong>代码:</strong> <a href="https://github.com/jenniferwingna/auto_eval" target="_blank">github.com/jenniferwingna/auto_eval</a>
    </p>
    <p style="margin-top:12px;font-size:12px;color:#64748b">
      受业界 Auto-Research 工具（GPT Researcher, PaperQA2, Semantic Scholar）启发构建。
      评测集设计参考了 BFCL, ToolBench, API-Bank, ToolSandbox, τ²-bench, CAR-bench, MetaTool,
      TRAJECT-Bench, CarMem, AgentBench, HELM 等多个业界基准的最佳实践。
    </p>
  </div>
</section>

<footer>
  <div class="container">
    <p>Auto-Eval Research Portal · Powered by Semantic Scholar &amp; arXiv · <a href="https://github.com/jenniferwingna/auto_eval" target="_blank">GitHub</a></p>
  </div>
</footer>

<button class="scroll-top" id="scrollTop" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">↑</button>

<script>
// ---- Scroll to top button ----
window.addEventListener('scroll', function() {{
  document.getElementById('scrollTop').classList.toggle('visible', window.scrollY > 300);
}});

// ---- Paper filtering ----
let activeTopic = 'all';
let activeSort = 'relevance';

function filterPapers() {{
  const query = (document.getElementById('searchInput').value || '').toLowerCase();
  const cards = document.querySelectorAll('.paper-card');
  cards.forEach(card => {{
    let show = true;
    if (activeTopic !== 'all' && card.dataset.topic !== activeTopic) show = false;
    if (query) {{
      const text = card.textContent.toLowerCase();
      if (!text.includes(query)) show = false;
    }}
    card.classList.toggle('hidden', !show);
  }});
}}

function filterTopic(topic, btn) {{
  activeTopic = topic;
  document.querySelectorAll('.topic-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  filterPapers();
}}

function sortPapers(method) {{
  activeSort = method;
  const grid = document.getElementById('papersGrid');
  const cards = Array.from(grid.querySelectorAll('.paper-card'));
  cards.sort((a, b) => {{
    if (method === 'relevance') return parseInt(b.dataset.score) - parseInt(a.dataset.score);
    if (method === 'citations') {{
      const ca = parseInt(a.querySelector('.pc-citations')?.textContent || '0');
      const cb = parseInt(b.querySelector('.pc-citations')?.textContent || '0');
      return cb - ca;
    }}
    if (method === 'year') return parseInt(b.dataset.year||'0') - parseInt(a.dataset.year||'0');
    return 0;
  }});
  cards.forEach(c => grid.appendChild(c));
}}

function clearFilters() {{
  document.getElementById('searchInput').value = '';
  activeTopic = 'all';
  activeSort = 'relevance';
  document.querySelectorAll('.topic-btn').forEach(b => b.classList.remove('active'));
  document.querySelector('.topic-btn[data-topic="all"]').classList.add('active');
  document.querySelector('.sort-select').value = 'relevance';
  const grid = document.getElementById('papersGrid');
  const cards = Array.from(grid.querySelectorAll('.paper-card'));
  cards.forEach(c => c.classList.remove('hidden'));
  cards.sort((a, b) => parseInt(b.dataset.score) - parseInt(a.dataset.score));
  cards.forEach(c => grid.appendChild(c));
}}

// Keyboard shortcut: / to focus search
document.addEventListener('keydown', function(e) {{
  if (e.key === '/' && document.activeElement === document.body) {{
    e.preventDefault();
    document.getElementById('searchInput').focus();
  }}
}});
</script>
</body>
</html>'''

    return html


def main():
    print("🔨 Generating Auto-Eval Research Website...")
    papers, insights = load_data()
    print(f"   Papers: {len(papers)}")
    print(f"   Insights themes: {len(insights.get('cross_cutting_themes', []))}")

    html = generate_html(papers, insights)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = os.path.getsize(OUTPUT_HTML) / 1024
    print(f"   ✅ Website generated: {OUTPUT_HTML} ({size_kb:.1f} KB)")
    print(f"   🌐 Open in browser or deploy to GitHub Pages")


if __name__ == "__main__":
    main()

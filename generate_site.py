#!/usr/bin/env python3
"""
Website Generator V2 for Auto-Eval Research Portal
====================================================
Tab-based layout: 论文库 | 车控启示 | 评测集生成 | 差距分析 | 关于
Chinese-first UI with bilingual paper data support.
"""

import json, os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PAPERS_JSON = os.path.join(SCRIPT_DIR, "papers.json")
INSIGHTS_JSON = os.path.join(SCRIPT_DIR, "insights.json")
RESEARCH_CASES_JSON = os.path.join(SCRIPT_DIR, "research_eval_cases.json")
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "index.html")

def load_json(path, default=None):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default or {}

def topic_label_zh(topic_key):
    return {
        "agent_evaluation": "Agent 评测框架",
        "function_calling": "函数调用评测",
        "car_agent": "车载 Agent",
        "eval_methodology": "评测方法论",
        "chinese_agent": "中文 Agent",
    }.get(topic_key, topic_key)

def topic_color(topic_key):
    return {
        "agent_evaluation": "#3b82f6",
        "function_calling": "#10b981",
        "car_agent": "#f59e0b",
        "eval_methodology": "#8b5cf6",
        "chinese_agent": "#ef4444",
    }.get(topic_key, "#64748b")

def score_stars(score):
    return "★" * score + "☆" * (5 - score)


def build_html():
    papers = load_json(PAPERS_JSON, {}).get("papers", [])
    insights = load_json(INSIGHTS_JSON, {})
    research_cases = load_json(RESEARCH_CASES_JSON, [])

    if isinstance(research_cases, dict):
        research_cases = research_cases.get("entries", research_cases.get("cases", []))

    total_papers = len(papers)
    total_cases = len(research_cases)

    # ---- Stats ----
    topics = {}
    for p in papers:
        t = p.get("topic", "unknown")
        topics[t] = topics.get(t, 0) + 1
    curated = sum(1 for p in papers if p.get("car_control_score", 0) >= 4)
    total_citations = sum(p.get("citations", 0) for p in papers)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ============ TAB 1: 论文库 ============
    topic_buttons = ""
    for tk in ["agent_evaluation", "function_calling", "car_agent", "eval_methodology", "chinese_agent"]:
        if tk in topics:
            zh = topic_label_zh(tk)
            tc = topic_color(tk)
            topic_buttons += f'<button class="tbtn" data-topic="{tk}" style="--tc:{tc}" onclick="filterTopic(\'{tk}\',this)">{zh}<span class="tcnt">{topics[tk]}</span></button>'

    paper_cards = ""
    for p in papers:
        tid = p.get("topic", "")
        zh = topic_label_zh(tid)
        color = topic_color(tid)
        score = p.get("car_control_score", 0)
        stars = score_stars(score) if score else ""
        authors = ", ".join(p.get("authors", [])[:4])
        if len(p.get("authors", [])) > 4:
            authors += " 等"
        year = p.get("year", "")
        venue = p.get("venue", "")
        citations = p.get("citations", 0)
        url = p.get("url", "#")
        car_insight = p.get("car_control_insight", "")

        # Tags
        tags_html = "".join(f'<span class="tag">{t}</span>' for t in p.get("tags", [])[:6])

        # Findings
        findings_html = ""
        for f in p.get("key_findings", []):
            findings_html += f'<li>{f}</li>'

        methodology = p.get("methodology", "")

        # Pre-compute nested HTML to avoid f-string escaping issues
        details_html = ""
        if findings_html:
            meth_section = f'<p class="meth"><b>方法论:</b> {methodology}</p>' if methodology else ""
            details_html = f'<details class="pcard-det"><summary>📋 关键发现与方法论</summary><ul class="findlist">{findings_html}</ul>{meth_section}</details>'

        car_box_html = ""
        if car_insight:
            stars_section = f'<span class="stars">{stars}</span>' if stars else ""
            car_box_html = f'<div class="car-box"><span class="car-label">🚗 车控启示</span><p>{car_insight}</p>{stars_section}</div>'

        paper_cards += f'''
        <div class="pcard" data-topic="{tid}" data-year="{year}" data-score="{score}">
          <div class="pcard-top">
            <span class="pcard-topic" style="background:{color}">{zh}</span>
            {f'<span class="pcard-venue">{venue}</span>' if venue else ''}
            <span class="pcard-year">{year}</span>
            {f'<span class="pcard-cite">{citations}+ 引用</span>' if citations else ''}
          </div>
          <h3 class="pcard-title"><a href="{url}" target="_blank">{p["title"]}</a></h3>
          <p class="pcard-auth">{authors}</p>
          <p class="pcard-abs">{p.get("abstract", "")[:350]}{"..." if len(p.get("abstract", "")) > 350 else ""}</p>
          {f'<div class="pcard-tags">{tags_html}</div>' if tags_html else ''}
          {details_html}
          {car_box_html}
        </div>'''

    # ============ TAB 2: 车控启示 ============
    insight_cards = ""
    for theme in insights.get("cross_cutting_themes", []):
        papers_ref = ", ".join(theme.get("papers", [])[:4])
        insight_cards += f'''
        <div class="ins-card">
          <h3>{theme.get("theme_zh", theme.get("theme", ""))}</h3>
          <span class="ins-theme-en">{theme.get("theme", "")}</span>
          <p class="ins-desc">{theme.get("description", "")}</p>
          <div class="ins-action"><b>🎯 车控行动项:</b> {theme.get("car_control_action", "")}</div>
          {f'<div class="ins-src">📄 {papers_ref}</div>' if papers_ref else ''}
        </div>'''

    # ============ TAB 3: 评测集生成 ============
    if total_cases > 0:
        case_cards = ""
        for c in research_cases:
            cid = c.get("id", "?")
            tag = c.get("tag_id", "")
            domain = c.get("domain", "")
            query = c.get("query", "")
            expected = c.get("expected", "")
            assertion = c.get("assertion", "")
            source_paper = c.get("source_paper", "")
            source_insight = c.get("source_insight", "")
            status = c.get("status", "pending_review")
            status_labels = {"pending_review": "⏳ 待审批", "approved": "✅ 已采纳", "rejected": "❌ 已拒绝"}
            status_cls = {"pending_review": "s-pending", "approved": "s-approved", "rejected": "s-rejected"}

            case_cards += f'''
            <div class="ecard {status_cls.get(status, '')}" data-status="{status}">
              <div class="ecard-top">
                <span class="ecard-tag">{tag}</span>
                <span class="ecard-domain">{domain}</span>
                <span class="ecard-id">{cid}</span>
                <span class="ecard-status">{status_labels.get(status, status)}</span>
              </div>
              <div class="ecard-query">"{query}"</div>
              <div class="ecard-exp">预期: {expected}</div>
              <div class="ecard-meta">
                <span class="ecard-assert">{assertion}</span>
                {f'<span class="ecard-src">📄 {source_paper}</span>' if source_paper else ''}
                {f'<span class="ecard-ins">💡 {source_insight}</span>' if source_insight else ''}
              </div>
            </div>'''

        cases_section = f'''
        <div class="cases-bar">
          <span>📋 共 <b>{total_cases}</b> 条待审批用例</span>
          <div>
            <button class="cbtn active" onclick="filterCases('all',this)">全部</button>
            <button class="cbtn" onclick="filterCases('pending_review',this)">⏳ 待审批</button>
            <button class="cbtn" onclick="filterCases('approved',this)">✅ 已采纳</button>
            <button class="cbtn" onclick="filterCases('rejected',this)">❌ 已拒绝</button>
            <button class="cbtn export" onclick="exportCases()">📥 导出可合并用例</button>
          </div>
        </div>
        <div class="ecards-grid">{case_cards}</div>'''
    else:
        cases_section = '''
        <div class="empty-state">
          <p style="font-size:48px">🔧</p>
          <h3>暂无自动生成的评测用例</h3>
          <p>运行 <code>python3 apply_insights.py</code> 从论文洞察生成新用例</p>
        </div>'''

    # ============ TAB 4: 差距分析 ============
    gap_html = ""
    if insights.get("gap_analysis"):
        ga = insights["gap_analysis"]
        have_items = "".join(f"<li>{i}</li>" for i in ga.get("what_we_have", []))
        missing_items = "".join(f"<li>{i}</li>" for i in ga.get("what_benchmarks_have_that_we_dont", []))
        unique_items = "".join(f"<li>{i}</li>" for i in ga.get("what_we_have_that_benchmarks_dont", []))
        gap_html = f'''
        <div class="gap-grid">
          <div class="gap-col have"><h4>✅ 我们已有的</h4><ul>{have_items}</ul></div>
          <div class="gap-col missing"><h4>🔧 业界有而我们缺的</h4><ul>{missing_items}</ul></div>
          <div class="gap-col unique"><h4>💎 我们有而业界缺的</h4><ul>{unique_items}</ul></div>
        </div>'''

    # ============ FULL HTML ============
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Auto-Eval Research | 车控 Agent 评测研究门户</title>
<meta name="description" content="自动化评测研究流水线——论文检索、洞察提取、评测集生成、车控场景应用">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth;font-size:16px}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;background:#f8fafc;color:#1e293b;line-height:1.6}}
a{{color:#2563eb;text-decoration:none}}a:hover{{text-decoration:underline}}
.container{{max-width:1320px;margin:0 auto;padding:0 24px}}

/* NAV */
nav{{background:#fff;border-bottom:1px solid #e2e8f0;position:sticky;top:0;z-index:100}}
.nav-inner{{max-width:1320px;margin:0 auto;padding:0 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px}}
.nav-logo{{font-weight:800;font-size:18px;color:#0f172a;padding:14px 0}}
.nav-logo span{{color:#3b82f6}}
.nav-tabs{{display:flex;gap:4px}}
.nav-tab{{padding:14px 18px;border:none;background:none;cursor:pointer;font-size:14px;font-weight:500;color:#64748b;border-bottom:3px solid transparent;transition:all .15s;white-space:nowrap}}
.nav-tab:hover{{color:#0f172a;background:#f8fafc}}
.nav-tab.active{{color:#3b82f6;border-bottom-color:#3b82f6;font-weight:700}}

/* HERO */
.hero{{background:linear-gradient(135deg,#0f172a,#1e293b,#1e3a5f);color:#fff;padding:56px 24px;text-align:center}}
.hero h1{{font-size:clamp(26px,5vw,40px);font-weight:800;margin-bottom:8px}}
.hero h1 span{{background:linear-gradient(135deg,#3b82f6,#10b981);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.hero p{{color:#94a3b8;font-size:16px;max-width:680px;margin:0 auto 20px}}
.hero-stats{{display:flex;gap:20px;justify-content:center;flex-wrap:wrap}}
.hstat{{text-align:center;min-width:90px}}
.hstat .num{{font-size:34px;font-weight:800;color:#fff}}
.hstat .lbl{{font-size:12px;color:#94a3b8;margin-top:2px}}

/* TABS CONTENT */
.tab-content{{display:none;padding:40px 0}}
.tab-content.active{{display:block}}

/* SECTION HEADERS */
.sec-hdr{{margin-bottom:28px}}
.sec-hdr h2{{font-size:24px;font-weight:700;color:#0f172a}}
.sec-hdr p{{color:#64748b;font-size:14px;margin-top:4px}}

/* FILTER BAR */
.fbar{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:20px;padding:14px 18px;background:#fff;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.05);position:sticky;top:57px;z-index:40}}
.fbar input{{padding:8px 14px;border:1px solid #e2e8f0;border-radius:8px;font-size:14px;min-width:220px;outline:none}}
.fbar input:focus{{border-color:#3b82f6}}
.tbtn{{padding:6px 14px;border:1.5px solid #e2e8f0;background:#fff;border-radius:8px;cursor:pointer;font-size:13px;font-weight:500;transition:all .15s;display:flex;align-items:center;gap:5px}}
.tbtn:hover{{border-color:var(--tc);background:#f8fafc}}
.tbtn.active{{background:var(--tc);color:#fff;border-color:var(--tc)}}
.tcnt{{font-size:11px;background:rgba(0,0,0,.06);padding:1px 6px;border-radius:8px}}
.tbtn.active .tcnt{{background:rgba(255,255,255,.2)}}
.fbar .reset{{padding:6px 14px;border:1px solid #fecaca;background:#fef2f2;color:#991b1b;border-radius:8px;cursor:pointer;font-size:13px;margin-left:auto}}
.fbar select{{padding:6px 12px;border:1px solid #e2e8f0;border-radius:8px;font-size:13px;background:#fff}}

/* PAPER CARDS */
.pgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(370px,1fr));gap:18px}}
.pcard{{background:#fff;border-radius:10px;padding:18px 22px;box-shadow:0 1px 3px rgba(0,0,0,.05);border:1px solid #f1f5f9;transition:all .2s}}
.pcard:hover{{box-shadow:0 4px 12px rgba(0,0,0,.08);transform:translateY(-2px)}}
.pcard.hidden{{display:none}}
.pcard-top{{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:8px}}
.pcard-topic{{font-size:10px;font-weight:600;color:#fff;padding:2px 8px;border-radius:4px}}
.pcard-venue{{font-size:10px;color:#64748b;background:#f1f5f9;padding:2px 8px;border-radius:4px}}
.pcard-year{{font-size:11px;color:#94a3b8;font-weight:500}}
.pcard-cite{{font-size:10px;color:#64748b;margin-left:auto}}
.pcard-title{{font-size:16px;font-weight:700;line-height:1.3;margin-bottom:4px}}
.pcard-title a{{color:#0f172a}}
.pcard-auth{{font-size:12px;color:#64748b;margin-bottom:6px}}
.pcard-abs{{font-size:12px;color:#475569;line-height:1.5;margin-bottom:8px;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}}
.pcard-tags{{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:8px}}
.tag{{font-size:10px;background:#eff6ff;color:#2563eb;padding:2px 7px;border-radius:3px;font-weight:500}}
.pcard-det{{font-size:12px;margin-top:auto}}
.pcard-det summary{{cursor:pointer;color:#3b82f6;font-weight:500;padding:4px 0}}
.findlist{{margin:6px 0 0 18px;color:#475569;font-size:11px;line-height:1.6}}
.findlist li{{margin-bottom:2px}}
.meth{{font-size:11px;color:#64748b;margin-top:6px;font-style:italic}}
.car-box{{margin-top:10px;padding:10px 14px;background:linear-gradient(135deg,#fffbeb,#fef3c7);border-left:3px solid #f59e0b;border-radius:0 8px 8px 0;font-size:12px}}
.car-label{{font-weight:700;color:#92400e;font-size:11px;display:block;margin-bottom:3px}}
.car-box p{{color:#78350f;line-height:1.5}}
.stars{{color:#f59e0b;font-size:13px;letter-spacing:1px}}

/* INSIGHT CARDS */
.igrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(370px,1fr));gap:18px}}
.ins-card{{background:#fff;border-radius:10px;padding:18px 22px;box-shadow:0 1px 3px rgba(0,0,0,.05);border-top:4px solid #3b82f6}}
.ins-card:nth-child(1){{border-top-color:#3b82f6}}
.ins-card:nth-child(2){{border-top-color:#10b981}}
.ins-card:nth-child(3){{border-top-color:#f59e0b}}
.ins-card:nth-child(4){{border-top-color:#ef4444}}
.ins-card:nth-child(5){{border-top-color:#8b5cf6}}
.ins-card:nth-child(6){{border-top-color:#ec4899}}
.ins-card h3{{font-size:16px;font-weight:700;color:#0f172a;margin-bottom:2px}}
.ins-theme-en{{font-size:11px;color:#94a3b8}}
.ins-desc{{font-size:13px;color:#475569;line-height:1.6;margin:8px 0}}
.ins-action{{font-size:13px;background:#f1f5f9;padding:10px 14px;border-radius:8px;line-height:1.5}}
.ins-src{{font-size:11px;color:#94a3b8;margin-top:6px}}

/* EVAL CASE CARDS */
.cases-bar{{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:20px;font-size:14px;color:#64748b}}
.cbtn{{padding:5px 14px;border:1px solid #e2e8f0;background:#fff;border-radius:6px;cursor:pointer;font-size:12px;transition:all .15s}}
.cbtn:hover{{background:#f1f5f9}}
.cbtn.active{{background:#334155;color:#fff;border-color:#334155}}
.cbtn.export{{background:#2563eb;color:#fff;border-color:#2563eb}}
.ecards-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:14px}}
.ecard{{background:#fff;border-radius:8px;padding:14px 18px;box-shadow:0 1px 2px rgba(0,0,0,.04);border-left:3px solid #e2e8f0;transition:all .15s}}
.ecard.hidden{{display:none}}
.ecard.s-pending{{border-left-color:#f59e0b}}
.ecard.s-approved{{border-left-color:#10b981}}
.ecard.s-rejected{{border-left-color:#ef4444}}
.ecard-top{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px}}
.ecard-tag{{font-size:11px;font-weight:600;background:#eff6ff;color:#2563eb;padding:2px 8px;border-radius:4px}}
.ecard-domain{{font-size:11px;color:#64748b;background:#f1f5f9;padding:2px 8px;border-radius:4px}}
.ecard-id{{font-size:10px;color:#94a3b8;font-family:monospace}}
.ecard-status{{font-size:11px;font-weight:600;margin-left:auto;padding:2px 8px;border-radius:4px}}
.s-pending .ecard-status{{background:#fef3c7;color:#92400e}}
.s-approved .ecard-status{{background:#dcfce7;color:#166534}}
.s-rejected .ecard-status{{background:#fef2f2;color:#991b1b}}
.ecard-query{{font-size:15px;font-weight:600;color:#0f172a;margin-bottom:4px}}
.ecard-exp{{font-size:12px;color:#475569;margin-bottom:6px}}
.ecard-meta{{display:flex;gap:6px;flex-wrap:wrap}}
.ecard-assert{{font-size:10px;background:#e0e7ff;color:#3730a3;padding:2px 8px;border-radius:3px}}
.ecard-src{{font-size:10px;color:#64748b;background:#f1f5f9;padding:2px 8px;border-radius:3px}}
.ecard-ins{{font-size:10px;color:#92400e;background:#fef3c7;padding:2px 8px;border-radius:3px}}

/* GAP ANALYSIS */
.gap-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}}
.gap-col{{background:#fff;border-radius:10px;padding:18px 22px;box-shadow:0 1px 3px rgba(0,0,0,.05)}}
.gap-col h4{{font-size:15px;font-weight:700;margin-bottom:10px}}
.gap-col ul{{list-style:none;font-size:13px;line-height:1.8;color:#475569}}
.gap-col.have{{border-left:4px solid #10b981}}
.gap-col.missing{{border-left:4px solid #f59e0b}}
.gap-col.unique{{border-left:4px solid #8b5cf6}}

/* EMPTY STATE */
.empty-state{{text-align:center;padding:60px 20px;color:#64748b}}
.empty-state code{{background:#e2e8f0;padding:2px 8px;border-radius:4px;font-size:13px}}

/* ABOUT */
.about{{background:#0f172a;color:#e2e8f0;padding:44px 24px;margin-top:40px}}
.about-inner{{max-width:1320px;margin:0 auto}}
.about h2{{font-size:20px;color:#fff;margin-bottom:12px}}
.about p{{font-size:13px;color:#94a3b8;line-height:1.8;max-width:800px}}
.about code{{background:#1e293b;padding:2px 8px;border-radius:4px;font-size:12px;color:#10b981}}
.about a{{color:#60a5fa}}

footer{{background:#0f172a;border-top:1px solid #1e293b;padding:20px;text-align:center;font-size:11px;color:#64748b}}

/* SCROLL TOP */
.st{{position:fixed;bottom:20px;right:20px;width:40px;height:40px;background:#0f172a;color:#fff;border:none;border-radius:50%;font-size:18px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.15);opacity:0;transition:opacity .3s;z-index:200}}
.st.visible{{opacity:1}}

@media(max-width:768px){{
  .pgrid,.igrid,.ecards-grid,.gap-grid{{grid-template-columns:1fr}}
  .hero-stats{{gap:10px}}
  .hstat .num{{font-size:26px}}
  .nav-tab{{padding:10px 12px;font-size:12px}}
  .fbar{{flex-direction:column;align-items:stretch}}
}}
</style>
</head>
<body>

<nav>
  <div class="nav-inner">
    <div class="nav-logo">🔬 <span>Auto-Eval</span> Research</div>
    <div class="nav-tabs">
      <button class="nav-tab active" onclick="switchTab('papers',this)">📄 论文库</button>
      <button class="nav-tab" onclick="switchTab('insights',this)">💡 车控启示</button>
      <button class="nav-tab" onclick="switchTab('cases',this)">🔧 评测集生成 <sup style="color:#f59e0b">{total_cases}</sup></button>
      <button class="nav-tab" onclick="switchTab('gap',this)">📊 差距分析</button>
      <button class="nav-tab" onclick="switchTab('about',this)">ℹ️ 关于</button>
    </div>
  </div>
</nav>

<section class="hero">
  <h1>车控 Agent 评测<br><span>自动化研究门户</span></h1>
  <p>基于 Semantic Scholar + arXiv API 的论文自动检索、中文摘要与洞察提取。将研究成果系统性应用到车控场景的 Agent 评测集设计中。</p>
  <div class="hero-stats">
    <div class="hstat"><div class="num">{total_papers}</div><div class="lbl">收录论文</div></div>
    <div class="hstat"><div class="num">{len(topics)}</div><div class="lbl">研究方向</div></div>
    <div class="hstat"><div class="num">{curated}</div><div class="lbl">车控高度相关</div></div>
    <div class="hstat"><div class="num">{total_cases}</div><div class="lbl">生成用例</div></div>
    <div class="hstat"><div class="num">{len(insights.get('cross_cutting_themes',[]))}</div><div class="lbl">跨领域洞察</div></div>
  </div>
</section>

<div class="container">

<!-- TAB 1: 论文库 -->
<div class="tab-content active" id="tab-papers">
  <div class="sec-hdr"><h2>📄 论文数据库</h2><p>收录 LLM Agent 评测、函数调用基准、车载 Agent 评估等方向的代表性论文</p></div>
  <div class="fbar">
    <input type="text" placeholder="🔍 搜索论文..." id="searchBox" oninput="filterPapers()">
    <button class="tbtn active" data-topic="all" onclick="filterTopic('all',this)">全部<span class="tcnt">{total_papers}</span></button>
    {topic_buttons}
    <select onchange="sortPapers(this.value)" style="padding:6px 12px;border:1px solid #e2e8f0;border-radius:8px;font-size:13px">
      <option value="relevance">按车控相关度</option>
      <option value="citations">按引用数</option>
      <option value="year">按年份</option>
    </select>
    <button class="reset" onclick="resetFilters()">重置</button>
  </div>
  <div class="pgrid" id="papersGrid">{paper_cards}</div>
</div>

<!-- TAB 2: 车控启示 -->
<div class="tab-content" id="tab-insights">
  <div class="sec-hdr"><h2>💡 跨论文洞察</h2><p>从 {total_papers} 篇论文中提取的 {len(insights.get('cross_cutting_themes',[]))} 个跨领域共识，映射到车控评测改进方向</p></div>
  <div class="igrid">{insight_cards}</div>
</div>

<!-- TAB 3: 评测集生成 -->
<div class="tab-content" id="tab-cases">
  <div class="sec-hdr"><h2>🔧 评测集自动生成</h2><p>基于论文洞察自动生成的评测用例。每条用例标注来源论文和洞察，审批后可合并到正式评测集。</p></div>
  {cases_section}
</div>

<!-- TAB 4: 差距分析 -->
<div class="tab-content" id="tab-gap">
  <div class="sec-hdr"><h2>📊 差距分析</h2><p>将现有车控评测集（207 条用例，48 Tags，6 维金标准）与业界主流评测框架进行系统对比</p></div>
  {gap_html}
</div>

</div>

<!-- TAB 5: 关于 -->
<div class="about" id="tab-about">
  <div class="about-inner">
    <h2>ℹ️ 关于 Auto-Eval Research</h2>
    <p>本项目是一个<b>自动化评测研究流水线</b>，自动检索、筛选、摘要 LLM Agent 评测领域的学术论文与工业框架，并将研究成果系统性应用到<b>车控场景的 Agent 评测集设计</b>中。</p>
    <p style="margin-top:10px"><b>数据源:</b> Semantic Scholar API, arXiv API<br><b>每日更新:</b> GitHub Actions 每天自动拉取最新论文<br><b>方法论:</b> 多源检索 → 去重合并 → 结构化摘要 → 跨论文洞察 → 车控映射 → 评测集生成<br><b>更新时间:</b> {now}<br><b>代码:</b> <a href="https://github.com/jenniferwingna/auto_eval" target="_blank">github.com/jenniferwingna/auto_eval</a></p>
    <p style="margin-top:8px;font-size:11px;color:#64748b">受 GPT Researcher, PaperQA2, STORM, Semantic Scholar 等工具启发。评测集设计参考 BFCL, ToolBench, API-Bank, ToolSandbox, τ²-bench, CAR-bench, MetaTool, TRAJECT-Bench, CarMem, AgentBench, HELM 等业界基准。</p>
  </div>
</div>

<footer><div class="container">Auto-Eval Research Portal · Powered by Semantic Scholar &amp; arXiv · <a href="https://github.com/jenniferwingna/auto_eval" target="_blank">GitHub</a></div></footer>

<button class="st" id="scrollTop" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">↑</button>

<script>
// Scroll top
window.addEventListener('scroll',()=>{{document.getElementById('scrollTop').classList.toggle('visible',window.scrollY>300)}});

// Tab switching
function switchTab(tab,btn){{
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(b=>b.classList.remove('active'));
  document.getElementById('tab-'+tab).classList.add('active');
  btn.classList.add('active');
  window.scrollTo({{top:0,behavior:'smooth'}});
}}

// Paper filtering
let activeTopic='all';
function filterPapers(){{
  let q=(document.getElementById('searchBox')?.value||'').toLowerCase();
  document.querySelectorAll('.pcard').forEach(c=>{{
    let show=true;
    if(activeTopic!=='all'&&c.dataset.topic!==activeTopic)show=false;
    if(q&&!c.textContent.toLowerCase().includes(q))show=false;
    c.classList.toggle('hidden',!show);
  }});
}}
function filterTopic(t,btn){{
  activeTopic=t;
  document.querySelectorAll('.tbtn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  filterPapers();
}}
function sortPapers(method){{
  let grid=document.getElementById('papersGrid'),cards=Array.from(grid.querySelectorAll('.pcard'));
  cards.sort((a,b)=>{{
    if(method==='relevance')return parseInt(b.dataset.score)-parseInt(a.dataset.score);
    if(method==='citations'){{let ca=parseInt(a.querySelector('.pcard-cite')?.textContent||'0'),cb=parseInt(b.querySelector('.pcard-cite')?.textContent||'0');return cb-ca;}}
    if(method==='year')return parseInt(b.dataset.year||'0')-parseInt(a.dataset.year||'0');
    return 0;
  }});
  cards.forEach(c=>grid.appendChild(c));
}}
function resetFilters(){{
  document.getElementById('searchBox').value='';activeTopic='all';
  document.querySelectorAll('.tbtn').forEach(b=>b.classList.remove('active'));
  document.querySelector('.tbtn[data-topic="all"]').classList.add('active');
  let grid=document.getElementById('papersGrid'),cards=Array.from(grid.querySelectorAll('.pcard'));
  cards.forEach(c=>c.classList.remove('hidden'));
  cards.sort((a,b)=>parseInt(b.dataset.score)-parseInt(a.dataset.score));
  cards.forEach(c=>grid.appendChild(c));
}}
document.addEventListener('keydown',e=>{{if(e.key==='/'&&document.activeElement===document.body){{e.preventDefault();document.getElementById('searchBox').focus();}}}});

// Case filtering
function filterCases(status,btn){{
  document.querySelectorAll('.cbtn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.ecard').forEach(c=>c.classList.toggle('hidden',status!=='all'&&c.dataset.status!==status));
}}
function exportCases(){{
  let approved=Array.from(document.querySelectorAll('.ecard.s-approved')).map(c=>({{
    id:c.querySelector('.ecard-id')?.textContent||'',
    tag_id:c.querySelector('.ecard-tag')?.textContent||'',
    domain:c.querySelector('.ecard-domain')?.textContent||'',
    query:c.querySelector('.ecard-query')?.textContent?.replace(/^"|"$/g,'')||'',
    expected:c.querySelector('.ecard-exp')?.textContent?.replace('预期: ','')||'',
    assertion:c.querySelector('.ecard-assert')?.textContent||'',
    source_paper:c.querySelector('.ecard-src')?.textContent?.replace('📄 ','')||'',
  }}));
  if(approved.length===0){{alert('没有已采纳的用例。请先在用例上将状态改为已采纳。');return;}}
  let blob=new Blob([JSON.stringify({{entries:approved}},null,2)],{{type:'application/json'}});
  let a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='approved_eval_cases.json';a.click();
}}
</script>
</body>
</html>'''

    return html


def main():
    print("🔨 生成 Auto-Eval Research V2 网站...")
    html = build_html()
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    size_kb = os.path.getsize(OUTPUT_HTML) / 1024
    print(f"   ✅ 网站已生成: {OUTPUT_HTML} ({size_kb:.1f} KB)")
    print(f"   🌐 本地预览: open {OUTPUT_HTML}")


if __name__ == "__main__":
    main()

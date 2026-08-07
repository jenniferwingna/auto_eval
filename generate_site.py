#!/usr/bin/env python3
"""
Website Generator V2.1 — Tab layout with Chinese paper details + grouped case approval.
"""
import json, os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def load_json(path, default=None):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default or {}

def topic_label_zh(tk):
    m = {"agent_evaluation":"Agent 评测框架","function_calling":"函数调用评测","car_agent":"车载 Agent","eval_methodology":"评测方法论","chinese_agent":"中文 Agent"}
    return m.get(tk, tk)

def topic_color(tk):
    return {"agent_evaluation":"#3b82f6","function_calling":"#10b981","car_agent":"#f59e0b","eval_methodology":"#8b5cf6","chinese_agent":"#ef4444"}.get(tk,"#64748b")

def stars_str(s):
    return "★"*s+"☆"*(5-s)

def build():
    papers = load_json(os.path.join(SCRIPT_DIR,"papers.json"),{}).get("papers",[])
    insights = load_json(os.path.join(SCRIPT_DIR,"insights.json"),{})
    rc_data = load_json(os.path.join(SCRIPT_DIR,"research_eval_cases.json"),[])
    if isinstance(rc_data, dict):
        cases = rc_data.get("entries", rc_data.get("cases", []))
    else:
        cases = rc_data

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_papers = len(papers)
    total_cases = len(cases)

    # Stats
    topics = {}
    for p in papers:
        t = p.get("topic","unknown")
        topics[t] = topics.get(t,0)+1
    curated = sum(1 for p in papers if p.get("car_control_score",0)>=4)

    # ======== TAB 1: PAPERS (click-to-expand Chinese detail) ========
    topic_btns = ""
    for tk in ["agent_evaluation","function_calling","car_agent","eval_methodology","chinese_agent"]:
        if tk in topics:
            zh = topic_label_zh(tk); tc = topic_color(tk)
            topic_btns += f'<button class="tbtn" data-topic="{tk}" style="--tc:{tc}" onclick="filterTopic(\'{tk}\',this)">{zh}<span class="tcnt">{topics[tk]}</span></button>'

    paper_cards = ""
    for i, p in enumerate(papers):
        tid = p.get("topic",""); zh_t = topic_label_zh(tid); color = topic_color(tid)
        pid = p.get("id","paper-"+str(i))
        score = p.get("car_control_score",0)
        stars = stars_str(score) if score else ""
        authors = ", ".join(p.get("authors",[])[:4])
        if len(p.get("authors",[]))>4: authors += " 等"
        title_zh = p.get("title_zh","")
        abstract_zh = p.get("abstract_zh","")
        findings_zh = p.get("findings_zh",[])
        findings_zh_html = "".join(f"<li>{f}</li>" for f in findings_zh)
        car_insight = p.get("car_control_insight","")
        methodology = p.get("methodology","")
        findings_en = p.get("key_findings",[])
        findings_en_html = "".join(f"<li>{f}</li>" for f in findings_en)
        tags_html = "".join(f'<span class="tag">{t}</span>' for t in p.get("tags",[])[:6])

        # Pre-compute car insight box
        car_box_html = ""
        if car_insight:
            s_html = f'<span class="stars">{stars}</span>' if stars else ""
            car_box_html = f'<div class="car-box"><span class="car-label">🚗 车控启示</span><p>{car_insight}</p>{s_html}</div>'

        paper_cards += f'''
        <div class="pcard" data-topic="{tid}" data-year="{p.get("year","")}" data-score="{score}" id="paper-{pid}">
          <div class="pcard-top">
            <span class="pcard-topic" style="background:{color}">{zh_t}</span>
            {f'<span class="pcard-venue">{p.get("venue","")}</span>' if p.get("venue") else ''}
            <span class="pcard-year">{p.get("year","")}</span>
            {f'<span class="pcard-cite">{p.get("citations",0)}+ 引用</span>' if p.get("citations") else ''}
            <button class="pcard-expand" onclick="togglePaperDetail('{pid}')" title="展开中文详情">📖</button>
          </div>
          <h3 class="pcard-title"><a href="{p.get("url","#")}" target="_blank">{p["title"]}</a></h3>
          {f'<p class="pcard-title-zh">{title_zh}</p>' if title_zh else ''}
          <p class="pcard-auth">{authors}</p>
          <p class="pcard-abs">{p.get("abstract","")[:300]}{"..." if len(p.get("abstract",""))>300 else ""}</p>
          {f'<div class="pcard-tags">{tags_html}</div>' if tags_html else ''}
          {car_box_html}

          <div class="pcard-detail" id="detail-{pid}" style="display:none">
            <div class="detail-inner">
              <h4>📝 中文摘要</h4>
              <p>{abstract_zh or "暂无中文摘要"}</p>
              {f'<h4>🔑 中文关键发现</h4><ul class="findlist">{findings_zh_html}</ul>' if findings_zh else ''}
              {f'<h4>📋 原文关键发现</h4><ul class="findlist">{findings_en_html}</ul>' if findings_en else ''}
              {f'<p class="meth"><b>方法论:</b> {methodology}</p>' if methodology else ''}
            </div>
          </div>
        </div>'''

    # ======== TAB 2: INSIGHTS ========
    insight_cards = ""
    for theme in insights.get("cross_cutting_themes",[]):
        pref = ", ".join(theme.get("papers",[])[:4])
        insight_cards += f'''
        <div class="ins-card">
          <h3>{theme.get("theme_zh",theme.get("theme",""))}</h3>
          <span class="ins-theme-en">{theme.get("theme","")}</span>
          <p class="ins-desc">{theme.get("description","")}</p>
          <div class="ins-action"><b>🎯 车控行动项:</b> {theme.get("car_control_action","")}</div>
          {f'<div class="ins-src">📄 {pref}</div>' if pref else ''}
        </div>'''

    # ======== TAB 3: CASES (grouped by paper, with approval) ========
    # Group cases by source_paper
    from collections import OrderedDict
    groups = OrderedDict()
    for c in cases:
        sp = c.get("source_paper","其他来源")
        if sp not in groups:
            groups[sp] = []
        groups[sp].append(c)

    # Paper group descriptions (Chinese methodology + insight summary for each group)
    group_descriptions = {
        "bfcl-v4, toolsandbox-2024, traject-bench-2026, tau2-bench-2024": {
            "papers": "BFCL v4 · ToolSandbox · TRAJECT-Bench · τ²-bench",
            "methodology": "BFCL v4 定义了有状态多轮函数调用评测标准；ToolSandbox 提出「里程碑 DAG」进行轨迹级评分；TRAJECT-Bench 揭示了「相似工具混淆」和「参数盲选」两大隐藏失败模式；τ²-bench 强调工具编排质量和错误恢复能力。",
            "insight": "单轮静态评测会高估实际性能 15-30%。评测必须追踪车辆状态跨轮变化，记录工具调用的完整轨迹而非只看最终结果。",
        },
        "agent-survey-2026, toolsandbox-2024, mcp-agentbench-2025": {
            "papers": "Agent Survey (ACL 2026) · ToolSandbox · MCP-AgentBench",
            "methodology": "ACL 2026 Agent 评测综述确立了「最终答案→执行轨迹→逐轮交互」三层评测架构；ToolSandbox 的里程碑 DAG 实现了中间步骤质量评估；MCP-AgentBench 提出「规则检查(80%)+LLM-judge(20%)」的双层判分方案。",
            "insight": "为 hard 组合题设计显式的里程碑（Milestone）路径。每一步工具调用都应有对应的验证点，而非只检查最终车辆状态。",
        },
        "traject-bench-2026, api-bank-2023, bfcl-v4": {
            "papers": "TRAJECT-Bench · API-Bank · BFCL v4",
            "methodology": "TRAJECT-Bench 发现「相似工具混淆」是 Agent 工具调用中最主要的失败模式——当两个工具描述重叠时（如 shade_curtain_opener vs shade_curtain_switch），模型选错工具的概率高达 40%+。API-Bank 将工具使用分解为规划→检索→执行三步，发现检索错误远多于参数错误。",
            "insight": "评测集必须覆盖功能相近的工具对（如 mirror_fold vs mirror_adjust、fragrance_switch vs fragrance_mode），测试模型在工具描述歧义下的辨别能力。",
        },
        "metatool-2024, bfcl-v4, api-bank-2023": {
            "papers": "MetaTool · BFCL v4 · API-Bank",
            "methodology": "MetaTool 首次将「相关性检测」——知道何时不调用工具——作为一等评测标准。实验表明模型在 20-40% 的无关查询中仍会触发工具调用。BFCL v4 将 relevance detection 纳入核心评测维度。",
            "insight": "评测集中负例（不该调用工具的 query）占比应从 15% 提升到 20-25%。关键是设计「微妙负例」——参数合法但语义矛盾、跨域混淆、闲聊中暗含功能词汇——而非明显错误。",
        },
        "car-mem-bench-2025, agent-survey-2026": {
            "papers": "CarMem · Agent Survey (ACL 2026)",
            "methodology": "CarMem 定义了车载语音助手的 5 种记忆操作（提取→存储→检索→更新→遗忘），发现多用户记忆隔离对大多数模型近乎为零能力。ACL 2026 综述将记忆和个性化列为「最欠评测的 Agent 能力」之一。",
            "insight": "记忆评测需要跨会话设计：偏好提取（本轮对话）、偏好存储和检索（下一趟行程）、偏好更新和冲突（新旧偏好矛盾）、多用户隔离（主驾 vs 副驾 vs 后排）——四个维度缺一不可。",
        },
        "stable-toolbench-2024, helm-2023": {
            "papers": "StableToolBench · HELM",
            "methodology": "StableToolBench 证明了真实 API 基准在 6 个月内因 API 变更丢失 15-30% 的测试用例。解决方案是版本化的 API 快照 + 模拟稳定 API 服务器。HELM 确立了「场景 × 指标」的标准化评测协议和透明度原则。",
            "insight": "我们的 tools_manifest.json（547 工具）是天然的稳定 API 快照。每次评测集发布应绑定工具清单版本号，注入测试用例应可精确复现（同样的错误注入→同样的拦截结果）。",
        },
    }

    # Find description for each group (fuzzy match)
    def get_group_desc(sp_key):
        # Exact match first
        if sp_key in group_descriptions:
            return group_descriptions[sp_key]
        # Fuzzy: check if key contains the sp_key or vice versa
        for gk, gd in group_descriptions.items():
            if sp_key in gk or gk in sp_key:
                return gd
        return None

    approved_count = 0; rejected_count = 0  # placeholder; actual counting in JS
    cases_html = ""
    for sp, case_list in groups.items():
        n = len(case_list)
        gid = sp.replace(" ","-").replace(",","").replace("/","-")[:40]
        case_cards = ""
        for c in case_list:
            cid = c.get("id","?")
            tag = c.get("tag_id","")
            domain = c.get("domain","")
            query = c.get("query","")
            expected = c.get("expected","")
            assertion = c.get("assertion","")
            si = c.get("source_insight","")
            case_cards += f'''
            <div class="ecard" data-case-id="{cid}" id="case-{cid}">
              <div class="ecard-top">
                <span class="ecard-tag">{tag}</span>
                <span class="ecard-domain">{domain}</span>
                <span class="ecard-id">{cid}</span>
                <span class="ecard-status" id="status-{cid}">⏳ 待审批</span>
              </div>
              <div class="ecard-query">"{query}"</div>
              <div class="ecard-exp">预期: {expected}</div>
              <div class="ecard-meta">
                <span class="ecard-assert">{assertion}</span>
                {f'<span class="ecard-ins">💡 {si[:60]}...</span>' if si else ''}
              </div>
              <div class="ecard-actions">
                <button class="act-btn approve" onclick="approveCase('{cid}',this)" title="采纳此用例">✅ 采纳</button>
                <button class="act-btn reject" onclick="rejectCase('{cid}',this)" title="拒绝此用例">❌ 拒绝</button>
                <button class="act-btn pending" onclick="resetCase('{cid}',this)" title="重置为待审批">⏳ 待定</button>
                <input type="text" class="act-note" id="note-{cid}" placeholder="📝 添加备注..." onchange="saveNote('{cid}')">
              </div>
            </div>'''

        desc = get_group_desc(sp)
        desc_html = ""
        if desc:
            desc_html = f'''
            <div class="cgroup-desc">
              <div class="cgdesc-row"><b>📚 来源论文:</b> {desc["papers"]}</div>
              <div class="cgdesc-row"><b>🔬 核心方法论:</b> {desc["methodology"]}</div>
              <div class="cgdesc-row"><b>💡 对车控评测的启示:</b> {desc["insight"]}</div>
            </div>'''

        cases_html += f'''
        <div class="case-group">
          <div class="cgroup-header" onclick="toggleGroup('{gid}')">
            <span class="cgroup-arrow" id="arrow-{gid}">▼</span>
            <span class="cgroup-title">📄 {sp}</span>
            <span class="cgroup-count">{n} 条用例</span>
            <span class="cgroup-stats" id="stats-{gid}"></span>
          </div>
          <div class="cgroup-body" id="group-{gid}">
            {desc_html}
            {case_cards}
          </div>
        </div>'''

    # ======== TAB 4: GAP ========
    gap_html = ""
    if insights.get("gap_analysis"):
        ga = insights["gap_analysis"]
        have = "".join(f"<li>{i}</li>" for i in ga.get("what_we_have",[]))
        missing = "".join(f"<li>{i}</li>" for i in ga.get("what_benchmarks_have_that_we_dont",[]))
        unique = "".join(f"<li>{i}</li>" for i in ga.get("what_we_have_that_benchmarks_dont",[]))
        gap_html = f'''
        <div class="gap-grid">
          <div class="gap-col have"><h4>✅ 我们已有的</h4><ul>{have}</ul></div>
          <div class="gap-col missing"><h4>🔧 业界有而我们缺的</h4><ul>{missing}</ul></div>
          <div class="gap-col unique"><h4>💎 我们有而业界缺的</h4><ul>{unique}</ul></div>
        </div>'''

    # ======== FULL HTML ========
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Auto-Eval Research | 车控 Agent 评测研究门户</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth;font-size:16px}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;background:#f8fafc;color:#1e293b;line-height:1.6}}
a{{color:#2563eb;text-decoration:none}}a:hover{{text-decoration:underline}}
.container{{max-width:1320px;margin:0 auto;padding:0 24px}}

nav{{background:#fff;border-bottom:1px solid #e2e8f0;position:sticky;top:0;z-index:100}}
.nav-inner{{max-width:1320px;margin:0 auto;padding:0 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}}
.nav-logo{{font-weight:800;font-size:18px;color:#0f172a;padding:12px 0}}
.nav-logo span{{color:#3b82f6}}
.nav-tabs{{display:flex;gap:4px}}
.nav-tab{{padding:12px 16px;border:none;background:none;cursor:pointer;font-size:14px;font-weight:500;color:#64748b;border-bottom:3px solid transparent;transition:all .15s;white-space:nowrap}}
.nav-tab:hover{{color:#0f172a;background:#f8fafc}}
.nav-tab.active{{color:#3b82f6;border-bottom-color:#3b82f6;font-weight:700}}

.hero{{position:relative;background:#0b1120;color:#fff;padding:72px 24px 60px;text-align:center;overflow:hidden}}
.hero::before{{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 80% 60% at 50% 30%,rgba(59,130,246,.12),transparent),radial-gradient(ellipse 60% 70% at 80% 70%,rgba(16,185,129,.08),transparent),radial-gradient(ellipse 50% 50% at 20% 60%,rgba(139,92,246,.06),transparent);pointer-events:none}}
.hero *{{position:relative;z-index:1}}
.hero-badge{{display:inline-block;padding:4px 14px;border:1px solid rgba(148,163,184,.25);border-radius:20px;font-size:12px;color:#94a3b8;margin-bottom:20px;letter-spacing:.5px}}
.hero h1{{font-size:clamp(28px,5vw,48px);font-weight:800;margin-bottom:12px;letter-spacing:-1px;line-height:1.15}}
.hero h1 span{{background:linear-gradient(135deg,#60a5fa,#34d399);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.hero-desc{{color:#94a3b8;font-size:16px;max-width:560px;margin:0 auto 36px;line-height:1.5}}
.hero-stats{{display:inline-flex;gap:2px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.06);border-radius:16px;padding:6px;flex-wrap:wrap;justify-content:center}}
.hstat{{display:flex;align-items:center;gap:10px;padding:12px 20px;border-radius:12px;transition:background .2s;cursor:default;min-width:100px;justify-content:center}}
.hstat:hover{{background:rgba(255,255,255,.04)}}
.hstat .num{{font-size:32px;font-weight:800;color:#fff;line-height:1;font-variant-numeric:tabular-nums;font-family:'SF Mono','JetBrains Mono','Fira Code',monospace}}
.hstat .info{{text-align:left}}
.hstat .lbl{{font-size:12px;color:#94a3b8;display:block}}
.hstat .sub{{font-size:10px;color:#64748b;display:block;margin-top:1px}}
.hstat .dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}
.hstat .dot.blue{{background:#3b82f6;box-shadow:0 0 8px rgba(59,130,246,.5)}}
.hstat .dot.green{{background:#10b981;box-shadow:0 0 8px rgba(16,185,129,.5)}}
.hstat .dot.amber{{background:#f59e0b;box-shadow:0 0 8px rgba(245,158,11,.5)}}
.hstat .dot.purple{{background:#8b5cf6;box-shadow:0 0 8px rgba(139,92,246,.5)}}
.hstat{{text-align:center;min-width:80px}}
.hstat .num{{font-size:32px;font-weight:800;color:#fff}}
.hstat .lbl{{font-size:11px;color:#94a3b8}}

.tab-content{{display:none;padding:36px 0}}
.tab-content.active{{display:block}}
.sec-hdr{{margin-bottom:24px}}
.sec-hdr h2{{font-size:22px;font-weight:700;color:#0f172a}}
.sec-hdr p{{color:#64748b;font-size:13px;margin-top:4px}}

/* FILTER BAR */
.fbar{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:18px;padding:12px 16px;background:#fff;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.04);position:sticky;top:53px;z-index:40}}
.fbar input{{padding:7px 14px;border:1px solid #e2e8f0;border-radius:8px;font-size:13px;min-width:200px;outline:none}}
.fbar input:focus{{border-color:#3b82f6}}
.tbtn{{padding:5px 12px;border:1.5px solid #e2e8f0;background:#fff;border-radius:8px;cursor:pointer;font-size:12px;font-weight:500;transition:all .15s;display:flex;align-items:center;gap:4px}}
.tbtn:hover{{border-color:var(--tc);background:#f8fafc}}
.tbtn.active{{background:var(--tc);color:#fff;border-color:var(--tc)}}
.tcnt{{font-size:10px;background:rgba(0,0,0,.06);padding:1px 5px;border-radius:8px}}
.tbtn.active .tcnt{{background:rgba(255,255,255,.2)}}
.fbar .reset{{padding:5px 12px;border:1px solid #fecaca;background:#fef2f2;color:#991b1b;border-radius:8px;cursor:pointer;font-size:12px;margin-left:auto}}
.fbar select{{padding:5px 10px;border:1px solid #e2e8f0;border-radius:8px;font-size:12px;background:#fff}}

/* PAPER CARDS */
.pgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(370px,1fr));gap:16px}}
.pcard{{background:#fff;border-radius:10px;padding:16px 20px;box-shadow:0 1px 3px rgba(0,0,0,.04);border:1px solid #f1f5f9;transition:all .2s}}
.pcard:hover{{box-shadow:0 4px 12px rgba(0,0,0,.06)}}
.pcard.hidden{{display:none}}
.pcard-top{{display:flex;gap:5px;flex-wrap:wrap;align-items:center;margin-bottom:6px}}
.pcard-topic{{font-size:10px;font-weight:600;color:#fff;padding:2px 7px;border-radius:4px}}
.pcard-venue{{font-size:10px;color:#64748b;background:#f1f5f9;padding:2px 7px;border-radius:4px}}
.pcard-year{{font-size:10px;color:#94a3b8}}
.pcard-cite{{font-size:10px;color:#64748b;margin-left:auto}}
.pcard-expand{{font-size:12px;background:#f1f5f9;border:1px solid #e2e8f0;border-radius:4px;cursor:pointer;padding:2px 8px;transition:all .15s}}
.pcard-expand:hover{{background:#e2e8f0}}
.pcard-expand.open{{background:#3b82f6;color:#fff;border-color:#3b82f6}}
.pcard-title{{font-size:15px;font-weight:700;line-height:1.3;margin-bottom:2px}}
.pcard-title a{{color:#0f172a}}
.pcard-title-zh{{font-size:13px;color:#3b82f6;font-weight:600;margin-bottom:4px}}
.pcard-auth{{font-size:11px;color:#64748b;margin-bottom:4px}}
.pcard-abs{{font-size:12px;color:#475569;line-height:1.5;margin-bottom:6px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}}
.pcard-tags{{display:flex;gap:3px;flex-wrap:wrap;margin-bottom:6px}}
.tag{{font-size:10px;background:#eff6ff;color:#2563eb;padding:1px 6px;border-radius:3px;font-weight:500}}
.pcard-detail{{margin-top:10px;border-top:1px solid #f1f5f9;padding-top:10px}}
.detail-inner h4{{font-size:13px;color:#0f172a;margin-bottom:4px;margin-top:8px}}
.detail-inner p{{font-size:12px;color:#475569;line-height:1.6}}
.detail-inner ul{{margin:4px 0 0 16px}}
.detail-inner li{{font-size:11px;color:#475569;line-height:1.5;margin-bottom:2px}}
.car-box{{margin-top:8px;padding:8px 12px;background:linear-gradient(135deg,#fffbeb,#fef3c7);border-left:3px solid #f59e0b;border-radius:0 6px 6px 0;font-size:11px}}
.car-label{{font-weight:700;color:#92400e;font-size:10px;display:block;margin-bottom:2px}}
.car-box p{{color:#78350f;line-height:1.4}}
.stars{{color:#f59e0b;font-size:12px;letter-spacing:1px}}

/* INSIGHTS */
.igrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(370px,1fr));gap:16px}}
.ins-card{{background:#fff;border-radius:10px;padding:16px 20px;box-shadow:0 1px 3px rgba(0,0,0,.04);border-top:4px solid #3b82f6}}
.ins-card:nth-child(1){{border-top-color:#3b82f6}}
.ins-card:nth-child(2){{border-top-color:#10b981}}
.ins-card:nth-child(3){{border-top-color:#f59e0b}}
.ins-card:nth-child(4){{border-top-color:#ef4444}}
.ins-card:nth-child(5){{border-top-color:#8b5cf6}}
.ins-card:nth-child(6){{border-top-color:#ec4899}}
.ins-card h3{{font-size:15px;font-weight:700;color:#0f172a}}
.ins-theme-en{{font-size:10px;color:#94a3b8;display:block;margin-top:1px}}
.ins-desc{{font-size:12px;color:#475569;line-height:1.5;margin:6px 0}}
.ins-action{{font-size:12px;background:#f1f5f9;padding:8px 12px;border-radius:8px;line-height:1.5}}
.ins-src{{font-size:10px;color:#94a3b8;margin-top:4px}}

/* CASE GROUPS */
.cases-bar{{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:16px;font-size:13px;color:#64748b}}
.cases-bar .export-btn{{padding:6px 16px;background:#2563eb;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:12px;font-weight:500}}
.cases-bar .export-btn:hover{{background:#1d4ed8}}
.case-group{{margin-bottom:12px;background:#fff;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.04);overflow:hidden}}
.cgroup-header{{padding:12px 18px;cursor:pointer;display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:#f8fafc;border-bottom:1px solid #f1f5f9;transition:background .15s;user-select:none}}
.cgroup-header:hover{{background:#f1f5f9}}
.cgroup-arrow{{font-size:12px;transition:transform .2s;color:#64748b;min-width:16px}}
.cgroup-title{{font-weight:600;font-size:14px;color:#0f172a}}
.cgroup-count{{font-size:11px;color:#64748b;background:#e2e8f0;padding:2px 8px;border-radius:4px}}
.cgroup-stats{{font-size:11px;margin-left:auto}}
.cgroup-body{{padding:12px 18px;display:block}}
.cgroup-body.collapsed{{display:none}}
.cgroup-desc{{margin:0 0 12px 0;padding:14px 16px;background:linear-gradient(135deg,#f0f9ff,#f8fafc);border:1px solid #e0e7ff;border-radius:8px;font-size:12px;line-height:1.6}}
.cgdesc-row{{margin-bottom:6px;color:#334155}}
.cgdesc-row b{{color:#0f172a}}
.cgdesc-row:last-child{{margin-bottom:0}}

/* EVAL CARDS */
.ecard{{background:#fff;border:1px solid #f1f5f9;border-left:3px solid #f59e0b;border-radius:6px;padding:12px 14px;margin-bottom:8px;transition:all .15s}}
.ecard.s-approved{{border-left-color:#10b981;background:#f0fdf4}}
.ecard.s-rejected{{border-left-color:#ef4444;background:#fef2f2;opacity:.7}}
.ecard-top{{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:6px}}
.ecard-tag{{font-size:10px;font-weight:600;background:#eff6ff;color:#2563eb;padding:1px 6px;border-radius:3px}}
.ecard-domain{{font-size:10px;color:#64748b;background:#f1f5f9;padding:1px 6px;border-radius:3px}}
.ecard-id{{font-size:10px;color:#94a3b8;font-family:monospace}}
.ecard-status{{font-size:10px;font-weight:600;margin-left:auto;padding:2px 7px;border-radius:3px}}
.s-approved .ecard-status{{background:#dcfce7;color:#166534}}
.s-rejected .ecard-status{{background:#fef2f2;color:#991b1b}}
.ecard-query{{font-size:14px;font-weight:600;color:#0f172a;margin-bottom:3px}}
.ecard-exp{{font-size:11px;color:#475569;margin-bottom:4px}}
.ecard-meta{{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:8px}}
.ecard-assert{{font-size:10px;background:#e0e7ff;color:#3730a3;padding:2px 7px;border-radius:3px}}
.ecard-ins{{font-size:10px;color:#92400e;background:#fef3c7;padding:2px 7px;border-radius:3px}}
.ecard-actions{{display:flex;gap:6px;align-items:center;flex-wrap:wrap}}
.act-btn{{padding:3px 10px;border:1px solid #e2e8f0;border-radius:5px;cursor:pointer;font-size:11px;transition:all .15s;background:#fff}}
.act-btn:hover{{opacity:.85}}
.act-btn.approve{{border-color:#10b981;color:#10b981}}
.act-btn.approve.active{{background:#10b981;color:#fff}}
.act-btn.reject{{border-color:#ef4444;color:#ef4444}}
.act-btn.reject.active{{background:#ef4444;color:#fff}}
.act-btn.pending{{border-color:#f59e0b;color:#f59e0b}}
.act-note{{flex:1;min-width:120px;padding:3px 8px;border:1px solid #e2e8f0;border-radius:5px;font-size:11px;outline:none}}
.act-note:focus{{border-color:#3b82f6}}

/* GAP */
.gap-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}}
.gap-col{{background:#fff;border-radius:10px;padding:16px 20px;box-shadow:0 1px 3px rgba(0,0,0,.04)}}
.gap-col h4{{font-size:14px;font-weight:700;margin-bottom:8px}}
.gap-col ul{{list-style:none;font-size:12px;line-height:1.7;color:#475569}}
.gap-col.have{{border-left:4px solid #10b981}}
.gap-col.missing{{border-left:4px solid #f59e0b}}
.gap-col.unique{{border-left:4px solid #8b5cf6}}

.empty-state{{text-align:center;padding:50px 20px;color:#64748b}}
.empty-state code{{background:#e2e8f0;padding:2px 7px;border-radius:4px;font-size:12px}}

.about{{background:#0f172a;color:#e2e8f0;padding:40px 24px;margin-top:36px}}
.about-inner{{max-width:1320px;margin:0 auto}}
.about h2{{font-size:18px;color:#fff;margin-bottom:10px}}
.about p,.about li{{font-size:12px;color:#94a3b8;line-height:1.7}}
.about code{{background:#1e293b;padding:1px 7px;border-radius:4px;font-size:11px;color:#10b981}}
.about a{{color:#60a5fa}}

footer{{background:#0f172a;border-top:1px solid #1e293b;padding:16px;text-align:center;font-size:11px;color:#64748b}}

.st{{position:fixed;bottom:16px;right:16px;width:36px;height:36px;background:#0f172a;color:#fff;border:none;border-radius:50%;font-size:16px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.15);opacity:0;transition:opacity .3s;z-index:200}}
.st.visible{{opacity:1}}

@media(max-width:768px){{
  .pgrid,.igrid,.gap-grid{{grid-template-columns:1fr}}
  .hero-stats{{gap:8px}}
  .hstat .num{{font-size:24px}}
  .nav-tab{{padding:10px 10px;font-size:11px}}
  .fbar{{flex-direction:column;align-items:stretch}}
  .ecard-actions{{flex-direction:column;align-items:stretch}}
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
  <div class="hero-badge">LLM Agent Evaluation Research Pipeline</div>
  <h1>车控 Agent <span>评测研究门户</span></h1>
  <p class="hero-desc">自动检索 · 智能摘要 · 洞察提取 · 评测集生成<br>将前沿学术成果系统性地应用到智能座舱 Agent 评测中</p>
  <div class="hero-stats">
    <div class="hstat"><span class="dot blue"></span><div class="num">{total_papers}</div><div class="info"><span class="lbl">收录论文</span><span class="sub">Semantic Scholar + arXiv</span></div></div>
    <div class="hstat"><span class="dot green"></span><div class="num">{len(topics)}</div><div class="info"><span class="lbl">研究方向</span><span class="sub">Agent · FC · 车载</span></div></div>
    <div class="hstat"><span class="dot amber"></span><div class="num">{curated}</div><div class="info"><span class="lbl">车控强相关</span><span class="sub">含中文启示</span></div></div>
    <div class="hstat"><span class="dot purple"></span><div class="num" id="hero-approved">0</div><div class="info"><span class="lbl">已采纳用例</span><span class="sub">待审批: {total_cases}</span></div></div>
  </div>
</section>

<div class="container">

<!-- TAB 1: 论文库 -->
<div class="tab-content active" id="tab-papers">
  <div class="sec-hdr"><h2>📄 论文数据库</h2><p>收录 LLM Agent 评测、函数调用、车载 Agent 等方向的代表性论文。点击 📖 展开中文摘要和关键发现。</p></div>
  <div class="fbar">
    <input type="text" placeholder="🔍 搜索论文标题/作者/摘要..." id="searchBox" oninput="filterPapers()">
    <button class="tbtn active" data-topic="all" onclick="filterTopic('all',this)">全部<span class="tcnt">{total_papers}</span></button>
    {topic_btns}
    <select onchange="sortPapers(this.value)" style="padding:5px 10px;border:1px solid #e2e8f0;border-radius:8px;font-size:12px">
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
  <div class="sec-hdr"><h2>💡 跨论文洞察</h2><p>从 {total_papers} 篇论文中提取的 {len(insights.get('cross_cutting_themes',[]))} 个共识，映射到车控评测改进方向</p></div>
  <div class="igrid">{insight_cards}</div>
</div>

<!-- TAB 3: 评测集生成 -->
<div class="tab-content" id="tab-cases">
  <div class="sec-hdr"><h2>🔧 评测集自动生成</h2><p>基于论文洞察分组生成评测用例。展开分组 → 逐条审批（采纳/拒绝）+ 备注。审批结果保存在浏览器中。</p></div>
  {f'''<div class="cases-bar">
    <span>📋 共 <b>{total_cases}</b> 条用例 · <b>{len(groups)}</b> 个论文来源 · 已采纳: <b id="total-approved">0</b> · 已拒绝: <b id="total-rejected">0</b></span>
    <div style="display:flex;gap:8px">
      <button class="act-btn approve" onclick="approveAll()">✅ 全部采纳</button>
      <button class="export-btn" onclick="exportApproved()">📥 导出已采纳</button>
    </div>
  </div>
  {cases_html}''' if total_cases > 0 else '<div class="empty-state"><p style="font-size:48px">🔧</p><h3>暂无自动生成的评测用例</h3><p>运行 <code>python3 apply_insights.py</code> 生成</p></div>'}
</div>

<!-- TAB 4: 差距分析 -->
<div class="tab-content" id="tab-gap">
  <div class="sec-hdr"><h2>📊 差距分析</h2><p>现有车控评测集（207条用例，48 Tags） vs 业界主流评测框架</p></div>
  {gap_html}
</div>

</div>

<div class="about" id="tab-about">
  <div class="about-inner">
    <h2>ℹ️ 关于 Auto-Eval Research</h2>
    <p>自动化评测研究流水线：多源检索 → 去重合并 → 结构化摘要 → 跨论文洞察 → 车控映射 → <b>评测集生成</b>。</p>
    <p style="margin-top:6px"><b>数据源:</b> Semantic Scholar API, arXiv API · <b>每日更新:</b> GitHub Actions 每天 UTC 2:00 自动运行 · <b>更新时间:</b> {now} · <b>代码:</b> <a href="https://github.com/jenniferwingna/auto_eval" target="_blank">GitHub</a></p>
  </div>
</div>

<footer><div class="container">Auto-Eval Research Portal · <a href="https://github.com/jenniferwingna/auto_eval" target="_blank">GitHub</a></div></footer>
<button class="st" id="scrollTop" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">↑</button>

<script>
// ==== SCROLL TOP ====
window.addEventListener('scroll',()=>{{document.getElementById('scrollTop').classList.toggle('visible',window.scrollY>300)}});

// ==== TAB SWITCHING ====
function switchTab(tab,btn){{
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(b=>b.classList.remove('active'));
  var el=document.getElementById('tab-'+tab);
  if(el)el.classList.add('active');
  btn.classList.add('active');
  window.scrollTo({{top:0,behavior:'smooth'}});
}}

// ==== PAPER FILTERING ====
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
    if(method==='citations'){{
      let ca=parseInt(a.querySelector('.pcard-cite')?.textContent||'0'),cb=parseInt(b.querySelector('.pcard-cite')?.textContent||'0');
      return cb-ca;
    }}
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

// ==== PAPER DETAIL TOGGLE ====
function togglePaperDetail(pid){{
  var detail=document.getElementById('detail-'+pid);
  var btn=document.querySelector('#paper-'+pid+' .pcard-expand');
  if(detail.style.display==='none'){{
    detail.style.display='block';
    btn.classList.add('open');
    btn.textContent='📖';
  }}else{{
    detail.style.display='none';
    btn.classList.remove('open');
    btn.textContent='📖';
  }}
}}

// ==== CASE GROUP TOGGLE ====
function toggleGroup(gid){{
  var body=document.getElementById('group-'+gid);
  var arrow=document.getElementById('arrow-'+gid);
  body.classList.toggle('collapsed');
  arrow.textContent=body.classList.contains('collapsed')?'▶':'▼';
}}

// ==== CASE APPROVAL (localStorage) ====
function getApprovals(){{try{{return JSON.parse(localStorage.getItem('auto_eval_approvals')||'{{}}');}}catch(e){{return {{}};}}}}
function setApprovals(data){{localStorage.setItem('auto_eval_approvals',JSON.stringify(data));updateStats();}}

function approveCase(cid,btn){{
  var data=getApprovals();
  data[cid]={{status:'approved',note:document.getElementById('note-'+cid)?.value||''}};
  setApprovals(data);
  applyCaseState(cid,'approved');
}}
function rejectCase(cid,btn){{
  var data=getApprovals();
  data[cid]={{status:'rejected',note:document.getElementById('note-'+cid)?.value||''}};
  setApprovals(data);
  applyCaseState(cid,'rejected');
}}
function resetCase(cid,btn){{
  var data=getApprovals();
  delete data[cid];
  setApprovals(data);
  applyCaseState(cid,'pending');
}}
function saveNote(cid){{
  var data=getApprovals();
  if(!data[cid])data[cid]={{status:'pending',note:''}};
  data[cid].note=document.getElementById('note-'+cid)?.value||'';
  setApprovals(data);
}}

function applyCaseState(cid,state){{
  var card=document.getElementById('case-'+cid);
  var statusEl=document.getElementById('status-'+cid);
  card.classList.remove('s-approved','s-rejected');
  if(state==='approved'){{card.classList.add('s-approved');statusEl.textContent='✅ 已采纳';}}
  else if(state==='rejected'){{card.classList.add('s-rejected');statusEl.textContent='❌ 已拒绝';}}
  else{{statusEl.textContent='⏳ 待审批';}}
  // Button states
  var btns=card.querySelectorAll('.act-btn');
  btns.forEach(b=>b.classList.remove('active'));
  if(state==='approved')btns[0].classList.add('active');
  if(state==='rejected')btns[1].classList.add('active');
  if(state==='pending')btns[2].classList.add('active');
}}

function updateStats(){{
  var data=getApprovals();
  var approved=0,rejected=0;
  Object.values(data).forEach(v=>{{if(v.status==='approved')approved++;if(v.status==='rejected')rejected++;}});
  var ta=document.getElementById('total-approved');if(ta)ta.textContent=approved;
  var tr=document.getElementById('total-rejected');if(tr)tr.textContent=rejected;
  var ha=document.getElementById('hero-approved');if(ha)ha.textContent=approved;
  // Per-group stats
  document.querySelectorAll('.cgroup-stats').forEach(el=>{{
    var gid=el.id.replace('stats-','');
    var body=document.getElementById('group-'+gid);
    if(!body)return;
    var cards=body.querySelectorAll('.ecard');
    var ga=0,gr=0;
    cards.forEach(c=>{{
      var cid=c.dataset.caseId;
      if(data[cid]?.status==='approved')ga++;
      if(data[cid]?.status==='rejected')gr++;
    }});
    el.textContent='✅'+ga+' ❌'+gr;
  }});
}}

function approveAll(){{
  if(!confirm('确定要采纳全部用例吗？'))return;
  var data=getApprovals();
  document.querySelectorAll('.ecard').forEach(c=>{{
    var cid=c.dataset.caseId;
    data[cid]={{status:'approved',note:document.getElementById('note-'+cid)?.value||data[cid]?.note||''}};
    applyCaseState(cid,'approved');
  }});
  setApprovals(data);
}}

function exportApproved(){{
  var data=getApprovals();
  var approved=[];
  document.querySelectorAll('.ecard').forEach(c=>{{
    var cid=c.dataset.caseId;
    if(data[cid]?.status==='approved'){{
      approved.push({{
        id:cid,
        tag_id:c.querySelector('.ecard-tag')?.textContent||'',
        domain:c.querySelector('.ecard-domain')?.textContent||'',
        query:c.querySelector('.ecard-query')?.textContent?.replace(/^"|"$/g,'')||'',
        expected:c.querySelector('.ecard-exp')?.textContent?.replace('预期: ','')||'',
        assertion:c.querySelector('.ecard-assert')?.textContent||'',
        note:data[cid].note||'',
      }});
    }}
  }});
  if(approved.length===0){{alert('没有已采纳的用例。请先审批用例。');return;}}
  var blob=new Blob([JSON.stringify({{approved_count:approved.length,entries:approved}},null,2)],{{type:'application/json'}});
  var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='approved_eval_cases.json';a.click();
}}

// Init on load
(function(){{
  var data=getApprovals();
  document.querySelectorAll('.ecard').forEach(c=>{{
    var cid=c.dataset.caseId;
    if(data[cid]){{
      applyCaseState(cid,data[cid].status);
      if(data[cid].note)document.getElementById('note-'+cid).value=data[cid].note;
    }}
  }});
  updateStats();
}})();
</script>
</body>
</html>'''

    return html


def main():
    print("🔨 生成 Auto-Eval V2.1 网站...")
    html = build()
    output = os.path.join(SCRIPT_DIR, "index.html")
    with open(output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"   ✅ 已生成: {output} ({os.path.getsize(output)/1024:.1f} KB)")
    print(f"   🌐 打开预览: open {output}")


if __name__ == "__main__":
    main()

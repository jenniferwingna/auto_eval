#!/usr/bin/env python3
"""
Auto-Eval Flask Server — serves website + AI chat API.
Deploy to Railway / Render for public access.

Local:  python3 app.py          → http://localhost:8765
Deploy: Railway auto-detects Procfile → public URL
"""

import json, os, re, sys
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder=".", static_url_path="")

DEEPSEEK_TOKEN = os.environ.get("DEEPSEEK_TOKEN", "")
DEEPSEEK_API = "https://api.deepseek.com/v1/chat/completions"

if not DEEPSEEK_TOKEN:
    print("❌ 请设置环境变量 DEEPSEEK_TOKEN")
    print("   Railway: 在 Dashboard → Variables 中添加")
    print("   本地: export DEEPSEEK_TOKEN=sk-xxx")
    sys.exit(1)

SYSTEM_PROMPT = """你是 Auto-Eval 研究助手，专门帮助用户理解和改进车控 Agent 评测集。

你的知识领域：
- LLM Agent 评测框架（BFCL, ToolBench, API-Bank, ToolSandbox, τ²-bench, CAR-bench, MetaTool, TRAJECT-Bench, AgentBench, HELM 等）
- 函数调用与工具使用评测方法论
- 车载语音助手 Agent 评测
- 中文自然语言评测集设计
- 评测集质量标准：覆盖完整性、语言真实性、判别效力、可复现性、结构无偏性、实用可执行性

回答要求：中文回复，简洁专业。问论文则简述核心方法和关键发现。问评测设计则给出可操作方案。结合车控场景（空调/车窗/座椅/灯光/天窗/遮阳帘/后视镜/后备箱/香氛/方向盘等）回答。"""


def call_deepseek(messages, max_tokens=2000):
    from urllib.request import Request, urlopen
    req = Request(
        DEEPSEEK_API,
        data=json.dumps({"model": "deepseek-chat", "messages": messages, "max_tokens": max_tokens, "temperature": 0.7}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_TOKEN}"},
    )
    try:
        with urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[API 调用失败: {e}]"


# ---- Serve static files ----
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def static_files(path):
    if os.path.exists(os.path.join(".", path)):
        return send_from_directory(".", path)
    return send_from_directory(".", "index.html")


# ---- API endpoints ----
@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])

    if not message:
        return jsonify({"reply": "请输入问题。"})

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history[-20:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": message})

    print(f"💬 Chat: {message[:80]}...")
    reply = call_deepseek(messages)
    print(f"   → {reply[:80]}...")
    return jsonify({"reply": reply})


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json() or {}
    count = data.get("count", 5)
    topic = data.get("topic", "")
    existing_tags = data.get("existing_tags", [])

    prompt = f"""基于你的车控 Agent 评测知识，生成 {count} 条新的评测用例。

{'主题/方向: ' + topic if topic else '请覆盖尚未充分测试的维度（如记忆、多轮状态追踪、工具歧义消解、微妙负例等）。'}

已有 Tag: {', '.join(existing_tags) if existing_tags else '无限制'}

每条用例严格按照 JSON 格式输出（只输出 JSON 数组）：
[
  {{
    "tag_id": "L1-TL-09 或 L2-MT-01 等",
    "dimension": "评测维度名称",
    "domain": "空调/车窗/天窗/遮阳帘/座椅/方向盘/灯光/后视镜/后备箱/香氛/多域/安全/记忆/闲聊 之一",
    "query": "用户自然语言query",
    "expected": "预期行为描述",
    "assertion": "主判据=action 或 主判据=state 或 约束:action xxx",
    "note": "可选标签，如 负例;多轮;口语噪音;hard;记忆依赖;需要初始状态"
  }}
]

要求：query 自然中文口语（含口语噪音更好），覆盖不同车控子域，正例+负例，断言可自动验证（不要 rubric）。"""

    print(f"🔧 Generate: {count} cases, topic='{topic}'")
    result = call_deepseek([{"role": "user", "content": prompt}], max_tokens=4000)

    cases = []
    try:
        m = re.search(r"\[.*\]", result, re.DOTALL)
        if m:
            cases = json.loads(m.group())
            for i, c in enumerate(cases):
                c["id"] = f"GEN-{i+1:04d}"
                c["status"] = "pending_review"
                c["source"] = "deepseek-generated"
    except Exception:
        cases = [{"error": "JSON parse failed", "raw": result[:300]}]

    return jsonify({"cases": cases})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    print(f"""
╔══════════════════════════════════════════╗
║  🤖 Auto-Eval Server                    ║
║  http://localhost:{port}                    ║
║  /api/chat     AI 对话                   ║
║  /api/generate 批量生成用例               ║
╚══════════════════════════════════════════╝
""")
    app.run(host="0.0.0.0", port=port, debug=False)

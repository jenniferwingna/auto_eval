from flask import Flask, request, jsonify
import json, os, re

app = Flask(__name__)
TOKEN = os.environ.get("DEEPSEEK_TOKEN", "")
API_URL = "https://api.deepseek.com/v1/chat/completions"

SYSTEM_PROMPT = "你是 Auto-Eval 研究助手，帮助理解和改进车控 Agent 评测集。知识领域：LLM Agent 评测框架（BFCL, ToolBench, API-Bank, ToolSandbox, CAR-bench, MetaTool, TRAJECT-Bench 等）、函数调用评测方法论、车载语音助手评测。用中文简洁回复。"


def call_ds(messages, max_tokens=2000):
    from urllib.request import Request, urlopen
    req = Request(API_URL,
        data=json.dumps({"model": "deepseek-chat", "messages": messages, "max_tokens": max_tokens, "temperature": 0.7}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"})
    with urlopen(req, timeout=25) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "token_set": bool(TOKEN)})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    msg = data.get("message", "").strip()
    history = data.get("history", [])
    if not msg:
        return jsonify({"reply": "请输入问题。"})

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history[-20:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": msg})

    try:
        reply = call_ds(messages)
    except Exception as e:
        reply = f"[API错误: {e}]"
    return jsonify({"reply": reply})


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}
    count = data.get("count", 5)
    topic = data.get("topic", "")
    existing_tags = data.get("existing_tags", [])

    prompt = f"""基于你的车控 Agent 评测知识，生成 {count} 条评测用例。

{'主题/方向: ' + topic if topic else '请覆盖记忆、多轮状态追踪、工具歧义消解、微妙负例等维度。'}
已有 Tag: {', '.join(existing_tags[:30]) if existing_tags else '无限制'}

严格按 JSON 数组输出（不要其他文字）：
[
  {{"tag_id": "...", "dimension": "...", "domain": "空调/车窗/天窗/遮阳帘/座椅/方向盘/灯光/后视镜/后备箱/香氛/多域/安全/记忆/闲聊", "query": "自然中文query", "expected": "预期行为", "assertion": "主判据=action 或 约束:action xxx", "note": "负例;多轮;口语噪音;hard 等"}}
]
要求：query 中文口语化，覆盖不同子域，正例+负例，断言可自动验证（不要 rubric）。"""

    try:
        result = call_ds([{"role": "user", "content": prompt}], max_tokens=4000)
    except Exception as e:
        return jsonify({"cases": [], "error": str(e)})

    cases = []
    try:
        m = re.search(r"\[.*\]", result, re.DOTALL)
        if m:
            cases = json.loads(m.group())
            for i, c in enumerate(cases):
                c["id"] = f"GEN-{i+1:04d}"
                c["status"] = "pending_review"
                c["source"] = "deepseek"
    except Exception:
        cases = [{"error": "parse failed"}]
    return jsonify({"cases": cases})

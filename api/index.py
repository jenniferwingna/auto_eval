"""Vercel Serverless — zero-dependency, uses only Python stdlib"""
import json, os, re, sys, traceback
from urllib.request import Request, urlopen
from urllib.error import URLError
from http.server import BaseHTTPRequestHandler

TOKEN = os.environ.get("DEEPSEEK_TOKEN", "")
API_URL = "https://api.deepseek.com/v1/chat/completions"

SYSTEM_PROMPT = "你是 Auto-Eval 研究助手，帮助理解和改进车控 Agent 评测集。知识领域：LLM Agent 评测框架（BFCL, ToolBench, API-Bank, CAR-bench 等）、函数调用评测方法论、车载语音助手评测。用中文简洁回复。"


def call_ds(messages, max_tokens=2000):
    body = json.dumps({"model": "deepseek-chat", "messages": messages, "max_tokens": max_tokens, "temperature": 0.7}).encode()
    req = Request(API_URL, data=body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"})
    with urlopen(req, timeout=25) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def json_response(data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return {"statusCode": status, "body": body.decode(),
            "headers": {"Content-Type": "application/json; charset=utf-8", "Access-Control-Allow-Origin": "*"}}


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path in ("/api/health", "/health"):
            resp = json_response({"status": "ok", "token_set": bool(TOKEN), "python": sys.version[:50]})
        else:
            resp = json_response({"error": "use /api/health, /api/chat, /api/generate"}, 404)
        self._send(resp)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
        except Exception:
            body = {}

        if self.path in ("/api/chat", "/chat"):
            resp = self._handle_chat(body)
        elif self.path in ("/api/generate", "/generate"):
            resp = self._handle_generate(body)
        else:
            resp = json_response({"error": f"unknown: {self.path}"}, 404)
        self._send(resp)

    def _send(self, resp):
        self.send_response(resp.get("statusCode", 200))
        for k, v in resp.get("headers", {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(resp["body"].encode())

    def _handle_chat(self, body):
        try:
            msg = body.get("message", "").strip()
            history = body.get("history", [])
            if not msg:
                return json_response({"reply": "请输入问题。"})

            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            for h in history[-20:]:
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
            messages.append({"role": "user", "content": msg})

            reply = call_ds(messages)
            return json_response({"reply": reply})
        except Exception as e:
            return json_response({"reply": f"[错误] {e}\n{traceback.format_exc()[:300]}"})

    def _handle_generate(self, body):
        try:
            count = body.get("count", 5)
            topic = body.get("topic", "")
            existing_tags = body.get("existing_tags", [])

            prompt = f"""基于你的车控 Agent 评测知识，生成 {count} 条评测用例。

{'主题/方向: ' + topic if topic else '请覆盖记忆、多轮状态追踪、工具歧义消解、微妙负例等维度。'}
已有 Tag: {', '.join(existing_tags[:30]) if existing_tags else '无限制'}

严格按 JSON 数组输出（不要其他文字）：
[
  {{"tag_id": "...", "dimension": "...", "domain": "空调/车窗/天窗/遮阳帘/座椅/方向盘/灯光/后视镜/后备箱/香氛/多域/安全/记忆/闲聊", "query": "自然中文query", "expected": "预期行为", "assertion": "主判据=action 或 约束:action xxx", "note": "负例;多轮;口语噪音;hard 等"}}
]
要求：query 中文口语化，覆盖不同子域，正例+负例，断言可自动验证（不要 rubric）。"""

            result = call_ds([{"role": "user", "content": prompt}], max_tokens=4000)

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

            return json_response({"cases": cases})
        except Exception as e:
            return json_response({"cases": [], "error": str(e), "trace": traceback.format_exc()[:300]})

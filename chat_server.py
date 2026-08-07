#!/usr/bin/env python3
"""
Local proxy server for Auto-Eval chat & batch generation.
Proxies requests to DeepSeek API without exposing the token to the browser.

Usage:
    python3 chat_server.py
    # → http://localhost:8765

Endpoints:
    POST /chat      {message, history} → {reply}
    POST /generate  {count, topic, existing_tags} → {cases}
    GET  /health    → {status: "ok"}
"""

import json, os, sys, re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError

# Token from environment variable or .env file
DEEPSEEK_TOKEN = os.environ.get("DEEPSEEK_TOKEN", "")

# Try loading from .env file if not in environment
if not DEEPSEEK_TOKEN:
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("DEEPSEEK_TOKEN="):
                    DEEPSEEK_TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

if not DEEPSEEK_TOKEN:
    print("❌ 未设置 DEEPSEEK_TOKEN！")
    print("   方法1: export DEEPSEEK_TOKEN=sk-xxx")
    print("   方法2: 在 auto_eval/ 目录下创建 .env 文件，内容: DEEPSEEK_TOKEN=sk-xxx")
    sys.exit(1)
DEEPSEEK_API = "https://api.deepseek.com/v1/chat/completions"
PORT = 8765

SYSTEM_PROMPT = """你是 Auto-Eval 研究助手，专门帮助用户理解和改进车控 Agent 评测集。

你的知识领域：
- LLM Agent 评测框架（BFCL, ToolBench, API-Bank, ToolSandbox, τ²-bench, CAR-bench, MetaTool, TRAJECT-Bench, AgentBench, HELM 等）
- 函数调用与工具使用评测方法论
- 车载语音助手 Agent 评测
- 中文自然语言评测集设计
- 评测集的质量标准：覆盖完整性、语言真实性、判别效力、可复现性、结构无偏性、实用可执行性

回答要求：
- 用中文回复，简洁专业
- 如果用户问具体论文，简述核心方法和关键发现
- 如果用户问评测设计建议，给出可操作的具体方案
- 涉及车控场景时，结合 547 个车控工具（空调/车窗/座椅/灯光/天窗/遮阳帘/后视镜/后备箱/香氛/方向盘等）的实际场景回答"""


class ChatHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress noisy logs

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json({})

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok", "port": PORT})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
        except Exception:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        if self.path == "/chat":
            self._handle_chat(body)
        elif self.path == "/generate":
            self._handle_generate(body)
        else:
            self._send_json({"error": "Not found"}, 404)

    def _call_deepseek(self, messages, max_tokens=2000):
        req = Request(
            DEEPSEEK_API,
            data=json.dumps({
                "model": "deepseek-chat",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7,
            }).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_TOKEN}",
            },
        )
        try:
            with urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                return data["choices"][0]["message"]["content"]
        except URLError as e:
            return f"[API 调用失败: {e}]"
        except Exception as e:
            return f"[错误: {e}]"

    def _handle_chat(self, body):
        message = body.get("message", "").strip()
        history = body.get("history", [])

        if not message:
            self._send_json({"reply": "请输入问题。"})
            return

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in history[-20:]:  # keep last 20 turns
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": message})

        print(f"💬 Chat: {message[:80]}...")
        reply = self._call_deepseek(messages)
        print(f"   → {reply[:80]}...")
        self._send_json({"reply": reply})

    def _handle_generate(self, body):
        count = body.get("count", 5)
        topic = body.get("topic", "")
        existing_tags = body.get("existing_tags", [])

        prompt = f"""基于你的车控 Agent 评测知识，生成 {count} 条新的评测用例。

{'主题/方向: ' + topic if topic else '请覆盖尚未充分测试的维度（如记忆、多轮状态追踪、工具歧义消解、微妙负例等）。'}

已有的 Tag: {', '.join(existing_tags) if existing_tags else '无限制'}

每条用例请严格按照以下 JSON 格式输出（不要输出其他内容，只输出 JSON 数组）：
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

要求：
- query 必须是自然的中文口语（包含口语噪音如嗯/那个/不对的更好）
- 覆盖不同的车控子域，不要集中在空调和车窗
- 包含正例和负例
- 断言必须可自动验证（action/state/label，不要 rubric）
"""

        print(f"🔧 Generate: {count} cases, topic='{topic}'")
        result = self._call_deepseek(
            [{"role": "user", "content": prompt}],
            max_tokens=4000,
        )
        print(f"   → {len(result)} chars")

        # Try to extract JSON array from response
        cases = []
        try:
            # Find JSON array in response
            json_match = re.search(r"\[.*\]", result, re.DOTALL)
            if json_match:
                cases = json.loads(json_match.group())
                # Add metadata
                for i, c in enumerate(cases):
                    c["id"] = f"GEN-{len(cases):04d}"  # will be fixed by caller
                    c["status"] = "pending_review"
                    c["source"] = "deepseek-generated"
        except Exception as e:
            print(f"   ⚠ JSON parse error: {e}")
            cases = [{"error": "Failed to parse generated cases", "raw": result[:500]}]

        self._send_json({"cases": cases, "raw_response": result[:200]})


def main():
    server = HTTPServer(("0.0.0.0", PORT), ChatHandler)
    print(f"""
╔══════════════════════════════════════════╗
║  🤖 Auto-Eval Chat Server               ║
║  DeepSeek 代理服务                       ║
║  http://localhost:{PORT}                    ║
║                                         ║
║  端点:                                   ║
║  POST /chat      AI 对话                 ║
║  POST /generate  批量生成用例             ║
║  GET  /health    健康检查                 ║
║                                         ║
║  按 Ctrl+C 停止                          ║
╚══════════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
        server.shutdown()


if __name__ == "__main__":
    main()

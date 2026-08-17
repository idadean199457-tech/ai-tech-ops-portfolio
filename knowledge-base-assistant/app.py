"""Local AI knowledge-base support assistant.

Runs with only Python's standard library. Set OPENAI_API_KEY to enable optional
LLM synthesis; without a key it still returns ranked, cited knowledge-base hits.
"""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import request


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "knowledge.json"
FEEDBACK_FILE = ROOT / "feedback.json"


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def terms(text: str) -> set[str]:
    cleaned = "".join(char.lower() for char in text if char.isalnum() or "\u4e00" <= char <= "\u9fff")
    return {cleaned[index : index + 2] for index in range(max(0, len(cleaned) - 1))} | set(cleaned)


def search(question: str, documents: list[dict]) -> list[dict]:
    query_terms = terms(question)
    ranked = []
    for document in documents:
        haystack = f"{document['title']} {document['tags']} {document['content']}"
        score = len(query_terms & terms(haystack))
        if score:
            ranked.append({**document, "score": score})
    return sorted(ranked, key=lambda item: item["score"], reverse=True)[:3]


def llm_answer(question: str, matches: list[dict]) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    context = "\n\n".join(f"[{item['id']}] {item['title']}: {item['content']}" for item in matches)
    prompt = (
        "你是企业 AI 产品技术支持助手。只根据给出的知识库回答，"
        "给出排查步骤、需要补充的信息和升级研发的条件。不要编造。\n\n"
        f"知识库：\n{context}\n\n客户问题：{question}"
    )
    payload = json.dumps(
        {
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
    ).encode("utf-8")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    req = request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "static"), **kwargs)

    def send_json(self, payload, status=HTTPStatus.OK):
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def read_body(self):
        size = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(size).decode("utf-8"))

    def do_GET(self):
        if self.path == "/api/health":
            self.send_json({"ok": True, "mode": "llm" if os.getenv("OPENAI_API_KEY") else "retrieval"})
            return
        if self.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        try:
            payload = self.read_body()
        except (ValueError, json.JSONDecodeError):
            self.send_json({"error": "请求格式无效"}, HTTPStatus.BAD_REQUEST)
            return
        if self.path == "/api/ask":
            question = str(payload.get("question", "")).strip()
            if len(question) < 4:
                self.send_json({"error": "请至少描述四个字的问题现象"}, HTTPStatus.BAD_REQUEST)
                return
            matches = search(question, load_json(DATA_FILE, []))
            answer = llm_answer(question, matches)
            if not answer:
                if matches:
                    answer = "建议先按以下知识库内容排查：\n" + "\n".join(
                        f"{index + 1}. {item['content']}" for index, item in enumerate(matches)
                    )
                else:
                    answer = "暂未检索到直接答案。请补充报错截图、复现步骤、账号角色、设备或接口信息后再升级研发。"
            self.send_json({"answer": answer, "sources": matches, "mode": "llm" if os.getenv("OPENAI_API_KEY") else "retrieval"})
            return
        if self.path == "/api/feedback":
            feedback = load_json(FEEDBACK_FILE, [])
            feedback.append({"question": payload.get("question", ""), "helpful": bool(payload.get("helpful"))})
            FEEDBACK_FILE.write_text(json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8")
            self.send_json({"ok": True})
            return
        self.send_json({"error": "未找到接口"}, HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    print("Knowledge assistant: http://127.0.0.1:8765")
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()

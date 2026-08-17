"""Customer-to-R&D issue workbench with local SQLite persistence."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DB = ROOT / "tickets.db"


def connect():
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, customer TEXT,
            category TEXT, priority TEXT, detail TEXT, status TEXT NOT NULL,
            diagnosis TEXT, created_at TEXT NOT NULL
        )""")
        if db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] == 0:
            db.execute("INSERT INTO tickets (title,customer,category,priority,detail,status,diagnosis,created_at) VALUES (?,?,?,?,?,?,?,?)", (
                "知识库回答未命中", "示例客户", "知识库", "P2", "上传文档后提问没有引用来源", "处理中",
                "核对文档索引状态、检索关键词和引用开关；补充问题截图与知识库版本。", datetime.now().isoformat(timespec="minutes")))


def diagnose(text: str) -> list[str]:
    rules = {
        "登录|权限|账号": "核对租户、账号角色、授权范围与登录状态。",
        "超时|接口|API|报错": "记录错误码、请求时间、Trace ID、接口地址和网络环境。",
        "知识库|回答|引用|检索": "确认文档已解析索引，检查切分、关键词、召回结果与引用设置。",
        "离线|设备|同步|终端": "核对设备状态、网络、账号权限、接口参数和数据同步时间。",
    }
    hits = [advice for keys, advice in rules.items() if any(key.lower() in text.lower() for key in keys.split("|"))]
    return hits or ["补充复现步骤、影响范围、截图或日志，再判断配置、产品缺陷或使用问题。"]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "static"), **kwargs)

    def send_json(self, payload, status=HTTPStatus.OK):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def body(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))).decode("utf-8"))

    def do_GET(self):
        if self.path == "/api/tickets":
            with connect() as db:
                rows = [dict(row) for row in db.execute("SELECT * FROM tickets ORDER BY id DESC")]
            self.send_json(rows); return
        if self.path == "/": self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        try: payload = self.body()
        except Exception: self.send_json({"error":"请求格式无效"}, HTTPStatus.BAD_REQUEST); return
        if self.path == "/api/tickets":
            title = str(payload.get("title", "")).strip(); detail = str(payload.get("detail", "")).strip()
            if not title or not detail: self.send_json({"error":"标题和问题描述不能为空"}, HTTPStatus.BAD_REQUEST); return
            diagnosis = "\n".join(diagnose(f"{title} {detail}"))
            with connect() as db:
                cursor = db.execute("INSERT INTO tickets (title,customer,category,priority,detail,status,diagnosis,created_at) VALUES (?,?,?,?,?,?,?,?)", (title, payload.get("customer", "未填写"), payload.get("category", "其他"), payload.get("priority", "P2"), detail, "待诊断", diagnosis, datetime.now().isoformat(timespec="minutes")))
                item = dict(db.execute("SELECT * FROM tickets WHERE id=?", (cursor.lastrowid,)).fetchone())
            self.send_json(item, HTTPStatus.CREATED); return
        if self.path.startswith("/api/tickets/") and self.path.endswith("/status"):
            ticket_id = self.path.split("/")[3]; status = payload.get("status")
            if status not in {"待诊断", "处理中", "待客户验证", "已关闭"}: self.send_json({"error":"状态无效"}, HTTPStatus.BAD_REQUEST); return
            with connect() as db: db.execute("UPDATE tickets SET status=? WHERE id=?", (status, ticket_id))
            self.send_json({"ok":True}); return
        self.send_json({"error":"未找到接口"}, HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    init_db(); print("Support workbench: http://127.0.0.1:8766"); ThreadingHTTPServer(("127.0.0.1", 8766), Handler).serve_forever()

import json
import os
import re
import base64
import uuid
from http.server import HTTPServer, SimpleHTTPRequestHandler

import csv_storage as db

HOST = "localhost"
PORT = 8000

IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "images")
os.makedirs(IMAGES_DIR, exist_ok=True)


class POSHandler(SimpleHTTPRequestHandler):

    def log_message(self, format, *args):
        try:
            msg = str(args[0])
            if "/api/" in msg:
                print(f"[API] {msg}  ->  {args[1]}")
        except Exception:
            pass

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")

        if path == "/api/products":
            return self._json(200, db.search_products(
                self._qparam("keyword"), self._qparam("category")
            ))

        if path == "/api/sales":
            return self._json(200, db.search_sales(
                self._qparam("date"), self._qparam("product")
            ))

        if path == "/api/sales/report":
            return self._json(200, db.report_sales_summary())

        m = re.match(r"^/api/sales/report/(daily|weekly|monthly|yearly)$", path)
        if m:
            return self._json(200, db.report_sales_by_period(m.group(1)))

        if path == "/api/logs":
            return self._json(200, db.search_logs(
                self._qparam("username"), self._qparam("date")
            ))

        if path == "/api/logs/report":
            return self._json(200, db.report_employee_hours())

        return super().do_GET()

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")
        body = self._read_body()

        if path == "/api/login":
            user = db.authenticate_user(body.get("username", ""), body.get("password", ""))
            if user:
                if user["role"] != "admin":
                    existing = db.search_logs(username=user["username"])
                    if not any(l for l in existing if not l.get("timeOut")):
                        db.save_log(user["username"])
                return self._json(200, {"ok": True, "role": user["role"], "username": user["username"]})
            return self._json(401, {"ok": False, "error": "Invalid credentials"})

        if path == "/api/register":
            result = db.save_user(body.get("username", ""), body.get("password", ""), body.get("role", "employee"))
            if result:
                return self._json(200, {"ok": True, "user": result})
            return self._json(409, {"ok": False, "error": "Username already exists"})

        if path == "/api/upload-image":
            data_url = body.get("image", "")
            if not data_url or not data_url.startswith("data:image/"):
                return self._json(400, {"ok": False, "error": "No valid image data"})
            try:
                header, encoded = data_url.split(",", 1)
                ext = header.split("/")[1].split(";")[0]
                ext = ext if ext in ("png", "jpeg", "jpg", "gif", "webp") else "png"
                filename = f"{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(IMAGES_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(base64.b64decode(encoded))
                return self._json(200, {"ok": True, "url": f"/data/images/{filename}"})
            except Exception as e:
                return self._json(500, {"ok": False, "error": str(e)})

        if path == "/api/products":
            product = db.save_product(
                name        = body.get("name", ""),
                price       = body.get("price", 0),
                category    = body.get("category", "others"),
                description = body.get("description", ""),
                image       = body.get("image", ""),
            )
            return self._json(201, {"ok": True, "product": product})

        if path == "/api/sales":
            sale = db.save_sale(body.get("items", []), body.get("total", 0))
            return self._json(201, {"ok": True, "sale": sale})

        if path == "/api/logs/timein":
            log = db.save_log(body.get("username", ""))
            return self._json(201, {"ok": True, "log": log})

        return self._json(404, {"error": "Not found"})

    def do_PUT(self):
        path = self.path.split("?")[0].rstrip("/")
        body = self._read_body()

        m = re.match(r"^/api/products/(.+)$", path)
        if m:
            updated = db.update_product(m.group(1), **body)
            if updated:
                return self._json(200, {"ok": True, "product": updated})
            return self._json(404, {"ok": False, "error": "Product not found"})

        if path == "/api/logs/timeout":
            log = db.update_log_timeout(body.get("id", ""), body.get("username", ""))
            if log:
                return self._json(200, {"ok": True, "log": log})
            return self._json(404, {"ok": False, "error": "No open log found"})

        return self._json(404, {"error": "Not found"})

    def do_DELETE(self):
        path = self.path.split("?")[0].rstrip("/")

        m = re.match(r"^/api/products/(.+)$", path)
        if m:
            pid = m.group(1)
            ok  = db.delete_product(pid) or db.delete_product_by_name(pid)
            return self._json(200 if ok else 404, {"ok": ok})

        if path == "/api/logs":
            db.clear_logs()
            return self._json(200, {"ok": True})

        return self._json(404, {"error": "Not found"})

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, status, data):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return {}

    def _qparam(self, key):
        from urllib.parse import urlparse, parse_qs
        qs   = parse_qs(urlparse(self.path).query)
        vals = qs.get(key, [""])
        return vals[0] if vals else ""


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"POS Server running at  http://{HOST}:{PORT}")
    print(f"Open your browser to:  http://{HOST}:{PORT}/login_ui.html")
    print("Press Ctrl+C to stop.\n")
    httpd = HTTPServer((HOST, PORT), POSHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
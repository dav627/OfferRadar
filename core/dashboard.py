"""
可视化仪表盘
本地 Web 服务：展示数据 + 在线编辑配置/公司清单/岗位关键词
"""

import json
import os
import sys
import webbrowser
import yaml
from collections import Counter
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs

from core import PROJECT_ROOT, DATA_DIR
from core.config import get_profile

HTML_PATH = Path(__file__).parent / "dashboard.html"
COMPANY_PATH = PROJECT_ROOT / "公司清单.json"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
PORT = 8686


def collect_data() -> dict:
    profile = get_profile()
    data = {"stats": {}, "status_dist": {}, "match_dist": {}, "tier_dist": {},
            "trend": {"dates": [], "counts": []}, "jobs": [], "emails": [],
            "companies": [], "profile": profile, "config": {}}

    # 公司清单
    companies = []
    if COMPANY_PATH.exists():
        with open(COMPANY_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        companies = raw.get("companies", [])
        data["companies"] = companies

    data["tier_dist"] = dict(sorted(Counter(c.get("tier", "?") for c in companies).items()))

    # Excel
    status_dist = Counter()
    match_dist = Counter()
    excel_path = DATA_DIR / "秋招投递跟踪表.xlsx"
    if excel_path.exists():
        try:
            import openpyxl
            wb = openpyxl.load_workbook(excel_path, read_only=True)
            ws = wb["投递跟踪表"]
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row[0]:
                    status_dist[row[13] or "未知"] += 1
                    match_dist[row[7] or "未知"] += 1
            wb.close()
        except Exception:
            pass
    data["status_dist"] = dict(status_dist)
    data["match_dist"] = dict(match_dist)

    # 最新抓取
    latest_path = DATA_DIR / "抓取结果" / "latest.json"
    jobs = []
    if latest_path.exists():
        with open(latest_path, encoding="utf-8") as f:
            jobs = json.load(f).get("jobs", [])
    data["jobs"] = jobs

    # 趋势
    scrape_dir = DATA_DIR / "抓取结果"
    trend = {}
    if scrape_dir.exists():
        for f in sorted(scrape_dir.glob("scrape_*.json")):
            try:
                with open(f, encoding="utf-8") as fh:
                    d = json.load(fh)
                ds = d.get("scraped_at", "")[:10]
                if ds:
                    trend[ds] = max(trend.get(ds, 0), d.get("total_jobs", 0))
            except Exception:
                pass
    data["trend"] = {"dates": list(trend.keys()), "counts": list(trend.values())}

    # 邮件
    ep = DATA_DIR / "email_results" / "latest.json"
    if ep.exists():
        try:
            with open(ep, encoding="utf-8") as f:
                data["emails"] = json.load(f).get("emails", [])
        except Exception:
            pass

    # config.yaml（只传非敏感字段给前端）
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        safe_cfg = {}
        for section in ["llm", "push", "email", "proxy", "schedule"]:
            safe_cfg[section] = cfg.get(section, {})
        # 脱敏: 只显示是否已填，不传完整 key
        if safe_cfg.get("llm", {}).get("api_key"):
            safe_cfg["llm"]["api_key"] = "sk-****" + safe_cfg["llm"]["api_key"][-4:]
        for ch in ["serverchan", "pushplus", "wecom_bot", "qmsg"]:
            sub = safe_cfg.get("push", {}).get(ch, {})
            for k in ["sendkey", "token", "webhook", "key"]:
                if sub.get(k):
                    sub[k] = "****" + sub[k][-4:]
        data["config"] = safe_cfg

    data["stats"] = {
        "companies": len(companies), "jobs": len(jobs),
        "pending": status_dist.get("待投递", 0),
        "interview": status_dist.get("面试中", 0),
        "offer": status_dist.get("offer", 0),
        "last_update": datetime.now().strftime("%m-%d %H:%M"),
        "profile": f"{profile['target_role']} · {profile['graduation']}届",
    }
    return data


def _save_companies(companies: list):
    with open(COMPANY_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    raw["companies"] = companies
    with open(COMPANY_PATH, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)


def _save_profile(profile: dict):
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    cfg["profile"] = profile
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _save_config_section(section: str, value: dict):
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    old = cfg.get(section, {})
    # Preserve masked sensitive values (don't overwrite real keys with ****)
    def _merge(old_dict, new_dict):
        for k, v in new_dict.items():
            if isinstance(v, str) and "****" in v:
                continue
            if isinstance(v, dict) and isinstance(old_dict.get(k), dict):
                _merge(old_dict[k], v)
            else:
                old_dict[k] = v
    _merge(old, value)
    cfg[section] = old
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def export_html(output_path: Path = None):
    if not output_path:
        output_path = DATA_DIR / "dashboard.html"
    data = collect_data()
    html = HTML_PATH.read_text(encoding="utf-8")
    inline_script = f"Promise.resolve({json.dumps(data, ensure_ascii=False)})"
    html = html.replace("fetch('/api/data').then(r => r.json())", inline_script)
    output_path.write_text(html, encoding="utf-8")
    print(f"[OK] 仪表盘已导出: {output_path}")
    return output_path


class DashboardHandler(SimpleHTTPRequestHandler):
    def _send_json(self, obj, code=200):
        content = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        return json.loads(body) if body else {}

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            content = HTML_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == "/api/data":
            self._send_json(collect_data())
        elif self.path == "/api/sources":
            from core.sources import get_cookie_status
            self._send_json(get_cookie_status())
        elif self.path == "/api/report":
            report_dir = DATA_DIR / "每日播报"
            reports = sorted(report_dir.glob("*.md"), reverse=True) if report_dir.exists() else []
            result = []
            for r in reports[:10]:
                result.append({"date": r.stem, "content": r.read_text(encoding="utf-8")})
            self._send_json({"reports": result})
        else:
            self.send_error(404)

    def do_POST(self):
        try:
            body = self._read_body()
            if self.path == "/api/companies":
                _save_companies(body.get("companies", []))
                self._send_json({"ok": True})
            elif self.path == "/api/profile":
                _save_profile(body)
                self._send_json({"ok": True})
            elif self.path == "/api/config":
                section = body.get("section", "")
                value = body.get("value", {})
                if section in ("llm", "push", "email", "proxy", "schedule"):
                    _save_config_section(section, value)
                    self._send_json({"ok": True})
                else:
                    self._send_json({"error": f"invalid section: {section}"}, 400)
            elif self.path == "/api/run":
                try:
                    import importlib
                    from core import config as _cfg_mod
                    _cfg_mod._config = None
                    # Ensure Excel exists
                    if not (DATA_DIR / "秋招投递跟踪表.xlsx").exists():
                        from core.excel import generate
                        generate()
                    import core.scraper_lite as _sl
                    importlib.reload(_sl)
                    jobs = _sl.run()
                    from core.report import run as report_run
                    report_run()
                    self._send_json({"ok": True, "jobs": len(jobs)})
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    self._send_json({"ok": False, "error": str(e)}, 500)
            elif self.path == "/api/login":
                platform = body.get("platform", "")
                import threading
                def _do_login():
                    from core.sources import login_and_save
                    login_and_save(platform)
                threading.Thread(target=_do_login, daemon=True).start()
                self._send_json({"ok": True, "msg": f"浏览器已打开，请在弹出的窗口中登录{platform}"})
            elif self.path == "/api/scrape-source":
                source = body.get("source", "")
                if source == "nowcoder":
                    from core.sources import scrape_nowcoder
                    kw = body.get("keyword", "")
                    results = scrape_nowcoder(kw)
                    self._send_json({"ok": True, "jobs": len(results), "data": results})
                elif source in ("alibaba", "meituan", "kuaishou", "xiaohongshu", "jd", "bilibili", "pinduoduo", "netease"):
                    from core.sources import scrape_with_cookies
                    results = scrape_with_cookies(source)
                    self._send_json({"ok": True, "jobs": len(results), "data": results})
                else:
                    self._send_json({"error": "unknown source"}, 400)
            else:
                self.send_error(404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass


def _ensure_init():
    """首次启动时自动初始化"""
    import shutil
    if not CONFIG_PATH.exists():
        tpl = PROJECT_ROOT / "config.yaml.example"
        if tpl.exists():
            shutil.copy(tpl, CONFIG_PATH)
    for d in ["抓取结果", "每日播报", "email_results", "cookies", "logs"]:
        (DATA_DIR / d).mkdir(parents=True, exist_ok=True)
    excel = DATA_DIR / "秋招投递跟踪表.xlsx"
    if not excel.exists():
        try:
            from core.excel import generate
            generate()
        except Exception as e:
            print(f"[WARN] Excel生成失败: {e}")


def serve(port: int = PORT, open_browser: bool = True):
    _ensure_init()
    try:
        server = HTTPServer(("127.0.0.1", port), DashboardHandler)
    except OSError as e:
        if "address already in use" in str(e).lower() or "10048" in str(e):
            print(f"[WARN] 端口 {port} 被占用，尝试 {port+1}")
            server = HTTPServer(("127.0.0.1", port + 1), DashboardHandler)
            port += 1
        else:
            raise
    url = f"http://127.0.0.1:{port}"
    print(f"[OK] 仪表盘已启动: {url}")
    print("[INFO] 按 Ctrl+C 停止")
    sys.stdout.flush()
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] 仪表盘已停止")
        server.server_close()

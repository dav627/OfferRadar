#!/usr/bin/env python3
"""
统一邮件监控模块
支持 Gmail API 和 IMAP（163/QQ/Outlook/其他）两种方式

Gmail:  通过 OAuth2 API 访问，需要 credentials.json
IMAP:   通过授权码/密码直接连接，适用于 163/QQ/Outlook 等国内邮箱
"""

import imaplib
import email
import email.header
import json
import os
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core import PROJECT_ROOT, DATA_DIR

RESULTS_DIR = DATA_DIR / "email_results"
RESULTS_DIR.mkdir(exist_ok=True)

# 已知的招聘邮件发件人域名
RECRUIT_DOMAINS = [
    "bytedance.com", "toutiao.com", "tencent.com", "qq.com",
    "alibaba-inc.com", "aligroup.com", "baidu.com",
    "meituan.com", "sankuai.com", "kuaishou.com", "huawei.com",
    "xiaohongshu.com", "jd.com", "netease.com", "163.com",
    "pinduoduo.com", "didi.com", "xiaomi.com", "oppo.com", "vivo.com",
    "deepseek.com", "zhipuai.cn", "moonshot.cn",
    "nowcoder.com", "beisen.com", "mokahr.com", "hotjob.cn",
]

RECRUIT_KEYWORDS = ["笔试", "面试", "offer", "录用", "通知",
                    "校园招聘", "秋招", "网申", "在线测评", "邀请函"]

# IMAP 服务器预设
IMAP_SERVERS = {
    "163":     {"host": "imap.163.com",        "port": 993},
    "126":     {"host": "imap.126.com",        "port": 993},
    "qq":      {"host": "imap.qq.com",         "port": 993},
    "gmail":   {"host": "imap.gmail.com",      "port": 993},
    "outlook": {"host": "imap-mail.outlook.com", "port": 993},
    "hotmail": {"host": "imap-mail.outlook.com", "port": 993},
    "yeah":    {"host": "imap.yeah.net",       "port": 993},
    "sina":    {"host": "imap.sina.com",       "port": 993},
}


def _decode_header(raw: str) -> str:
    """解码邮件头（处理 =?UTF-8?B?xxx?= 等编码）"""
    parts = email.header.decode_header(raw)
    result = []
    for text, charset in parts:
        if isinstance(text, bytes):
            result.append(text.decode(charset or "utf-8", errors="ignore"))
        else:
            result.append(text)
    return "".join(result)


def _detect_provider(addr: str) -> str:
    """从邮箱地址推断邮箱提供商"""
    domain = addr.split("@")[-1].lower()
    for provider, cfg in IMAP_SERVERS.items():
        if provider in domain:
            return provider
    return ""


def _is_recruit_email(subject: str, from_addr: str) -> bool:
    for domain in RECRUIT_DOMAINS:
        if domain in from_addr.lower():
            return True
    for kw in RECRUIT_KEYWORDS:
        if kw in subject:
            return True
    return False


def _identify_company(from_addr: str) -> str:
    company_map = {
        "bytedance": "字节跳动", "toutiao": "字节跳动",
        "tencent": "腾讯", "alibaba": "阿里巴巴", "aligroup": "阿里巴巴",
        "baidu": "百度", "meituan": "美团", "sankuai": "美团",
        "kuaishou": "快手", "huawei": "华为", "xiaohongshu": "小红书",
        "jd.com": "京东", "netease": "网易", "xiaomi": "小米",
        "deepseek": "DeepSeek", "zhipuai": "智谱AI", "moonshot": "月之暗面",
    }
    for key, name in company_map.items():
        if key in from_addr.lower():
            return name
    return "未知"


def _categorize(subject: str) -> str:
    if any(kw in subject for kw in ["笔试", "测评", "在线测试"]):
        return "笔试通知"
    if any(kw in subject for kw in ["面试", "邀请"]):
        return "面试邀请"
    if any(kw in subject for kw in ["offer", "录用", "录取"]):
        return "Offer通知"
    if any(kw in subject for kw in ["网申", "简历", "投递"]):
        return "投递确认"
    return "其他"


# ==================== IMAP 方式 ====================

def fetch_via_imap(config: dict, days: int = 1) -> list:
    """通过 IMAP 协议获取邮件（163/QQ/Outlook 等）"""
    addr = config.get("address", "")
    password = config.get("password", "")  # 授权码，非登录密码
    provider = config.get("provider", "") or _detect_provider(addr)
    host = config.get("imap_host", "") or IMAP_SERVERS.get(provider, {}).get("host", "")
    port = config.get("imap_port", 0) or IMAP_SERVERS.get(provider, {}).get("port", 993)

    if not all([addr, password, host]):
        print(f"[ERROR] IMAP 配置不完整: address={bool(addr)}, password={bool(password)}, host={bool(host)}")
        return []

    print(f"[INFO] 连接 {host}:{port} ({addr})...")

    try:
        conn = imaplib.IMAP4_SSL(host, port)
        conn.login(addr, password)
        conn.select("INBOX")
    except Exception as e:
        print(f"[ERROR] IMAP 连接失败: {e}")
        if "AUTHENTICATIONFAILED" in str(e) or "LOGIN" in str(e):
            print("  提示: 请确认使用的是【授权码】而非登录密码")
            print("  163邮箱: 设置 → POP3/SMTP/IMAP → 开启IMAP → 获取授权码")
            print("  QQ邮箱:  设置 → 账户 → 开启IMAP → 获取授权码")
        return []

    since_date = (datetime.now() - timedelta(days=3)).strftime("%d-%b-%Y")
    _, msg_ids = conn.search(None, f'(UNSEEN SINCE "{since_date}")')

    emails_found = []
    for msg_id in msg_ids[0].split()[-50:]:
        # PEEK: read without changing UNSEEN flag
        _, data = conn.fetch(msg_id, "(BODY.PEEK[])")
        raw = data[0][1]
        msg = email.message_from_bytes(raw)

        subject = _decode_header(msg.get("Subject", ""))
        from_raw = _decode_header(msg.get("From", ""))
        date_str = msg.get("Date", "")

        if _is_recruit_email(subject, from_raw):
            # Extract body preview
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(msg.get_content_charset() or "utf-8", errors="ignore")

            emails_found.append({
                "subject": subject,
                "from": from_raw,
                "date": date_str[:30],
                "company": _identify_company(from_raw),
                "category": _categorize(subject),
                "snippet": body[:200].replace("\n", " ").strip(),
            })

    conn.logout()
    return emails_found


# ==================== Gmail API 方式 ====================

def fetch_via_gmail(days: int = 1) -> list:
    """通过 Gmail API 获取邮件（需要 credentials.json + token.json）"""
    try:
        from core.gmail import fetch_recent_recruit_emails
        return fetch_recent_recruit_emails(days)
    except Exception as e:
        print(f"[ERROR] Gmail API 调用失败: {e}")
        return []


# ==================== 统一入口 ====================

def fetch_emails(config: dict, days: int = 1) -> list:
    """根据配置自动选择 Gmail API 或 IMAP"""
    method = config.get("method", "").lower()

    if method == "gmail_api":
        print("[INFO] 使用 Gmail API 模式")
        return fetch_via_gmail(days)
    elif method == "imap":
        print("[INFO] 使用 IMAP 模式")
        return fetch_via_imap(config, days)
    else:
        # Auto detect
        if (PROJECT_ROOT / "token.json").exists():
            print("[INFO] 检测到 token.json，使用 Gmail API")
            return fetch_via_gmail(days)
        elif config.get("address") and config.get("password"):
            print("[INFO] 使用 IMAP 模式")
            return fetch_via_imap(config, days)
        else:
            print("[WARN] 未配置邮箱监控")
            return []


def _one_line_summary(e: dict) -> str:
    """一句话概括邮件内容"""
    snippet = e.get("snippet", "")[:80].replace("\n", " ").strip()
    if not snippet:
        return e.get("subject", "")[:50]
    return snippet


def generate_email_report(emails: list) -> str:
    """生成邮件监控报告（仅未读邮件，一句话概括）"""
    if not emails:
        return ""

    report = "\n## 邮箱监控（最近3天未读）\n\n"

    for e in emails:
        tag = f"**[{e['category']}]**" if e["category"] != "其他" else ""
        company = e.get("company", "未知")
        summary = _one_line_summary(e)
        report += f"- {tag} {company} | {summary}\n"

    return report


def save_results(emails: list):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {"checked_at": datetime.now().isoformat(), "total": len(emails), "emails": emails}
    path = RESULTS_DIR / f"email_{timestamp}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    # Also save latest
    with open(RESULTS_DIR / "latest.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    return path


if __name__ == "__main__":
    from core import config as config_loader
    cfg = config_loader.get_email_config()
    days = 7
    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])
    emails = fetch_emails(cfg, days)
    if emails:
        save_results(emails)
        print(generate_email_report(emails))
    else:
        print("[INFO] 未发现招聘邮件")

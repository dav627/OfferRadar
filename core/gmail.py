#!/usr/bin/env python3
"""
Gmail 监控模块
监控招聘相关邮件：笔试通知、面试邀请、offer通知等
需要先完成 Gmail API OAuth2 授权

首次使用：
1. 访问 https://console.cloud.google.com/apis/credentials
2. 创建 OAuth 2.0 客户端（桌面应用类型）
3. 下载 credentials.json 放到本目录
4. 运行 python3 gmail_monitor.py --auth 完成首次授权
"""

import os
import sys
import json
import base64
import re
from datetime import datetime, timedelta
from pathlib import Path

from core import config as config_loader
from typing import Optional

from core import PROJECT_ROOT, DATA_DIR
CREDENTIALS_PATH = PROJECT_ROOT / "credentials.json"
TOKEN_PATH = PROJECT_ROOT / "token.json"
GMAIL_RESULTS_DIR = DATA_DIR / "gmail_results"
GMAIL_RESULTS_DIR.mkdir(exist_ok=True)

# 招聘相关关键词 - 用于过滤邮件
RECRUIT_KEYWORDS = [
    "笔试", "面试", "offer", "录用", "通知",
    "校园招聘", "秋招", "网申",
    "在线测评", "测试链接", "邀请函",
    "HR", "人力资源",
]

# 已知的招聘邮件发件人域名
RECRUIT_DOMAINS = [
    "bytedance.com", "toutiao.com",
    "tencent.com", "qq.com",
    "alibaba-inc.com", "aligroup.com",
    "baidu.com",
    "meituan.com", "sankuai.com",
    "kuaishou.com",
    "huawei.com",
    "xiaohongshu.com",
    "jd.com",
    "netease.com", "163.com",
    "pinduoduo.com",
    "didi.com", "didiglobal.com",
    "xiaomi.com",
    "oppo.com", "vivo.com",
    "honor.com",
    "deepseek.com",
    "zhipuai.cn",
    "moonshot.cn",
    "nowcoder.com",
    "beisen.com",  # 北森（很多公司用的招聘系统）
    "mokahr.com",  # Moka（招聘系统）
    "hotjob.cn",
]


def get_gmail_service():
    """获取已授权的 Gmail API service"""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("[ERROR] 请安装: pip3 install google-auth google-auth-oauthlib google-api-python-client")
        return None

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                print(f"[ERROR] 未找到 {CREDENTIALS_PATH}")
                print("请按以下步骤配置：")
                print("1. 访问 https://console.cloud.google.com/apis/credentials")
                print("2. 创建项目 → 启用 Gmail API")
                print("3. 创建 OAuth 2.0 客户端 ID（桌面应用）")
                print("4. 下载 JSON 并保存为 credentials.json 到本目录")
                print("5. 重新运行: python3 gmail_monitor.py --auth")
                return None

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            # Print URL for manual auth instead of auto-opening browser
            creds = flow.run_local_server(port=8090, open_browser=False,
                                          prompt="consent",
                                          authorization_prompt_message="请在浏览器中打开以下链接完成授权：\n{url}")

        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    import httplib2
    from google_auth_httplib2 import AuthorizedHttp
    proxy = config_loader.get_proxy()
    if proxy.get("http"):
        from urllib.parse import urlparse
        p = urlparse(proxy["http"])
        proxy_info = httplib2.ProxyInfo(
            proxy_type=httplib2.socks.PROXY_TYPE_HTTP,
            proxy_host=p.hostname or "127.0.0.1",
            proxy_port=p.port or 7897,
        )
        http = httplib2.Http(proxy_info=proxy_info)
    else:
        http = httplib2.Http()
    authed_http = AuthorizedHttp(creds, http=http)
    return build("gmail", "v1", http=authed_http)


def is_recruit_email(msg_data: dict) -> bool:
    """判断邮件是否与招聘相关"""
    headers = {h["name"].lower(): h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
    subject = headers.get("subject", "")
    from_addr = headers.get("from", "")

    # Check if from known recruitment domains
    for domain in RECRUIT_DOMAINS:
        if domain in from_addr.lower():
            return True

    # Check subject for recruitment keywords
    for kw in RECRUIT_KEYWORDS:
        if kw in subject:
            return True

    return False


def extract_email_info(msg_data: dict) -> dict:
    """提取邮件关键信息"""
    headers = {h["name"].lower(): h["value"] for h in msg_data.get("payload", {}).get("headers", [])}

    # Try to get body text
    body = ""
    payload = msg_data.get("payload", {})
    if "body" in payload and payload["body"].get("data"):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    elif "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                break

    # Determine email category
    subject = headers.get("subject", "")
    category = "其他"
    if any(kw in subject for kw in ["笔试", "测评", "在线测试"]):
        category = "笔试通知"
    elif any(kw in subject for kw in ["面试", "邀请"]):
        category = "面试邀请"
    elif any(kw in subject for kw in ["offer", "录用", "录取"]):
        category = "Offer通知"
    elif any(kw in subject for kw in ["网申", "简历", "投递"]):
        category = "投递确认"

    # Try to identify company
    from_addr = headers.get("from", "")
    company = "未知"
    company_map = {
        "bytedance": "字节跳动", "toutiao": "字节跳动",
        "tencent": "腾讯", "qq.com": "腾讯",
        "alibaba": "阿里巴巴", "aligroup": "阿里巴巴",
        "baidu": "百度",
        "meituan": "美团", "sankuai": "美团",
        "kuaishou": "快手",
        "huawei": "华为",
        "xiaohongshu": "小红书",
        "jd.com": "京东",
        "netease": "网易", "163.com": "网易",
        "xiaomi": "小米",
        "deepseek": "DeepSeek",
    }
    for domain_key, company_name in company_map.items():
        if domain_key in from_addr.lower():
            company = company_name
            break

    return {
        "id": msg_data.get("id", ""),
        "subject": subject,
        "from": from_addr,
        "date": headers.get("date", ""),
        "company": company,
        "category": category,
        "snippet": msg_data.get("snippet", ""),
        "body_preview": body[:500] if body else "",
    }


def fetch_recent_recruit_emails(days: int = 3) -> list:
    """获取最近3天的未读招聘邮件"""
    service = get_gmail_service()
    if not service:
        return []

    after_date = (datetime.now() - timedelta(days=3)).strftime("%Y/%m/%d")
    query = f"is:unread after:{after_date} ("
    query += " OR ".join(f'from:{d}' for d in RECRUIT_DOMAINS[:10])
    query += " OR " + " OR ".join(f'subject:{kw}' for kw in RECRUIT_KEYWORDS[:5])
    query += ")"

    print(f"[INFO] 搜索邮件: {query[:100]}...")

    try:
        results = service.users().messages().list(
            userId="me", q=query, maxResults=50
        ).execute()
    except Exception as e:
        print(f"[ERROR] Gmail API 调用失败: {e}")
        return []

    messages = results.get("messages", [])
    if not messages:
        print("[INFO] 未找到新的招聘邮件")
        return []

    print(f"[INFO] 找到 {len(messages)} 封邮件，正在解析...")

    recruit_emails = []
    for msg in messages:
        try:
            msg_data = service.users().messages().get(
                userId="me", id=msg["id"], format="full"
            ).execute()
            if is_recruit_email(msg_data):
                info = extract_email_info(msg_data)
                recruit_emails.append(info)
        except Exception as e:
            print(f"[WARN] 解析邮件失败: {e}")

    return recruit_emails


def save_email_results(emails: list):
    """保存邮件检查结果"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        "checked_at": datetime.now().isoformat(),
        "total_emails": len(emails),
        "emails": emails
    }

    output_path = GMAIL_RESULTS_DIR / f"gmail_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    latest_path = GMAIL_RESULTS_DIR / "latest.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[DONE] 邮件结果已保存: {output_path}")
    return output_path


def generate_email_report(emails: list) -> str:
    """生成邮件监控报告片段（嵌入每日播报）"""
    if not emails:
        return "\n## Gmail 监控\n\n无新的招聘相关邮件。\n"

    report = "\n## Gmail 监控\n\n"
    report += f"发现 **{len(emails)}** 封招聘相关邮件：\n\n"
    report += "| 时间 | 公司 | 类别 | 主题 |\n"
    report += "|------|------|------|------|\n"

    for email in emails:
        date = email.get("date", "")[:16]
        report += f"| {date} | {email['company']} | {email['category']} | {email['subject'][:40]} |\n"

    # Highlight important ones
    important = [e for e in emails if e["category"] in ("笔试通知", "面试邀请", "Offer通知")]
    if important:
        report += "\n### 重要通知\n\n"
        for e in important:
            report += f"- **[{e['category']}]** {e['company']} - {e['subject']}\n"
            if e.get("snippet"):
                report += f"  > {e['snippet'][:100]}\n"

    return report


def run(days: int = 1):
    """主入口"""
    print(f"[INFO] Gmail 监控开始 - 检查最近{days}天邮件")

    emails = fetch_recent_recruit_emails(days)
    if emails:
        save_email_results(emails)
        report = generate_email_report(emails)
        print(report)
    else:
        print("[INFO] 无新招聘邮件")

    return emails


def gmail_auth():
    """手动 OAuth 授权流程"""
    import warnings
    warnings.filterwarnings("ignore")
    from google_auth_oauthlib.flow import Flow

    if not CREDENTIALS_PATH.exists():
        print(f"[ERROR] 未找到 {CREDENTIALS_PATH}")
        return False

    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_PATH),
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        redirect_uri="urn:ietf:wg:oauth:2.0:oob",
    )
    auth_url, _ = flow.authorization_url(prompt="consent")

    print("=" * 60)
    print("  Gmail 授权")
    print("=" * 60)
    print("\n请复制以下链接到浏览器打开：\n")
    print(auth_url)
    print()
    code = input("授权完成后，把页面上显示的授权码粘贴到这里: ").strip()

    flow.fetch_token(code=code)
    with open(TOKEN_PATH, "w") as f:
        f.write(flow.credentials.to_json())

    print("\n[DONE] 授权成功！token 已保存")
    return True

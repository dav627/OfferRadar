#!/usr/bin/env python3
"""
消息推送模块
支持多种推送渠道将每日播报发送到手机

支持的渠道：
1. Server酱 (推荐) - 免费，微信推送
   注册: https://sct.ftqq.com/
   获取 SendKey 后填入 config.json

2. PushPlus - 免费，微信推送，支持更多模板
   注册: https://www.pushplus.plus/
   获取 token 后填入 config.json

3. 企业微信机器人 - 适合群通知
   创建群机器人获取 webhook URL

4. QQ (通过 Qmsg酱)
   注册: https://qmsg.zendee.cn/
"""

import json
import sys
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional

from core import PROJECT_ROOT, DATA_DIR
from core import config as config_loader


def load_config() -> dict:
    return {"push_channels": config_loader.get_push_config()}


def push_serverchan(title: str, content: str, sendkey: str) -> bool:
    """Server酱推送"""
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = urllib.parse.urlencode({
        "title": title[:100],
        "desp": content[:32000],
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            if result.get("code") == 0:
                print("[OK] Server酱推送成功")
                return True
            else:
                print(f"[FAIL] Server酱: {result.get('message', 'unknown error')}")
                return False
    except Exception as e:
        print(f"[ERROR] Server酱推送失败: {e}")
        return False


def push_pushplus(title: str, content: str, token: str) -> bool:
    """PushPlus推送"""
    url = "http://www.pushplus.plus/send"
    data = json.dumps({
        "token": token,
        "title": title[:100],
        "content": content,
        "template": "markdown",
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            if result.get("code") == 200:
                print("[OK] PushPlus推送成功")
                return True
            else:
                print(f"[FAIL] PushPlus: {result.get('msg', 'unknown error')}")
                return False
    except Exception as e:
        print(f"[ERROR] PushPlus推送失败: {e}")
        return False


def push_wecom_bot(title: str, content: str, webhook: str) -> bool:
    """企业微信机器人推送"""
    # 企业微信限制 markdown 4096字节
    msg = f"## {title}\n\n{content[:3500]}"
    data = json.dumps({
        "msgtype": "markdown",
        "markdown": {"content": msg}
    }).encode("utf-8")

    try:
        req = urllib.request.Request(webhook, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            if result.get("errcode") == 0:
                print("[OK] 企业微信机器人推送成功")
                return True
            else:
                print(f"[FAIL] 企业微信: {result.get('errmsg', '')}")
                return False
    except Exception as e:
        print(f"[ERROR] 企业微信推送失败: {e}")
        return False


def push_qmsg(title: str, content: str, key: str, qq: str) -> bool:
    """Qmsg酱推送到QQ"""
    url = f"https://qmsg.zendee.cn/send/{key}"
    # QQ消息不支持markdown，转为纯文本
    plain_text = content.replace("#", "").replace("*", "").replace("|", " ")
    msg = f"【{title}】\n\n{plain_text[:1000]}"

    data = urllib.parse.urlencode({
        "msg": msg,
        "qq": qq,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            if result.get("success"):
                print("[OK] Qmsg推送成功")
                return True
            else:
                print(f"[FAIL] Qmsg: {result.get('reason', '')}")
                return False
    except Exception as e:
        print(f"[ERROR] Qmsg推送失败: {e}")
        return False


def send_notification(title: str, content: str) -> dict:
    """通过所有已启用的渠道发送通知"""
    config = load_config()
    channels = config.get("push_channels", {})
    results = {}

    if channels.get("serverchan", {}).get("enabled"):
        sendkey = channels["serverchan"]["sendkey"]
        results["serverchan"] = push_serverchan(title, content, sendkey)

    if channels.get("pushplus", {}).get("enabled"):
        token = channels["pushplus"]["token"]
        results["pushplus"] = push_pushplus(title, content, token)

    if channels.get("wecom_bot", {}).get("enabled"):
        webhook = channels["wecom_bot"]["webhook"]
        results["wecom_bot"] = push_wecom_bot(title, content, webhook)

    if channels.get("qmsg", {}).get("enabled"):
        key = channels["qmsg"]["key"]
        qq = channels["qmsg"]["qq"]
        results["qmsg"] = push_qmsg(title, content, key, qq)

    if not results:
        print("[WARN] 未启用任何推送渠道")
        print("[INFO] 请编辑 config.json 配置推送渠道")

    return results


def send_daily_report():
    """发送每日播报"""
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = DATA_DIR / "每日播报" / f"{today}.md"

    if not report_path.exists():
        print(f"[ERROR] 未找到今日播报: {report_path}")
        return

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    title = f"秋招日报 {today}"
    results = send_notification(title, content)

    success = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n[SUMMARY] 推送完成: {success}/{total} 个渠道成功")


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        print("[TEST] 发送测试消息...")
        send_notification("秋招Agent测试", "这是一条测试消息，如果你收到了说明推送配置成功！")
    else:
        send_daily_report()

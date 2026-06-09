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
    """通过所有已启用的渠道发送通知，并记录推送结果"""
    from core.db import log_push

    config = load_config()
    channels = config.get("push_channels", {})
    results = {}

    push_fns = {
        "serverchan": lambda ch: push_serverchan(title, content, ch["sendkey"]),
        "pushplus": lambda ch: push_pushplus(title, content, ch["token"]),
        "wecom_bot": lambda ch: push_wecom_bot(title, content, ch["webhook"]),
        "qmsg": lambda ch: push_qmsg(title, content, ch["key"], ch["qq"]),
    }

    for name, fn in push_fns.items():
        ch = channels.get(name, {})
        if ch.get("enabled"):
            try:
                ok = fn(ch)
                results[name] = ok
                log_push(name, title, content[:150], ok)
            except Exception as e:
                results[name] = False
                log_push(name, title, content[:150], False, str(e))

    if not results:
        print("[WARN] 未启用任何推送渠道")

    return results


def _build_smart_title(new_count: int, expiring_count: int, companies: list) -> str:
    """生成智能推送标题"""
    today = datetime.now().strftime("%m-%d")
    parts = []
    if new_count > 0:
        co_text = "/".join(companies[:2])
        parts.append(f"+{new_count}新岗 {co_text}")
    if expiring_count > 0:
        parts.append(f"{expiring_count}个即将截止")
    if parts:
        return f"秋招{today} | {' · '.join(parts)}"
    return f"秋招日报 {today} | 暂无新增"


def _build_push_content(report_raw: str, new_jobs: list, expiring: list) -> str:
    """构建适合微信阅读的推送内容（非原始 Markdown）"""
    sections = []

    # 截止紧急提醒
    if expiring:
        lines = ["## ⚠️ 即将截止\n"]
        for j in expiring:
            from datetime import datetime as dt
            days = max(0, (dt.strptime(j["deadline"], "%Y-%m-%d") - dt.now()).days)
            urgency = "**今天截止!**" if days == 0 else f"还剩{days}天"
            lines.append(f"- **{j['company']}** {j['title']} — {urgency}")
        sections.append("\n".join(lines))

    # 新增岗位
    if new_jobs:
        lines = [f"## 📋 今日新增 {len(new_jobs)} 个岗位\n"]
        for j in new_jobs[:10]:
            lines.append(f"- **{j['company']}** {j['title']}")
        if len(new_jobs) > 10:
            lines.append(f"- ...等共{len(new_jobs)}个")
        sections.append("\n".join(lines))

    # 状态总览
    try:
        from core.db import get_stats
        stats = get_stats()
        status = stats.get("by_status", {})
        overview = f"""## 📊 投递进度

| 状态 | 数量 |
|------|------|
| 待投递 | {status.get('待投递', 0)} |
| 已投递 | {status.get('已投递', 0)} |
| 面试中 | {status.get('面试中', 0)} |
| Offer | {status.get('offer', 0)} |
| 总岗位 | {stats.get('total', 0)} |"""
        sections.append(overview)
    except Exception:
        pass

    if not sections:
        sections.append("今日无新增岗位，市场平静。\n\n打开仪表盘查看详情。")

    return "\n\n---\n\n".join(sections)


def send_daily_report():
    """发送每日播报——智能标题 + 模板化内容"""
    today = datetime.now().strftime("%Y-%m-%d")

    # 获取今日数据
    new_jobs = []
    expiring = []
    try:
        from core.db import get_new_jobs, get_expiring_jobs
        today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
        new_jobs = get_new_jobs(since=today_start)
        expiring = get_expiring_jobs(3)
    except Exception:
        pass

    # 新增岗位的公司列表
    new_companies = list(dict.fromkeys(j["company"] for j in new_jobs))

    # 智能标题
    title = _build_smart_title(len(new_jobs), len(expiring), new_companies)

    # 原始播报内容
    report_path = DATA_DIR / "每日播报" / f"{today}.md"
    report_raw = ""
    if report_path.exists():
        with open(report_path, "r", encoding="utf-8") as f:
            report_raw = f.read()

    # 构建推送专用内容
    content = _build_push_content(report_raw, new_jobs, expiring)

    # 推送
    results = send_notification(title, content)

    success = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n[SUMMARY] 推送完成: {success}/{total} 个渠道成功")

    # 截止紧急单独推一条
    if expiring:
        urgent = [j for j in expiring if j.get("deadline") == today]
        if urgent:
            urgent_title = f"⚠️ 今天截止！{len(urgent)}个岗位"
            urgent_content = "\n".join(f"- **{j['company']}** {j['title']}" for j in urgent)
            send_notification(urgent_title, urgent_content)


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        print("[TEST] 发送测试消息...")
        send_notification("秋招Agent测试", "这是一条测试消息，如果你收到了说明推送配置成功！")
    else:
        send_daily_report()

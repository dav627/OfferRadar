"""
统一配置加载器
优先级: .env 文件 > 环境变量 > config.json > 默认值
"""

import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR / ".env"
CONFIG_PATH = BASE_DIR / "config.json"
SCHEDULE_PATH = BASE_DIR / "schedule.json"


def _load_env_file():
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if value and key not in os.environ:
                os.environ[key] = value


_load_env_file()


def get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def get_proxy() -> dict:
    http = get("HTTP_PROXY")
    https = get("HTTPS_PROXY")
    return {"http": http, "https": https} if http or https else {}


def get_push_config() -> dict:
    config = {"serverchan": {}, "pushplus": {}, "wecom_bot": {}, "qmsg": {}}

    sk = get("SERVERCHAN_SENDKEY")
    if sk:
        config["serverchan"] = {"enabled": True, "sendkey": sk}

    tk = get("PUSHPLUS_TOKEN")
    if tk:
        config["pushplus"] = {"enabled": True, "token": tk}

    wh = get("WECOM_BOT_WEBHOOK")
    if wh:
        config["wecom_bot"] = {"enabled": True, "webhook": wh}

    qk = get("QMSG_KEY")
    qq = get("QMSG_QQ")
    if qk and qq:
        config["qmsg"] = {"enabled": True, "key": qk, "qq": qq}

    # Fallback: read from config.json if .env not configured
    if not any(v.get("enabled") for v in config.values()) and CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            file_config = json.load(f)
        return file_config.get("push_channels", config)

    return config


def get_llm_config() -> dict:
    return {
        "api_key": get("LLM_API_KEY"),
        "base_url": get("LLM_BASE_URL", "https://api.deepseek.com/v1"),
        "model": get("LLM_MODEL", "deepseek-chat"),
    }


def get_schedule_config() -> dict:
    defaults = {"enabled": False, "time": "09:00", "mode": "lite",
                "gmail": True, "push": True}
    if SCHEDULE_PATH.exists():
        with open(SCHEDULE_PATH) as f:
            saved = json.load(f)
        defaults.update(saved)
    return defaults


def save_schedule_config(config: dict):
    with open(SCHEDULE_PATH, "w") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

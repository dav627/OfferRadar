"""
统一配置加载器
所有配置集中在 config.yaml 中管理
优先级: config.yaml > .env 环境变量 > 默认值
"""

import os
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.yaml"
ENV_PATH = BASE_DIR / ".env"

_config = None


def _load():
    global _config
    if _config is not None:
        return _config

    # Load .env as fallback
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                if v.strip() and k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip()

    # Load config.yaml
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            _config = yaml.safe_load(f) or {}
    else:
        _config = {}

    return _config


def get(section: str, key: str, default=""):
    """读取配置: get("llm", "api_key")"""
    cfg = _load()
    return cfg.get(section, {}).get(key, default) or default


def get_section(section: str) -> dict:
    """读取整个配置段: get_section("push")"""
    cfg = _load()
    return cfg.get(section, {})


def get_llm_config() -> dict:
    cfg = _load()
    llm = cfg.get("llm", {})
    return {
        "api_key": llm.get("api_key") or os.environ.get("LLM_API_KEY", ""),
        "base_url": llm.get("base_url") or os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1"),
        "model": llm.get("model") or os.environ.get("LLM_MODEL", "deepseek-chat"),
    }


def get_proxy() -> dict:
    cfg = _load()
    proxy = cfg.get("proxy", {})
    http = proxy.get("http") or os.environ.get("HTTP_PROXY", "")
    https = proxy.get("https") or os.environ.get("HTTPS_PROXY", "")
    return {"http": http, "https": https} if http or https else {}


def get_push_config() -> dict:
    cfg = _load()
    push = cfg.get("push", {})

    result = {}
    for channel in ["serverchan", "pushplus", "wecom_bot", "qmsg"]:
        ch = push.get(channel, {})
        if ch.get("enabled"):
            result[channel] = ch
        else:
            result[channel] = {}

    # .env fallback
    if not any(v.get("enabled") for v in result.values()):
        sk = os.environ.get("SERVERCHAN_SENDKEY", "")
        if sk:
            result["serverchan"] = {"enabled": True, "sendkey": sk}

    return result


def get_email_config() -> dict:
    cfg = _load()
    return cfg.get("email", {})


def get_schedule_config() -> dict:
    cfg = _load()
    defaults = {"enabled": False, "time": "09:00", "mode": "lite", "email": True, "push": True}
    defaults.update(cfg.get("schedule", {}))
    return defaults


def save_schedule_config(sched: dict):
    cfg = _load()
    cfg["schedule"] = sched
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

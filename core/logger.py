"""
统一日志系统
- 同时输出到终端和文件
- 仪表盘可通过 /api/logs 查看
"""

import logging
import sys
from pathlib import Path
from core import DATA_DIR

LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "offerradar.log"

_initialized = False


def get_logger(name: str = "offerradar") -> logging.Logger:
    global _initialized
    logger = logging.getLogger(name)

    if not _initialized:
        logger.setLevel(logging.DEBUG)

        fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s",
                                datefmt="%m-%d %H:%M:%S")

        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

        # File handler
        fh = logging.FileHandler(str(LOG_FILE), encoding="utf-8", mode="a")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

        _initialized = True

    return logger


def get_recent_logs(lines: int = 100) -> str:
    if not LOG_FILE.exists():
        return ""
    text = LOG_FILE.read_text(encoding="utf-8", errors="ignore")
    return "\n".join(text.strip().split("\n")[-lines:])

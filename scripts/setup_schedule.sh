#!/bin/bash
# 秋招Agent定时任务配置脚本
# 使用 macOS launchd 设置每天自动执行

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.$(whoami).qiuzhao-agent"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
LOG_DIR="$SCRIPT_DIR/logs"
PYTHON_PATH=$(which python3)
HOUR=${1:-9}
MINUTE=${2:-0}

mkdir -p "$LOG_DIR"

echo "=== 秋招Agent 定时任务配置 ==="
echo "脚本目录: $SCRIPT_DIR"
echo "Python路径: $PYTHON_PATH"
echo "执行时间: 每天 ${HOUR}:$(printf '%02d' $MINUTE)"
echo ""

cat > "$PLIST_PATH" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_PATH}</string>
        <string>${SCRIPT_DIR}/run_daily.py</string>
        <string>--lite</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>${HOUR}</integer>
        <key>Minute</key>
        <integer>${MINUTE}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:${HOME}/Library/Python/3.9/bin</string>
    </dict>
</dict>
</plist>
PLIST

echo "已创建 plist: $PLIST_PATH"
launchctl unload "$PLIST_PATH" 2>/dev/null
launchctl load "$PLIST_PATH"

echo "定时任务已加载！"
echo ""
echo "常用命令:"
echo "  手动触发: launchctl start $PLIST_NAME"
echo "  查看状态: launchctl list | grep qiuzhao"
echo "  停止任务: launchctl unload $PLIST_PATH"
echo "  查看日志: tail -f $LOG_DIR/stdout.log"

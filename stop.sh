#!/usr/bin/env bash
# Stop the HokkienTTS chat UI.  Run from Git Bash:  ./stop.sh
PID=$(netstat -ano 2>/dev/null | grep "127.0.0.1:7860" | grep LISTENING | awk '{print $NF}' | head -1)
if [ -n "$PID" ]; then
  taskkill //F //PID "$PID" >/dev/null 2>&1
  echo "Stopped chat app (PID $PID)."
else
  echo "Chat app is not running."
fi

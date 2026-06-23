#!/usr/bin/env bash
# Start the HokkienTTS chat UI.  Run from Git Bash:  ./run.sh
# (Windows-compatible: uses the project's omnivoice_env Python.)
cd "$(dirname "$0")" || exit 1

# If an instance is already listening on 7860, stop it first so the port is free.
EXISTING=$(netstat -ano 2>/dev/null | grep "127.0.0.1:7860" | grep LISTENING | awk '{print $NF}' | head -1)
if [ -n "$EXISTING" ]; then
  echo "Stopping existing instance (PID $EXISTING)..."
  taskkill //F //PID "$EXISTING" >/dev/null 2>&1
  sleep 1
fi

export PYTHONUTF8=1
echo "Starting HokkienTTS chat app (loading model + warming up, ~20-30s)..."
omnivoice_env/Scripts/python.exe chat_app.py > chat_app.log 2>&1 &

echo
echo "  Watch startup:  tail -f chat_app.log   (wait for 'Ready')"
echo "  Then open:      http://127.0.0.1:7860"
echo "  Stop it with:   ./stop.sh"

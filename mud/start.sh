#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/mud.pid"
LOG_FILE="$SCRIPT_DIR/mud.log"

# Check for an existing run via PID file
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "MUD is already running (PID $OLD_PID). Use ./stop.sh to stop it first."
        exit 1
    else
        echo "Stale PID file found (PID $OLD_PID is gone). Cleaning up."
        rm -f "$PID_FILE"
    fi
fi

# Also check by process name in case PID file is missing
EXISTING=$(pgrep -f "python.*main\.py" 2>/dev/null || true)
if [ -n "$EXISTING" ]; then
    echo "Warning: found existing MUD process(es) without a PID file: $EXISTING"
    echo "Run ./stop.sh to clean them up, or kill manually."
    exit 1
fi

cd "$SCRIPT_DIR"

# venv/ is gitignored, so build it on a fresh checkout. Also re-install when
# the venv exists but is missing packages (e.g. an earlier install failed).
if [ ! -f venv/bin/activate ]; then
    # PYTHON=... wins. Otherwise take the newest Python 3.10+ we can find,
    # since on macOS plain python3 is often Apple's 3.9 ahead of Homebrew's.
    PY="${PYTHON:-}"
    if [ -z "$PY" ]; then
        for cand in python3.14 python3.13 python3.12 python3.11 python3.10 \
                    /opt/homebrew/bin/python3 /usr/local/bin/python3 python3 python; do
            if command -v "$cand" >/dev/null 2>&1 &&
               "$cand" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
                PY="$cand"
                break
            fi
        done
    fi
    if [ -z "$PY" ] || ! "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
        echo "Error: no Python 3.10 or newer found (python3 is $(python3 --version 2>&1))."
        echo "On macOS: brew install python, then run ./start.sh again."
        echo "To use a specific interpreter: PYTHON=/path/to/python3 ./start.sh"
        exit 1
    fi
    echo "No virtualenv found. Creating venv/ with $("$PY" --version)..."
    "$PY" -m venv venv
fi
if ! venv/bin/python -c "import aiohttp, yaml" 2>/dev/null; then
    echo "Installing requirements into venv/..."
    venv/bin/python -m pip install -r requirements.txt
fi

source venv/bin/activate

echo "Starting MUD server..."
nohup python3 main.py >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "MUD started (PID $(cat $PID_FILE)). Logs: $LOG_FILE"

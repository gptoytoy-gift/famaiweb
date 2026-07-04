#!/bin/bash
cd "/Users/gift_ncp/Documents/Codex/2026-06-22/h/outputs/famai-real-starter"

for port in 8787 8788 8789 8790 8791 8792 8793 8794 8795; do
  pid="$(lsof -tiTCP:$port -sTCP:LISTEN 2>/dev/null)"
  if [ -n "$pid" ]; then
    kill $pid 2>/dev/null
  fi
done

sleep 1
echo "Starting Famai Motor dashboard at http://127.0.0.1:8791"
/usr/bin/python3 server.py 8791

#!/bin/bash
cd "/Users/gift_ncp/Documents/Codex/2026-06-22/h/outputs/famai-real-starter"

echo "Starting Famai Motor dashboard..."
echo ""
echo "Open this link after the server starts:"
echo "http://127.0.0.1:8801/#registration-data"
echo ""
echo "Keep this Terminal window open while using the dashboard."
echo ""

/usr/bin/python3 server.py 8801

echo ""
echo "Dashboard stopped or could not start."
echo "If you see an error above, send a screenshot of this Terminal window."
read -p "Press Enter to close..."

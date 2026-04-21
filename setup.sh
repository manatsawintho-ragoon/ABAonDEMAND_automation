#!/bin/bash
echo "============================================"
echo "  ABA on Demand Automator - Setup (Mac/Linux)"
echo "============================================"

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] ไม่พบ Python 3"
    echo "Mac:   brew install python3"
    echo "Linux: sudo apt install python3 python3-pip"
    exit 1
fi
echo "[1/3] Python 3 พบแล้ว: $(python3 --version)"

# Install Playwright
echo "[2/3] กำลังติดตั้ง Playwright..."
pip3 install playwright --quiet || pip install playwright --quiet
echo "Playwright ติดตั้งแล้ว"

# Install Chromium
echo "[3/3] กำลังดาวน์โหลด Chromium..."
python3 -m playwright install chromium || playwright install chromium
echo "Chromium ติดตั้งแล้ว"

echo ""
echo "============================================"
echo "  Setup เสร็จ!  รัน:  python3 main.py"
echo "============================================"

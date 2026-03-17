#!/bin/bash
cd "$(dirname "$0")"
echo ""
echo " ====================================="
echo "  My Yt Video Downloader v4  —  Lancement"
echo " ====================================="
echo ""
echo " [1/2] Installation des dépendances Python..."
pip3 install customtkinter customtkinter yt-dlp Pillow --quiet --upgrade 2>/dev/null || \
pip  install customtkinter customtkinter yt-dlp Pillow --quiet --upgrade

echo " [2/2] Enregistrement dans les menus système..."
python3 install.py 2>/dev/null || python install.py

echo ""
echo " Lancement de My Yt Video Downloader..."
python3 app.py 2>/dev/null || python app.py
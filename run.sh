#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════
#  My Yt Video Downloader v4  —  Script de lancement automatique
#  • Vérifie / installe Python, pip, ffmpeg, git
#  • Clone ou met à jour le dépôt GitHub
#  • Crée et active un environnement virtuel Python (.venv)
#  • Installe les dépendances Python dans le venv
#  • Intègre l'app dans les menus système
#  • Lance l'application depuis le venv
# ╚══════════════════════════════════════════════════════════════════════════════

REPO_URL="https://github.com/Andry030/MyYtVideoDwn.git"
REPO_DIR="MyYtVideoDwn"
VENV_DIR=".venv"

# ── Couleurs terminal ─────────────────────────────────────────────────────────
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
BOLD="\033[1m"
RESET="\033[0m"

ok()   { echo -e "  ${GREEN}✓${RESET} $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}  $1"; }
err()  { echo -e "  ${RED}✗${RESET}  $1"; exit 1; }
step() { echo -e "\n${BOLD}${CYAN}[$1]${RESET} $2"; }

# ── Bannière ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN} ╔═══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${CYAN} ║   My Yt Video Downloader v4  —  Setup    ║${RESET}"
echo -e "${BOLD}${CYAN} ╚═══════════════════════════════════════════╝${RESET}"
echo ""

# ── Détection de la plateforme ────────────────────────────────────────────────
OS="$(uname -s 2>/dev/null || echo "unknown")"
case "$OS" in
    Linux*)  PLATFORM="linux" ;;
    Darwin*) PLATFORM="macos" ;;
    *)       PLATFORM="unknown" ;;
esac

# ╔══════════════════════════════════════════════════════════════════════════════
#  ÉTAPE 1 — Python 3.9+
# ╚══════════════════════════════════════════════════════════════════════════════
step "1/6" "Vérification de Python 3..."

SYS_PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        VER=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        MAJOR=$(echo "$VER" | cut -d. -f1)
        MINOR=$(echo "$VER" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 9 ]; then
            SYS_PYTHON="$cmd"
            ok "Python $VER trouvé  →  $(command -v $cmd)"
            break
        else
            warn "Python $VER trop ancien (3.9+ requis)..."
        fi
    fi
done

if [ -z "$SYS_PYTHON" ]; then
    warn "Python 3.9+ non trouvé. Tentative d'installation automatique..."
    if [ "$PLATFORM" = "linux" ]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip python3-venv
        elif command -v pacman &>/dev/null; then
            sudo pacman -Sy --noconfirm python python-pip
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y python3 python3-pip
        else
            err "Gestionnaire de paquets non reconnu. Installez Python 3.9+ : https://www.python.org/downloads/"
        fi
    elif [ "$PLATFORM" = "macos" ]; then
        if command -v brew &>/dev/null; then brew install python
        else err "Homebrew non trouvé. Installez Python 3.9+ : https://www.python.org/downloads/"; fi
    else
        err "Installez Python 3.9+ : https://www.python.org/downloads/"
    fi
    for cmd in python3 python; do
        command -v "$cmd" &>/dev/null && SYS_PYTHON="$cmd" && break
    done
    [ -z "$SYS_PYTHON" ] && err "Python introuvable même après installation. Vérifiez le PATH."
    ok "Python installé avec succès."
fi

# ╔══════════════════════════════════════════════════════════════════════════════
#  ÉTAPE 2 — pip + venv (module système)
# ╚══════════════════════════════════════════════════════════════════════════════
step "2/6" "Vérification de pip et du module venv..."

# pip
if ! $SYS_PYTHON -m pip --version &>/dev/null; then
    warn "pip absent. Installation..."
    if [ "$PLATFORM" = "linux" ]; then
        if command -v apt-get &>/dev/null; then sudo apt-get install -y python3-pip
        elif command -v pacman &>/dev/null; then sudo pacman -Sy --noconfirm python-pip
        elif command -v dnf &>/dev/null; then sudo dnf install -y python3-pip
        else $SYS_PYTHON -m ensurepip --upgrade || true; fi
    else
        $SYS_PYTHON -m ensurepip --upgrade || true
    fi
fi
$SYS_PYTHON -m pip --version &>/dev/null && ok "pip disponible." || err "pip introuvable. Voir : https://pip.pypa.io"

# module venv
if ! $SYS_PYTHON -m venv --help &>/dev/null 2>&1; then
    warn "Module venv absent. Installation..."
    if [ "$PLATFORM" = "linux" ] && command -v apt-get &>/dev/null; then
        sudo apt-get install -y python3-venv
    fi
fi
$SYS_PYTHON -m venv --help &>/dev/null 2>&1 && ok "Module venv disponible." || err "Module venv introuvable. Installez python3-venv."

# ╔══════════════════════════════════════════════════════════════════════════════
#  ÉTAPE 3 — ffmpeg
# ╚══════════════════════════════════════════════════════════════════════════════
step "3/6" "Vérification de ffmpeg..."

if command -v ffmpeg &>/dev/null; then
    ok "ffmpeg trouvé  →  $(command -v ffmpeg)"
else
    warn "ffmpeg absent. Tentative d'installation automatique..."
    FFMPEG_OK=false
    if [ "$PLATFORM" = "linux" ]; then
        if command -v apt-get &>/dev/null; then sudo apt-get install -y ffmpeg && FFMPEG_OK=true
        elif command -v pacman &>/dev/null; then sudo pacman -Sy --noconfirm ffmpeg && FFMPEG_OK=true
        elif command -v dnf &>/dev/null; then sudo dnf install -y ffmpeg && FFMPEG_OK=true; fi
    elif [ "$PLATFORM" = "macos" ]; then
        if command -v brew &>/dev/null; then brew install ffmpeg && FFMPEG_OK=true; fi
    fi
    if $FFMPEG_OK; then
        ok "ffmpeg installé avec succès."
    else
        warn "ffmpeg non installé — fusion vidéo/audio et MP3 indisponibles."
        warn "Installez-le manuellement : https://ffmpeg.org/download.html"
    fi
fi

# ╔══════════════════════════════════════════════════════════════════════════════
#  ÉTAPE 4 — Cloner ou mettre à jour le dépôt
# ╚══════════════════════════════════════════════════════════════════════════════
step "4/6" "Récupération du code source..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/app.py" ]; then
    ok "Dépôt déjà présent  →  $SCRIPT_DIR"
    if command -v git &>/dev/null && [ -d "$SCRIPT_DIR/.git" ]; then
        echo "  → Vérification des mises à jour..."
        git -C "$SCRIPT_DIR" pull --quiet \
            && ok "Dépôt à jour." \
            || warn "Mise à jour impossible (pas de réseau ?). Version locale conservée."
    fi
    APP_DIR="$SCRIPT_DIR"
else
    # Installer git si nécessaire
    if ! command -v git &>/dev/null; then
        warn "git absent. Installation..."
        if [ "$PLATFORM" = "linux" ]; then
            if command -v apt-get &>/dev/null; then sudo apt-get install -y git
            elif command -v pacman &>/dev/null; then sudo pacman -Sy --noconfirm git
            elif command -v dnf &>/dev/null; then sudo dnf install -y git
            else err "Impossible d'installer git. Voir : https://git-scm.com/downloads"; fi
        elif [ "$PLATFORM" = "macos" ]; then
            if command -v brew &>/dev/null; then brew install git
            else xcode-select --install 2>/dev/null || true; fi
        fi
        command -v git &>/dev/null || err "git introuvable. Installez-le : https://git-scm.com/downloads"
    fi

    TARGET_DIR="$(pwd)/$REPO_DIR"
    if [ -d "$TARGET_DIR/.git" ]; then
        ok "Dépôt existant trouvé  →  $TARGET_DIR"
        git -C "$TARGET_DIR" pull --quiet \
            && ok "Dépôt mis à jour." \
            || warn "Mise à jour impossible. Version locale conservée."
    else
        echo "  → Clonage depuis $REPO_URL..."
        git clone "$REPO_URL" "$TARGET_DIR"
        ok "Clonage terminé  →  $TARGET_DIR"
    fi
    APP_DIR="$TARGET_DIR"
fi

cd "$APP_DIR"

# ╔══════════════════════════════════════════════════════════════════════════════
#  ÉTAPE 5 — Création / réutilisation du venv
# ╚══════════════════════════════════════════════════════════════════════════════
step "5/6" "Environnement virtuel Python (.venv)..."

VENV_PATH="$APP_DIR/$VENV_DIR"
VENV_PYTHON="$VENV_PATH/bin/python"
VENV_PIP="$VENV_PATH/bin/pip"

if [ -f "$VENV_PYTHON" ]; then
    ok "venv existant réutilisé  →  $VENV_PATH"
else
    echo "  → Création du venv dans $VENV_PATH ..."
    $SYS_PYTHON -m venv "$VENV_PATH"
    ok "venv créé avec succès."
fi

# Mise à jour de pip dans le venv
echo "  → Mise à jour de pip dans le venv..."
"$VENV_PYTHON" -m pip install --upgrade pip --quiet
ok "pip venv à jour  →  $("$VENV_PYTHON" -m pip --version 2>&1 | head -1)"

# ╔══════════════════════════════════════════════════════════════════════════════
#  ÉTAPE 6 — Dépendances + intégration système + lancement
# ╚══════════════════════════════════════════════════════════════════════════════
step "6/6" "Installation des dépendances et intégration système..."

# Passer le chemin du venv python à install.py via variable d'environnement
export YTDLX_VENV_PYTHON="$VENV_PYTHON"
"$VENV_PYTHON" install.py || {
    warn "install.py a rencontré une erreur. Installation pip directe dans le venv..."
    "$VENV_PYTHON" -m pip install --upgrade --quiet customtkinter yt-dlp Pillow
}

# ── Lancement ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN} ╔═══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${GREEN} ║  ✓  Tout est prêt — Lancement en cours…  ║${RESET}"
echo -e "${BOLD}${GREEN} ╚═══════════════════════════════════════════╝${RESET}"
echo ""

"$VENV_PYTHON" app.py
#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════
#  My Yt Video Downloader v4  —  Script de lancement automatique
#  • Vérifie / installe Python, pip, ffmpeg, git
#  • Clone ou met à jour le dépôt GitHub
#  • Installe les dépendances Python
#  • Intègre l'app dans les menus système
#  • Lance l'application
# ╚══════════════════════════════════════════════════════════════════════════════

set -e  # Arrêt immédiat sur erreur non gérée

REPO_URL="https://github.com/Andry030/MyYtVideoDwn.git"
REPO_DIR="MyYtVideoDwn"

# ── Couleurs terminal ─────────────────────────────────────────────────────────
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
BOLD="\033[1m"
RESET="\033[0m"

ok()   { echo -e "  ${GREEN}✓${RESET} $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}  $1"; }
err()  { echo -e "  ${RED}✗${RESET}  $1"; }
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
#  ÉTAPE 1 — Python
# ╚══════════════════════════════════════════════════════════════════════════════
step "1/5" "Vérification de Python 3..."

PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        VER=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        MAJOR=$(echo "$VER" | cut -d. -f1)
        MINOR=$(echo "$VER" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 9 ]; then
            PYTHON="$cmd"
            ok "Python $VER trouvé  →  $(command -v $cmd)"
            break
        else
            warn "Python $VER trop ancien (3.9+ requis), on continue la recherche..."
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    warn "Python 3.9+ non trouvé. Tentative d'installation automatique..."
    if [ "$PLATFORM" = "linux" ]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip python3-venv
        elif command -v pacman &>/dev/null; then
            sudo pacman -Sy --noconfirm python python-pip
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y python3 python3-pip
        else
            err "Gestionnaire de paquets non reconnu."
            err "Installez Python 3.9+ manuellement : https://www.python.org/downloads/"
            exit 1
        fi
    elif [ "$PLATFORM" = "macos" ]; then
        if command -v brew &>/dev/null; then
            brew install python
        else
            err "Homebrew non trouvé."
            err "Installez Python 3.9+ manuellement : https://www.python.org/downloads/"
            exit 1
        fi
    else
        err "Impossible d'installer Python automatiquement sur cette plateforme."
        err "Installez Python 3.9+ : https://www.python.org/downloads/"
        exit 1
    fi
    # Re-détecter après installation
    for cmd in python3 python; do
        command -v "$cmd" &>/dev/null && PYTHON="$cmd" && break
    done
    [ -z "$PYTHON" ] && { err "Python introuvable même après installation. Vérifiez le PATH."; exit 1; }
    ok "Python installé avec succès."
fi

# ╔══════════════════════════════════════════════════════════════════════════════
#  ÉTAPE 2 — pip
# ╚══════════════════════════════════════════════════════════════════════════════
step "2/5" "Vérification de pip..."

if ! $PYTHON -m pip --version &>/dev/null; then
    warn "pip non disponible. Tentative d'installation..."
    if [ "$PLATFORM" = "linux" ]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get install -y python3-pip
        elif command -v pacman &>/dev/null; then
            sudo pacman -Sy --noconfirm python-pip
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y python3-pip
        else
            $PYTHON -m ensurepip --upgrade || true
        fi
    elif [ "$PLATFORM" = "macos" ]; then
        $PYTHON -m ensurepip --upgrade || true
    fi
fi

if $PYTHON -m pip --version &>/dev/null; then
    ok "pip disponible  →  $($PYTHON -m pip --version 2>&1 | head -1)"
else
    err "pip introuvable. Installez-le manuellement : https://pip.pypa.io/en/stable/installation/"
    exit 1
fi

# ╔══════════════════════════════════════════════════════════════════════════════
#  ÉTAPE 3 — ffmpeg
# ╚══════════════════════════════════════════════════════════════════════════════
step "3/5" "Vérification de ffmpeg..."

if command -v ffmpeg &>/dev/null; then
    ok "ffmpeg trouvé  →  $(command -v ffmpeg)"
else
    warn "ffmpeg non trouvé. Tentative d'installation automatique..."
    if [ "$PLATFORM" = "linux" ]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get install -y ffmpeg
        elif command -v pacman &>/dev/null; then
            sudo pacman -Sy --noconfirm ffmpeg
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y ffmpeg
        else
            err "Impossible d'installer ffmpeg automatiquement."
            err "Installez-le manuellement : https://ffmpeg.org/download.html"
            err "L'application se lancera mais la fusion vidéo/audio et le MP3 ne fonctionneront pas."
        fi
    elif [ "$PLATFORM" = "macos" ]; then
        if command -v brew &>/dev/null; then
            brew install ffmpeg
        else
            err "Homebrew non trouvé. Installez ffmpeg manuellement : https://ffmpeg.org/download.html"
            err "L'application se lancera mais la fusion vidéo/audio et le MP3 ne fonctionneront pas."
        fi
    fi
    command -v ffmpeg &>/dev/null && ok "ffmpeg installé avec succès." || warn "ffmpeg absent — certaines fonctions seront limitées."
fi

# ╔══════════════════════════════════════════════════════════════════════════════
#  ÉTAPE 4 — Cloner ou mettre à jour le dépôt
# ╚══════════════════════════════════════════════════════════════════════════════
step "4/5" "Récupération du code source..."

# Si le script est exécuté depuis l'intérieur du dépôt déjà cloné, on reste sur place
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/app.py" ]; then
    ok "Dépôt déjà présent  →  $SCRIPT_DIR"
    # Tenter une mise à jour silencieuse si git est disponible
    if command -v git &>/dev/null && [ -d "$SCRIPT_DIR/.git" ]; then
        echo "  → Vérification des mises à jour..."
        git -C "$SCRIPT_DIR" pull --quiet && ok "Dépôt à jour." || warn "Mise à jour impossible (pas de réseau ?). On continue avec la version locale."
    fi
    APP_DIR="$SCRIPT_DIR"
else
    # Pas dans le dépôt — il faut cloner
    if ! command -v git &>/dev/null; then
        warn "git non trouvé. Tentative d'installation..."
        if [ "$PLATFORM" = "linux" ]; then
            if command -v apt-get &>/dev/null; then sudo apt-get install -y git
            elif command -v pacman &>/dev/null; then sudo pacman -Sy --noconfirm git
            elif command -v dnf &>/dev/null; then sudo dnf install -y git
            else err "Impossible d'installer git. Installez-le manuellement."; exit 1
            fi
        elif [ "$PLATFORM" = "macos" ]; then
            if command -v brew &>/dev/null; then brew install git
            else xcode-select --install 2>/dev/null || true
            fi
        fi
        command -v git &>/dev/null || { err "git introuvable. Installez-le : https://git-scm.com/downloads"; exit 1; }
    fi

    TARGET_DIR="$(pwd)/$REPO_DIR"
    if [ -d "$TARGET_DIR/.git" ]; then
        ok "Dépôt existant trouvé  →  $TARGET_DIR"
        git -C "$TARGET_DIR" pull --quiet && ok "Dépôt mis à jour." || warn "Mise à jour impossible. On continue avec la version locale."
    else
        echo "  → Clonage de $REPO_URL..."
        git clone "$REPO_URL" "$TARGET_DIR"
        ok "Clonage terminé  →  $TARGET_DIR"
    fi
    APP_DIR="$TARGET_DIR"
fi

cd "$APP_DIR"

# ╔══════════════════════════════════════════════════════════════════════════════
#  ÉTAPE 5 — Dépendances Python + intégration système + lancement
# ╚══════════════════════════════════════════════════════════════════════════════
step "5/5" "Installation des dépendances Python et intégration système..."

# install.py gère lui-même les dépendances pip ET les raccourcis/menus
$PYTHON install.py 2>/dev/null || {
    # Fallback : pip direct si install.py échoue
    warn "install.py a rencontré une erreur. Installation pip directe..."
    $PYTHON -m pip install --upgrade --quiet customtkinter yt-dlp Pillow
}

# ── Lancement ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN} ✓ Tout est prêt. Lancement de My Yt Video Downloader...${RESET}"
echo ""

$PYTHON app.py
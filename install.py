#!/usr/bin/env python3
"""
My Yt Video Downloader — Script d'installation système
  1. Crée / réutilise un environnement virtuel Python (.venv)
  2. Installe les dépendances Python dans le venv
  3. Crée les raccourcis/menus selon la plateforme :
       • Linux  -> ~/.local/share/applications/*.desktop + icônes PNG
       • Windows -> Raccourci Démarrer + Bureau
       • macOS  -> Bundle .app dans ~/Applications
"""

import sys
import os
import struct
import zlib
import textwrap
import subprocess
import venv as _venv_mod

# --- Identité de l'app -------------------------------------------------------
APP_NAME    = "My Yt Video Downloader"
APP_ID      = "my-yt-video-downloader"
APP_VERSION = "4.0"
APP_DESC    = "Téléchargeur YouTube — Vidéos, Playlists, Multi-qualité"
APP_COMMENT = "Télécharge des vidéos et playlists YouTube en MP4 ou MP3"
APP_CATS    = "AudioVideo;Video;Network;"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_PY    = os.path.join(SCRIPT_DIR, "app.py")
VENV_DIR   = os.path.join(SCRIPT_DIR, ".venv")

# --- Couleurs icône -----------------------------------------------------------
COL_BG      = (9,   9,  15)
COL_SURFACE = (16,  16,  28)
COL_ACCENT  = (124, 111, 255)
COL_GLOW    = (157, 144, 255)
COL_CYAN    = (0,  212, 255)

# --- Dépendances requises -----------------------------------------------------
REQUIREMENTS = [
    "customtkinter>=5.2.0",
    "yt-dlp>=2024.1.0",
    "Pillow>=9.0.0",
]


# =============================================================================
#  HELPERS — résolution du python du venv
# =============================================================================
def _venv_python():
    if sys.platform == "win32":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")


def _in_venv():
    """
    Retourne True si le script tourne effectivement depuis le venv attendu.
    On teste plusieurs choses pour éviter les faux négatifs (symlinks, sys.prefix, marqueur env).
    """
    try:
        venv_real = os.path.realpath(VENV_DIR)
        exe_real  = os.path.realpath(sys.executable)
        if exe_real.startswith(venv_real):
            return True

        # Parfois l'exécutable est un symlink vers /usr/bin/python, mais sys.prefix
        # pointe correctement vers le venv. Tester sys.prefix aussi.
        prefix_real = os.path.realpath(getattr(sys, "prefix", ""))
        if prefix_real and prefix_real.startswith(venv_real):
            return True

        # Vérifier si on a relancé le script avec notre marqueur d'env.
        env_mark = os.environ.get("YTDLX_VENV_STARTED")
        env_venv_py = os.environ.get("YTDLX_VENV_PYTHON")
        if env_mark == "1":
            # si on a enregistré quel python on a voulu utiliser, comparer les realpaths
            if env_venv_py and os.path.realpath(env_venv_py) == exe_real:
                return True
            # sinon, si l'utilisateur a forcé le marqueur, considérer qu'on est déjà relancé
            return True

    except Exception:
        # En cas d'erreur inattendue, retourner False pour garder le comportement sûr.
        return False

    return False


def create_venv():
    venv_py = _venv_python()

    if _in_venv():
        print(f"  ✓ Venv actif          →  {VENV_DIR}")
        return

    if not os.path.isfile(venv_py):
        print(f"  → Création du venv dans {VENV_DIR} ...")
        _venv_mod.create(VENV_DIR, with_pip=True, clear=False, upgrade_deps=True)
        print(f"  ✓ Venv créé.")
    else:
        print(f"  ✓ Venv existant réutilisé  →  {VENV_DIR}")

    # Si on arrive ici, on a un venv plausible. Relancer depuis le python du venv
    # mais protéger contre une boucle infinie : poser un marqueur d'environnement.
    if os.environ.get("YTDLX_VENV_STARTED") == "1":
        # On avait déjà tenté de relancer mais _in_venv() est toujours False.
        # Éviter de relancer à l'infini : avertir et continuer avec l'interpréteur courant.
        print("  ⚠ Attention : relance depuis le venv tentée précédemment mais non détectée.")
        print(f"    sys.executable = {sys.executable}")
        print(f"    attendu venv python = {venv_py}")
        print("    → Continuer sans relancer pour éviter une boucle infinie.")
        return

    print(f"  → Relancement depuis le venv...")
    env  = os.environ.copy()
    env["YTDLX_VENV_PYTHON"] = venv_py
    env["YTDLX_VENV_STARTED"] = "1"
    args = [venv_py, __file__] + sys.argv[1:]
    try:
        os.execve(venv_py, args, env)
    except FileNotFoundError:
        print("  ✖ Erreur : l'exécutable du venv introuvable au moment du relancement.")
        print(f"    Chemin attendu : {venv_py}")
    except PermissionError:
        print("  ✖ Erreur : permission refusée en essayant d'exécuter le python du venv.")
    except OSError as e:
        print(f"  ✖ Erreur OS lors du execve : {e}")
    # Si execve échoue, on continue (évite boucle infinie).


# =============================================================================
#  ÉTAPE 2 — Installation des dépendances dans le venv
# =============================================================================
def install_dependencies():
    print("── Dépendances Python ──────────────────────────────────────────────")

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip", "--quiet"],
        check=False
    )

    req_file = os.path.join(SCRIPT_DIR, "requirements.txt")
    if os.path.isfile(req_file):
        print(f"  → Installation depuis {req_file}")
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "--quiet",
               "-r", req_file]
    else:
        print(f"  → Installation : {', '.join(REQUIREMENTS)}")
        cmd = ([sys.executable, "-m", "pip", "install", "--upgrade", "--quiet"]
               + REQUIREMENTS)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("  ✓ Dépendances installées avec succès.")
    else:
        print("  ⚠ Avertissement pip :")
        print(result.stderr.strip())
    print()


# =============================================================================
#  GÉNÉRATION ICÔNE PNG (stdlib uniquement)
# =============================================================================
def _make_png(size=256):
    w = h = size
    half = size // 2
    pixels = bytearray(w * h * 4)

    def px(x, y, r, g, b, a=255):
        if 0 <= x < w and 0 <= y < h:
            off = (y * w + x) * 4
            ao  = pixels[off + 3]
            if ao == 0:
                pixels[off:off+4] = [r, g, b, a]
            else:
                fa, ba = a / 255, ao / 255
                na = fa + ba * (1 - fa)
                if na > 0:
                    pixels[off]   = int((r*fa + pixels[off]  *ba*(1-fa)) / na)
                    pixels[off+1] = int((g*fa + pixels[off+1]*ba*(1-fa)) / na)
                    pixels[off+2] = int((b*fa + pixels[off+2]*ba*(1-fa)) / na)
                    pixels[off+3] = int(na * 255)

    radius = size // 6
    cx = cy = half
    for y in range(h):
        for x in range(w):
            rx = max(radius - x, 0, x - (w - 1 - radius))
            ry = max(radius - y, 0, y - (h - 1 - radius))
            if (rx*rx + ry*ry) ** 0.5 <= radius:
                d  = min(((x-cx)**2+(y-cy)**2)**.5 / (half*1.4), 1.0)
                px(x, y,
                   int(COL_BG[0]+(COL_SURFACE[0]-COL_BG[0])*(1-d)),
                   int(COL_BG[1]+(COL_SURFACE[1]-COL_BG[1])*(1-d)),
                   int(COL_BG[2]+(COL_SURFACE[2]-COL_BG[2])*(1-d)))

    halo_r = int(half * 0.72)
    thick  = int(size * 0.022)
    for y in range(h):
        for x in range(w):
            d = ((x-cx)**2+(y-cy)**2)**.5
            if abs(d - halo_r) <= thick:
                alpha = int(255 * (1 - abs(d - halo_r) / (thick + 1)))
                px(x, y, *COL_ACCENT, alpha)

    tri_size = int(half * 0.44)
    tri_x    = int(cx - tri_size * 0.28)
    for y in range(h):
        dy = y - cy
        if abs(dy) > tri_size:
            continue
        ratio   = 1 - abs(dy) / (tri_size + 1)
        x_right = tri_x + int(tri_size * ratio * 1.5)
        for x in range(tri_x, x_right + 1):
            al = 180 if x == tri_x else (120 if x == x_right else 255)
            t  = (x - tri_x) / max(x_right - tri_x, 1)
            px(x, y,
               int(COL_ACCENT[0]+(COL_GLOW[0]-COL_ACCENT[0])*t),
               int(COL_ACCENT[1]+(COL_GLOW[1]-COL_ACCENT[1])*t),
               int(COL_ACCENT[2]+(COL_GLOW[2]-COL_ACCENT[2])*t), al)

    arrow_cx = int(cx + half * 0.28)
    arrow_cy = int(cy + half * 0.52)
    shaft_w  = max(2, size // 40)
    shaft_h  = int(size * 0.13)
    head_w   = int(size * 0.09)
    head_h   = int(size * 0.06)
    for y in range(arrow_cy - shaft_h, arrow_cy):
        for x in range(arrow_cx - shaft_w, arrow_cx + shaft_w + 1):
            px(x, y, *COL_CYAN)
    for dy in range(head_h):
        w2 = int(head_w * dy / head_h)
        for x in range(arrow_cx - w2, arrow_cx + w2 + 1):
            px(x, arrow_cy + dy, *COL_CYAN)

    def _chunk(tag, data):
        c = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", c)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    raw  = bytearray()
    for y in range(h):
        raw.append(0)
        raw.extend(pixels[y*w*4:(y+1)*w*4])
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))


# =============================================================================
#  INSTALLATION LINUX
# =============================================================================
def install_linux():
    python_exe = sys.executable   # .venv/bin/python

    for res, subdir in ((256, "256x256"), (48, "48x48")):
        icon_dir = os.path.expanduser(
            f"~/.local/share/icons/hicolor/{subdir}/apps")
        os.makedirs(icon_dir, exist_ok=True)
        with open(os.path.join(icon_dir, f"{APP_ID}.png"), "wb") as f:
            f.write(_make_png(res))
        print(f"  ✓ Icône {res}px   →  {icon_dir}/{APP_ID}.png")

    desktop_dir  = os.path.expanduser("~/.local/share/applications")
    os.makedirs(desktop_dir, exist_ok=True)
    desktop_path = os.path.join(desktop_dir, f"{APP_ID}.desktop")

    with open(desktop_path, "w") as f:
        f.write(textwrap.dedent(f"""\
            [Desktop Entry]
            Version=1.0
            Type=Application
            Name={APP_NAME}
            GenericName={APP_DESC}
            Comment={APP_COMMENT}
            Exec={python_exe} {MAIN_PY}
            Icon={APP_ID}
            Terminal=false
            Categories={APP_CATS}
            Keywords=youtube;download;video;mp3;mp4;playlist;
            StartupNotify=true
            StartupWMClass=YTDLXPro
        """))
    os.chmod(desktop_path, 0o755)
    print(f"  ✓ Lanceur      →  {desktop_path}")

    for cmd in (
        ["gtk-update-icon-cache", "-f", "-t",
         os.path.expanduser("~/.local/share/icons/hicolor")],
        ["update-desktop-database", desktop_dir],
    ):
        try:
            subprocess.run(cmd, check=False, capture_output=True)
        except FileNotFoundError:
            pass

    for bureau_name in ("Desktop", "Bureau"):
        bureau = os.path.join(os.path.expanduser("~"), bureau_name)
        if os.path.isdir(bureau):
            import shutil
            dest = os.path.join(bureau, f"{APP_ID}.desktop")
            shutil.copy(desktop_path, dest)
            os.chmod(dest, 0o755)
            print(f"  ✓ Bureau       →  {dest}")
            break

    print()
    print(f"  Installation terminée !")
    print(f"  Cherchez «\u00a0{APP_NAME}\u00a0» dans votre menu Applications.")


# =============================================================================
#  INSTALLATION WINDOWS
# =============================================================================
def install_windows():
    python_exe = sys.executable
    ico_path   = os.path.join(SCRIPT_DIR, f"{APP_ID}.ico")
    _make_ico(ico_path)
    print(f"  ✓ Icône ICO    →  {ico_path}")

    start_menu = os.path.join(
        os.environ.get("APPDATA", ""), "Microsoft", "Windows",
        "Start Menu", "Programs")
    os.makedirs(start_menu, exist_ok=True)
    lnk_start   = os.path.join(start_menu, f"{APP_NAME}.lnk")

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if not os.path.isdir(desktop):
        desktop = os.path.join(os.path.expanduser("~"), "Bureau")
    lnk_desktop = (os.path.join(desktop, f"{APP_NAME}.lnk")
                   if os.path.isdir(desktop) else None)

    for lnk in ([lnk_start] + ([lnk_desktop] if lnk_desktop else [])):
        ps = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s  = $ws.CreateShortcut("{lnk}"); '
            f'$s.TargetPath       = "{python_exe}"; '
            f'$s.Arguments        = \'"{MAIN_PY}"\'; '
            f'$s.WorkingDirectory = "{SCRIPT_DIR}"; '
            f'$s.IconLocation     = "{ico_path}"; '
            f'$s.Description      = "{APP_DESC}"; '
            f'$s.Save()'
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       check=True, capture_output=True)
        label = "Démarrer" if lnk == lnk_start else "Bureau"
        print(f"  ✓ Raccourci {label}  →  {lnk}")

    print()
    print(f"  Installation terminée !")
    print(f"  Cherchez «\u00a0{APP_NAME}\u00a0» dans le menu Démarrer.")


def _make_ico(path):
    sizes = [16, 32, 48, 256]
    pngs  = [_make_png(s) for s in sizes]
    n     = len(sizes)
    data_offset = 6 + n * 16
    dirs = bytearray()
    datas = bytearray()
    for s, png in zip(sizes, pngs):
        sz = s if s < 256 else 0
        dirs  += struct.pack("<BBBBHHII", sz, sz, 0, 0, 1, 32,
                             len(png), data_offset + len(datas))
        datas += png
    with open(path, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, n) + bytes(dirs) + bytes(datas))


# =============================================================================
#  INSTALLATION macOS
# =============================================================================
def install_macos():
    python_exe = sys.executable
    apps_dir   = os.path.expanduser("~/Applications")
    os.makedirs(apps_dir, exist_ok=True)
    app_bundle = os.path.join(apps_dir, f"{APP_NAME}.app")

    contents  = os.path.join(app_bundle, "Contents")
    macos_dir = os.path.join(contents, "MacOS")
    res_dir   = os.path.join(contents, "Resources")
    os.makedirs(macos_dir, exist_ok=True)
    os.makedirs(res_dir, exist_ok=True)

    png256    = _make_png(256)
    icns_path = os.path.join(res_dir, f"{APP_ID}.icns")
    tag       = b"ic08"
    body      = tag + struct.pack(">I", 8 + len(png256)) + png256
    with open(icns_path, "wb") as f:
        f.write(b"icns" + struct.pack(">I", 8 + len(body)) + body)
    print(f"  ✓ Icône ICNS   →  {icns_path}")

    launcher = os.path.join(macos_dir, APP_NAME.replace(" ", ""))
    with open(launcher, "w") as f:
        f.write(textwrap.dedent(f"""\
            #!/bin/bash
            cd "{SCRIPT_DIR}"
            "{python_exe}" "{MAIN_PY}"
        """))
    os.chmod(launcher, 0o755)
    print(f"  ✓ Lanceur      →  {launcher}")

    with open(os.path.join(contents, "Info.plist"), "w") as f:
        f.write(textwrap.dedent(f"""\
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
              "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0">
            <dict>
                <key>CFBundleName</key>             <string>{APP_NAME}</string>
                <key>CFBundleDisplayName</key>      <string>{APP_NAME}</string>
                <key>CFBundleIdentifier</key>       <string>com.ytdlxpro.app</string>
                <key>CFBundleVersion</key>          <string>{APP_VERSION}</string>
                <key>CFBundleExecutable</key>       <string>{APP_NAME.replace(' ','')}</string>
                <key>CFBundleIconFile</key>         <string>{APP_ID}</string>
                <key>NSHighResolutionCapable</key>  <true/>
                <key>CFBundlePackageType</key>      <string>APPL</string>
            </dict>
            </plist>
        """))
    print(f"  ✓ Bundle .app  →  {app_bundle}")
    print()
    print(f"  Installation terminée !")
    print(f"  Ouvrez ~/Applications et double-cliquez sur «\u00a0{APP_NAME}.app\u00a0».")


# =============================================================================
#  DÉSINSTALLATION
# =============================================================================
def uninstall():
    import shutil
    removed = 0
    targets = []

    if sys.platform == "linux":
        targets = [
            os.path.expanduser(
                f"~/.local/share/applications/{APP_ID}.desktop"),
            os.path.expanduser(
                f"~/.local/share/icons/hicolor/256x256/apps/{APP_ID}.png"),
            os.path.expanduser(
                f"~/.local/share/icons/hicolor/48x48/apps/{APP_ID}.png"),
        ]
        for b in ("Desktop", "Bureau"):
            targets.append(os.path.join(
                os.path.expanduser("~"), b, f"{APP_ID}.desktop"))

    elif sys.platform == "win32":
        start_menu = os.path.join(
            os.environ.get("APPDATA", ""), "Microsoft", "Windows",
            "Start Menu", "Programs", f"{APP_NAME}.lnk")
        targets = [
            start_menu,
            os.path.join(os.path.expanduser("~"), "Desktop",
                         f"{APP_NAME}.lnk"),
            os.path.join(SCRIPT_DIR, f"{APP_ID}.ico"),
        ]

    elif sys.platform == "darwin":
        bundle = os.path.expanduser(f"~/Applications/{APP_NAME}.app")
        if os.path.isdir(bundle):
            shutil.rmtree(bundle)
            print(f"  ✓ Supprimé : {bundle}")
            removed += 1

    for t in targets:
        if os.path.exists(t):
            os.remove(t)
            print(f"  ✓ Supprimé : {t}")
            removed += 1

    # Proposer de supprimer le venv
    if os.path.isdir(VENV_DIR):
        try:
            answer = input(
                f"\n  Supprimer aussi le venv ({VENV_DIR}) ? [o/N] "
            ).strip().lower()
        except EOFError:
            answer = "n"
        if answer in ("o", "oui", "y", "yes"):
            shutil.rmtree(VENV_DIR)
            print(f"  ✓ Venv supprimé : {VENV_DIR}")
            removed += 1

    if removed == 0:
        print("  Aucun fichier d'installation trouvé.")
    else:
        print(f"\n  Désinstallation terminée ({removed} élément(s) supprimé(s)).")


# =============================================================================
#  MAIN
# =============================================================================
def main():
    if not os.path.isfile(MAIN_PY):
        print(f"\n  ERREUR : {MAIN_PY} introuvable.")
        print("  Placez install.py dans le même dossier que app.py.")
        sys.exit(1)

    args = sys.argv[1:]

    if "--uninstall" in args or "-u" in args:
        print(f"\n── Désinstallation de {APP_NAME} ──────────────────────────────")
        uninstall()
        return

    print(f"\n── Installation de {APP_NAME} v{APP_VERSION} ─────────────────────")
    print(f"   Script principal : {MAIN_PY}")
    print(f"   Python courant   : {sys.executable}")
    print()

    # 1 — Venv (peut faire os.execve et relancer le script)
    print("── Environnement virtuel (.venv) ───────────────────────────────────")
    create_venv()
    print()

    # 2 — Dépendances dans le venv
    install_dependencies()

    # 3 — Intégration système
    print("── Intégration système ─────────────────────────────────────────────")
    if sys.platform == "linux":
        install_linux()
    elif sys.platform == "win32":
        install_windows()
    elif sys.platform == "darwin":
        install_macos()
    else:
        print(f"  Plateforme non reconnue : {sys.platform}")
        print("  Lancez l'app manuellement : .venv/bin/python app.py")


if __name__ == "__main__":
    main()
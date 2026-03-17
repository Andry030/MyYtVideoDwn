#!/usr/bin/env python3
"""
My Yt Video Downloader — Script d'installation système
Crée les raccourcis/menus selon la plateforme :
  • Linux  → ~/.local/share/applications/My Yt Video Downloader.desktop + icône PNG
  • Windows → Raccourci dans Démarrer > Programmes + Bureau (optionnel)
  • macOS  → Bundle .app dans ~/Applications
"""

import sys
import os
import struct
import zlib
import textwrap
import subprocess

# ─── Palette identique à l'app ───────────────────────────────────────────────
APP_NAME    = "My Yt Video Downloader"
APP_ID      = "my-yt-video-downloader"
APP_VERSION = "4.0"
APP_DESC    = "Téléchargeur YouTube — Vidéos, Playlists, Multi-qualité"
APP_COMMENT = "Télécharge des vidéos et playlists YouTube en MP4 ou MP3"
APP_CATS    = "AudioVideo;Video;Network;"

# Chemin absolu du script principal (résolu depuis l'emplacement de install.py)
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
MAIN_PY     = os.path.join(SCRIPT_DIR, "app.py")

# ─── Couleurs icône (reprend la palette C de l'app) ──────────────────────────
COL_BG      = (9,   9,  15)    # #09090f
COL_SURFACE = (16,  16,  28)   # #10101c
COL_ACCENT  = (124, 111, 255)  # #7c6fff
COL_GLOW    = (157, 144, 255)  # #9d90ff
COL_CYAN    = (0,  212, 255)   # #00d4ff
COL_WHITE   = (234, 234, 248)  # #eaeaf8


# ╔══════════════════════════════════════════════════════════════════════════════
#  GÉNÉRATION DE L'ICÔNE PNG (pur Python, sans dépendance externe)
# ╚══════════════════════════════════════════════════════════════════════════════
def _make_png(size=256) -> bytes:
    """
    Génère un PNG carré de `size`x`size` représentant le logo YT-DLX Pro :
    fond sombre arrondi, triangle "play" violet, flèche de téléchargement.
    Entièrement en Python stdlib (struct + zlib).
    """
    w = h = size
    half = size // 2

    # Image RGBA initialisée à transparent
    pixels = bytearray(w * h * 4)

    def px(x, y, r, g, b, a=255):
        if 0 <= x < w and 0 <= y < h:
            off = (y * w + x) * 4
            # alpha-blend sur fond transparent
            ao = pixels[off + 3]
            if ao == 0:
                pixels[off:off+4] = [r, g, b, a]
            else:
                fa = a / 255
                ba = ao / 255
                na = fa + ba * (1 - fa)
                if na > 0:
                    pixels[off]   = int((r * fa + pixels[off]   * ba * (1-fa)) / na)
                    pixels[off+1] = int((g * fa + pixels[off+1] * ba * (1-fa)) / na)
                    pixels[off+2] = int((b * fa + pixels[off+2] * ba * (1-fa)) / na)
                    pixels[off+3] = int(na * 255)

    # ── Fond arrondi ──────────────────────────────────────────────────────────
    radius = size // 6
    cx = cy = half
    for y in range(h):
        for x in range(w):
            # Coins arrondis via distance aux 4 coins d'un rectangle intérieur
            rx = max(radius - x, 0, x - (w - 1 - radius))
            ry = max(radius - y, 0, y - (h - 1 - radius))
            dist = (rx*rx + ry*ry) ** 0.5
            if dist <= radius:
                # Fond principal : dégradé radial léger
                d = ((x - cx)**2 + (y - cy)**2) ** 0.5 / (half * 1.4)
                d = min(d, 1.0)
                r = int(COL_BG[0] + (COL_SURFACE[0] - COL_BG[0]) * (1 - d))
                g = int(COL_BG[1] + (COL_SURFACE[1] - COL_BG[1]) * (1 - d))
                b = int(COL_BG[2] + (COL_SURFACE[2] - COL_BG[2]) * (1 - d))
                px(x, y, r, g, b)

    # ── Cercle accent (halo) ──────────────────────────────────────────────────
    halo_r = int(half * 0.72)
    for y in range(h):
        for x in range(w):
            d = ((x - cx)**2 + (y - cy)**2) ** 0.5
            thick = int(size * 0.022)
            if abs(d - halo_r) <= thick:
                alpha = int(255 * (1 - abs(d - halo_r) / (thick + 1)))
                px(x, y, *COL_ACCENT, alpha)

    # ── Triangle "play" ────────────────────────────────────────────────────────
    tri_size = int(half * 0.44)
    tri_x    = int(cx - tri_size * 0.28)   # légèrement à droite du centre
    for row in range(-tri_size, tri_size + 1):
        width = abs(row) * 0  # sera calculé
    # Triangle par rasterisation directe
    for y in range(h):
        dy = y - cy
        if abs(dy) > tri_size: continue
        ratio = 1 - abs(dy) / (tri_size + 1)
        x_left  = tri_x
        x_right = tri_x + int(tri_size * ratio * 1.5)
        for x in range(x_left, x_right + 1):
            # anti-aliasing bord gauche / droit
            al = 255
            if x == x_left:
                al = 180
            elif x == x_right:
                al = 120
            # dégradé accent → glow
            t = (x - x_left) / max(x_right - x_left, 1)
            r = int(COL_ACCENT[0] + (COL_GLOW[0] - COL_ACCENT[0]) * t)
            g = int(COL_ACCENT[1] + (COL_GLOW[1] - COL_ACCENT[1]) * t)
            b = int(COL_ACCENT[2] + (COL_GLOW[2] - COL_ACCENT[2]) * t)
            px(x, y, r, g, b, al)

    # ── Flèche ↓ (téléchargement) en bas à droite ─────────────────────────────
    arrow_cx = int(cx + half * 0.28)
    arrow_cy = int(cy + half * 0.52)
    shaft_w  = max(2, size // 40)
    shaft_h  = int(size * 0.13)
    head_w   = int(size * 0.09)
    head_h   = int(size * 0.06)
    # Tige
    for y in range(arrow_cy - shaft_h, arrow_cy):
        for x in range(arrow_cx - shaft_w, arrow_cx + shaft_w + 1):
            px(x, y, *COL_CYAN)
    # Tête de flèche (triangle)
    for dy in range(head_h):
        ratio = dy / head_h
        w2 = int(head_w * ratio)
        for x in range(arrow_cx - w2, arrow_cx + w2 + 1):
            px(x, arrow_cy + dy, *COL_CYAN)

    # ── Encoder en PNG ────────────────────────────────────────────────────────
    def _chunk(tag: bytes, data: bytes) -> bytes:
        c = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", c)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)   # RGB (on va mettre RGBA)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)   # 6 = RGBA

    raw_rows = bytearray()
    for y in range(h):
        raw_rows.append(0)   # filter byte
        raw_rows.extend(pixels[y*w*4:(y+1)*w*4])

    compressed = zlib.compress(bytes(raw_rows), 9)

    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", ihdr)
           + _chunk(b"IDAT", compressed)
           + _chunk(b"IEND", b""))
    return png


# ╔══════════════════════════════════════════════════════════════════════════════
#  INSTALLATION LINUX
# ╚══════════════════════════════════════════════════════════════════════════════
def install_linux():
    python_exe = sys.executable

    # ── Icône ─────────────────────────────────────────────────────────────────
    icon_dir = os.path.expanduser("~/.local/share/icons/hicolor/256x256/apps")
    os.makedirs(icon_dir, exist_ok=True)
    icon_path = os.path.join(icon_dir, f"{APP_ID}.png")
    with open(icon_path, "wb") as f:
        f.write(_make_png(256))
    print(f"  ✓ Icône        → {icon_path}")

    # Icône 48px pour les menus plus petits
    icon_dir48 = os.path.expanduser("~/.local/share/icons/hicolor/48x48/apps")
    os.makedirs(icon_dir48, exist_ok=True)
    with open(os.path.join(icon_dir48, f"{APP_ID}.png"), "wb") as f:
        f.write(_make_png(48))

    # ── Fichier .desktop ──────────────────────────────────────────────────────
    desktop_dir = os.path.expanduser("~/.local/share/applications")
    os.makedirs(desktop_dir, exist_ok=True)
    desktop_path = os.path.join(desktop_dir, f"{APP_ID}.desktop")

    desktop_content = textwrap.dedent(f"""\
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
    """)

    with open(desktop_path, "w") as f:
        f.write(desktop_content)
    os.chmod(desktop_path, 0o755)
    print(f"  ✓ Lanceur      → {desktop_path}")

    # ── Mise à jour du cache d'icônes ─────────────────────────────────────────
    try:
        subprocess.run(
            ["gtk-update-icon-cache", "-f", "-t",
             os.path.expanduser("~/.local/share/icons/hicolor")],
            check=False, capture_output=True
        )
    except FileNotFoundError:
        pass   # gtk-update-icon-cache pas disponible, pas grave

    # ── Mise à jour de la base .desktop (xdg) ─────────────────────────────────
    try:
        subprocess.run(
            ["update-desktop-database", desktop_dir],
            check=False, capture_output=True
        )
    except FileNotFoundError:
        pass

    # ── Raccourci sur le Bureau (si ~/Desktop ou ~/Bureau existe) ─────────────
    for bureau_name in ("Desktop", "Bureau"):
        bureau = os.path.join(os.path.expanduser("~"), bureau_name)
        if os.path.isdir(bureau):
            dest = os.path.join(bureau, f"{APP_ID}.desktop")
            import shutil
            shutil.copy(desktop_path, dest)
            os.chmod(dest, 0o755)
            print(f"  ✓ Bureau       → {dest}")
            break

    print()
    print(f"  Installation terminée !")
    print(f"  Cherchez « {APP_NAME} » dans votre menu Applications.")


# ╔══════════════════════════════════════════════════════════════════════════════
#  INSTALLATION WINDOWS
# ╚══════════════════════════════════════════════════════════════════════════════
def install_windows():
    python_exe = sys.executable

    # Générer l'icône .ico (multi-résolution : 16, 32, 48, 256)
    ico_path = os.path.join(SCRIPT_DIR, f"{APP_ID}.ico")
    _make_ico(ico_path)
    print(f"  ✓ Icône ICO    → {ico_path}")

    # Chemins cibles
    start_menu = os.path.join(
        os.environ.get("APPDATA",""), "Microsoft","Windows",
        "Start Menu","Programs"
    )
    os.makedirs(start_menu, exist_ok=True)
    lnk_start  = os.path.join(start_menu, f"{APP_NAME}.lnk")

    desktop    = os.path.join(os.path.expanduser("~"), "Desktop")
    if not os.path.isdir(desktop):
        desktop = os.path.join(os.path.expanduser("~"), "Bureau")
    lnk_desktop = os.path.join(desktop, f"{APP_NAME}.lnk") if os.path.isdir(desktop) else None

    # Créer les raccourcis via PowerShell (pas besoin de pywin32)
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
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            check=True, capture_output=True
        )
        label = "Démarrer" if lnk == lnk_start else "Bureau"
        print(f"  ✓ Raccourci {label} → {lnk}")

    print()
    print(f"  Installation terminée !")
    print(f"  Cherchez « {APP_NAME} » dans le menu Démarrer.")


def _make_ico(path: str):
    """Génère un fichier .ico multi-résolution (16, 32, 48, 256)."""
    sizes = [16, 32, 48, 256]
    pngs  = [_make_png(s) for s in sizes]

    # Format ICO : header + répertoire + données PNG
    n = len(sizes)
    header = struct.pack("<HHH", 0, 1, n)  # reserved, type=1(ICO), count
    dir_size   = n * 16
    data_offset = 6 + dir_size

    dirs  = bytearray()
    datas = bytearray()
    for s, png in zip(sizes, pngs):
        sz = s if s < 256 else 0   # 0 = 256 dans le format ICO
        dirs  += struct.pack("<BBBBHHII",
                             sz, sz, 0, 0, 1, 32,
                             len(png), data_offset + len(datas))
        datas += png

    with open(path, "wb") as f:
        f.write(header + bytes(dirs) + bytes(datas))


# ╔══════════════════════════════════════════════════════════════════════════════
#  INSTALLATION macOS
# ╚══════════════════════════════════════════════════════════════════════════════
def install_macos():
    python_exe = sys.executable
    apps_dir   = os.path.expanduser("~/Applications")
    os.makedirs(apps_dir, exist_ok=True)
    app_bundle = os.path.join(apps_dir, f"{APP_NAME}.app")

    # Structure du bundle
    contents   = os.path.join(app_bundle, "Contents")
    macos_dir  = os.path.join(contents, "MacOS")
    res_dir    = os.path.join(contents, "Resources")
    os.makedirs(macos_dir, exist_ok=True)
    os.makedirs(res_dir,   exist_ok=True)

    # ── Icône ICNS (encapsule un PNG 256px) ────────────────────────────────
    png256 = _make_png(256)
    icns_path = os.path.join(res_dir, f"{APP_ID}.icns")
    # Format ICNS minimal : magic + taille + tag ic08 (256×256 PNG)
    tag  = b"ic08"
    body = tag + struct.pack(">I", 8 + len(png256)) + png256
    icns = b"icns" + struct.pack(">I", 8 + len(body)) + body
    with open(icns_path, "wb") as f:
        f.write(icns)
    print(f"  ✓ Icône ICNS   → {icns_path}")

    # ── Script lanceur shell ───────────────────────────────────────────────
    launcher = os.path.join(macos_dir, APP_NAME.replace(" ",""))
    with open(launcher, "w") as f:
        f.write(textwrap.dedent(f"""\
            #!/bin/bash
            cd "{SCRIPT_DIR}"
            "{python_exe}" "{MAIN_PY}"
        """))
    os.chmod(launcher, 0o755)
    print(f"  ✓ Lanceur      → {launcher}")

    # ── Info.plist ─────────────────────────────────────────────────────────
    plist = textwrap.dedent(f"""\
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
    """)
    with open(os.path.join(contents, "Info.plist"), "w") as f:
        f.write(plist)
    print(f"  ✓ Bundle .app  → {app_bundle}")

    print()
    print(f"  Installation terminée !")
    print(f"  Ouvrez ~/Applications et double-cliquez sur « {APP_NAME}.app ».")


# ╔══════════════════════════════════════════════════════════════════════════════
#  DÉSINSTALLATION
# ╚══════════════════════════════════════════════════════════════════════════════
def uninstall():
    removed = 0
    targets = []

    if sys.platform == "linux":
        targets = [
            os.path.expanduser(f"~/.local/share/applications/{APP_ID}.desktop"),
            os.path.expanduser(f"~/.local/share/icons/hicolor/256x256/apps/{APP_ID}.png"),
            os.path.expanduser(f"~/.local/share/icons/hicolor/48x48/apps/{APP_ID}.png"),
        ]
        for bureau_name in ("Desktop", "Bureau"):
            targets.append(os.path.join(os.path.expanduser("~"), bureau_name, f"{APP_ID}.desktop"))

    elif sys.platform == "win32":
        start_menu = os.path.join(
            os.environ.get("APPDATA",""), "Microsoft","Windows",
            "Start Menu","Programs", f"{APP_NAME}.lnk"
        )
        desktop = os.path.join(os.path.expanduser("~"), "Desktop", f"{APP_NAME}.lnk")
        targets = [start_menu, desktop, os.path.join(SCRIPT_DIR, f"{APP_ID}.ico")]

    elif sys.platform == "darwin":
        import shutil
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

    if removed == 0:
        print("  Aucun fichier d'installation trouvé.")
    else:
        print(f"\n  Désinstallation terminée ({removed} fichier(s) supprimé(s)).")


# ╔══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ╚══════════════════════════════════════════════════════════════════════════════
def main():
    # Vérification que ytdlx_pro.py existe
    if not os.path.isfile(MAIN_PY):
        print(f"\n  ERREUR : {MAIN_PY} introuvable.")
        print("  Placez install.py dans le même dossier que app.py.")
        sys.exit(1)

    # Lire les arguments
    args = sys.argv[1:]
    if "--uninstall" in args or "-u" in args:
        print(f"\n── Désinstallation de {APP_NAME} ──────────────────────────────")
        uninstall()
        return

    print(f"\n── Installation de {APP_NAME} v{APP_VERSION} ─────────────────────")
    print(f"   Script principal : {MAIN_PY}")
    print(f"   Python           : {sys.executable}")
    print()

    if sys.platform == "linux":
        install_linux()
    elif sys.platform == "win32":
        install_windows()
    elif sys.platform == "darwin":
        install_macos()
    else:
        print(f"  Plateforme non reconnue : {sys.platform}")
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
YT-DLX Pro v4  —  Téléchargeur YouTube  +  Historique persistant
Dépendances : pip install customtkinter yt-dlp Pillow
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import yt_dlp
import threading, os, subprocess, sys, time, io, re, json, uuid
from datetime import datetime
import urllib.request

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ─── Palette ─────────────────────────────────────────────────────────────────
C = dict(
    bg="#09090f",     surface="#10101c",  card="#181828",    card2="#1e1e32",
    border="#28284a", border2="#353560",
    accent="#7c6fff", accent_dim="#5a4fcc", accent_glow="#9d90ff",
    cyan="#00d4ff",   green="#00e676",    green_dim="#00b060",
    red="#ff3d71",    yellow="#ffe600",   orange="#ff8c00",
    text="#eaeaf8",   text2="#c0c0e0",    dim="#5a5a8a",     dim2="#404070",
    thumb_bg="#1a1a30",
)

# ─── Qualités ─────────────────────────────────────────────────────────────────
QUALITIES = [
    ("Meilleure",  "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",                False),
    ("4K (2160p)", "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160]",  False),
    ("1440p (2K)", "bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/best[height<=1440]",  False),
    ("1080p HD",   "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]",  False),
    ("720p",       "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",    False),
    ("480p",       "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]",    False),
    ("360p",       "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]",    False),
    ("MP3 Audio",  "bestaudio/best",                                                            True),
]
Q_NAMES = [q[0] for q in QUALITIES]

THUMB_W, THUMB_H = 142, 80

# ─── Utilitaires ──────────────────────────────────────────────────────────────
_ANSI = re.compile(r'\x1b\[[0-9;]*[mGKHF]')
def strip_ansi(s): return _ANSI.sub("", s).strip() if s else ""

def fmt_bytes(b):
    if b is None or b == 0: return ""
    for u in ("o","Ko","Mo","Go"):
        if abs(b) < 1024: return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} To"

def _find_vlc():
    if sys.platform == "win32":
        for p in (r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                  r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"):
            if os.path.exists(p): return p
    elif sys.platform == "darwin":
        p = "/Applications/VLC.app/Contents/MacOS/VLC"
        if os.path.exists(p): return p
    else:
        for c in ("vlc","vlc-wrapper"):
            try:
                r = subprocess.run(["which",c], capture_output=True, text=True, timeout=2)
                if r.returncode == 0: return r.stdout.strip()
            except Exception: pass
    return None

VLC_PATH = _find_vlc()

def _open_with_vlc(path):
    if not VLC_PATH: return False
    try:
        subprocess.Popen([VLC_PATH, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception: return False

def _xopen(path):
    try:
        if sys.platform == "win32":    os.startfile(path)
        elif sys.platform == "darwin": subprocess.Popen(["open", path])
        else: subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception: pass

def _best_thumb(info):
    if not info: return None
    t = info.get("thumbnail")
    if t: return t
    thumbs = info.get("thumbnails") or []
    ranked = sorted([th for th in thumbs if th.get("url")],
                    key=lambda x: x.get("width") or 0, reverse=True)
    return ranked[0]["url"] if ranked else None

class DownloadCancelled(Exception): pass


# ╔══════════════════════════════════════════════════════════════════════════════
#  GESTIONNAIRE D'HISTORIQUE  (JSON persistant)
# ╚══════════════════════════════════════════════════════════════════════════════
class HistoryManager:
    """Charge / sauvegarde l'historique dans ~/.ytdlx_pro/history.json"""

    FILE = os.path.join(os.path.expanduser("~"), ".ytdlx_pro", "history.json")

    def __init__(self):
        os.makedirs(os.path.dirname(self.FILE), exist_ok=True)
        self._entries: list[dict] = []
        self._load()

    def _load(self):
        try:
            with open(self.FILE, "r", encoding="utf-8") as f:
                self._entries = json.load(f)
        except Exception:
            self._entries = []

    def _save(self):
        try:
            with open(self.FILE, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, ensure_ascii=False, indent=2)
        except Exception: pass

    def add(self, title, url, thumb_url, quality, filepath, size_bytes=None) -> dict:
        entry = {
            "id":         str(uuid.uuid4()),
            "title":      title,
            "url":        url,
            "thumb_url":  thumb_url or "",
            "quality":    quality,
            "filepath":   filepath or "",
            "date":       datetime.now().strftime("%d/%m/%Y  %H:%M"),
            "size_bytes": size_bytes or 0,
        }
        self._entries.insert(0, entry)
        self._save()
        return entry

    def delete(self, entry_id: str):
        self._entries = [e for e in self._entries if e["id"] != entry_id]
        self._save()

    def clear(self):
        self._entries.clear()
        self._save()

    def search(self, query: str) -> list[dict]:
        q = query.lower().strip()
        if not q: return list(self._entries)
        return [e for e in self._entries if q in e["title"].lower() or q in e["url"].lower()]

    @property
    def entries(self): return list(self._entries)
    def __len__(self): return len(self._entries)


# ╔══════════════════════════════════════════════════════════════════════════════
#  LIGNE D'HISTORIQUE
# ╚══════════════════════════════════════════════════════════════════════════════
class HistoryRow(ctk.CTkFrame):

    def __init__(self, parent, entry: dict, on_delete, on_redownload, **kw):
        super().__init__(parent, fg_color=C["card"], corner_radius=9,
                         border_width=1, border_color=C["border"], **kw)
        self.entry       = entry
        self.on_delete   = on_delete
        self.on_redownload = on_redownload
        self._thumb_ref  = None
        self._build()
        if entry.get("thumb_url") and HAS_PIL:
            threading.Thread(target=self._load_thumb, daemon=True).start()

    def _build(self):
        self.columnconfigure(1, weight=1)

        tf = ctk.CTkFrame(self, fg_color=C["thumb_bg"], corner_radius=6,
                          width=THUMB_W, height=THUMB_H)
        tf.grid(row=0, column=0, rowspan=2, padx=(10,8), pady=8, sticky="n")
        tf.grid_propagate(False)
        self._thumb_lbl = ctk.CTkLabel(tf, text="▶", font=("Segoe UI",28),
                                        text_color=C["dim2"],
                                        width=THUMB_W, height=THUMB_H)
        self._thumb_lbl.place(relx=0.5, rely=0.5, anchor="center")

        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.grid(row=0, column=1, sticky="ew", padx=(0,8), pady=(8,2))
        mid.columnconfigure(0, weight=1)

        short = (self.entry["title"][:74]+"…") if len(self.entry["title"])>74 else self.entry["title"]
        ctk.CTkLabel(mid, text=short, font=("Segoe UI",12,"bold"),
                     text_color=C["text"], anchor="w",
        ).grid(row=0, column=0, sticky="ew")

        fp = self.entry.get("filepath","")
        exists = os.path.exists(fp) if fp else False
        sz  = fmt_bytes(self.entry.get("size_bytes") or 0)
        meta_parts = [self.entry.get("date",""), self.entry.get("quality","")]
        if sz: meta_parts.append(sz)

        file_color = C["green"] if exists else C["dim"]
        file_icon  = "●" if exists else "○"
        meta_str   = "  •  ".join(p for p in meta_parts if p)

        meta_row = ctk.CTkFrame(mid, fg_color="transparent")
        meta_row.grid(row=1, column=0, sticky="ew", pady=(2,0))

        ctk.CTkLabel(meta_row, text=file_icon, font=("Segoe UI",11),
                     text_color=file_color, width=14,
        ).pack(side="left")
        ctk.CTkLabel(meta_row, text=meta_str, font=("Segoe UI",10),
                     text_color=C["dim"],
        ).pack(side="left", padx=(4,0))

        bb = ctk.CTkFrame(self, fg_color="transparent")
        bb.grid(row=0, column=2, rowspan=2, padx=(0,10), pady=8, sticky="n")

        def mk(txt, cmd, tc=C["text2"], w=52):
            return ctk.CTkButton(
                bb, text=txt, width=w, height=28,
                font=("Segoe UI",10,"bold"),
                fg_color=C["card2"], hover_color=C["border2"],
                text_color=tc, corner_radius=7, command=cmd,
            )

        mk("↓ Retéléch.", lambda: self.on_redownload(self.entry),
           tc=C["accent_glow"], w=90).pack(pady=(0,4))

        btn_row = ctk.CTkFrame(bb, fg_color="transparent")
        btn_row.pack()

        btn_open = mk("▶", lambda: _xopen(fp) if exists else None, tc=C["cyan"], w=34)
        btn_open.pack(side="left", padx=(0,3))
        if not exists: btn_open.configure(state="disabled")

        folder = os.path.dirname(fp) if fp else ""
        folder_ok = os.path.isdir(folder)
        btn_dir = mk("Dir", lambda: _xopen(folder) if folder_ok else None, tc=C["text2"], w=38)
        btn_dir.pack(side="left", padx=(0,3))
        if not folder_ok: btn_dir.configure(state="disabled")

        mk("✕", lambda: self.on_delete(self.entry["id"]), tc=C["red"], w=30).pack(side="left")

    def _load_thumb(self):
        try:
            req = urllib.request.Request(self.entry["thumb_url"],
                                         headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = r.read()
            img = Image.open(io.BytesIO(data)).resize((THUMB_W,THUMB_H), Image.LANCZOS)
            cimg = ctk.CTkImage(img, size=(THUMB_W,THUMB_H))
            self.after(0, lambda: self._apply_thumb(cimg))
        except Exception: pass

    def _apply_thumb(self, img):
        self._thumb_ref = img
        self._thumb_lbl.configure(image=img, text="")


# ╔══════════════════════════════════════════════════════════════════════════════
#  PANNEAU HISTORIQUE
# ╚══════════════════════════════════════════════════════════════════════════════
class HistoryPanel(ctk.CTkFrame):

    def __init__(self, parent, history: HistoryManager, on_redownload, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self._hist        = history
        self._on_redl     = on_redownload
        self._rows: list[HistoryRow] = []
        self._search_var  = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._render())
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(6,4))
        top.grid_columnconfigure(0, weight=1)

        srch = ctk.CTkEntry(
            top, textvariable=self._search_var,
            placeholder_text="🔍  Rechercher dans l'historique...",
            font=("Segoe UI",11), height=34,
            fg_color=C["card"], border_color=C["border2"],
            text_color=C["text"], placeholder_text_color=C["dim"],
        )
        srch.grid(row=0, column=0, sticky="ew", padx=(0,8))

        self._lbl_count = ctk.CTkLabel(
            top, text="", font=("Segoe UI",10), text_color=C["dim"],
        )
        self._lbl_count.grid(row=0, column=1, padx=(0,10))

        ctk.CTkButton(
            top, text="Tout effacer", font=("Segoe UI",10),
            width=100, height=34, fg_color=C["card2"],
            hover_color=C["border"], text_color=C["red"],
            corner_radius=8, command=self._clear_all,
        ).grid(row=0, column=2)

        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["accent"],
        )
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0,4))
        self._scroll.grid_columnconfigure(0, weight=1)

        self._lbl_empty = ctk.CTkLabel(
            self._scroll,
            text="◷  Aucun téléchargement dans l'historique\n\n"
                 "Les vidéos téléchargées avec succès apparaîtront ici.",
            font=("Segoe UI",12), text_color=C["dim"], justify="center",
        )
        self._lbl_empty.grid(row=0, column=0, pady=60)

        self._render()

    def _render(self):
        for r in self._rows:
            r.grid_forget(); r.destroy()
        self._rows.clear()

        query   = self._search_var.get()
        entries = self._hist.search(query)

        if not entries:
            self._lbl_empty.grid(row=0, column=0, pady=60)
            self._lbl_count.configure(text="")
            return

        self._lbl_empty.grid_forget()
        for i, entry in enumerate(entries):
            row = HistoryRow(
                self._scroll, entry,
                on_delete=self._delete_entry,
                on_redownload=self._on_redl,
            )
            row.grid(row=i, column=0, sticky="ew", padx=4, pady=3)
            self._rows.append(row)

        n = len(entries)
        total = len(self._hist)
        self._lbl_count.configure(
            text=f"{n} / {total}" if query else f"{total} entrée(s)"
        )

    def _delete_entry(self, entry_id: str):
        self._hist.delete(entry_id)
        self._render()

    def _clear_all(self):
        self._hist.clear()
        self._render()

    def refresh(self):
        self._render()


# ╔══════════════════════════════════════════════════════════════════════════════
#  CARTE DE TÉLÉCHARGEMENT
# ╚══════════════════════════════════════════════════════════════════════════════
class DownloadCard(ctk.CTkFrame):

    BORDER = {
        "pending":     C["border"],
        "downloading": C["accent"],
        "paused":      C["yellow"],
        "done":        C["green_dim"],
        "error":       C["red"],
    }

    def __init__(self, parent, title, url, thumb_url,
                 on_remove, on_download_one=None, default_quality=Q_NAMES[0], **kw):
        super().__init__(parent, fg_color=C["card"], corner_radius=10,
                         border_width=1, border_color=C["border"], **kw)
        self.url         = url
        self.title       = title
        self.thumb_url   = thumb_url
        self.on_remove   = on_remove
        self.status      = "pending"
        self.filepath    = None
        self.dest_dir    = None
        self._pause_ev   = threading.Event()
        self._cancel_ev  = threading.Event()
        self._qual_var   = tk.StringVar(value=default_quality)
        self._thumb_ref  = None
        self._size_bytes   = 0
        self._fetched_size = 0
        self._on_size_ready    = None
        self._on_download_one  = on_download_one
        self._build()
        if thumb_url and HAS_PIL:
            threading.Thread(target=self._load_thumb, daemon=True).start()
        self._qual_var.trace_add('write', lambda *_: self._start_size_fetch())

    def _build(self):
        self.columnconfigure(1, weight=1)

        tf = ctk.CTkFrame(self, fg_color=C["thumb_bg"], corner_radius=7,
                          width=THUMB_W, height=THUMB_H)
        tf.grid(row=0, column=0, rowspan=3, padx=(10,8), pady=10, sticky="n")
        tf.grid_propagate(False)
        self._thumb_icon = ctk.CTkLabel(tf, text="▶", font=("Segoe UI",30),
                                         text_color=C["dim2"],
                                         width=THUMB_W, height=THUMB_H)
        self._thumb_icon.place(relx=0.5, rely=0.5, anchor="center")
        for w in (tf, self._thumb_icon):
            w.bind("<Button-1>", lambda _: self._preview())
            w.bind("<Enter>",    lambda _: self._thumb_icon.configure(text_color=C["cyan"]))
            w.bind("<Leave>",    lambda _: self._thumb_icon.configure(text_color=C["dim2"]))

        row0 = ctk.CTkFrame(self, fg_color="transparent")
        row0.grid(row=0, column=1, sticky="ew", padx=(0,10), pady=(10,2))
        row0.columnconfigure(0, weight=1)
        short = (self.title[:72]+"…") if len(self.title)>72 else self.title
        ctk.CTkLabel(row0, text=short, font=("Segoe UI",12,"bold"),
                     text_color=C["text"], anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=(0,8))

        bb = ctk.CTkFrame(row0, fg_color="transparent")
        bb.grid(row=0, column=1, sticky="e")

        def mk(txt, cmd, col, tc=C["text2"], w=34):
            b = ctk.CTkButton(bb, text=txt, width=w, height=28,
                              font=("Segoe UI",11,"bold"),
                              fg_color=C["card2"], hover_color=C["border2"],
                              text_color=tc, corner_radius=7, command=cmd)
            b.grid(row=0, column=col, padx=2)
            return b

        self._btn_dl_one = mk("↓",   self._do_dl_one,            0, tc=C["green"],  w=30)
        self._btn_prev   = mk("▶",   self._preview,              1, tc=C["cyan"],   w=30)
        self._btn_pause  = mk("||",  self._toggle_pause,         2, tc=C["yellow"], w=30)
        self._btn_cancel = mk("■",   self._do_cancel,            3, tc=C["red"],    w=30)
        self._btn_folder = mk("Dir", self._open_folder,          4,                  w=34)
        self._btn_del    = mk("✕",   lambda: self.on_remove(self), 5, tc=C["red"],  w=30)
        self._btn_pause.configure(state="disabled")
        self._btn_cancel.configure(state="disabled")
        self._btn_folder.configure(state="disabled")

        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.grid(row=1, column=1, sticky="ew", padx=(0,10), pady=(0,2))
        self._qual_menu = ctk.CTkOptionMenu(
            row1, values=Q_NAMES, variable=self._qual_var,
            font=("Segoe UI",10), fg_color=C["card2"],
            button_color=C["border2"], button_hover_color=C["accent_dim"],
            dropdown_fg_color=C["card2"], dropdown_text_color=C["text"],
            dropdown_hover_color=C["border"], width=114, height=24, corner_radius=6,
        )
        self._qual_menu.pack(side="left", padx=(0,8))
        ctk.CTkLabel(row1, text="|", font=("Segoe UI",10),
                     text_color=C["dim2"], width=6).pack(side="left")
        self._lbl_size  = ctk.CTkLabel(row1, text="", font=("Segoe UI",10),
                                        text_color=C["dim"], width=84)
        self._lbl_size.pack(side="left", padx=(4,0))
        self._lbl_speed = ctk.CTkLabel(row1, text="", font=("Segoe UI",10),
                                        text_color=C["cyan"])
        self._lbl_speed.pack(side="left", padx=(6,0))
        self._lbl_eta   = ctk.CTkLabel(row1, text="", font=("Segoe UI",10),
                                        text_color=C["dim"])
        self._lbl_eta.pack(side="left", padx=(6,0))

        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.grid(row=2, column=1, sticky="ew", padx=(0,10), pady=(0,10))
        row2.columnconfigure(0, weight=1)
        self._pb = ctk.CTkProgressBar(row2, height=5, fg_color=C["border2"],
                                       progress_color=C["accent"])
        self._pb.set(0)
        self._pb.grid(row=0, column=0, sticky="ew", padx=(0,8))
        self._lbl_pct = ctk.CTkLabel(row2, text="En attente",
                                      font=("Courier New",10), text_color=C["dim"],
                                      width=90, anchor="e")
        self._lbl_pct.grid(row=0, column=1)

    def _load_thumb(self):
        try:
            req = urllib.request.Request(self.thumb_url,
                                         headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = r.read()
            img  = Image.open(io.BytesIO(data)).resize((THUMB_W,THUMB_H), Image.LANCZOS)
            cimg = ctk.CTkImage(img, size=(THUMB_W,THUMB_H))
            self.after(0, lambda: self._apply_thumb(cimg))
        except Exception: pass

    def _apply_thumb(self, img):
        self._thumb_ref = img
        self._thumb_icon.configure(image=img, text="")

    def _start_size_fetch(self, on_ready=None):
        if on_ready is not None:
            self._on_size_ready = on_ready
        if self.status in ("downloading", "paused", "done"): return
        self._lbl_size.configure(text="...", text_color=C["dim2"])
        threading.Thread(target=self._do_size_fetch, daemon=True).start()

    def _do_size_fetch(self):
        fmt_str, is_audio = self.get_quality()
        try:
            opts = {
                "quiet": True, "no_warnings": True,
                "skip_download": True, "no_color": True,
                "format": "bestaudio/best" if is_audio else fmt_str,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
            total = 0
            for fmt in (info.get("requested_formats") or [info]):
                total += fmt.get("filesize") or fmt.get("filesize_approx") or 0
            if total == 0:
                total = info.get("filesize") or info.get("filesize_approx") or 0
            self._fetched_size = total
            self.after(0, lambda b=total: self._apply_fetched_size(b))
        except Exception:
            self._fetched_size = 0
            self.after(0, lambda: self._lbl_size.configure(text="—", text_color=C["dim2"]))

    def _apply_fetched_size(self, b):
        sz = fmt_bytes(b)
        self._lbl_size.configure(
            text=sz if sz else "—",
            text_color=C["cyan"] if sz else C["dim2"],
        )
        if self._on_size_ready:
            self._on_size_ready(self)

    def _preview(self):
        if self.filepath and os.path.exists(self.filepath):
            _xopen(self.filepath); return
        if self.dest_dir and os.path.isdir(self.dest_dir):
            parts = sorted(f for f in os.listdir(self.dest_dir) if f.endswith(".part"))
            if parts:
                part_path = os.path.join(self.dest_dir, parts[-1])
                if not _open_with_vlc(part_path): _xopen(self.dest_dir)

    def _open_folder(self):
        if self.dest_dir and os.path.isdir(self.dest_dir):
            _xopen(self.dest_dir)

    def _do_dl_one(self):
        if self._on_download_one and self.status == "pending":
            self._on_download_one(self)

    def _toggle_pause(self):
        if self.status == "downloading":
            self._pause_ev.set(); self.status = "paused"
            self._btn_pause.configure(text="▶")
            self._lbl_pct.configure(text="En pause", text_color=C["yellow"])
            self._lbl_speed.configure(text=""); self._lbl_eta.configure(text="")
            self.configure(border_color=self.BORDER["paused"])
        elif self.status == "paused":
            self._pause_ev.clear(); self.status = "downloading"
            self._btn_pause.configure(text="||")
            self.configure(border_color=self.BORDER["downloading"])

    def _do_cancel(self):
        self._cancel_ev.set(); self._pause_ev.clear()
        self._btn_pause.configure(state="disabled")
        self._btn_cancel.configure(state="disabled")

    def get_quality(self):
        sel = self._qual_var.get()
        for name, fmt, audio in QUALITIES:
            if name == sel: return fmt, audio
        return QUALITIES[0][1], False

    def set_downloading(self, dest):
        self.status = "downloading"; self.dest_dir = dest
        self._qual_menu.configure(state="disabled")
        self._btn_dl_one.configure(state="disabled")
        self._btn_pause.configure(state="normal")
        self._btn_cancel.configure(state="normal")
        self._btn_del.configure(state="disabled")
        self._pb.configure(progress_color=C["accent"])
        self.configure(border_color=self.BORDER["downloading"])

    def update_progress(self, pct_str, speed, eta, total_b, dl_b):
        pct_clean = strip_ansi(pct_str or "")
        try:
            pct = float(pct_clean.replace("%","").strip()) / 100
            self._pb.set(min(max(pct,0),1))
            self._lbl_pct.configure(text=f"{pct*100:.0f} %", text_color=C["text2"])
        except Exception: pass
        spd = strip_ansi(speed or ""); et = strip_ansi(eta or "")
        self._lbl_speed.configure(text=f"↓ {spd}" if spd else "")
        self._lbl_eta.configure(text=f"ETA {et}" if et else "")
        if total_b:
            self._size_bytes = total_b
            t_str = fmt_bytes(total_b)
            d_str = fmt_bytes(dl_b) if dl_b else ""
            if d_str and d_str != t_str:
                self._lbl_size.configure(
                    text=f"{d_str} / {t_str}", text_color=C["cyan"])
            else:
                self._lbl_size.configure(text=t_str, text_color=C["cyan"])
        elif dl_b:
            self._size_bytes = dl_b
            self._lbl_size.configure(
                text=fmt_bytes(dl_b)+" reçu", text_color=C["cyan"])

    def set_processing(self):
        self._lbl_pct.configure(text="Conversion…", text_color=C["yellow"])
        self._lbl_speed.configure(text=""); self._lbl_eta.configure(text="")

    def set_done(self, fp):
        self.status = "done"; self.filepath = fp
        if fp: self.dest_dir = os.path.dirname(fp)
        self._pb.set(1.0); self._pb.configure(progress_color=C["green"])
        self._lbl_pct.configure(text="100 %", text_color=C["green"])
        self._lbl_speed.configure(text=""); self._lbl_eta.configure(text="")
        self.configure(border_color=self.BORDER["done"])
        self._btn_dl_one.configure(state="disabled")
        self._btn_pause.configure(state="disabled")
        self._btn_cancel.configure(state="disabled")
        self._btn_folder.configure(state="normal")
        self._btn_del.configure(state="normal")

    def set_error(self, msg):
        self.status = "error"
        self._pb.configure(progress_color=C["red"])
        self._lbl_pct.configure(text=f"Err: {strip_ansi(msg)[:50]}", text_color=C["red"])
        self._lbl_speed.configure(text=""); self._lbl_eta.configure(text="")
        self.configure(border_color=self.BORDER["error"])
        self._btn_dl_one.configure(state="normal")
        self._btn_pause.configure(state="disabled")
        self._btn_cancel.configure(state="disabled")
        self._btn_del.configure(state="normal")
        self._qual_menu.configure(state="normal")

    def set_cancelled(self):
        self.status = "pending"; self._pb.set(0)
        self._pb.configure(progress_color=C["dim"])
        self._lbl_pct.configure(text="Annulé", text_color=C["dim"])
        self._lbl_speed.configure(text=""); self._lbl_eta.configure(text="")
        self.configure(border_color=C["dim2"])
        self._btn_dl_one.configure(state="normal")
        self._btn_pause.configure(state="disabled")
        self._btn_cancel.configure(state="disabled")
        self._btn_del.configure(state="normal")
        self._qual_menu.configure(state="normal")
        self._cancel_ev.clear(); self._pause_ev.clear()


# ╔══════════════════════════════════════════════════════════════════════════════
#  APPLICATION PRINCIPALE
# ╚══════════════════════════════════════════════════════════════════════════════
class YTDLXApp(ctk.CTk):

    # Caractères du spinner braille (rotation fluide)
    _SPIN = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

    def __init__(self):
        super().__init__()
        self.title("My Yt Video Downloader")
        self.geometry("940x760")
        self.minsize(750, 580)
        self.configure(fg_color=C["bg"])
        self._dest    = tk.StringVar(value=self._default_dir())
        self._gqual   = tk.StringVar(value=Q_NAMES[0])
        self.cards: list[DownloadCard] = []
        self._history = HistoryManager()
        self._active_tab = "queue"

        # ── État du fetch d'infos ──────────────────────────────────────────
        self._fetch_cancel_ev = threading.Event()   # signale l'annulation
        self._fetch_running   = False               # garde-fou UI
        self._anim_job        = None                # id du after() spinner
        self._anim_idx        = 0

        self._build_ui()

    @staticmethod
    def _default_dir():
        for n in ("Downloads","Téléchargements","Desktop","Bureau"):
            p = os.path.join(os.path.expanduser("~"), n)
            if os.path.isdir(p): return p
        return os.path.expanduser("~")

    # ══════════════════════════════════════════════════════════════════════════
    #  Construction UI
    # ══════════════════════════════════════════════════════════════════════════
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=0, height=58)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        hdr.grid_propagate(False)

        ctk.CTkLabel(hdr, text=" ▶  My Yt Video Downloader",
                     font=("Courier New",22,"bold"), text_color=C["accent_glow"],
        ).grid(row=0, column=0, padx=18, sticky="w")
        ctk.CTkLabel(hdr,
                     text="Téléchargeur YouTube  •  Vidéos & Playlists  •  Multi-qualité",
                     font=("Segoe UI",10), text_color=C["dim"],
        ).grid(row=0, column=1, padx=6, sticky="w")
        ctk.CTkLabel(hdr, text=" v4.0 ",
                     font=("Courier New",9,"bold"),
                     text_color=C["accent"], fg_color=C["card2"], corner_radius=4,
        ).grid(row=0, column=2, padx=18, sticky="e")

        # ── Saisie URL ───────────────────────────────────────────────────────
        url_box = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=12,
                               border_width=1, border_color=C["border"])
        url_box.grid(row=1, column=0, padx=14, pady=(12,5), sticky="ew")
        url_box.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(url_box,
                     text="  URL YouTube — vidéo ou playlist complète",
                     font=("Segoe UI",10), text_color=C["dim"], anchor="w",
        ).grid(row=0, column=0, padx=14, pady=(8,1), sticky="w")

        ur = ctk.CTkFrame(url_box, fg_color="transparent")
        ur.grid(row=1, column=0, padx=10, pady=(0,6), sticky="ew")
        ur.grid_columnconfigure(0, weight=1)

        self._url_ent = ctk.CTkEntry(
            ur, placeholder_text="https://youtube.com/watch?v=...  ou  playlist?list=...",
            font=("Courier New",11), height=42,
            fg_color=C["card"], border_color=C["border2"],
            text_color=C["text"], placeholder_text_color=C["dim"],
        )
        self._url_ent.grid(row=0, column=0, sticky="ew", padx=(0,8))
        self._url_ent.bind("<Return>", lambda _: self._fetch_and_add())

        self._btn_add = ctk.CTkButton(
            ur, text="+  Ajouter", font=("Segoe UI",12,"bold"),
            width=120, height=42, fg_color=C["accent"],
            hover_color=C["accent_dim"], corner_radius=10,
            command=self._fetch_and_add,
        )
        self._btn_add.grid(row=0, column=1)

        # ── Barre de progression indéterminée (cachée par défaut) ───────────
        # Affichée uniquement pendant le fetch d'informations
        self._fetch_pb = ctk.CTkProgressBar(
            url_box, mode="indeterminate", height=3,
            fg_color=C["border"], progress_color=C["accent"],
        )
        self._fetch_pb.grid(row=2, column=0, padx=10, pady=(0,8), sticky="ew")
        self._fetch_pb.grid_remove()   # cachée au départ

        # ── Label de statut du fetch (vidéos trouvées, etc.) ────────────────
        self._lbl_fetch_info = ctk.CTkLabel(
            url_box, text="", font=("Segoe UI",10),
            text_color=C["dim"], anchor="w",
        )
        self._lbl_fetch_info.grid(row=3, column=0, padx=14, pady=(0,6), sticky="w")
        self._lbl_fetch_info.grid_remove()

        # ── Options ─────────────────────────────────────────────────────────
        opt = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=12,
                           border_width=1, border_color=C["border"])
        opt.grid(row=2, column=0, padx=14, pady=5, sticky="ew")
        opt.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(opt, text="Qualité défaut :",
                     font=("Segoe UI",11), text_color=C["dim"],
        ).grid(row=0, column=0, padx=(14,6), pady=11)
        ctk.CTkOptionMenu(
            opt, values=Q_NAMES, variable=self._gqual,
            font=("Segoe UI",11), fg_color=C["card"],
            button_color=C["accent"], button_hover_color=C["accent_dim"],
            dropdown_fg_color=C["card2"], dropdown_text_color=C["text"],
            dropdown_hover_color=C["border"], width=135, corner_radius=8,
        ).grid(row=0, column=1, padx=(0,20), pady=11)
        ctk.CTkLabel(opt, text="Dossier :",
                     font=("Segoe UI",11), text_color=C["dim"],
        ).grid(row=0, column=2, padx=(0,6), pady=11)
        self._lbl_dir = ctk.CTkLabel(opt, text=self._trim(self._dest.get()),
                                      font=("Courier New",10), text_color=C["cyan"])
        self._lbl_dir.grid(row=0, column=3, padx=(0,10), pady=11, sticky="e")
        ctk.CTkButton(
            opt, text="Parcourir", font=("Segoe UI",11),
            height=34, width=100, fg_color=C["card2"],
            hover_color=C["border"], corner_radius=8, command=self._choose_dir,
        ).grid(row=0, column=4, padx=(0,12), pady=11)

        # ── Conteneur à onglets ──────────────────────────────────────────────
        tab_container = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=12,
                                     border_width=1, border_color=C["border"])
        tab_container.grid(row=3, column=0, padx=14, pady=5, sticky="nsew")
        tab_container.grid_rowconfigure(1, weight=1)
        tab_container.grid_columnconfigure(0, weight=1)

        tab_bar = ctk.CTkFrame(tab_container, fg_color="transparent", height=42)
        tab_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(8,0))
        tab_bar.grid_columnconfigure(2, weight=1)
        tab_bar.grid_propagate(False)

        self._tab_q_btn = ctk.CTkButton(
            tab_bar, text="↓  File d'attente",
            font=("Segoe UI",11,"bold"), width=150, height=32,
            fg_color=C["accent"], hover_color=C["accent_dim"],
            text_color=C["text"], corner_radius=8,
            command=lambda: self._switch_tab("queue"),
        )
        self._tab_q_btn.grid(row=0, column=0, padx=(0,6))

        self._tab_h_btn = ctk.CTkButton(
            tab_bar, text="◷  Historique",
            font=("Segoe UI",11,"bold"), width=150, height=32,
            fg_color=C["card2"], hover_color=C["border"],
            text_color=C["dim"], corner_radius=8,
            command=lambda: self._switch_tab("history"),
        )
        self._tab_h_btn.grid(row=0, column=1, padx=(0,6))

        self._lbl_q = ctk.CTkLabel(
            tab_bar, text="File  —  vide",
            font=("Segoe UI",11), text_color=C["dim"], anchor="w",
        )
        self._lbl_q.grid(row=0, column=2, padx=(8,0), sticky="w")

        ctk.CTkButton(
            tab_bar, text="Nettoyer", font=("Segoe UI",10),
            height=28, width=80, fg_color=C["card2"],
            hover_color=C["border"], text_color=C["dim"], corner_radius=6,
            command=self._clear_done,
        ).grid(row=0, column=3, sticky="e")

        # ── Page File d'attente ──────────────────────────────────────────────
        self._page_queue = ctk.CTkFrame(tab_container, fg_color="transparent")
        self._page_queue.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self._page_queue.grid_rowconfigure(0, weight=1)
        self._page_queue.grid_columnconfigure(0, weight=1)

        self._scroll = ctk.CTkScrollableFrame(
            self._page_queue, fg_color="transparent",
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["accent"],
        )
        self._scroll.grid(row=0, column=0, sticky="nsew", padx=6, pady=(4,6))
        self._scroll.grid_columnconfigure(0, weight=1)

        self._lbl_empty = ctk.CTkLabel(
            self._scroll,
            text="▶  Aucune vidéo dans la file\n\n"
                 "Collez une URL YouTube ci-dessus et cliquez  +  Ajouter",
            font=("Segoe UI",12), text_color=C["dim"], justify="center",
        )
        self._lbl_empty.grid(row=0, column=0, pady=60)

        # ── Page Historique ──────────────────────────────────────────────────
        self._page_history = HistoryPanel(
            tab_container, history=self._history,
            on_redownload=self._redownload_from_history,
        )
        self._page_history.grid(row=1, column=0, sticky="nsew", padx=6, pady=(4,6))
        self._page_history.grid_remove()

        # ── Footer ──────────────────────────────────────────────────────────
        foot = ctk.CTkFrame(self, fg_color=C["surface"],
                            corner_radius=0, height=60)
        foot.grid(row=4, column=0, sticky="ew")
        foot.grid_columnconfigure(0, weight=1)
        foot.grid_propagate(False)
        self._lbl_status = ctk.CTkLabel(
            foot, text="Prêt.", font=("Segoe UI",11),
            text_color=C["dim"], anchor="w",
        )
        self._lbl_status.grid(row=0, column=0, padx=18, sticky="w")

        self._lbl_total = ctk.CTkLabel(
            foot, text="",
            font=("Segoe UI", 11), text_color=C["dim"],
        )
        self._lbl_total.grid(row=0, column=1, padx=(0, 18))

        self._btn_dl = ctk.CTkButton(
            foot, text="↓  Tout télécharger",
            font=("Segoe UI",13,"bold"), height=40, width=185,
            fg_color=C["accent"], hover_color=C["accent_dim"],
            corner_radius=10, command=self._start_all,
        )
        self._btn_dl.grid(row=0, column=2, padx=(0, 18), sticky="e")

    # ══════════════════════════════════════════════════════════════════════════
    #  Onglets
    # ══════════════════════════════════════════════════════════════════════════
    def _switch_tab(self, tab: str):
        self._active_tab = tab
        if tab == "queue":
            self._page_history.grid_remove()
            self._page_queue.grid()
            self._tab_q_btn.configure(fg_color=C["accent"], text_color=C["text"])
            self._tab_h_btn.configure(fg_color=C["card2"], text_color=C["dim"])
        else:
            self._page_queue.grid_remove()
            self._page_history.grid()
            self._page_history.refresh()
            self._tab_h_btn.configure(fg_color=C["accent"], text_color=C["text"])
            self._tab_q_btn.configure(fg_color=C["card2"], text_color=C["dim"])

    # ══════════════════════════════════════════════════════════════════════════
    #  Helpers
    # ══════════════════════════════════════════════════════════════════════════
    @staticmethod
    def _trim(p, n=42):
        return p if len(p) <= n else "…" + p[-(n-1):]

    def _choose_dir(self):
        d = filedialog.askdirectory(initialdir=self._dest.get())
        if d:
            self._dest.set(d)
            self._lbl_dir.configure(text=self._trim(d))

    def _status(self, msg, color=None):
        self._lbl_status.configure(text=msg, text_color=color or C["dim"])

    def _refresh_q(self):
        n    = len(self.cards)
        done = sum(1 for c in self.cards if c.status == "done")
        dl   = sum(1 for c in self.cards if c.status in ("downloading","paused"))
        pend = sum(1 for c in self.cards if c.status == "pending")
        if n == 0:
            self._lbl_q.configure(text="File  —  vide"); return
        parts = [f"{n} vidéo(s)"]
        if dl:   parts.append(f"{dl} en cours")
        if done: parts.append(f"{done} ✓")
        if pend: parts.append(f"{pend} en attente")
        self._lbl_q.configure(text="  •  ".join(parts))

    def _refresh_total(self, _card=None):
        if not self.cards:
            self._lbl_total.configure(text=""); return
        known   = [(c._size_bytes or c._fetched_size) for c in self.cards
                   if (c._size_bytes or c._fetched_size) > 0]
        pending = [c for c in self.cards
                   if (c._size_bytes == 0 and c._fetched_size == 0
                       and c.status == "pending")]
        total   = sum(known)
        sz      = fmt_bytes(total)
        if not sz:
            self._lbl_total.configure(text=""); return
        tilde   = "~" if pending else ""
        n_known = len(known)
        n_total = len(self.cards)
        count   = f"{n_known}/{n_total}" if n_known < n_total else f"{n_total}"
        self._lbl_total.configure(
            text=f"Total ({count} vidéos) : {tilde}{sz}",
            text_color=C["text2"],
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  Spinner / animation pendant le fetch
    # ══════════════════════════════════════════════════════════════════════════
    def _start_spinner(self):
        """Démarre l'animation braille dans la barre de statut."""
        self._stop_spinner()
        self._anim_idx = 0
        self._tick_spinner()

    def _tick_spinner(self):
        spin = self._SPIN[self._anim_idx % len(self._SPIN)]
        self._anim_idx += 1
        # Met à jour le statut avec l'icône tournante
        self._lbl_status.configure(
            text=f"  {spin}  Récupération des informations en cours…",
            text_color=C["cyan"],
        )
        self._anim_job = self.after(80, self._tick_spinner)

    def _stop_spinner(self):
        if self._anim_job is not None:
            self.after_cancel(self._anim_job)
            self._anim_job = None

    # ══════════════════════════════════════════════════════════════════════════
    #  Helpers UI fetch (factorisation)
    # ══════════════════════════════════════════════════════════════════════════
    def _fetch_ui_start(self):
        """Passe l'UI en mode 'chargement en cours'."""
        self._fetch_running = True
        # Le bouton devient "Annuler" (rouge)
        self._btn_add.configure(
            text="✕  Annuler",
            fg_color=C["red"],
            hover_color="#c0294f",
            command=self._cancel_fetch,
        )
        # Barre indéterminée visible + démarrée
        self._fetch_pb.grid()
        self._fetch_pb.start()
        # Spinner dans le footer
        self._start_spinner()
        # Info fetch sous la barre
        self._lbl_fetch_info.configure(text="")
        self._lbl_fetch_info.grid()

    def _fetch_ui_stop(self):
        """Remet l'UI dans l'état normal après un fetch (succès, erreur ou annulation)."""
        self._fetch_running = False
        self._stop_spinner()
        self._fetch_pb.stop()
        self._fetch_pb.grid_remove()
        self._lbl_fetch_info.grid_remove()
        # Restaurer le bouton Ajouter
        self._btn_add.configure(
            text="+  Ajouter",
            fg_color=C["accent"],
            hover_color=C["accent_dim"],
            command=self._fetch_and_add,
            state="normal",
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  Récupération URL
    # ══════════════════════════════════════════════════════════════════════════
    def _fetch_and_add(self):
        # Ignore si un fetch est déjà en cours
        if self._fetch_running:
            return

        url = self._url_ent.get().strip()
        if not url:
            return

        # On NE vide PAS l'URL ici — seulement en cas de succès
        self._fetch_cancel_ev.clear()
        self._fetch_ui_start()

        # Basculer sur l'onglet file automatiquement
        if self._active_tab != "queue":
            self._switch_tab("queue")

        def _work():
            try:
                opts = {"quiet":True,"no_warnings":True,
                        "extract_flat":"in_playlist","skip_download":True}
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)

                # Annulation demandée pendant le fetch réseau ?
                if self._fetch_cancel_ev.is_set():
                    self.after(0, self._on_fetch_cancelled)
                    return

                items = []
                if "entries" in info:
                    entries = [e for e in (info.get("entries") or []) if e]
                    total_pl = len(entries)
                    for i, e in enumerate(entries, 1):
                        if self._fetch_cancel_ev.is_set():
                            # Annulation en cours de parsing playlist
                            self.after(0, self._on_fetch_cancelled)
                            return
                        vid_url = (e.get("webpage_url") or e.get("url")
                                   or f"https://www.youtube.com/watch?v={e.get('id','')}")
                        items.append((e.get("title") or "Sans titre", vid_url, _best_thumb(e)))
                        # Mise à jour compteur playlist en live
                        self.after(0, lambda c=i, t=total_pl:
                                   self._lbl_fetch_info.configure(
                                       text=f"  Playlist : {c} / {t} vidéos trouvées…",
                                       text_color=C["accent_glow"],
                                   ))
                else:
                    items.append((info.get("title") or "Sans titre", url, _best_thumb(info)))

                self.after(0, lambda it=items: self._add_cards(it))

            except Exception as ex:
                if self._fetch_cancel_ev.is_set():
                    self.after(0, self._on_fetch_cancelled)
                else:
                    self.after(0, lambda: self._fetch_err(str(ex)))

        threading.Thread(target=_work, daemon=True).start()

    def _cancel_fetch(self):
        """L'utilisateur a cliqué sur Annuler pendant le fetch."""
        self._fetch_cancel_ev.set()
        # L'UI sera remise en état par _on_fetch_cancelled (appelé depuis le thread)
        # ou directement ici si le thread a déjà terminé.
        self._on_fetch_cancelled()

    def _on_fetch_cancelled(self):
        self._fetch_ui_stop()
        # L'URL est conservée intacte — l'utilisateur peut réessayer
        self._status("  Chargement annulé.", C["yellow"])

    def _add_cards(self, items):
        """Appelé après un fetch réussi — vide l'input URL et ajoute les cartes."""
        self._fetch_ui_stop()
        # ── Vider l'URL seulement en cas de succès ──
        self._url_ent.delete(0, "end")

        if self._lbl_empty.winfo_ismapped():
            self._lbl_empty.grid_forget()

        for title, url, thumb in items:
            card = DownloadCard(
                self._scroll, title=title, url=url, thumb_url=thumb,
                on_remove=self._remove_card,
                on_download_one=self._run_one,
                default_quality=self._gqual.get(),
            )
            card.grid(row=len(self.cards)+1, column=0, sticky="ew", padx=4, pady=4)
            self.cards.append(card)
            card._start_size_fetch(on_ready=self._refresh_total)

        self._refresh_q()
        self._refresh_total()
        n = len(items)
        self._status(
            f"  ✓  {n} vidéo(s) ajoutée(s) à la file.",
            C["green"],
        )

    def _fetch_err(self, msg):
        self._fetch_ui_stop()
        # URL conservée pour que l'utilisateur puisse corriger et réessayer
        self._status(f"  ✗  Erreur : {strip_ansi(msg)[:90]}", C["red"])

    # ── Re-télécharger depuis l'historique ────────────────────────────────
    def _redownload_from_history(self, entry: dict):
        self._switch_tab("queue")
        if self._lbl_empty.winfo_ismapped():
            self._lbl_empty.grid_forget()
        card = DownloadCard(
            self._scroll,
            title=entry["title"], url=entry["url"],
            thumb_url=entry.get("thumb_url",""),
            on_remove=self._remove_card,
            on_download_one=self._run_one,
            default_quality=entry.get("quality", Q_NAMES[0]),
        )
        card.grid(row=len(self.cards)+1, column=0, sticky="ew", padx=4, pady=4)
        self.cards.append(card)
        card._start_size_fetch(on_ready=self._refresh_total)
        self._refresh_q()
        self._refresh_total()
        self._status(f"  Ajouté à la file : {entry['title'][:55]}…", C["accent_glow"])

    # ══════════════════════════════════════════════════════════════════════════
    #  Gestion file
    # ══════════════════════════════════════════════════════════════════════════
    def _remove_card(self, card):
        if card.status in ("downloading","paused"): return
        card.grid_forget(); card.destroy()
        if card in self.cards: self.cards.remove(card)
        for i, c in enumerate(self.cards):
            c.grid(row=i+1, column=0, sticky="ew", padx=4, pady=4)
        if not self.cards:
            self._lbl_empty.grid(row=0, column=0, pady=60)
        self._refresh_q()
        self._refresh_total()

    def _clear_done(self):
        for c in list(self.cards):
            if c.status in ("done","error"):
                self._remove_card(c)

    def _start_all(self):
        pending = [c for c in self.cards if c.status == "pending"]
        if not pending:
            self._status("Aucune vidéo en attente.", C["yellow"]); return
        self._btn_dl.configure(state="disabled", text="En cours…")
        self._run_queue(pending, 0)

    def _run_one(self, card: "DownloadCard"):
        if card.status != "pending": return
        self._run_queue([card], 0)

    # ══════════════════════════════════════════════════════════════════════════
    #  Exécution séquentielle + sauvegarde historique
    # ══════════════════════════════════════════════════════════════════════════
    def _run_queue(self, queue, idx):
        is_solo = (len(queue) == 1)
        if idx >= len(queue):
            if not is_solo:
                self._btn_dl.configure(state="normal", text="↓  Tout télécharger")
                self._status("✓  Tous les téléchargements terminés !", C["green"])
            else:
                still_active = any(c.status in ("downloading","paused")
                                   for c in self.cards)
                if not still_active:
                    self._btn_dl.configure(state="normal", text="↓  Tout télécharger")
            return

        card = queue[idx]
        if card.status != "pending":
            self.after(0, lambda: self._run_queue(queue, idx+1)); return

        dest              = self._dest.get()
        fmt_str, is_audio = card.get_quality()
        fp_ref            = [None]
        n                 = len(queue)

        card.set_downloading(dest)
        if is_solo:
            self._status(f"Téléchargement  —  {card.title[:65]}…", C["cyan"])
        else:
            self._status(f"Téléchargement {idx+1}/{n}  —  {card.title[:55]}…", C["cyan"])
        self._refresh_q()

        def _hook(d):
            while card._pause_ev.is_set():
                if card._cancel_ev.is_set(): raise DownloadCancelled()
                time.sleep(0.1)
            if card._cancel_ev.is_set(): raise DownloadCancelled()
            if d["status"] == "downloading":
                pct   = d.get("_percent_str","?%")
                speed = d.get("_speed_str","")
                eta   = d.get("_eta_str","")
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                dl_b  = d.get("downloaded_bytes")
                fn    = d.get("filename")
                if fn: fp_ref[0] = fn
                self.after(0, lambda p=pct,s=speed,e=eta,t=total,b=dl_b:
                           card.update_progress(p,s,e,t,b))
            elif d["status"] == "finished":
                fn = d.get("filename")
                if fn: fp_ref[0] = fn
                self.after(0, card.set_processing)

        def _run():
            opts = {
                "outtmpl":        os.path.join(dest,"%(title)s.%(ext)s"),
                "progress_hooks": [_hook],
                "noplaylist":     True,
                "quiet":          True,
                "no_warnings":    True,
                "no_color":       True,
            }
            if is_audio:
                opts["format"] = "bestaudio/best"
                opts["postprocessors"] = [{
                    "key":"FFmpegExtractAudio",
                    "preferredcodec":"mp3",
                    "preferredquality":"192",
                }]
            else:
                opts["format"]              = fmt_str
                opts["merge_output_format"] = "mp4"

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(card.url, download=True)
                    if info:
                        base = os.path.splitext(ydl.prepare_filename(info))[0]
                        for ext in (".mp4",".mp3",".mkv",".webm",".m4a"):
                            if os.path.exists(base+ext):
                                fp_ref[0] = base+ext; break

                fp = fp_ref[0]
                try:
                    sz = os.path.getsize(fp) if fp and os.path.exists(fp) else card._size_bytes
                except Exception: sz = card._size_bytes
                self._history.add(
                    title=card.title,
                    url=card.url,
                    thumb_url=card.thumb_url or "",
                    quality=card._qual_var.get(),
                    filepath=fp or "",
                    size_bytes=sz,
                )
                self.after(0, self._update_history_badge)
                self.after(0, lambda: card.set_done(fp))

            except DownloadCancelled:
                self.after(0, card.set_cancelled)

            except Exception as ex:
                err = strip_ansi(str(ex))
                self.after(0, lambda: card.set_error(err))

            finally:
                self.after(0, self._refresh_q)
                self.after(0, self._refresh_total)
                self.after(50, lambda: self._run_queue(queue, idx+1))

        threading.Thread(target=_run, daemon=True).start()

    def _update_history_badge(self):
        n = len(self._history)
        self._tab_h_btn.configure(
            text=f"◷  Historique  ({n})" if n else "◷  Historique"
        )
        if self._active_tab == "history":
            self._page_history.refresh()


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = YTDLXApp()
    app.mainloop()
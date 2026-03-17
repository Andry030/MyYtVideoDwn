# 🎬 My Yt Video Downloader v4 — YT-DLX Pro

> Téléchargeur YouTube moderne avec interface graphique sombre et interactive.  
> Propulsé par **yt-dlp** & **customtkinter**.

---

## ✨ Fonctionnalités

| Fonctionnalité | Détail |
|---|---|
| 🎬 Vidéos & Playlists | Télécharge une URL unique ou une playlist complète en une seule opération |
| 🎨 Multi-qualité | Meilleure, 4K (2160p), 1440p (2K), 1080p HD, 720p, 480p, 360p, MP3 Audio |
| 📋 File d'attente | Ajoutez plusieurs URLs et tout télécharge à la suite automatiquement |
| ⏸ Pause / Reprise | Mettez en pause et reprenez n'importe quel téléchargement en cours |
| ❌ Annulation | Annulez un téléchargement individuel à tout moment |
| 🖼 Miniatures | Aperçu de la vignette de chaque vidéo chargé en arrière-plan |
| 📏 Taille estimée | Estimation du poids du fichier avant de lancer le téléchargement |
| 📁 Dossier de destination | Choisissez librement où enregistrer vos fichiers |
| 📂 Ouvrir le dossier | Accédez directement au répertoire du fichier téléchargé |
| ▶ Ouvrir la vidéo | Lancez la vidéo dans votre lecteur (VLC détecté automatiquement, sinon lecteur système) |
| 🗑 Nettoyage rapide | Supprimez les téléchargements terminés ou videz toute la file |
| 🕘 Historique persistant | Tous vos téléchargements sont mémorisés dans `~/.ytdlx_pro/history.json` |
| 🔍 Recherche dans l'historique | Filtrez vos téléchargements passés par titre ou URL |
| 🔁 Re-télécharger | Relancez n'importe quel téléchargement depuis l'historique |
| 🖥 Interface 100 % dark | Thème sombre et moderne avec palette violette/cyan |

---

## 📸 Interface

L'interface est organisée en deux onglets :

- **File d'attente** — saisie d'URL, sélection de qualité, dossier de destination, progression en temps réel pour chaque vidéo.
- **Historique** — liste scrollable de tous vos téléchargements passés, avec miniatures, date, qualité, taille, et boutons d'action (ouvrir, re-télécharger, supprimer).

---

## 🚀 Installation et lancement

### Prérequis

- **Python 3.9+** → [https://www.python.org/downloads/](https://www.python.org/downloads/)
- **pip** (inclus avec Python)
- **ffmpeg** (fusion vidéo/audio et conversion MP3)

| Plateforme | Commande |
|---|---|
| Windows | [Télécharger ffmpeg](https://ffmpeg.org/download.html) → ajouter au PATH |
| Linux (Debian/Ubuntu) | `sudo apt install ffmpeg` |
| Linux (Arch) | `sudo pacman -S ffmpeg` |
| macOS | `brew install ffmpeg` |

---

### ▶ Lancement rapide

#### Linux / macOS

```bash
chmod +x run.sh
./run.sh
```

Le script `run.sh` installe automatiquement les dépendances Python et enregistre l'application dans les menus système avant de la lancer.

#### Toutes plateformes (manuel)

```bash
pip install customtkinter yt-dlp Pillow
python app.py
```

---

## 🗂 Structure du projet

```
MyYtVideoDwn/
├── app.py              # Application principale (interface + logique de téléchargement)
├── install.py          # Script d'installation système (raccourcis, icônes)
├── run.sh              # Script de lancement Linux/macOS (installe + lance)
├── requirements.txt    # Dépendances Python
└── README.md           # Ce fichier
```

---

## 📦 Dépendances Python

```
customtkinter >= 5.2.0
yt-dlp        >= 2024.1.0
Pillow        >= 9.0.0
```

Installation :

```bash
pip install -r requirements.txt
```

---

## 🖥 Installation système (intégration menu)

Le script `install.py` crée des raccourcis et une icône générée automatiquement (sans dépendance externe) sur votre système :

| Plateforme | Ce qui est créé |
|---|---|
| **Linux** | Fichier `.desktop` dans `~/.local/share/applications/` + icône PNG 48 et 256 px + raccourci Bureau |
| **Windows** | Raccourci dans Démarrer > Programmes + Bureau, avec icône `.ico` multi-résolution |
| **macOS** | Bundle `~/Applications/My Yt Video Downloader.app` avec icône `.icns` et `Info.plist` |

### Lancer l'installation manuellement

```bash
python install.py
```

### Désinstaller

```bash
python install.py --uninstall
# ou
python install.py -u
```

---

## 🎨 Qualités disponibles

| Label | Format |
|---|---|
| Meilleure | Meilleure vidéo MP4 + meilleur audio disponible |
| 4K (2160p) | Vidéo ≤ 2160p MP4 + audio M4A |
| 1440p (2K) | Vidéo ≤ 1440p MP4 + audio M4A |
| 1080p HD | Vidéo ≤ 1080p MP4 + audio M4A |
| 720p | Vidéo ≤ 720p MP4 + audio M4A |
| 480p | Vidéo ≤ 480p MP4 + audio M4A |
| 360p | Vidéo ≤ 360p MP4 + audio M4A |
| MP3 Audio | Meilleur audio uniquement, converti en MP3 via ffmpeg |

---

## 🕘 Historique persistant

L'historique de tous vos téléchargements est sauvegardé automatiquement dans :

```
~/.ytdlx_pro/history.json
```

Chaque entrée contient : titre, URL, miniature, qualité choisie, chemin du fichier, date et heure, et taille en octets.

Depuis l'onglet **Historique** vous pouvez :
- 🔍 **Rechercher** par titre ou URL
- ▶ **Re-télécharger** une vidéo passée directement vers le dossier de destination actuel
- 🗑 **Supprimer** une entrée individuelle
- 🧹 **Tout effacer** en un clic

---

## 📤 Partager avec des amis

Envoyez simplement le dossier entier contenant :

```
app.py
install.py
run.sh
requirements.txt
README.md
```

Vos amis ont seulement besoin de **Python 3.9+** et de **ffmpeg**, puis ils lancent :

```bash
./run.sh          # Linux / macOS
# ou
pip install customtkinter yt-dlp Pillow && python app.py   # toutes plateformes
```

---

## 🛠 Créer un exécutable autonome `.exe` (Windows, optionnel)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "YT-DLX Pro" app.py
```

Le fichier `.exe` autonome apparaîtra dans le dossier `dist/`.

> ⚠️ **ffmpeg** doit toujours être installé et accessible dans le PATH sur la machine cible, même avec l'exécutable.

---

## 🔧 Dépannage

| Problème | Solution |
|---|---|
| `ModuleNotFoundError: customtkinter` | Lancer `pip install customtkinter yt-dlp Pillow` |
| Pas d'audio dans la vidéo téléchargée | Vérifier que `ffmpeg` est installé et dans le PATH |
| La conversion MP3 échoue | Même cause : installer/configurer `ffmpeg` |
| VLC ne s'ouvre pas depuis l'app | Installer VLC ou utiliser "Ouvrir le dossier" et lancer manuellement |
| L'historique est vide après réinstallation | L'historique est dans `~/.ytdlx_pro/history.json`, il persiste entre les installations |
| Erreur `403 / Sign in required` | Mettre à jour yt-dlp : `pip install -U yt-dlp` |

---

## 📄 Licence

Ce projet est distribué librement. Consultez les conditions d'utilisation de **yt-dlp** et de **YouTube** avant tout usage.

---

*My Yt Video Downloader v4 — propulsé par [yt-dlp](https://github.com/yt-dlp/yt-dlp) & [customtkinter](https://github.com/TomSchimansky/CustomTkinter)*
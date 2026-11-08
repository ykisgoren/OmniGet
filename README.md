<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?logo=python" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/yt--dlp-latest-red?logo=youtube" alt="yt-dlp">
  <img src="https://img.shields.io/badge/CustomTkinter-5.x-blueviolet" alt="CustomTkinter">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="Multi-platform">
</p>

<h1 align="center">OmniGet – Universal Video Downloader</h1>

<p align="center">
  A clean, modern desktop GUI for downloading video and audio from YouTube, Vimeo,
  and <a href="https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md">1000+ other sites</a>,
  powered by <strong>yt-dlp</strong> and <strong>CustomTkinter</strong>.
</p>

---

## ✨ Features

| Feature | Detail |
|---|---|
| **Universal Downloads** | Supports any site that yt-dlp supports (YouTube, Vimeo, Twitter/X, Twitch, SoundCloud, …) |
| **Multiple Formats** | Best Video + Audio (MP4), Audio Only (MP3 @ 192 kbps), Video Only (MP4) |
| **Real-time Progress** | Live progress bar showing percentage, download speed, and ETA |
| **Non-blocking UI** | Download runs in a background thread – the window stays responsive |
| **Dark / Light / System Theme** | Toggle appearance mode from the footer |
| **Auto Save** | Files are saved to your OS `~/Downloads` folder automatically |

---

## 📸 Screenshot

> _Add a screenshot here once the app is running (`docs/screenshot.png`)._

---

## 🔧 Requirements

### Runtime dependencies

| Software | Minimum version | Purpose |
|---|---|---|
| **Python** | 3.9 | Runtime |
| **yt-dlp** | 2024.1.1 | Download engine |
| **customtkinter** | 5.2.2 | Modern Tkinter GUI |
| **FFmpeg** | any recent | Stream merging & audio transcoding |

### FFmpeg installation

FFmpeg **must** be on your system `PATH` for stream merging and MP3 conversion to work.

| OS | Install command |
|---|---|
| **Windows** | `winget install Gyan.FFmpeg` |
| **macOS** | `brew install ffmpeg` |
| **Linux (Debian/Ubuntu)** | `sudo apt install ffmpeg` |

---

## 🚀 Getting Started

### 1 – Clone the repository

```bash
git clone https://github.com/your-username/OmniGet.git
cd OmniGet
```

### 2 – Create and activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3 – Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4 – Run the app

```bash
python main.py
```

---

## 📦 Building a Standalone Executable (PyInstaller)

You can ship OmniGet as a single `.exe` / binary with no Python installation required:

```bash
# Windows – produces dist\OmniGet.exe
pyinstaller --onefile --windowed --name OmniGet main.py

# macOS – produces dist/OmniGet.app
pyinstaller --onefile --windowed --name OmniGet main.py
```

> [!NOTE]
> PyInstaller does **not** bundle FFmpeg. Users of the standalone build must still install FFmpeg separately.

---

## 🗂 Project Structure

```
OmniGet/
├── main.py          # CustomTkinter GUI – entry point
├── downloader.py    # yt-dlp download engine (UI-independent)
├── requirements.txt # Python package dependencies
├── .gitignore       # Standard Python gitignore
└── README.md        # This file
```

---

## 🤝 Contributing

Contributions, bug reports, and feature requests are welcome!  
Please open an [issue](../../issues) or submit a [pull request](../../pulls).

1. Fork the repo.
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "feat: add my feature"`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a pull request.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

---

## 🙏 Acknowledgements

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) – the powerful download engine behind OmniGet
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) – modern Tkinter widgets
- [FFmpeg](https://ffmpeg.org/) – the multimedia Swiss Army knife

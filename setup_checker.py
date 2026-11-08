"""
setup_checker.py
================
OmniGet – Dependency bootstrap module
--------------------------------------
Run automatically at startup (before the main GUI appears).

Checks for:
  1. FFmpeg – required for stream merging and audio conversion
  2. yt-dlp  – auto-updated to the latest version if already installed

If FFmpeg is missing, a small CustomTkinter splash window is shown that:
  - Explains what is being installed
  - Runs the installation via PowerShell in a background thread
  - Closes automatically when done (or shows an error with instructions)

This module is completely UI-independent from the main window.
"""

import os
import sys
import shutil
import subprocess
import threading
import customtkinter as ctk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ffmpeg_is_available() -> bool:
    """Return True if 'ffmpeg' resolves on the current PATH."""
    return shutil.which("ffmpeg") is not None


def _yt_dlp_is_available() -> bool:
    """Return True if yt-dlp can be imported (bundled inside the exe)."""
    try:
        import yt_dlp  # noqa: F401
        return True
    except ImportError:
        return False


def _run_ps(command: str) -> tuple[int, str, str]:
    """
    Execute a PowerShell command and return (returncode, stdout, stderr).
    Uses -ExecutionPolicy Bypass so the user does not need to change their
    system policy.
    """
    result = subprocess.run(
        [
            "powershell.exe",
            "-ExecutionPolicy", "Bypass",
            "-NoProfile",
            "-NonInteractive",
            "-Command", command,
        ],
        capture_output=True,
        text=True,
        timeout=300,       # 5-minute cap; ffmpeg zip is ~130 MB
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ---------------------------------------------------------------------------
# FFmpeg installer logic (runs in a background thread)
# ---------------------------------------------------------------------------

# PowerShell script that:
#   1. Tries winget (fastest, already on Windows 10/11)
#   2. Falls back to a direct GitHub release download + extract + PATH patch
_FFMPEG_PS_SCRIPT = r"""
$ErrorActionPreference = 'Stop'

# ── Try winget first ────────────────────────────────────────────────────────
$winget = Get-Command winget -ErrorAction SilentlyContinue
if ($winget) {
    Write-Output "STEP:winget"
    winget install --id Gyan.FFmpeg --source winget `
          --accept-package-agreements --accept-source-agreements --silent
    if ($LASTEXITCODE -eq 0) { Write-Output "DONE:winget"; exit 0 }
    Write-Output "WARN:winget failed, falling back to manual install"
}

# ── Manual fallback: download ffmpeg-release-essentials.zip from GitHub ────
Write-Output "STEP:download"
$dest    = "$env:LOCALAPPDATA\OmniGet\ffmpeg"
$zip     = "$env:TEMP\ffmpeg_omniget.zip"
$release = "https://github.com/GyanD/codexffmpeg/releases/latest/download/ffmpeg-release-essentials.zip"

New-Item -ItemType Directory -Force -Path $dest | Out-Null
Invoke-WebRequest -Uri $release -OutFile $zip -UseBasicParsing

Write-Output "STEP:extract"
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip_obj = [System.IO.Compression.ZipFile]::OpenRead($zip)
foreach ($entry in $zip_obj.Entries) {
    $name = $entry.FullName
    # Only extract bin\*.exe files
    if ($name -match 'bin\\(ffmpeg|ffprobe|ffplay)\.exe$') {
        $outFile = Join-Path $dest ([System.IO.Path]::GetFileName($name))
        [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $outFile, $true)
    }
}
$zip_obj.Dispose()
Remove-Item $zip -Force

# ── Patch user PATH permanently ─────────────────────────────────────────────
Write-Output "STEP:path"
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($userPath -notlike "*$dest*") {
    [Environment]::SetEnvironmentVariable('Path', "$userPath;$dest", 'User')
}
# Also patch current session so we don't need a restart
$env:Path += ";$dest"

Write-Output "DONE:manual"
"""


class SetupWindow(ctk.CTkToplevel):
    """
    Small splash / progress window shown while dependencies install.
    Blocks the main event loop via wait_window().
    """

    def __init__(self, master=None):
        super().__init__(master)
        self.title("OmniGet – First-Run Setup")
        self.geometry(self._center(480, 260))
        self.resizable(False, False)
        self.grab_set()          # Modal – user cannot click behind it
        self.protocol("WM_DELETE_WINDOW", lambda: None)  # Prevent manual close

        self.grid_columnconfigure(0, weight=1)

        # Icon / heading
        ctk.CTkLabel(
            self,
            text="⚙  First-Run Setup",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, pady=(24, 4), padx=24, sticky="w")

        ctk.CTkLabel(
            self,
            text="OmniGet needs FFmpeg to merge video and audio streams.\n"
                 "It will be downloaded and configured automatically.",
            font=ctk.CTkFont(size=13),
            text_color="gray",
            justify="left",
            wraplength=430,
        ).grid(row=1, column=0, padx=24, pady=(0, 16), sticky="w")

        # Spinner / progress bar (indeterminate while installing)
        self.progress = ctk.CTkProgressBar(self, mode="indeterminate", height=12)
        self.progress.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 8))
        self.progress.start()

        # Status text
        self.status_lbl = ctk.CTkLabel(
            self,
            text="Checking system…",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
        )
        self.status_lbl.grid(row=3, column=0, sticky="w", padx=24)

        # Result will be stored here so the caller can check it
        self.success = False
        self.error_message = ""

    # ------------------------------------------------------------------ #

    def run_install(self):
        """Start the install thread and block until it finishes."""
        t = threading.Thread(target=self._install_worker, daemon=True)
        t.start()
        # Keep the window alive until the thread calls self.destroy()
        self.wait_window()

    def _set_status(self, text: str):
        """Thread-safe status update."""
        self.after(0, lambda: self.status_lbl.configure(text=text))

    def _install_worker(self):
        """Runs in a background thread – does the actual installation."""
        try:
            self._set_status("Running installer via PowerShell…")
            rc, out, err = _run_ps(_FFMPEG_PS_SCRIPT)

            if "DONE:" in out or rc == 0:
                # Also refresh PATH in the current process so ffmpeg works
                # immediately without restarting the exe.
                dest = os.path.join(
                    os.environ.get("LOCALAPPDATA", ""), "OmniGet", "ffmpeg"
                )
                if os.path.isdir(dest) and dest not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + dest

                self.success = True
                self._set_status("✅ FFmpeg installed successfully!")
                self.after(1200, self.destroy)
            else:
                self.success = False
                self.error_message = err or out or "Unknown error."
                self._set_status(f"⚠  Install failed. See error dialog.")
                self.after(500, self._show_error)

        except subprocess.TimeoutExpired:
            self.success = False
            self.error_message = "Installation timed out (>5 min)."
            self._set_status("⚠  Timed out.")
            self.after(500, self._show_error)

        except Exception as exc:
            self.success = False
            self.error_message = str(exc)
            self._set_status("⚠  Unexpected error.")
            self.after(500, self._show_error)

    def _show_error(self):
        """Replace the progress bar with an error message + manual instructions."""
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(0)

        ctk.CTkLabel(
            self,
            text=(
                "Could not install FFmpeg automatically.\n\n"
                "Please install it manually:\n"
                "  winget install Gyan.FFmpeg\n\n"
                f"Error: {self.error_message[:120]}"
            ),
            font=ctk.CTkFont(size=11),
            text_color="#e05252",
            justify="left",
            wraplength=430,
        ).grid(row=4, column=0, padx=24, pady=(8, 0), sticky="w")

        ctk.CTkButton(
            self,
            text="Continue Anyway",
            width=140,
            command=self.destroy,
        ).grid(row=5, column=0, pady=(12, 16))

    @staticmethod
    def _center(w: int, h: int) -> str:
        import tkinter as tk
        t = tk.Tk(); t.withdraw()
        sw, sh = t.winfo_screenwidth(), t.winfo_screenheight()
        t.destroy()
        return f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def ensure_dependencies(master_root=None) -> bool:
    """
    Check all runtime dependencies. If anything is missing, install it.

    Parameters
    ----------
    master_root : ctk.CTk | None
        The parent CTk root (used to keep the splash modal). Pass None if
        called before the main window exists.

    Returns
    -------
    bool
        True  – all dependencies are satisfied (or were just installed).
        False – something is still missing (user chose to continue anyway).
    """
    all_ok = True

    # ── FFmpeg ───────────────────────────────────────────────────────────────
    if not _ffmpeg_is_available():
        splash = SetupWindow(master=master_root)
        splash.run_install()         # blocks until done
        all_ok = splash.success

    return all_ok

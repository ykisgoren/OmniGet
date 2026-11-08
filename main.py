"""
main.py
=======
OmniGet – Universal Video Downloader
-------------------------------------
Entry point and GUI layer built with CustomTkinter.

Run with:
    python main.py          (from an activated venv)

Build a standalone .exe with:
    pyinstaller --onefile --windowed --name OmniGet main.py
"""

import threading
import customtkinter as ctk

# Import the download engine (kept completely separate from the UI).
from downloader import (
    start_download,
    FORMAT_BEST,
    FORMAT_AUDIO,
    FORMAT_VIDEO,
)


# ---------------------------------------------------------------------------
# Appearance defaults – set before any widget is created
# ---------------------------------------------------------------------------
ctk.set_appearance_mode("System")          # Follows OS dark/light preference
ctk.set_default_color_theme("blue")        # Clean blue accent palette


# ---------------------------------------------------------------------------
# Main application class
# ---------------------------------------------------------------------------

class OmniGetApp(ctk.CTk):
    """
    The root window of OmniGet.

    Responsibilities
    ----------------
    - Build and lay out every widget.
    - Dispatch download tasks to a background thread.
    - Receive real-time progress updates (via after()) and push them to the UI.
    - Prevent multiple simultaneous downloads by disabling the Download button.
    """

    # Window geometry
    WIN_WIDTH  = 620
    WIN_HEIGHT = 420

    # Format choices (must stay in sync with downloader.py FORMAT_* constants)
    FORMAT_OPTIONS = [FORMAT_BEST, FORMAT_AUDIO, FORMAT_VIDEO]

    def __init__(self):
        super().__init__()

        # ------------------------------------------------------------------ #
        # Window setup                                                         #
        # ------------------------------------------------------------------ #
        self.title("OmniGet – Universal Video Downloader")
        self.geometry(self._center_geometry(self.WIN_WIDTH, self.WIN_HEIGHT))
        self.resizable(False, False)        # Fixed size for a clean look

        # ------------------------------------------------------------------ #
        # Layout grid: 1 column that fills the window                         #
        # ------------------------------------------------------------------ #
        self.grid_columnconfigure(0, weight=1)

        # ------------------------------------------------------------------ #
        # Build UI sections                                                    #
        # ------------------------------------------------------------------ #
        self._build_header()
        self._build_url_section()
        self._build_format_section()
        self._build_action_section()
        self._build_progress_section()
        self._build_footer()

    # ------------------------------------------------------------------ #
    # Widget builders                                                       #
    # ------------------------------------------------------------------ #

    def _build_header(self):
        """App title and subtitle banner."""
        header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 4))
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_frame,
            text="OmniGet",
            font=ctk.CTkFont(size=28, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header_frame,
            text="Universal Video Downloader  •  Powered by yt-dlp",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        ).grid(row=1, column=0, sticky="w")

    def _build_url_section(self):
        """URL entry field with label."""
        url_frame = ctk.CTkFrame(self, corner_radius=10)
        url_frame.grid(row=1, column=0, sticky="ew", padx=24, pady=(12, 0))
        url_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            url_frame,
            text="Video URL",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 2))

        self.url_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="Paste a YouTube, Vimeo, or any supported URL here…",
            height=40,
            font=ctk.CTkFont(size=13),
        )
        self.url_entry.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))

    def _build_format_section(self):
        """Format dropdown with label."""
        fmt_frame = ctk.CTkFrame(self, corner_radius=10)
        fmt_frame.grid(row=2, column=0, sticky="ew", padx=24, pady=(10, 0))
        fmt_frame.grid_columnconfigure(0, weight=1)
        fmt_frame.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            fmt_frame,
            text="Download Format",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 2))

        self.format_var = ctk.StringVar(value=self.FORMAT_OPTIONS[0])

        self.format_menu = ctk.CTkOptionMenu(
            fmt_frame,
            variable=self.format_var,
            values=self.FORMAT_OPTIONS,
            width=240,
            height=36,
            font=ctk.CTkFont(size=13),
        )
        self.format_menu.grid(row=0, column=1, sticky="e", padx=14, pady=(10, 10))

    def _build_action_section(self):
        """Download button."""
        action_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        action_frame.grid(row=3, column=0, sticky="ew", padx=24, pady=(12, 0))
        action_frame.grid_columnconfigure(0, weight=1)

        self.download_btn = ctk.CTkButton(
            action_frame,
            text="⬇  Download",
            height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._on_download_click,
        )
        self.download_btn.grid(row=0, column=0, sticky="ew")

    def _build_progress_section(self):
        """Progress bar + status label."""
        prog_frame = ctk.CTkFrame(self, corner_radius=10)
        prog_frame.grid(row=4, column=0, sticky="ew", padx=24, pady=(14, 0))
        prog_frame.grid_columnconfigure(0, weight=1)

        # Progress bar – starts empty (value=0)
        self.progress_bar = ctk.CTkProgressBar(
            prog_frame,
            height=16,
            mode="determinate",
        )
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))

        # Status label below the bar
        self.status_label = ctk.CTkLabel(
            prog_frame,
            text="Ready – paste a URL and press Download.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
        )
        self.status_label.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))

    def _build_footer(self):
        """Small footer with appearance-mode toggle."""
        footer_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        footer_frame.grid(row=5, column=0, sticky="ew", padx=24, pady=(12, 16))
        footer_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            footer_frame,
            text="Open-source • github.com/your-username/OmniGet",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).grid(row=0, column=0, sticky="w")

        # Appearance toggle (Light / Dark / System)
        self.appearance_menu = ctk.CTkOptionMenu(
            footer_frame,
            values=["System", "Light", "Dark"],
            width=110,
            height=28,
            font=ctk.CTkFont(size=11),
            command=self._change_appearance,
        )
        self.appearance_menu.set("System")
        self.appearance_menu.grid(row=0, column=1, sticky="e")

    # ------------------------------------------------------------------ #
    # Event handlers                                                        #
    # ------------------------------------------------------------------ #

    def _on_download_click(self):
        """
        Triggered when the user presses Download.

        Validates inputs, disables the button, resets the progress bar, then
        spawns a daemon thread that calls downloader.start_download().
        The thread communicates back via self._handle_progress(), which is
        marshalled to the main thread using self.after().
        """
        url           = self.url_entry.get().strip()
        format_choice = self.format_var.get()

        if not url:
            self._update_status("⚠  Please paste a URL first.", is_error=True)
            return

        # Reset UI state for new download
        self.download_btn.configure(state="disabled", text="Downloading…")
        self.format_menu.configure(state="disabled")
        self.progress_bar.set(0)
        self._update_status("Starting download…")

        # Spawn background thread so the GUI stays responsive
        thread = threading.Thread(
            target=start_download,
            args=(url, format_choice, self._thread_safe_callback),
            daemon=True,   # Thread exits automatically when the app closes
        )
        thread.start()

    def _thread_safe_callback(self, data: dict):
        """
        Called from the downloader thread – must NOT touch Tkinter widgets
        directly. Instead, schedule _handle_progress on the main thread.
        """
        # after(0, ...) queues the call for the next Tk event-loop iteration.
        self.after(0, self._handle_progress, data)

    def _handle_progress(self, data: dict):
        """
        Receives progress data on the main thread and updates widgets.

        Parameters
        ----------
        data : dict
            Keys: status, percent (0-1 float | None), message (str).
        """
        status  = data.get("status")
        percent = data.get("percent")
        message = data.get("message", "")

        # Update the progress bar if we have a valid percentage
        if percent is not None:
            self.progress_bar.set(percent)

        if status == "downloading":
            self._update_status(message)

        elif status == "finished":
            # Raw download done; FFmpeg may still be running
            self.progress_bar.set(1.0)
            self._update_status(message)

        elif status == "done":
            # Everything complete
            self.progress_bar.set(1.0)
            self._update_status(message)
            self._re_enable_controls()

        elif status == "error":
            self.progress_bar.set(0)
            self._update_status(message, is_error=True)
            self._re_enable_controls()

    # ------------------------------------------------------------------ #
    # Helpers                                                               #
    # ------------------------------------------------------------------ #

    def _update_status(self, text: str, is_error: bool = False):
        """Update the status label text and colour."""
        color = "#e05252" if is_error else ("gray" if ctk.get_appearance_mode() == "Light" else "#aaaaaa")
        self.status_label.configure(text=text, text_color=color)

    def _re_enable_controls(self):
        """Re-enable the Download button and format menu after a job finishes."""
        self.download_btn.configure(state="normal", text="⬇  Download")
        self.format_menu.configure(state="normal")

    @staticmethod
    def _change_appearance(mode: str):
        """Switch the global CTk appearance mode."""
        ctk.set_appearance_mode(mode)

    @staticmethod
    def _center_geometry(width: int, height: int) -> str:
        """
        Return a Tkinter geometry string that centres the window on screen.

        Uses a temporary hidden root trick to query the screen dimensions
        before the main window is fully realised.
        """
        import tkinter as tk
        tmp = tk.Tk()
        tmp.withdraw()
        screen_w = tmp.winfo_screenwidth()
        screen_h = tmp.winfo_screenheight()
        tmp.destroy()

        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        return f"{width}x{height}+{x}+{y}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = OmniGetApp()
    app.mainloop()

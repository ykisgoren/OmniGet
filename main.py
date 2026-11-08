"""
main.py
=======
OmniGet - Universal Video Downloader
-------------------------------------
Entry point and GUI layer built with CustomTkinter.

The window is resizable and enforces a minimum size so no widget is ever
clipped, regardless of the user's display DPI or scaling.

On first run (or when FFmpeg is missing), setup_checker.py installs it
automatically via PowerShell before the main window opens.

Build a standalone .exe:
    pyinstaller --onefile --windowed --name OmniGet
        --collect-data customtkinter --collect-data yt_dlp main.py
"""

import threading
import customtkinter as ctk

# Self-bootstrapping dependency check (runs before the main UI).
from setup_checker import ensure_dependencies

# Download engine - completely UI-independent.
from downloader import (
    start_download,
    FORMAT_BEST,
    FORMAT_AUDIO,
    FORMAT_VIDEO,
)


# ---------------------------------------------------------------------------
# Global appearance - set before any widget is created
# ---------------------------------------------------------------------------
ctk.set_appearance_mode("System")      # Tracks OS dark / light preference
ctk.set_default_color_theme("blue")


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------

class OmniGetApp(ctk.CTk):
    """
    Root window of OmniGet.

    Layout (top to bottom, single stretching column):
        Header  (title + subtitle)
        URL card
        Format + Download card
        Progress card
        Footer
    """

    WIN_WIDTH   = 620
    WIN_HEIGHT  = 440      # Comfortable default
    WIN_MIN_H   = 420      # Never shrink below this
    PADX        = 20       # Horizontal outer padding
    CARD_PAD    = 12       # Inner card padding

    FORMAT_OPTIONS = [FORMAT_BEST, FORMAT_AUDIO, FORMAT_VIDEO]

    def __init__(self):
        super().__init__()

        # -- Window chrome ---------------------------------------------------
        self.title("OmniGet - Universal Video Downloader")
        self.geometry(self._center_geometry(self.WIN_WIDTH, self.WIN_HEIGHT))
        self.minsize(self.WIN_WIDTH, self.WIN_MIN_H)
        self.resizable(True, True)      # Allow resize so nothing gets clipped

        # Single stretching column
        self.grid_columnconfigure(0, weight=1)
        # Progress card row absorbs any extra vertical space
        self.grid_rowconfigure(3, weight=1)

        # -- Build all sections ----------------------------------------------
        self._build_header()        # row 0
        self._build_url_card()      # row 1
        self._build_action_card()   # row 2  (format dropdown + download btn)
        self._build_progress_card() # row 3
        self._build_footer()        # row 4

    # ------------------------------------------------------------------ #
    # Section builders                                                      #
    # ------------------------------------------------------------------ #

    def _build_header(self):
        """Title banner row."""
        hf = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        hf.grid(row=0, column=0, sticky="ew", padx=self.PADX, pady=(20, 6))
        hf.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hf, text="OmniGet",
            font=ctk.CTkFont(size=26, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            hf,
            text="Universal Video Downloader  |  Powered by yt-dlp",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        ).grid(row=1, column=0, sticky="w")

    def _build_url_card(self):
        """URL input card."""
        card = ctk.CTkFrame(self, corner_radius=10)
        card.grid(row=1, column=0, sticky="ew", padx=self.PADX, pady=(0, 8))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="Video URL",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=self.CARD_PAD, pady=(10, 2))

        self.url_entry = ctk.CTkEntry(
            card,
            placeholder_text="Paste a YouTube, Vimeo, or any supported URL here...",
            height=38,
            font=ctk.CTkFont(size=13),
        )
        self.url_entry.grid(
            row=1, column=0, sticky="ew",
            padx=self.CARD_PAD, pady=(0, 10),
        )

    def _build_action_card(self):
        """
        Combined card: format selector on the left, Download button on the right.
        Putting them in one card keeps the layout compact and unambiguous.
        """
        card = ctk.CTkFrame(self, corner_radius=10)
        card.grid(row=2, column=0, sticky="ew", padx=self.PADX, pady=(0, 8))
        card.grid_columnconfigure(0, weight=1)   # label
        card.grid_columnconfigure(1, weight=0)   # dropdown  (fixed width)
        card.grid_columnconfigure(2, weight=0)   # button    (fixed width)

        # -- Format label ----------------------------------------------------
        ctk.CTkLabel(
            card, text="Format",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(self.CARD_PAD, 6), pady=12)

        # -- Dropdown --------------------------------------------------------
        self.format_var = ctk.StringVar(value=self.FORMAT_OPTIONS[0])
        self.format_menu = ctk.CTkOptionMenu(
            card,
            variable=self.format_var,
            values=self.FORMAT_OPTIONS,
            width=210,
            height=36,
            font=ctk.CTkFont(size=12),
        )
        self.format_menu.grid(row=0, column=1, padx=6, pady=12)

        # -- Download button -------------------------------------------------
        self.download_btn = ctk.CTkButton(
            card,
            text="Download",
            width=148,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_download_click,
        )
        self.download_btn.grid(
            row=0, column=2,
            padx=(6, self.CARD_PAD), pady=12,
        )

    def _build_progress_card(self):
        """Progress bar + multi-line status label."""
        card = ctk.CTkFrame(self, corner_radius=10)
        card.grid(row=3, column=0, sticky="nsew", padx=self.PADX, pady=(0, 8))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            card, text="Progress",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=self.CARD_PAD, pady=(10, 4))

        self.progress_bar = ctk.CTkProgressBar(card, height=14, mode="determinate")
        self.progress_bar.set(0)
        self.progress_bar.grid(
            row=1, column=0, sticky="ew",
            padx=self.CARD_PAD, pady=(0, 6),
        )

        self.status_label = ctk.CTkLabel(
            card,
            text="Ready - paste a URL and press Download.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
            wraplength=560,     # Wraps long error messages cleanly
            justify="left",
        )
        self.status_label.grid(
            row=2, column=0, sticky="ew",
            padx=self.CARD_PAD, pady=(0, 10),
        )

    def _build_footer(self):
        """Footer: GitHub link on the left, appearance toggle on the right."""
        ff = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        ff.grid(row=4, column=0, sticky="ew", padx=self.PADX, pady=(0, 14))
        ff.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            ff,
            text="Open-source  |  github.com/ykisgoren/OmniGet",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).grid(row=0, column=0, sticky="w")

        # -- Appearance toggle -----------------------------------------------
        ctk.CTkLabel(
            ff, text="Theme:",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).grid(row=0, column=1, padx=(0, 4))

        self.appearance_menu = ctk.CTkOptionMenu(
            ff,
            values=["System", "Light", "Dark"],
            width=100,
            height=26,
            font=ctk.CTkFont(size=11),
            command=ctk.set_appearance_mode,
        )
        self.appearance_menu.set("System")
        self.appearance_menu.grid(row=0, column=2)

    # ------------------------------------------------------------------ #
    # Event handlers                                                        #
    # ------------------------------------------------------------------ #

    def _on_download_click(self):
        """
        Validate, disable controls, then start download in a daemon thread.
        """
        url           = self.url_entry.get().strip()
        format_choice = self.format_var.get()

        if not url:
            self._update_status("Please paste a URL first.", is_error=True)
            return

        # Reset UI
        self.download_btn.configure(state="disabled", text="Downloading...")
        self.format_menu.configure(state="disabled")
        self.progress_bar.set(0)
        self._update_status("Starting download...")

        threading.Thread(
            target=start_download,
            args=(url, format_choice, self._thread_safe_callback),
            daemon=True,
        ).start()

    def _thread_safe_callback(self, data: dict):
        """Route hook events from the download thread to the main thread."""
        self.after(0, self._handle_progress, data)

    def _handle_progress(self, data: dict):
        """Update widgets from the main thread."""
        status  = data.get("status")
        percent = data.get("percent")
        message = data.get("message", "")

        if percent is not None:
            self.progress_bar.set(percent)

        if status == "downloading":
            self._update_status(message)
        elif status == "finished":
            self.progress_bar.set(1.0)
            self._update_status(message)
        elif status == "done":
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
        color = "#e05252" if is_error else "gray"
        self.status_label.configure(text=text, text_color=color)

    def _re_enable_controls(self):
        self.download_btn.configure(state="normal", text="Download")
        self.format_menu.configure(state="normal")

    @staticmethod
    def _center_geometry(width: int, height: int) -> str:
        """Return a geometry string centred on the primary monitor."""
        import tkinter as tk
        t = tk.Tk(); t.withdraw()
        sw, sh = t.winfo_screenwidth(), t.winfo_screenheight()
        t.destroy()
        return f"{width}x{height}+{(sw-width)//2}+{(sh-height)//2}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Build the main window first so the setup splash has a Tk parent.
    app = OmniGetApp()

    # Run dependency check with the real window as parent (modal splash).
    ensure_dependencies(master_root=app)

    # All good - show the main window.
    app.mainloop()

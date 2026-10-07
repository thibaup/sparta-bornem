import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, Toplevel
from tkinter import font as tkFont
import os
import sys
import subprocess
import time
import json
import urllib.request
import random
import re
import webbrowser
from urllib.error import HTTPError, URLError
import threading
import queue
import http.server
import socketserver
import stat
import utils
try:
    from PIL import Image
except ImportError:
    Image = None
import warnings

# Prevent DecompressionBombError for large images
if Image is not None:
    Image.MAX_IMAGE_PIXELS = None
warnings.filterwarnings("ignore", category=UserWarning, module="PIL.Image")

# --- Config Loading with GUI Error Handling ---
try:
    import config
except ImportError:
    # Create a temporary root just to show the error
    temp_root = tk.Tk()
    temp_root.withdraw()
    messagebox.showerror("Fatal App Error", "config.py not found.\nPlease ensure the configuration file is present.")
    temp_root.destroy()
    sys.exit(1)

# --- Tab Imports ---
try:
    from tabs.news_tab import create_news_tab
    from tabs.records_tab import create_records_tab
    from tabs.calendar_tab import create_calendar_tab
    from tabs.documents_tab import create_documents_tab
    from tabs.trainers_tab import create_trainers_tab
    from tabs.sponsors_tab import create_sponsors_tab
    from tabs.bestuur_tab import create_people_tab
    from tabs.ages_tab import create_ages_tab
    from tabs.faq_tab import create_faq_tab
    from tabs.text_editor_tab import create_text_editor_tab
    from tabs.media_manager_tab import create_media_manager_tab
    from tabs.images_tab import create_images_tab
except ImportError as e:
    temp_root = tk.Tk()
    temp_root.withdraw()
    messagebox.showerror("Fatal App Error", f"Failed to load tab modules:\n{e}")
    temp_root.destroy()
    sys.exit(1)


class WebsiteEditorApp:
    def __init__(self, root):
        self.root = root
        utils.recover_editor_transactions()
        self.root.title("Thiberta Software - Website Editor")

        # Center the window
        window_width = 1300
        window_height = 950
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)
        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        self.root.minsize(1080, 760)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.text_editor_parsed_soups = {}
        self.tab_managers = {}
        self._close_after_publish = False
        self._busy = False
        self._closing = False
        self._discarding_changes = False
        self._async_results = queue.SimpleQueue()

        self._setup_styles()
        self._create_widgets()
        self._layout_widgets()
        self._create_tabs()

        self.set_status("Editor gestart.")

        # Scheduled tasks
        self.root.after(100, self._perform_initial_load)
        self.root.after(300, self._check_for_app_update)
        self.root.after(50, self._drain_async_results)

    def _setup_styles(self):
        style = ttk.Style()
        try:
            themes = style.theme_names()
            # Prefer modern looking themes
            preferred_themes = ["clam", "vista", "aqua", "default"]
            for theme in preferred_themes:
                if theme in themes:
                    style.theme_use(theme)
                    break
        except tk.TclError:
            pass

        self.default_font_family = "Segoe UI" if sys.platform == "win32" else "TkDefaultFont"
        self.default_font_size = 10
        self.desc_font_size = 9
        self.bold_font_weight = "bold"

        self.desc_font = tkFont.Font(family=self.default_font_family, size=self.desc_font_size)
        self.bold_font = tkFont.Font(family=self.default_font_family, size=self.default_font_size, weight=self.bold_font_weight)
        self.link_font = tkFont.Font(family=self.default_font_family, size=self.default_font_size, underline=True)
        self.title_font = tkFont.Font(family=self.default_font_family, size=self.default_font_size + 6, weight="bold")
        self.default_font = tkFont.Font(family=self.default_font_family, size=self.default_font_size)

        style.configure("TLabel", font=self.default_font)
        style.configure("TButton", font=self.default_font)
        style.configure("TEntry", font=self.default_font)
        style.configure("TCombobox", font=self.default_font)
        style.configure("Treeview.Heading", font=self.bold_font)
        style.configure("Treeview", rowheight=25, font=self.default_font)
        style.configure("TNotebook", padding=(4, 4))
        style.configure("TNotebook.Tab", padding=(12, 7), font=self.default_font)
        style.configure("BottomBar.TFrame", padding=(6, 4))
        style.configure("Status.TLabel", padding=(8, 4))
        style.configure("Primary.TButton", font=self.bold_font)

        # Custom Styles
        style.configure("Desc.TLabel", foreground="#6B7280", font=self.desc_font)
        style.configure("Error.TLabel", foreground="red", font=self.default_font)
        style.configure("Bold.TLabel", font=self.bold_font)
        style.configure("Warning.TLabel", foreground="orange", font=self.default_font)
        style.configure("Notify.TLabel", foreground="#D35400", font=self.default_font)
        style.configure("Link.TLabel", foreground="#1774b4", font=self.link_font)
        style.configure("Title.TLabel", font=self.title_font)
        style.configure("Card.TFrame", padding=24, relief="groove", borderwidth=1)
        style.configure("Inline.TFrame", padding=0)

        try:
            style.map("TEntry", fieldbackground=[("invalid", "#FED8D8"), ("!invalid", "white")])
        except tk.TclError:
            pass

    def _create_widgets(self):
        self.main_frame = ttk.Frame(self.root)
        self.notebook = ttk.Notebook(self.main_frame)
        self.bottom_bar = ttk.Frame(self.main_frame, style="BottomBar.TFrame")

        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(self.bottom_bar, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, style="Status.TLabel")

        # Progress bar for async operations
        self.progress_bar = ttk.Progressbar(self.bottom_bar, mode='indeterminate', length=200)

        self.reload_button = ttk.Button(self.bottom_bar, text="Alles herladen", command=self._reload_all_tabs)
        self.preview_button = ttk.Button(self.bottom_bar, text="Preview openen", command=self._open_preview_external)
        self.git_publish_button = ttk.Button(self.bottom_bar, text="Wijzigingen publiceren", command=self._git_publish_click, style="Primary.TButton")

    def _layout_widgets(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.notebook.grid(row=0, column=0, pady=(8, 8), padx=10, sticky="nsew")

        self.bottom_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), pady=2)

        # Progress bar is packed but hidden initially
        self.git_publish_button.pack(side=tk.RIGHT, pady=2)
        self.preview_button.pack(side=tk.RIGHT, padx=(0, 8), pady=2)
        self.reload_button.pack(side=tk.RIGHT, padx=(0, 8), pady=2)

    def _create_tabs(self):
        tab_definitions = [
            (" Nieuws Beheren ", create_news_tab, "news", 0),
            (" Records Bewerken ", create_records_tab, "records", 10),
            (" Kalender Bewerken ", create_calendar_tab, "calendar", 10),
            (" Documenten ", create_documents_tab, "documents", 10),
            (" Trainers & Tijden ", create_trainers_tab, "trainers", 10),
            (" Bestuur & Jury ", create_people_tab, "bestuur_jury", 10),
            (" Leeftijden ", create_ages_tab, "ages", 0),
            (" FAQ ", create_faq_tab, "faq", 10),
            (" Sponsors ", create_sponsors_tab, "sponsors", 0),
            (" Images ", create_images_tab, "images", 10),
            (" Media Beheren ", create_media_manager_tab, "media", 0),
            (" Website Tekst ", create_text_editor_tab, "text_editor", 10),
        ]

        for text, creator_func, key, padding in tab_definitions:
            frame = ttk.Frame(self.notebook, padding=padding)
            frame.grid_rowconfigure(0, weight=1)
            frame.grid_columnconfigure(0, weight=1)
            self.notebook.add(frame, text=text)
            self.tab_managers[key] = creator_func(frame, self)

        self.tab_managers["preview"] = PreviewManager(None, self)

    def _open_preview_external(self):
        preview = self.tab_managers.get("preview")
        if preview and hasattr(preview, "open_external"):
            preview.open_external()
            self.set_status("Live preview geopend in de browser.", duration_ms=3000)
            return
        self.set_status("Live preview is nog niet beschikbaar.", is_error=True, duration_ms=4000)

    def toggle_interaction(self, enable=True):
        """Disables/Enables tabs and buttons during heavy operations."""
        self._busy = not enable
        state = "normal" if enable else "disabled"
        self.git_publish_button.config(state=state)
        self.reload_button.config(state=state)
        self.preview_button.config(state=state)
        if not enable:
            self._focus_before_busy = self.root.focus_get()
            self._busy_overlay = ttk.Frame(self.notebook, padding=30, takefocus=True)
            ttk.Label(self._busy_overlay, text="Git-bewerking bezig. Even geduld...").pack(expand=True)
            self._busy_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._busy_overlay.lift()
            self._busy_overlay.bind('<KeyPress>', lambda event: 'break')
            self._busy_overlay.focus_set()
            self.root.config(cursor="watch")
            self.progress_bar.pack(side=tk.RIGHT, padx=10)
            self.progress_bar.start(10)
        else:
            if getattr(self, '_busy_overlay', None):
                self._busy_overlay.destroy()
                self._busy_overlay = None
            focused = getattr(self, '_focus_before_busy', None)
            if focused and focused.winfo_exists():
                focused.focus_set()
            self.root.config(cursor="")
            self.progress_bar.stop()
            self.progress_bar.pack_forget()

    # --- Async Helper ---
    def _run_async_task(self, target_func, callback_func, *args):
        """Runs target_func in a thread, then calls callback_func on main thread with result."""
        def wrapper():
            try:
                result = target_func(*args)
            except Exception as e:
                result = e
            self._async_results.put((callback_func, result))

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()

    def _drain_async_results(self):
        if self._closing:
            return
        try:
            while not self._async_results.empty():
                callback, result = self._async_results.get_nowait()
                try:
                    callback(result)
                except Exception as error:
                    self.toggle_interaction(True)
                    self.set_status(f"Bewerking mislukt: {error}", is_error=True)
                if self._closing:
                    return
        finally:
            if not self._closing:
                self.root.after(50, self._drain_async_results)

    # --- Startup Logic ---
    def _perform_initial_load(self):
        self.set_status("Initiële data laden...", duration_ms=3000)
        self._reload_all_tabs(automatic=True)
        # Run git pull in background after UI is ready
        self.root.after(500, self._start_startup_pull)

    def _start_startup_pull(self):
        if self._closing:
            return
        if self._busy:
            self.root.after(500, self._start_startup_pull)
            return
        self.set_status("Controleren op updates (git pull)...")
        self.toggle_interaction(False)
        self._run_async_task(self._perform_git_pull_logic, self._on_startup_pull_complete)

    def _perform_git_pull_logic(self):
        target_branch = getattr(config, "GIT_TARGET_BRANCH", "main")
        branch = self._run_git_command(["git", "symbolic-ref", "--quiet", "--short", "HEAD"], "check startup branch")
        if branch.returncode != 0 or branch.stdout.strip() != target_branch:
            return subprocess.CompletedProcess([], 1, stdout="", stderr=f"Huidige branch is niet '{target_branch}'; automatisch herladen overgeslagen.")
        return self._run_git_command(["git", "pull", "--ff-only", "origin", target_branch], "git pull (startup)")

    def _on_startup_pull_complete(self, result):
        self.toggle_interaction(True)

        if isinstance(result, Exception):
            self.set_status(f"Fout tijdens update: {result}", is_error=True)
            return

        if result.returncode == 0:
            if "Already up to date" not in result.stdout:
                self.set_status("Bijgewerkt vanaf server. Herladen...", duration_ms=7000)
                messagebox.showinfo("Updates Gedownload", "Lokale bestanden bijgewerkt.\nTabs worden herladen.", parent=self.root)
                self._reload_all_tabs(automatic=True)
            else:
                self.set_status("Lokale versie is up-to-date.", duration_ms=5000)
        else:
            stderr_output = result.stderr or result.stdout
            err_msg = f"Automatische 'git pull' bij opstarten mislukt.\n\nGit Foutmelding:\n{stderr_output}"
            self.set_status("Opstart git pull mislukt.", is_error=True, duration_ms=10000)
            # Optional: Don't show popup on startup failure to avoid annoyance, just status bar
            print(err_msg)

    def set_status(self, message, is_error=False, duration_ms=0):
        if not hasattr(self, "status_var"): return
        self.status_var.set(message)
        self.status_label.config(foreground="red" if is_error else "black")

        if hasattr(self, "_status_clear_timer") and self._status_clear_timer:
            self.root.after_cancel(self._status_clear_timer)
            self._status_clear_timer = None

        if duration_ms > 0:
            self._status_clear_timer = self.root.after(duration_ms, self._clear_status)

    def _clear_status(self):
        if hasattr(self, "status_var"):
            self.status_var.set("")
        self._status_clear_timer = None

    def _unsaved_tab_keys(self):
        return [key for key, manager in self.tab_managers.items()
                if hasattr(manager, 'has_unsaved_changes') and manager.has_unsaved_changes()]

    def _reload_all_tabs(self, automatic=False):
        dirty = self._unsaved_tab_keys()
        if dirty and not automatic and not messagebox.askyesno(
                "Niet opgeslagen", "Er zijn niet-opgeslagen wijzigingen in: " + ', '.join(dirty) +
                ".\nToch alle tabs herladen en deze wijzigingen verwijderen?", icon='warning', parent=self.root):
            return
        self.set_status("Data herladen in tabs...", duration_ms=4000)

        reload_map = {
            "news": "_news_load_and_populate_treeview",
            "records": "_records_discover_and_populate_categories",
            "calendar": "_calendar_load_from_json",
            "documents": ["_rep_load", "_dl_load"],
            "trainers": "_trainers_load",
            "bestuur_jury": "reload",
            "ages": "_load_ages",
            "faq": "reload_data",
            "sponsors": "_load_sponsors",
            "images": "reload_data",
            "media": "reload_data",
            "text_editor": "_scan_and_populate_files",
        }

        failures = []
        self._discarding_changes = True
        try:
            for key, methods in reload_map.items():
                if automatic and key in dirty:
                    continue
                manager = self.tab_managers.get(key)
                if not manager: continue
                method_list = methods if isinstance(methods, (list, tuple)) else [methods]
                for method_name in method_list:
                    if hasattr(manager, method_name):
                        try:
                            if getattr(manager, method_name)() is False:
                                failures.append(key)
                        except Exception as e:
                            failures.append(key)
                            print(f"Error reloading tab '{key}' via '{method_name}': {e}")

        finally:
            self._discarding_changes = False
        self.root.update_idletasks()
        utils.cleanup_pending_assets(self)
        if failures:
            self.set_status("Herladen mislukt voor: " + ', '.join(sorted(set(failures))), is_error=True)
            return False
        self.set_status("Opgeslagen tabs herladen; niet-opgeslagen wijzigingen behouden." if automatic and dirty
                        else "Tabs herladen. Klaar.", duration_ms=3000)

    def _git_paths(self):
        base = getattr(config, "APP_BASE_DIR", "")
        g = os.path.join(base, ".git")
        return g, os.path.join(g, "index"), os.path.join(g, "index.lock")

    def _ensure_git_configs(self):
        self._run_git_command(["git", "config", "windows.appendAtomically", "false"], "config")
        self._run_git_command(["git", "config", "core.longpaths", "true"], "config")

    def _clear_stale_git_lock(self, stale_after_seconds=15 * 60):
        _, _, lock = self._git_paths()
        try:
            if not os.path.exists(lock):
                return True
            age_seconds = time.time() - os.path.getmtime(lock)
            if age_seconds < stale_after_seconds:
                return False
            os.remove(lock)
            return True
        except Exception:
            return False

    def _ensure_git_index_writable(self):
        _, idx, _ = self._git_paths()
        try:
            if os.path.exists(idx):
                os.chmod(idx, stat.S_IWRITE)
        except Exception:
            pass

    def _recover_git_index(self, rebuild=False):
        # Never delete the index or reset staging to recover a write error.
        self._ensure_git_index_writable()
        _, _, lock = self._git_paths()
        return not os.path.exists(lock)

    def _is_index_write_error(self, result):
        s = (result.stderr or "") + (result.stdout or "")
        s = s.lower()
        return ("could not write index" in s) or ("index.lock" in s) or ("invalid write operation detected" in s)

    def _run_git_index_safe(self, cmd, desc):
        res = self._run_git_command(cmd, desc)
        if res.returncode != 0 and self._is_index_write_error(res):
            if self._recover_git_index(rebuild=False):
                res = self._run_git_command(cmd, desc + " (retry)")
        return res

    def _run_git_command(self, command_list, description):
        # Note: This is called from background threads now.
        # Do not touch GUI widgets directly here (except thread-safe ones or via queue, but set_status uses var.set which is mostly safe in Tkinter, though better to be careful)

        self._ensure_git_index_writable()
        # self.set_status(f"Uitvoeren {description}...") # Avoid GUI updates from thread if possible

        if not os.path.isdir(config.APP_BASE_DIR):
            return subprocess.CompletedProcess(command_list, -1, stdout="", stderr="Base directory not found.")

        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        try:
            return subprocess.run(
                command_list,
                cwd=config.APP_BASE_DIR,
                capture_output=True,
                text=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                startupinfo=startupinfo,
                timeout=60,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            return subprocess.CompletedProcess(command_list, -1, stdout="", stderr=str(e))

    # --- Git Publish Workflow (Async) ---
    def _git_publish_click(self, close_after_success=False, discard_unsaved=False):
        if self._busy:
            return
        dirty = self._unsaved_tab_keys()
        if dirty and not discard_unsaved:
            messagebox.showwarning("Eerst opslaan", "Sla eerst de wijzigingen in deze tabs op: " + ', '.join(dirty), parent=self.root)
            return
        cleanup_errors = utils.cleanup_pending_assets(self, include_drafts=not discard_unsaved)
        if cleanup_errors:
            messagebox.showerror("Bestanden opruimen mislukt", '\n'.join(cleanup_errors), parent=self.root)
            return
        self._close_after_publish = False
        commit_msg = simpledialog.askstring("Commit Bericht", "Voer een beschrijving van de wijzigingen in:", parent=self.root)
        if not commit_msg:
            self.set_status("Publicatie geannuleerd.", duration_ms=3000)
            return

        if not messagebox.askyesno("Bevestig Publicatie", "Klaar om wijzigingen te publiceren?", parent=self.root):
            self.set_status("Publicatie geannuleerd.", duration_ms=3000)
            return

        self.set_status("Publiceren... Even geduld.")
        self.toggle_interaction(False)
        self._close_after_publish = bool(close_after_success)

        # Run the heavy lifting in a thread
        self._run_async_task(self._publication_workflow, self._on_publish_complete, commit_msg)

    def _on_publish_complete(self, result):
        self.toggle_interaction(True)
        close_after_publish = self._close_after_publish
        self._close_after_publish = False

        if isinstance(result, Exception):
            messagebox.showerror("Systeemfout", f"Er is een fout opgetreden:\n{result}", parent=self.root)
            self.set_status("Publicatie gecrasht.", is_error=True)
            return

        success, message = result
        if success:
            self._reload_all_tabs(automatic=True)
            messagebox.showinfo("Publicatie Succesvol", message, parent=self.root)
            self.set_status("Publicatie voltooid.", duration_ms=5000)
            if close_after_publish:
                self._destroy_app()
        else:
            messagebox.showerror("Publicatie Mislukt", message, parent=self.root)
            self.set_status("Publicatie mislukt.", is_error=True)

    def _publication_workflow(self, commit_msg):
        self._ensure_git_configs()
        target_branch = getattr(config, "GIT_TARGET_BRANCH", "main")
        branch = self._run_git_command(["git", "symbolic-ref", "--quiet", "--short", "HEAD"], "check branch")
        if branch.returncode != 0 or branch.stdout.strip() != target_branch:
            return False, f"Publiceren vereist de lokale branch '{target_branch}'. Huidige branch: {branch.stdout.strip() or 'onbekend'}."
        status = self._run_git_command(["git", "status", "--porcelain"], "check status")
        if status.returncode != 0:
            return False, f"Kon status niet controleren:\n{status.stderr}"
        conflicts = self._run_git_command(["git", "diff", "--name-only", "--diff-filter=U"], "check conflicts")
        if conflicts.returncode != 0 or conflicts.stdout.strip():
            return False, "Los eerst bestaande Git-conflicten op voordat je publiceert."

        stash_id = None

        def stash_head():
            result = self._run_git_command(["git", "rev-parse", "--verify", "refs/stash"], "check stash")
            return result.stdout.strip() if result.returncode == 0 else None

        def restore_local_changes():
            if not stash_id:
                return True, ""
            restored = self._run_git_index_safe(["git", "stash", "apply", "--index", stash_id], "restore editor changes")
            if restored.returncode != 0:
                return False, f"Lokale wijzigingen blijven bewaard in stash {stash_id}.\nHerstellen vereist aandacht; er zijn mogelijk conflicten.\n{restored.stderr or restored.stdout}"
            # Drop only this operation's stash, leaving any pre-existing stashes alone.
            listed = self._run_git_command(["git", "stash", "list", "--format=%gd:%H"], "find restored stash")
            for line in listed.stdout.splitlines():
                reference, _, identity = line.partition(':')
                if identity == stash_id:
                    self._run_git_command(["git", "stash", "drop", reference], "drop restored stash")
                    break
            return True, ""

        if status.stdout.strip():
            previous = stash_head()
            excludes = getattr(config, "GIT_STASH_EXCLUDES", [])
            pathspec = ["--", "."] + [f":(exclude){path}" for path in excludes]
            result = self._run_git_index_safe(["git", "stash", "push", "-u", "-m", "Website editor publication"] + pathspec, "save local changes")
            current = stash_head()
            if current and current != previous:
                stash_id = current
            if result.returncode != 0:
                _, recovery = restore_local_changes()
                return False, f"Stash mislukt:\n{result.stderr or result.stdout}\n{recovery}"

        pulled = self._run_git_command(["git", "pull", "--ff-only", "origin", target_branch], "git pull")
        restored, recovery = restore_local_changes()
        if pulled.returncode != 0:
            return False, f"Pull mislukt. {'Lokale wijzigingen zijn hersteld.' if restored else recovery}\n{pulled.stderr or pulled.stdout}"
        if not restored:
            return False, recovery

        publish_excludes = getattr(config, "GIT_STASH_EXCLUDES", [])
        publish_pathspec = ["--", "."] + [f":(exclude){path}" for path in publish_excludes]
        added = self._run_git_index_safe(["git", "add"] + publish_pathspec, "git add")
        if added.returncode != 0:
            return False, f"Git add mislukt:\n{added.stderr}"
        staged = self._run_git_command(["git", "diff", "--cached", "--quiet"] + publish_pathspec, "check staged changes")
        if staged.returncode not in (0, 1):
            return False, f"Kon wijzigingen niet controleren:\n{staged.stderr}"
        if staged.returncode == 1:
            committed = self._run_git_index_safe(["git", "commit", "--only", "-m", commit_msg] + publish_pathspec, "git commit")
            if committed.returncode != 0:
                return False, f"Commit mislukt:\n{committed.stderr or committed.stdout}"
        pushed = self._run_git_command(["git", "push", "origin", f"HEAD:{target_branch}"], "git push")
        if pushed.returncode != 0:
            return False, f"Push mislukt; lokale wijzigingen en commits zijn bewaard.\n{pushed.stderr or pushed.stdout}"
        return True, "Wijzigingen succesvol gepubliceerd."

    def _has_unpublished_changes(self):
        target_branch = getattr(config, "GIT_TARGET_BRANCH", "main")
        status_res = self._run_git_command(["git", "status", "--porcelain"], "check status")
        dirty = status_res.returncode == 0 and bool(status_res.stdout.strip())

        ahead_res = self._run_git_command(["git", "rev-list", "--count", f"origin/{target_branch}..HEAD"], "check ahead")
        ahead_count = ahead_res.stdout.strip() if ahead_res.returncode == 0 else "0"
        ahead = ahead_count.isdigit() and int(ahead_count) > 0

        return dirty or ahead

    def _on_close(self):
        if self._busy:
            self.set_status("Wacht tot de huidige Git-bewerking klaar is voordat je afsluit.", duration_ms=4000)
            return
        dirty = self._unsaved_tab_keys()
        if dirty and not messagebox.askyesno("Niet opgeslagen", "Er zijn niet-opgeslagen wijzigingen in: " +
                                            ', '.join(dirty) + ".\nAfsluiten zonder deze wijzigingen op te slaan?",
                                            icon='warning', parent=self.root):
            return
        # Check for changes in a simplified way (blocking is okay here as we are closing)
        try:
            if self._has_unpublished_changes():
                choice = messagebox.askyesnocancel(
                    "Ongepubliceerde wijzigingen",
                    "Er zijn wijzigingen die nog niet gepubliceerd zijn.\nWil je nu publiceren?\n\nJa = Publiceren en afsluiten\nNee = Afsluiten zonder publiceren\nAnnuleren = Terugkeren",
                    parent=self.root,
                )
                if choice is True:
                    self._git_publish_click(close_after_success=True, discard_unsaved=bool(dirty))
                    return
                elif choice is False:
                    pass # Close
                else:
                    return # Cancel
        except Exception:
            pass

        self._destroy_app()

    def _destroy_app(self):
        utils.cleanup_pending_assets(self, include_drafts=False)
        self._closing = True
        for m in self.tab_managers.values():
            if hasattr(m, "destroy"):
                m.destroy()
        self.root.destroy()

    # --- Version & Updates ---
    def _version_tuple(self, s):
        nums = [int(x) for x in re.findall(r"\d+", str(s))][:4]
        while len(nums) < 4: nums.append(0)
        return tuple(nums)

    def _win_file_version(self, path):
        try:
            import ctypes, ctypes.wintypes
            size = ctypes.windll.version.GetFileVersionInfoSizeW(path, None)
            if not size: return "0.0.0.0"
            res = ctypes.create_string_buffer(size)
            ctypes.windll.version.GetFileVersionInfoW(path, 0, size, res)
            lptr = ctypes.c_void_p()
            lsize = ctypes.wintypes.UINT()
            if not ctypes.windll.version.VerQueryValueW(res, "\\VarFileInfo\\Translation", ctypes.byref(lptr), ctypes.byref(lsize)):
                return "0.0.0.0"
            lang = ctypes.cast(lptr.value, ctypes.POINTER(ctypes.c_ushort))[0]
            codepage = ctypes.cast(lptr.value, ctypes.POINTER(ctypes.c_ushort))[1]
            block = f"\\StringFileInfo\\{lang:04x}{codepage:04x}\\FileVersion"
            if not ctypes.windll.version.VerQueryValueW(res, block, ctypes.byref(lptr), ctypes.byref(lsize)):
                return "0.0.0.0"
            return ctypes.wstring_at(lptr.value)
        except Exception:
            return "0.0.0.0"

    def _current_app_version(self):
        if sys.platform == "win32" and getattr(sys, "frozen", False):
            return self._win_file_version(sys.executable)
        return getattr(config, "APP_VERSION", "0.0.0.0")

    def _fetch_json(self, url, timeout=10):
        # ... (Same as original, omitted for brevity but assumed present) ...
        # Simplified for this output:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            return {}

    def _open_url(self, url):
        try: webbrowser.open(url)
        except Exception: pass

    def _show_update_dialog(self, latest, exe_url, notes):
        top = Toplevel(self.root)
        top.title("Nieuwe versie beschikbaar")
        top.transient(self.root)
        top.grab_set()

        frm = ttk.Frame(top, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")

        cur = self._current_app_version()
        ttk.Label(frm, text=f"Nieuwe versie: {latest}", style="Bold.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(frm, text=f"Huidige versie: {cur}", style="Desc.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 8))
        if notes:
            ttk.Label(frm, text=notes.strip(), wraplength=400).grid(row=2, column=0, sticky="w", pady=(0, 8))

        btns = ttk.Frame(frm)
        btns.grid(row=4, column=0, sticky="e")
        ttk.Button(btns, text="Downloaden", command=lambda: (self._open_url(exe_url), top.destroy())).pack(side="left", padx=5)
        ttk.Button(btns, text="Sluiten", command=top.destroy).pack(side="left")

        top.update_idletasks()
        w, h = top.winfo_width(), top.winfo_height()
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        top.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _check_for_app_update(self):
        # Run in thread to avoid startup freeze
        self._run_async_task(self._check_update_logic, self._on_update_check_complete)

    def _check_update_logic(self):
        default_url = "https://raw.githubusercontent.com/thibaup/sparta-bornem/main/update.json"
        url = getattr(config, "UPDATE_MANIFEST_URL", default_url) or default_url
        return self._fetch_json(url)

    def _on_update_check_complete(self, manifest):
        if not manifest or not isinstance(manifest, dict): return

        latest = str(manifest.get("version", "0.0.0.0"))
        exe_url = str(manifest.get("exe_url", "")).strip()
        notes = str(manifest.get("notes", "") or "")
        cur = self._current_app_version()

        if self._version_tuple(latest) > self._version_tuple(cur) and exe_url:
            self._show_update_dialog(latest, exe_url, notes)


class PreviewManager:
    def __init__(self, frame, app):
        self.app = app
        self.frame = frame
        self.toolbar = None
        self.view = None
        self.port = None
        self.server = None
        self.server_thread = None
        self.url_var = tk.StringVar()

        if self.frame is not None:
            self.toolbar = ttk.Frame(self.frame)
            self.toolbar.pack(side="top", fill="x")
            self.view = ttk.Frame(self.frame, padding=16)
            self.view.pack(side="top", fill="both", expand=True)
            self.open_btn = ttk.Button(self.toolbar, text="Open in browser", command=self._open_ext)
            self.copy_btn = ttk.Button(self.toolbar, text="Kopieer link", command=self._copy_link)
            self.open_btn.pack(side="left", padx=(0, 6))
            self.copy_btn.pack(side="left", padx=(0, 6))

        self._start_server()
        if self.view is not None:
            self._render_link()

    def _site_dir(self):
        base = getattr(config, "APP_BASE_DIR", "") or ""
        if base and os.path.isdir(base): return base
        if getattr(sys, "frozen", False): return os.path.dirname(sys.executable)
        return os.getcwd()

    def _url(self, path=""):
        return f"http://127.0.0.1:{self.port}/" + path

    def _start_server(self):
        import mimetypes, posixpath, shutil
        from urllib.parse import unquote
        root_dir = self._site_dir()

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, fmt, *args): pass
            def do_GET(self):
                try:
                    p = self.path.split("?", 1)[0].split("#", 1)[0]
                    p = posixpath.normpath(unquote(p))
                    if p.startswith("/"): p = p[1:]
                    full = os.path.normpath(os.path.join(root_dir, p))
                    if os.path.isdir(full): full = os.path.join(full, "index.html")
                    # Prevent path traversal outside the site root.
                    try:
                        root_abs = os.path.normcase(os.path.realpath(root_dir))
                        full_abs = os.path.normcase(os.path.realpath(full))
                        if os.path.commonpath([root_abs, full_abs]) != root_abs:
                            self.send_error(404); return
                    except ValueError:
                        self.send_error(404); return
                    if not os.path.exists(full):
                        self.send_error(404); return

                    ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
                    with open(full, "rb") as f:
                        self.send_response(200)
                        self.send_header("Content-Type", ctype)
                        self.send_header("Content-Length", str(os.stat(full).st_size))
                        self.end_headers()
                        shutil.copyfileobj(f, self.wfile)
                except Exception: pass

        class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
            daemon_threads = True
            allow_reuse_address = True

        self.server = ThreadedServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]

        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

    def _render_link(self):
        if self.view is None:
            return
        for w in self.view.winfo_children(): w.destroy()
        url = self._url()
        self.url_var.set(url)

        container = ttk.Frame(self.view)
        container.place(relx=0.5, rely=0.5, anchor="center")

        card = ttk.Frame(container, style="Card.TFrame")
        card.grid(row=0, column=0, sticky="nsew")

        ttk.Label(card, text="Live Preview", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(card, text="Open de website in je browser:", style="Desc.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 10))

        entry = ttk.Entry(card, width=50)
        entry.grid(row=2, column=0, sticky="w")
        entry.insert(0, url)
        entry.configure(state="readonly")

        ttk.Button(card, text="Openen", command=self._open_ext).grid(row=3, column=0, sticky="e", pady=(10,0))

    def _copy_link(self):
        self.app.root.clipboard_clear()
        self.app.root.clipboard_append(self._url())
        self.app.set_status("Link gekopieerd.", duration_ms=2500)

    def _open_ext(self):
        webbrowser.open(self._url())

    def get_url(self): return self._url()
    def open_external(self): self._open_ext()

    def destroy(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()


if __name__ == "__main__":
    root = tk.Tk()
    app = WebsiteEditorApp(root)
    root.mainloop()

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import sys
import subprocess

import config

from tabs.news_tab import create_news_tab
from tabs.records_tab import create_records_tab
from tabs.calendar_tab import create_calendar_tab
from tabs.reports_tab import create_reports_tab
from tabs.images_tab import create_images_tab
from tabs.text_editor_tab import create_text_editor_tab
from tabs.trainers_tab import create_trainers_tab

class WebsiteEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Thiberta Software - Website Editor")
        self.root.geometry("1300x950")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        try:
             themes = style.theme_names(); preferred_themes = ["clam", "vista", "aqua", "default"]
             for theme in preferred_themes:
                 if theme in themes: style.theme_use(theme); break
        except tk.TclError: pass
        self.default_font_family = "Segoe UI" if sys.platform == "win32" else "TkDefaultFont"; self.default_font_size = 9; self.desc_font_size = 8; self.bold_font_weight = 'bold'
        self.desc_font = (self.default_font_family, self.desc_font_size); self.bold_font = (self.default_font_family, self.default_font_size, self.bold_font_weight)
        style.configure("TLabel", font=(self.default_font_family, self.default_font_size)); style.configure("TButton", font=(self.default_font_family, self.default_font_size))
        style.configure("TEntry", font=(self.default_font_family, self.default_font_size)); style.configure("TCombobox", font=(self.default_font_family, self.default_font_size))
        style.configure("Treeview.Heading", font=self.bold_font); style.configure("Treeview", rowheight=25, font=(self.default_font_family, self.default_font_size))
        style.configure("Desc.TLabel", foreground="grey", font=self.desc_font); style.configure("Error.TLabel", foreground="red", font=(self.default_font_family, self.default_font_size))
        style.configure("Bold.TLabel", font=self.bold_font); style.configure("Warning.TLabel", foreground="orange", font=(self.default_font_family, self.default_font_size))
        try: style.map('TEntry', fieldbackground=[('invalid', '#FED8D8'), ('!invalid', 'white')], bordercolor=[('invalid', 'red'), ('!invalid', 'grey')], foreground=[('invalid', 'black'), ('!invalid', 'black')])
        except tk.TclError: pass

        self.notebook = ttk.Notebook(root)
        self.notebook.grid(row=0, column=0, pady=10, padx=10, sticky='nsew')

        self.news_tab_frame = ttk.Frame(self.notebook, padding="0")
        self.records_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.calendar_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.reports_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.images_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.text_editor_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.trainers_tab_frame = ttk.Frame(self.notebook, padding="10") # New Frame

        for frame in [self.news_tab_frame, self.records_tab_frame, self.calendar_tab_frame, self.reports_tab_frame, self.images_tab_frame, self.text_editor_tab_frame, self.trainers_tab_frame]:
            frame.grid_rowconfigure(0, weight=1)
            frame.grid_columnconfigure(0, weight=1)

        self.notebook.add(self.news_tab_frame, text=' Nieuws Beheren ')
        self.notebook.add(self.records_tab_frame, text=' Records Bewerken ')
        self.notebook.add(self.calendar_tab_frame, text=' Kalender Bewerken ')
        self.notebook.add(self.reports_tab_frame, text=' Verslagen Beheren ')
        self.notebook.add(self.trainers_tab_frame, text=' Trainers & Tijden ') # New Tab Added
        self.notebook.add(self.images_tab_frame, text=' Afbeeldingen Beheren ')
        self.notebook.add(self.text_editor_tab_frame, text=' Website Tekst Bewerken ')


        bottom_bar_frame = ttk.Frame(root)
        bottom_bar_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 5))
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(bottom_bar_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), pady=2)
        self.git_publish_button = ttk.Button(bottom_bar_frame, text="Wijzigingen Publiceren (Git)", command=self._git_publish)
        self.git_publish_button.pack(side=tk.RIGHT, pady=2)
        self.set_status("Applicatie gestart. Initialiseren...")

        self.text_editor_parsed_soups = {} # Share parsed soups

        # Instantiate tabs
        self.news_tab_manager = create_news_tab(self.news_tab_frame, self)
        self.records_tab_manager = create_records_tab(self.records_tab_frame, self)
        self.calendar_tab_manager = create_calendar_tab(self.calendar_tab_frame, self)
        self.reports_tab_manager = create_reports_tab(self.reports_tab_frame, self)
        self.trainers_tab_manager = create_trainers_tab(self.trainers_tab_frame, self) # New Tab Instance
        self.images_tab_manager = create_images_tab(self.images_tab_frame, self)
        self.text_editor_tab_manager = create_text_editor_tab(self.text_editor_tab_frame, self)

        self.set_status("Initialisatie voltooid. Klaar.", duration_ms=5000)

    def _git_publish(self):
        git_dir = os.path.join(config.APP_BASE_DIR, '.git')
        if not os.path.isdir(git_dir):
            messagebox.showwarning("Git Fout", f"Kon geen '.git' map vinden in:\n{config.APP_BASE_DIR}\n\nZorg ervoor dat deze applicatie draait vanuit de hoofdmap van uw Git repository.", parent=self.root)
            self.set_status("Publiceren mislukt: Geen Git repository hoofdmap.", is_error=True); return
        commit_msg = simpledialog.askstring("Commit Bericht", "Voer een korte beschrijving van de wijzigingen in:", parent=self.root)
        if not commit_msg: self.set_status("Git publicatie geannuleerd: Geen commit bericht ingevoerd.", duration_ms=3000); return
        if not messagebox.askyesno("Bevestig Git Publicatie", f"Dit voert uit:\n1. git pull\n2. git add .\n3. git commit -m \"{commit_msg}\"\n4. git push\n\nDoorgaan?", parent=self.root):
            self.set_status("Git publicatie geannuleerd door gebruiker.", duration_ms=3000); return
        self.git_publish_button.config(state=tk.DISABLED); self.root.update_idletasks()
        def run_git_command(command_list, description):
            self.set_status(f"Uitvoeren {description}..."); self.root.update_idletasks(); startupinfo = None
            if sys.platform == "win32": startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startupinfo.wShowWindow = subprocess.SW_HIDE
            try:
                result = subprocess.run(command_list, cwd=config.APP_BASE_DIR, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace', startupinfo=startupinfo)
                return result
            except FileNotFoundError: return None
            except Exception as e: return False
        final_success, error_details = True, ""
        pull_result = run_git_command(['git', 'pull'], 'git pull')
        if pull_result is None or pull_result is False: error_details = "Commando Mislukt: git pull\n\nFout: 'git' niet gevonden of Python fout."; final_success = False
        elif pull_result.returncode != 0:
            if "Merge conflict" in pull_result.stdout or "Merge conflict" in pull_result.stderr or "Automatic merge failed" in pull_result.stderr: error_details = "Merge Conflict Gedetecteerd!\n\n'git pull' resulteerde in merge conflicten.\nLos conflicten handmatig op buiten deze app."; final_success = False
            else: error_details = f"Commando Mislukt: git pull\n\nFout Code: {pull_result.returncode}\n\n{pull_result.stderr or pull_result.stdout}"; final_success = False
        else: self.set_status("Pull succesvol. Doorgaan..."); self.root.update_idletasks()
        if final_success:
            add_result = run_git_command(['git', 'add', '.'], 'git add .');
            if add_result is None or add_result is False or add_result.returncode != 0: error_details = f"Commando Mislukt: git add .\n\n{add_result.stderr or add_result.stdout if isinstance(add_result, subprocess.CompletedProcess) else 'Git niet gevonden of Python fout'}"; final_success = False
        if final_success:
            commit_result = run_git_command(['git', 'commit', '-m', commit_msg], f'git commit -m "{commit_msg}"')
            if commit_result is None or commit_result is False: error_details = "Commando Mislukt: git commit\n\nGit niet gevonden of Python fout"; final_success = False
            elif commit_result.returncode != 0:
                 if "nothing to commit" in commit_result.stdout or "nothing added to commit" in commit_result.stderr or "no changes added to commit" in commit_result.stdout: self.set_status("Niets nieuws te committen. Controleer push..."); self.root.update_idletasks()
                 else: error_details = f"Commando Mislukt: git commit\n\nFout Code: {commit_result.returncode}\n\n{commit_result.stderr or commit_result.stdout}"; final_success = False
        if final_success:
             push_result = run_git_command(['git', 'push'], 'git push')
             if push_result is None or push_result is False or push_result.returncode != 0:
                  error_details = f"Commando Mislukt: git push\n\nFout Code: {push_result.returncode if isinstance(push_result, subprocess.CompletedProcess) else 'N/A'}\n\n{push_result.stderr or push_result.stdout if isinstance(push_result, subprocess.CompletedProcess) else 'Git niet gevonden of Python fout'}"
                  if isinstance(push_result, subprocess.CompletedProcess) and 'rejected' in push_result.stderr and ('non-fast-forward' in push_result.stderr or 'fetch first' in push_result.stderr): error_details += "\n\nHint: Externe wijzigingen bestaan. Probeer 'git pull' handmatig."
                  final_success = False
        self.git_publish_button.config(state=tk.NORMAL)
        if final_success: messagebox.showinfo("Git Publicatie Succesvol", "Wijzigingen succesvol gepulled, toegevoegd, gecommit, en gepushed.", parent=self.root); self.set_status("Git publicatie succesvol voltooid.", duration_ms=5000)
        else: messagebox.showerror("Git Publicatie Mislukt", error_details, parent=self.root); self.set_status("Git publicatie mislukt. Zie foutmelding popup.", is_error=True)

    def set_status(self, message, is_error=False, duration_ms=0):
        self.status_var.set(message); self.status_label.config(foreground="red" if is_error else "black")
        if hasattr(self, "_status_clear_timer") and self._status_clear_timer: self.root.after_cancel(self._status_clear_timer); self._status_clear_timer = None
        if duration_ms > 0: self._status_clear_timer = self.root.after(duration_ms, self._clear_status)

    def _clear_status(self):
        self.status_var.set(""); self.status_label.config(foreground="black"); self._status_clear_timer = None
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, Toplevel, Label, Entry, Button
from tkinter import font as tkFont
import os
import sys
import webbrowser
import subprocess
import shutil
import time
from pathlib import Path

try:
    import config
except ImportError as e:
        try:
            tk.Tk().withdraw()
            messagebox.showerror("Fatal Setup Error", f"Could not load config.py:\n{e}")
        except:
            pass
        sys.exit(1)

GIT_DOWNLOAD_URL = "https://git-scm.com/downloads"
GITHUB_SIGNUP_URL = "https://github.com/signup"
GITHUB_LOGIN_URL = "https://github.com/login"

def run_git_command(command_list, description="Git command", check_returncode=False):
    print(f"Running Git: {' '.join(command_list)} ({description})")
    app_base_dir_value = getattr(config, 'APP_BASE_DIR', '')
    if not app_base_dir_value:
        err_msg = "Git command error: config.APP_BASE_DIR is not set."
        print(err_msg)
        return subprocess.CompletedProcess(command_list, -1, stdout="", stderr=err_msg)
    base_path = Path(app_base_dir_value)
    try:
        base_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        err_msg = f"Git command error: Could not create base directory '{base_path}': {e}"
        print(err_msg)
        return subprocess.CompletedProcess(command_list, -1, stdout="", stderr=err_msg)
    if not base_path.is_dir():
        err_msg = f"Git command error: Base path '{base_path}' exists but is not a directory."
        print(err_msg)
        return subprocess.CompletedProcess(command_list, -1, stdout="", stderr=err_msg)
    try:
        timeout_seconds = 120
        result = subprocess.run(
            command_list,
            cwd=str(base_path),
            capture_output=True,
            text=True,
            check=check_returncode,
            encoding='utf-8',
            errors='replace',
            timeout=timeout_seconds
        )
        print(f"Git Command Result ({description}):")
        if result.stdout:
            print(f"  stdout: {result.stdout.strip()}")
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()}")
        print(f"  returncode: {result.returncode}")
        return result
    except FileNotFoundError:
        err_msg = "'git' command not found. Is Git installed and in PATH?"
        print(err_msg)
        return subprocess.CompletedProcess(command_list, -1, stdout="", stderr=err_msg)
    except subprocess.TimeoutExpired:
        err_msg = f"Git command timed out after {timeout_seconds} seconds."
        print(err_msg)
        return subprocess.CompletedProcess(command_list, -1, stdout="", stderr=err_msg)
    except subprocess.CalledProcessError as e:
        print(f"Error running git command (ret {e.returncode}): {e.stderr or e.stdout}")
        return e
    except Exception as e:
        err_msg = f"Unexpected Python error running git command: {e}"
        print(err_msg)
        import traceback; traceback.print_exc()
        return subprocess.CompletedProcess(command_list, -1, stdout="", stderr=err_msg)

def check_git_installation() -> bool:
    print("Checking Git installation...")
    return bool(shutil.which("git"))

class SetupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Website Editor - Setup Check")
        window_width, window_height = 500, 280
        screen_width, screen_height = root.winfo_screenwidth(), root.winfo_screenheight()
        center_x, center_y = int(screen_width/2 - window_width/2), int(screen_height/2 - window_height/2)
        root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        root.resizable(False, False)
        self.setup_styles()
        main_frame = ttk.Frame(root, padding=20)
        main_frame.pack(expand=True, fill=tk.BOTH)
        self.status_var = tk.StringVar(value="Initialiseren setup...")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, wraplength=460, justify=tk.LEFT, font=self.default_font)
        status_label.pack(pady=(0, 15), anchor=tk.W, fill=tk.X)
        self.progress_var = tk.DoubleVar()
        self.progressbar = ttk.Progressbar(main_frame, orient="horizontal", length=460, mode="determinate", variable=self.progress_var, maximum=6)
        self.progressbar.pack(pady=5, fill=tk.X)
        self.action_frame = ttk.Frame(main_frame)
        self.action_frame.pack(pady=(15, 0), fill=tk.X, side=tk.BOTTOM)
        self.root.after(100, self.run_setup_checks)

    def setup_styles(self):
        style = ttk.Style()
        try:
            themes = style.theme_names()
            preferred_themes = ["clam", "vista", "aqua", "default"]
            for theme in preferred_themes:
                if theme in themes:
                    style.theme_use(theme)
                    break
        except tk.TclError:
            pass
        self.default_font_family = "Segoe UI" if sys.platform == "win32" else "TkDefaultFont"
        self.default_font_size = 10
        self.link_font = tkFont.Font(family=self.default_font_family, size=self.default_font_size, underline=True)
        self.default_font = tkFont.Font(family=self.default_font_family, size=self.default_font_size)
        style.configure("TLabel", font=self.default_font)
        style.configure("TButton", font=self.default_font)
        style.configure("Link.TLabel", foreground="blue", font=self.link_font)

    def update_status(self, message, progress_increment=1):
        print(f"Setup Status: {message}")
        self.status_var.set(message)
        if progress_increment > 0:
            self.progress_var.set(self.progress_var.get() + progress_increment)
        self.root.update_idletasks()

    def show_error_and_exit(self, title, message):
        self.status_var.set(f"Fout: {title}")
        self.clear_action_frame()
        ttk.Button(self.action_frame, text="Afsluiten", command=self.root.destroy).pack(side=tk.RIGHT, pady=5)
        messagebox.showerror(title, message, parent=self.root)

    def clear_action_frame(self):
        for widget in self.action_frame.winfo_children():
            widget.destroy()

    def display_git_not_installed(self):
        self.clear_action_frame()
        button_subframe = ttk.Frame(self.action_frame)
        button_subframe.pack(pady=5)
        link_label = ttk.Label(button_subframe, text="Download Git", style="Link.TLabel", cursor="hand2")
        link_label.pack(side=tk.LEFT, padx=5)
        link_label.bind("<Button-1>", lambda e: webbrowser.open(GIT_DOWNLOAD_URL))
        retry_button = ttk.Button(button_subframe, text="Opnieuw proberen", command=self.retry_setup_checks)
        retry_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_subframe, text="Afsluiten", command=self.root.destroy).pack(side=tk.LEFT, padx=5)

    def retry_setup_checks(self):
        self.clear_action_frame()
        self.progress_var.set(1.0)
        self.update_status("Opnieuw proberen Git installatie te controleren...", progress_increment=0)
        self.root.after(100, self.run_setup_checks)

    def run_setup_checks(self):
        try:
            self.progress_var.set(0.0)
            self.update_status("Controleren configuratie...", progress_increment=0)
            app_base_dir_value = getattr(config, 'APP_BASE_DIR', '')
            if not app_base_dir_value:
                self.show_error_and_exit("Configuratie Fout", "config.APP_BASE_DIR is niet ingesteld in config.py.")
                return
            base_path = Path(app_base_dir_value)
            try:
                base_path.mkdir(parents=True, exist_ok=True)
                print(f"Base directory exists or created: {base_path}")
            except OSError as e:
                self.show_error_and_exit("Configuratie Fout", f"config.APP_BASE_DIR kon niet worden gemaakt:\n'{base_path}'\nFout: {e}")
                return
            if not base_path.is_dir():
                self.show_error_and_exit("Configuratie Fout", f"config.APP_BASE_DIR pad bestaat maar is geen map:\n'{base_path}'")
                return
            if not hasattr(config, 'REPO_URL') or not config.REPO_URL:
                self.show_error_and_exit("Configuratie Fout", "config.REPO_URL is niet ingesteld in config.py.")
                return
            self.update_status("Configuratie OK.", progress_increment=1)
            self.update_status("Controleren Git installatie...", progress_increment=0)
            if not check_git_installation():
                self.status_var.set("Fout: Git is niet geïnstalleerd of niet gevonden in PATH.")
                self.display_git_not_installed()
                return
            self.update_status("Git gevonden.", progress_increment=1)
            self.update_status("Controleren Git user.name / user.email...", progress_increment=0)
            name_res = run_git_command(['git', 'config', '--get', 'user.name'], 'check name')
            email_res = run_git_command(['git', 'config', '--get', 'user.email'], 'check email')
            git_name = name_res.stdout.strip() if getattr(name_res, "returncode", -1) == 0 and name_res.stdout else None
            git_email = email_res.stdout.strip() if getattr(email_res, "returncode", -1) == 0 and email_res.stdout else None
            if not git_name or not git_email:
                self.status_var.set("Git configuratie (naam/email) ontbreekt of is leeg.")
                self.root.update_idletasks()
                user_details = self._show_git_config_dialog()
                if user_details:
                    git_name = user_details['name']
                    git_email = user_details['email']
                    self.update_status("Instellen Git configuratie (globaal)...", progress_increment=0)
                    name_set_res = run_git_command(['git', 'config', '--global', 'user.name', git_name], 'set global name')
                    email_set_res = run_git_command(['git', 'config', '--global', 'user.email', git_email], 'set global email')
                    if name_set_res.returncode != 0 or email_set_res.returncode != 0:
                        err_details = []
                        if name_set_res.returncode != 0:
                            err_details.append(f"Instellen Naam:\n{(name_set_res.stderr or name_set_res.stdout or 'Onbekende fout').strip()}")
                        if email_set_res.returncode != 0:
                            err_details.append(f"Instellen Email:\n{(email_set_res.stderr or email_set_res.stdout or 'Onbekende fout').strip()}")
                        joined_error_details = "\n\n".join(err_details)
                        error_message = f"Kon Git naam/email niet globaal instellen:\n\n{joined_error_details}"
                        self.show_error_and_exit("Configuratie Fout", error_message)
                        return
                else:
                    self.status_var.set("Setup geannuleerd: Git configuratie vereist.")
                    self.clear_action_frame()
                    ttk.Button(self.action_frame, text="Afsluiten", command=self.root.destroy).pack(side=tk.RIGHT)
                    return
            self.update_status("Git naam & email gecontroleerd.", progress_increment=1)
            self.update_status("Controleren repository status...", progress_increment=0)
            git_dir = base_path / '.git'
            repo_url = config.REPO_URL
            target_branch = getattr(config, 'GIT_TARGET_BRANCH', 'main')
            needs_init = not git_dir.is_dir()
            needs_remote = True
            needs_initial_pull = True
            if needs_init:
                self.update_status(f"Initialiseren Git repository (git init -b {target_branch})...", progress_increment=0)
                init_res = run_git_command(['git', 'init', f'--initial-branch={target_branch}'], 'git init')
                if init_res.returncode != 0:
                    init_res_fb = run_git_command(['git', 'init'], 'git init (fallback)')
                    if init_res_fb.returncode != 0:
                        self.show_error_and_exit("Git Fout", f"Kon repository niet initialiseren (fallback poging):\n{init_res_fb.stderr or init_res_fb.stdout}")
                        return
                    rename_res = run_git_command(['git', 'branch', '-M', target_branch], f'rename initial branch to {target_branch}')
                    if rename_res.returncode != 0:
                        print(f"Warning: could not rename initial branch to {target_branch}: {rename_res.stderr or rename_res.stdout}")
                self.update_status("Repository geïnitialiseerd.", progress_increment=0)
                needs_remote = True
                needs_initial_pull = True
            else:
                remote_res = run_git_command(['git', 'remote', 'get-url', 'origin'], 'check origin url')
                if getattr(remote_res, "returncode", -1) == 0:
                    origin_url = remote_res.stdout.strip()
                    if origin_url == repo_url:
                        print("Remote 'origin' is correctly configured.")
                        needs_remote = False
                        head_check = run_git_command(['git', 'rev-parse', '--verify', 'HEAD'], 'check HEAD exists')
                        needs_initial_pull = (head_check.returncode != 0)
                        status_msg = "Repo OK, remote OK." + (" Al gesynchroniseerd." if not needs_initial_pull else "")
                        self.update_status(status_msg, progress_increment=0)
                    else:
                        err_msg = (
                            f"Remote 'origin' wijst naar de verkeerde URL!\n\n"
                            f"Ingesteld: {origin_url}\nVerwacht: {repo_url}\n\n"
                            f"Corrigeer dit handmatig (bv. 'git remote set-url origin {repo_url}') "
                            f"in de map '{base_path}' en herstart de setup."
                        )
                        self.show_error_and_exit("Git Remote Fout", err_msg)
                        return
                elif "No such remote" in (remote_res.stderr or ""):
                    needs_remote = True
                    needs_initial_pull = True
                else:
                    self.show_error_and_exit("Git Fout", f"Kon remote 'origin' status niet controleren:\n{remote_res.stderr or remote_res.stdout}")
                    return
            if needs_remote:
                self.update_status("Toevoegen remote 'origin'...", progress_increment=0)
                remote_add_res = run_git_command(['git', 'remote', 'add', 'origin', repo_url], 'add remote origin')
                if remote_add_res.returncode != 0:
                    if "remote origin already exists" in (remote_add_res.stderr or "").lower():
                        verify_res = run_git_command(['git', 'remote', 'get-url', 'origin'], 're-check origin url')
                        if getattr(verify_res, "returncode", -1) == 0 and verify_res.stdout.strip() == repo_url:
                            needs_initial_pull = True
                        else:
                            verify_url = verify_res.stdout.strip() if getattr(verify_res, "returncode", -1) == 0 else "Kon niet ophalen"
                            err_msg = (
                                f"Kon remote 'origin' niet toevoegen omdat deze al bestaat, maar de URL is onjuist!\n\n"
                                f"Ingesteld: {verify_url}\nVerwacht: {repo_url}\n\n"
                                f"Corrigeer dit handmatig (bv. 'git remote set-url origin {repo_url}') "
                                f"in de map '{base_path}' en herstart de setup."
                            )
                            self.show_error_and_exit("Git Remote Fout", err_msg)
                            return
                    else:
                        self.show_error_and_exit("Git Fout", f"Kon remote 'origin' niet toevoegen:\n{remote_add_res.stderr or remote_add_res.stdout}")
                        return
                self.update_status("Remote 'origin' toegevoegd.", progress_increment=0)
                needs_initial_pull = True
            self.update_status("Repository status OK.", progress_increment=1)
            if needs_initial_pull:
                self.update_status(f"Eerste synchronisatie met server (git pull origin {target_branch})...", progress_increment=0)
                pull_cmd = ['git', 'pull', 'origin', target_branch, '--allow-unrelated-histories']
                pull_res = run_git_command(pull_cmd, f'initial git pull {target_branch}')
                if pull_res.returncode != 0:
                    stderr_lower = (pull_res.stderr or pull_res.stdout or "").lower()
                    if f"couldn't find remote ref {target_branch}" in stderr_lower or ("fatal: refusing to merge unrelated histories" in stderr_lower and '--allow-unrelated-histories' not in pull_cmd):
                        messagebox.showinfo(
                            "Info - Lege Repository / Branch?",
                            f"Kon geen '{target_branch}' branch vinden op de server, of de historie is niet gerelateerd.\n"
                            f"Dit is normaal als de repository nieuw/leeg is.\n\n"
                            f"Setup gaat door, maar u moet mogelijk de eerste commit zelf pushen.",
                            parent=self.root
                        )
                        self.update_status("Synchronisatie overgeslagen (lege repo/branch?).", progress_increment=1)
                    elif "authentication failed" in stderr_lower:
                        self.show_error_and_exit("Git Pull Fout", f"Authenticatie mislukt:\nControleer uw Git credentials.\n\n{pull_res.stderr or pull_res.stdout}")
                        return
                    elif "could not resolve host" in stderr_lower or "repository not found" in stderr_lower:
                        self.show_error_and_exit("Git Pull Fout", f"Kan server/repository niet vinden:\nControleer config.REPO_URL en internet.\n\n{pull_res.stderr or pull_res.stdout}")
                        return
                    elif "connection timed out" in stderr_lower:
                        self.show_error_and_exit("Git Pull Fout", f"Verbinding time-out:\nControleer internet en server status.\n\n{pull_res.stderr or pull_res.stdout}")
                        return
                    elif ("permission" in stderr_lower and "denied" in stderr_lower) or "forbidden" in stderr_lower:
                        self.show_error_and_exit("Git Pull Fout", f"Permissie geweigerd:\nControleer leestoegang tot de repository.\n\n{pull_res.stderr or pull_res.stdout}")
                        return
                    elif "failed to connect" in stderr_lower:
                        self.show_error_and_exit("Git Pull Fout", f"Kon geen verbinding maken:\nControleer netwerk/firewall.\n\n{pull_res.stderr or pull_res.stdout}")
                        return
                    elif "already up-to-date" in (pull_res.stdout or "").lower():
                        print("Pull reported 'Already up-to-date'.")
                        self.update_status("Repository is al up-to-date.", progress_increment=1)
                    else:
                        self.show_error_and_exit("Git Pull Fout", f"Kon niet synchroniseren met de server:\n{pull_res.stderr or pull_res.stdout}")
                        return
                else:
                    self.update_status("Synchronisatie voltooid.", progress_increment=1)
            else:
                self.update_status("Repository is al gesynchroniseerd.", progress_increment=1)
            self.update_status("Alle controles voltooid!", progress_increment=1)
            self.progressbar.config(value=self.progressbar['maximum'])
            self.root.destroy()
        except Exception as e:
            print(f"Onverwachte setup fout: {e}")
            import traceback; traceback.print_exc()
            self.clear_action_frame()
            ttk.Button(self.action_frame, text="Afsluiten", command=self.root.destroy).pack(side=tk.RIGHT, pady=5)
            self.show_error_and_exit("Setup Fout", f"Een onverwachte fout is opgetreden tijdens de setup:\n{e}")

    def _show_git_config_dialog(self):
        dialog = Toplevel(self.root)
        dialog.title("Git Configuratie Nodig")
        dialog.geometry("450x350")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        details = {'name': None, 'email': None}
        main_frame = ttk.Frame(dialog, padding=15)
        main_frame.pack(expand=True, fill=tk.BOTH)
        ttk.Label(main_frame, text="Git heeft uw naam en e-mailadres nodig om wijzigingen (commits) te registreren.", wraplength=400).pack(pady=(0, 5))
        ttk.Label(main_frame, text="Deze worden opgeslagen in uw globale Git configuratie.", wraplength=400, style="TLabel").pack(pady=(0, 15))
        name_frame = ttk.Frame(main_frame)
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text="Naam:", width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 5))
        name_entry = ttk.Entry(name_frame)
        name_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        name_entry.focus_set()
        email_frame = ttk.Frame(main_frame)
        email_frame.pack(fill=tk.X, pady=5)
        ttk.Label(email_frame, text="E-mail:", width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 5))
        email_entry = ttk.Entry(email_frame)
        email_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(15, 10))
        ttk.Label(main_frame, text="Een GitHub account is nodig om wijzigingen online te publiceren.", wraplength=400).pack(pady=(0,5))
        link_frame = ttk.Frame(main_frame)
        link_frame.pack(pady=5)
        def open_link(url):
            try:
                webbrowser.open(url, new=2)
            except Exception as e:
                print(f"Kon link {url} niet openen: {e}")
        ttk.Button(link_frame, text="GitHub Account Maken", command=lambda: open_link(GITHUB_SIGNUP_URL)).pack(side=tk.LEFT, padx=5)
        ttk.Button(link_frame, text="Inloggen op GitHub", command=lambda: open_link(GITHUB_LOGIN_URL)).pack(side=tk.LEFT, padx=5)
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)
        def on_ok():
            name = name_entry.get().strip()
            email = email_entry.get().strip()
            if not name:
                messagebox.showwarning("Input Vereist", "Vul uw naam in.", parent=dialog)
                name_entry.focus_set()
                return
            if not email:
                messagebox.showwarning("Input Vereist", "Vul uw e-mailadres in.", parent=dialog)
                email_entry.focus_set()
                return
            if '@' not in email or '.' not in email.split('@')[-1] or len(email.split('@')[-1]) < 2:
                messagebox.showwarning("Ongeldige E-mail", "Vul een geldig e-mailadres in (bv. naam@example.com).", parent=dialog)
                email_entry.focus_set()
                return
            details['name'] = name
            details['email'] = email
            dialog.grab_release()
            dialog.destroy()
        def on_cancel():
            details['name'] = None
            details['email'] = None
            dialog.grab_release()
            dialog.destroy()
        ok_button = ttk.Button(button_frame, text="Opslaan", command=on_ok)
        ok_button.pack(side=tk.RIGHT, padx=(5,0))
        cancel_button = ttk.Button(button_frame, text="Annuleren", command=on_cancel)
        cancel_button.pack(side=tk.RIGHT)
        dialog.bind('<Return>', lambda event=None: ok_button.invoke())
        dialog.bind('<Escape>', lambda event=None: cancel_button.invoke())
        self.root.update_idletasks()
        dialog_width = dialog.winfo_reqwidth()
        dialog_height = dialog.winfo_reqheight()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()
        x = main_x + (main_width // 2) - (dialog_width // 2)
        y = main_y + (main_height // 2) - (dialog_height // 2)
        dialog.geometry(f'+{x}+{y}')
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        self.root.wait_window(dialog)
        return details if details.get('name') and details.get('email') else None

if __name__ == "__main__":
    setup_root = tk.Tk()
    setup_app = SetupApp(setup_root)
    setup_root.mainloop()

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog, font as tkFont
import os
import copy
import pathlib
import shutil
import html
from PIL import Image, ImageTk

# Assumed external modules based on original code
import config
import utils

# --- Helper Functions ---

def center_window(window, parent=None):
    """Centers a popup window relative to its parent or the screen."""
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()

    if parent:
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
    else:
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

    window.geometry(f'+{x}+{y}')

# --- Dialog Classes ---

class EditTimeDialog(tk.Toplevel):
    def __init__(self, parent, title, category_name_html, initial_times_list, callback):
        super().__init__(parent)
        self.transient(parent)
        self.category_name_display = utils.strip_html(category_name_html)
        self.title(f"{title} - {self.category_name_display}")
        self.category_name_html = category_name_html
        self.initial_data = [dict(item) for item in initial_times_list]
        self.callback = callback
        self.result = None
        self.time_entries = []

        self.geometry("650x500")

        # Main container
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Header
        ttk.Label(main_frame, text=f"Tijden voor: {self.category_name_display}", style="Bold.TLabel").pack(pady=(0, 10), anchor='w')

        # Scrollable Area Setup
        scroll_container = ttk.Frame(main_frame, borderwidth=1, relief="sunken")
        scroll_container.pack(fill="both", expand=True, pady=5)

        self.canvas = tk.Canvas(scroll_container, borderwidth=0, highlightthickness=0, bg="#ffffff")
        self.vsb = ttk.Scrollbar(scroll_container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.scrollable_frame = ttk.Frame(self.canvas)

        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # Bindings for scrolling
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.bind('<Enter>', self._bind_mousewheel)
        self.canvas.bind('<Leave>', self._unbind_mousewheel)

        # Column Headers inside scrollable area
        header_frame = ttk.Frame(self.scrollable_frame)
        header_frame.pack(fill=tk.X, pady=(5, 5), padx=5)
        ttk.Label(header_frame, text="Dag", width=15, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="Tijd", width=20, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="Nota (optioneel)", width=25, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=2)

        self._populate_times()

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0), side=tk.BOTTOM)

        ttk.Button(button_frame, text="+ Regel Toevoegen", command=self._add_time_entry).pack(side=tk.LEFT)

        action_btns = ttk.Frame(button_frame)
        action_btns.pack(side=tk.RIGHT)
        ttk.Button(action_btns, text="Opslaan", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_btns, text="Annuleren", command=self.on_cancel).pack(side=tk.LEFT)

        center_window(self, parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.bind("<Escape>", self.on_cancel)
        self.wait_window()

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        delta = 1 if event.num == 5 or event.delta < 0 else -1
        self.canvas.yview_scroll(delta, "units")

    def _strip_parentheses_from_note(self, note_text):
        if note_text and note_text.startswith('(') and note_text.endswith(')'):
            return note_text[1:-1]
        return note_text

    def _populate_times(self):
        # Clean existing rows (skip header)
        for child in self.scrollable_frame.winfo_children():
            # Rough check to avoid deleting the header frame created in __init__
            # A better way is to keep header separate, but sticking to logic structure:
            if isinstance(child, ttk.Frame) and hasattr(child, 'is_entry_row'):
                child.destroy()
            elif isinstance(child, ttk.Frame) and not child.winfo_children(): # Cleanup empties
                child.destroy()

        self.time_entries = []
        sorted_times = sorted(self.initial_data, key=lambda x: config.DAYS_ORDER.get(x.get('day', '').capitalize(), 99))

        for time_data in sorted_times:
            note_text = self._strip_parentheses_from_note(time_data.get('note') or '')
            self._add_time_entry(time_data.get('day',''), time_data.get('time',''), note_text)

        self.scrollable_frame.update_idletasks()
        self._on_frame_configure(None)

    def _add_time_entry(self, day="", time="", note=""):
        entry_frame = ttk.Frame(self.scrollable_frame)
        entry_frame.is_entry_row = True # Mark for cleanup
        entry_frame.pack(fill=tk.X, pady=2, padx=5)

        day_entry = ttk.Entry(entry_frame, width=15)
        day_entry.insert(0, day)
        day_entry.pack(side=tk.LEFT, padx=(0, 2))

        time_entry = ttk.Entry(entry_frame, width=20)
        time_entry.insert(0, time)
        time_entry.pack(side=tk.LEFT, padx=2)

        note_entry = ttk.Entry(entry_frame)
        note_entry.insert(0, note)
        note_entry.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        del_btn = ttk.Button(entry_frame, text="X", width=3, style="Small.TButton",
                             command=lambda f=entry_frame: self._remove_time_entry(f))
        del_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.time_entries.append({'frame': entry_frame, 'day': day_entry, 'time': time_entry, 'note': note_entry})

        self.scrollable_frame.update_idletasks()
        self._on_frame_configure(None)

    def _remove_time_entry(self, frame_to_remove):
        frame_to_remove.destroy()
        self.time_entries = [e for e in self.time_entries if e['frame'].winfo_exists()]
        self.scrollable_frame.update_idletasks()
        self._on_frame_configure(None)

    def on_ok(self):
        self.result = []
        for entry in self.time_entries:
            if entry['frame'].winfo_exists():
                day = entry['day'].get().strip()
                time = entry['time'].get().strip()
                note = entry['note'].get().strip()

                if day and time:
                    self.result.append({
                        'day': day,
                        'time': time,
                        'note': f"({note})" if note else None
                    })

        if self.callback:
            self.callback(self.category_name_html, self.result)
        self.destroy()

    def on_cancel(self, event=None):
        self.destroy()

class ContactDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_data=None, existing_roles=None, callback=None):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.callback = callback
        self.initial_data = initial_data or {}
        self.existing_roles = existing_roles or []
        self.result = None
        self.selected_image_source_path = None

        # UI Setup
        frame = ttk.Frame(self, padding="20")
        frame.pack(expand=True, fill=tk.BOTH)

        # Grid Configuration
        frame.columnconfigure(1, weight=1)

        row_index = 0

        # Role
        ttk.Label(frame, text="Rol:").grid(row=row_index, column=0, sticky=tk.E, padx=5, pady=5)
        self.role_entry = ttk.Entry(frame, width=40)
        self.role_entry.grid(row=row_index, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
        self.role_entry.insert(0, self.initial_data.get('role', ''))
        if self.initial_data.get('is_edit_mode'):
            self.role_entry.config(state=tk.DISABLED)
        row_index += 1

        # Name
        ttk.Label(frame, text="Naam:").grid(row=row_index, column=0, sticky=tk.E, padx=5, pady=5)
        self.name_entry = ttk.Entry(frame, width=40)
        self.name_entry.grid(row=row_index, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
        self.name_entry.insert(0, self.initial_data.get('name', ''))
        row_index += 1

        # Email
        ttk.Label(frame, text="E-mail:").grid(row=row_index, column=0, sticky=tk.E, padx=5, pady=5)
        self.email_entry = ttk.Entry(frame, width=40)
        self.email_entry.grid(row=row_index, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
        self.email_entry.insert(0, self.initial_data.get('email', '') or '')
        row_index += 1

        # Phone
        ttk.Label(frame, text="Tel:").grid(row=row_index, column=0, sticky=tk.E, padx=5, pady=5)
        self.phone_entry = ttk.Entry(frame, width=40)
        self.phone_entry.grid(row=row_index, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
        self.phone_entry.insert(0, self.initial_data.get('phone', '') or '')
        row_index += 1

        # Image
        ttk.Label(frame, text="Afbeelding:").grid(row=row_index, column=0, sticky=tk.E, padx=5, pady=5)
        self.img_src_var = tk.StringVar(value=self.initial_data.get('image', '') or '')

        img_entry = ttk.Entry(frame, textvariable=self.img_src_var, width=40, state="readonly")
        img_entry.grid(row=row_index, column=1, sticky="ew", padx=5, pady=5)

        ttk.Button(frame, text="Bladeren...", command=self._browse_image).grid(row=row_index, column=2, sticky="w", padx=5, pady=5)
        row_index += 1

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row_index, column=0, columnspan=3, pady=(20, 0), sticky=tk.E)

        ttk.Button(button_frame, text="OK", command=self.on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Annuleren", command=self.on_cancel).pack(side=tk.RIGHT)

        center_window(self, parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.bind("<Return>", self.on_ok)
        self.bind("<Escape>", self.on_cancel)

        self.name_entry.focus_set()
        self.wait_window(self)

    def _browse_image(self):
        source_path = filedialog.askopenfilename(
            title="Selecteer Contact Afbeelding",
            filetypes=(("Afbeeldingen", "*.jpg *.jpeg *.png *.gif .webp .bmp"), ("Alle", "*.*")),
            parent=self
        )
        if source_path:
            self.selected_image_source_path = source_path
            self.img_src_var.set(f"[Nieuw: {os.path.basename(source_path)}]")

    def on_ok(self, event=None):
        role = self.role_entry.get().strip()
        name = self.name_entry.get().strip()

        if not role:
            messagebox.showwarning("Invoer Vereist", "Rol mag niet leeg zijn.", parent=self)
            self.role_entry.focus_set()
            return
        if not name:
            messagebox.showwarning("Invoer Vereist", "Naam mag niet leeg zijn.", parent=self)
            self.name_entry.focus_set()
            return

        is_edit = self.initial_data.get('is_edit_mode', False)
        orig_role = self.initial_data.get('role')

        if not is_edit or (is_edit and role != orig_role):
            if role in self.existing_roles:
                messagebox.showwarning("Rol Bestaat Al", f"Rol '{role}' bestaat al.", parent=self)
                self.role_entry.focus_set()
                return

        img_src = self.initial_data.get('image')
        img_copy = None

        if self.selected_image_source_path:
            img_src = None
            img_copy = self.selected_image_source_path

        self.result = {
            'role': role,
            'name': name,
            'email': self.email_entry.get().strip() or None,
            'phone': self.phone_entry.get().strip() or None,
            'image': img_src,
            '_source_path_to_copy': img_copy,
            'imageAlt': f"Foto {name}"
        }

        if self.callback:
            if self.callback(self.result, orig_role) is False:
                return
        self.destroy()

    def on_cancel(self, event=None):
        self.destroy()

class TrainerDialog(tk.Toplevel):
    def __init__(self, parent, title, categories, initial_data=None, callback=None):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.callback = callback
        self.initial_data = initial_data or {}

        # Ensure "New Group" is at the bottom
        clean_cats = [c for c in categories if c != "<Nieuwe Groep...>"]
        self.categories = sorted(clean_cats) + ["<Nieuwe Groep...>"]
        self.result = None

        frame = ttk.Frame(self, padding="20")
        frame.pack(expand=True, fill=tk.BOTH)
        frame.columnconfigure(1, weight=1)

        row_index = 0

        # Group Selection
        ttk.Label(frame, text="Groep:").grid(row=row_index, column=0, sticky=tk.E, padx=5, pady=5)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(frame, textvariable=self.category_var, values=self.categories, state="readonly", width=38)
        self.category_combo.grid(row=row_index, column=1, sticky="ew", padx=5, pady=5)

        initial_cat = self.initial_data.get('groupName')
        if initial_cat and initial_cat in self.categories:
            self.category_var.set(initial_cat)
        else:
            self.category_var.set(self.categories[0] if len(self.categories) > 1 else "<Nieuwe Groep...>")

        self.category_combo.bind("<<ComboboxSelected>>", self._toggle_new_category)
        row_index += 1

        # New Group Entry (Dynamic)
        self.new_category_label = ttk.Label(frame, text="Nieuwe Groep Naam:")
        self.new_category_entry = ttk.Entry(frame, width=40)

        self.new_category_label.grid(row=row_index, column=0, sticky=tk.E, padx=5, pady=5)
        self.new_category_entry.grid(row=row_index, column=1, sticky="ew", padx=5, pady=5)
        row_index += 1

        # Name
        ttk.Label(frame, text="Naam:").grid(row=row_index, column=0, sticky=tk.E, padx=5, pady=5)
        self.name_entry = ttk.Entry(frame, width=40)
        self.name_entry.grid(row=row_index, column=1, sticky="ew", padx=5, pady=5)
        self.name_entry.insert(0, self.initial_data.get('name', ''))
        row_index += 1

        # Email
        ttk.Label(frame, text="E-mail (optioneel):").grid(row=row_index, column=0, sticky=tk.E, padx=5, pady=5)
        self.email_entry = ttk.Entry(frame, width=40)
        self.email_entry.grid(row=row_index, column=1, sticky="ew", padx=5, pady=5)
        self.email_entry.insert(0, self.initial_data.get('email', '') or '')
        row_index += 1

        # Phone
        ttk.Label(frame, text="Tel (optioneel):").grid(row=row_index, column=0, sticky=tk.E, padx=5, pady=5)
        self.phone_entry = ttk.Entry(frame, width=40)
        self.phone_entry.grid(row=row_index, column=1, sticky="ew", padx=5, pady=5)
        self.phone_entry.insert(0, self.initial_data.get('phone', '') or '')
        row_index += 1

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row_index, column=0, columnspan=2, pady=(20, 0), sticky=tk.E)

        ttk.Button(button_frame, text="OK", command=self.on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Annuleren", command=self.on_cancel).pack(side=tk.RIGHT)

        self._toggle_new_category()
        center_window(self, parent)
        self.grab_set()

        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.bind("<Return>", self.on_ok)
        self.bind("<Escape>", self.on_cancel)
        self.name_entry.focus_set()
        self.wait_window(self)

    def _toggle_new_category(self, event=None):
        is_new = self.category_var.get() == "<Nieuwe Groep...>"
        if is_new:
            self.new_category_label.grid()
            self.new_category_entry.grid()
            self.new_category_entry.config(state=tk.NORMAL)
            self.new_category_entry.focus_set()
        else:
            self.new_category_label.grid_remove()
            self.new_category_entry.grid_remove()
            self.new_category_entry.config(state=tk.DISABLED)
            self.new_category_entry.delete(0, tk.END)

    def on_ok(self, event=None):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Invoer Vereist", "Naam mag niet leeg zijn.", parent=self)
            self.name_entry.focus_set()
            return

        cat_selection = self.category_var.get()
        if cat_selection == "<Nieuwe Groep...>":
            cat_to_save = self.new_category_entry.get().strip()
            if not cat_to_save:
                messagebox.showwarning("Invoer Vereist", "Voer naam nieuwe groep in.", parent=self)
                self.new_category_entry.focus_set()
                return
        elif not cat_selection:
            messagebox.showwarning("Invoer Vereist", "Selecteer een groep.", parent=self)
            self.category_combo.focus_set()
            return
        else:
            cat_to_save = cat_selection

        self.result = {
            'name': name,
            'email': self.email_entry.get().strip() or None,
            'phone': self.phone_entry.get().strip() or None,
            'groupName': cat_to_save
        }

        if self.callback:
            self.callback(self.result, self.initial_data.get('groupName'), self.initial_data.get('original_trainer_index'), self.initial_data.get('iid'))
        self.destroy()

    def on_cancel(self, event=None):
        self.destroy()

class ImagePreviewDialog(tk.Toplevel):
    def __init__(self, parent, image_local_path):
        super().__init__(parent)
        self.transient(parent)
        self.title("Afbeelding Preview")
        self.geometry("600x600")

        self.image_label = ttk.Label(self)
        self.image_label.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        if not self._load_image(image_local_path):
            return
        center_window(self, parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda e: self.destroy())
        self.wait_window(self)

    def _load_image(self, image_path):
        try:
            if not os.path.exists(image_path):
                messagebox.showerror("Fout", f"Afbeeldingsbestand niet gevonden:\n{image_path}", parent=self)
                self.destroy()
                return False

            with Image.open(image_path) as source_image:
                img = source_image.copy()
            w, h = img.size
            # Resize if too big
            max_size = 580
            ratio = min(max_size/w, max_size/h)
            if ratio < 1:
                img = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)

            self.tk_image = ImageTk.PhotoImage(img) # Keep reference
            self.image_label.config(image=self.tk_image)
            self.title(f"Preview: {os.path.basename(image_path)} ({img.width}x{img.height})")
            return True
        except Exception as e:
            messagebox.showerror("Fout bij laden afbeelding", f"Kon afbeelding niet laden:\n{image_path}\n{e}", parent=self)
            self.destroy()
            return False

class EditSingleImageDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_alt="", initial_src_display="", callback=None):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.callback = callback
        self.result = None
        self.selected_local_path = None

        frame = ttk.Frame(self, padding="20")
        frame.pack(expand=True, fill=tk.BOTH)
        frame.columnconfigure(1, weight=1)

        row_index = 0

        ttk.Label(frame, text="Afbeelding bron:").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.src_display_var = tk.StringVar(value=initial_src_display or "Geen afbeelding geselecteerd")

        lbl_src = ttk.Label(frame, textvariable=self.src_display_var, wraplength=350, justify=tk.LEFT)
        lbl_src.grid(row=row_index, column=1, sticky="ew", padx=5, pady=5)

        ttk.Button(frame, text="Bladeren...", command=self._browse_image).grid(row=row_index, column=2, sticky="w", padx=5, pady=5)
        row_index += 1

        ttk.Label(frame, text="Alt tekst:").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.alt_entry = ttk.Entry(frame, width=50)
        self.alt_entry.grid(row=row_index, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
        self.alt_entry.insert(0, initial_alt)
        row_index += 1

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row_index, column=0, columnspan=3, pady=(20, 0), sticky=tk.E)
        ttk.Button(button_frame, text="OK", command=self.on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Annuleren", command=self.on_cancel).pack(side=tk.RIGHT)

        center_window(self, parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.bind("<Return>", self.on_ok)
        self.bind("<Escape>", self.on_cancel)
        self.alt_entry.focus_set()
        self.wait_window(self)

    def _browse_image(self):
        source_path = filedialog.askopenfilename(
            title="Selecteer Afbeelding",
            filetypes=(("Afbeeldingen", "*.jpg *.jpeg *.png *.gif *.webp *.bmp"), ("Alle", "*.*")),
            parent=self
        )
        if source_path:
            self.selected_local_path = source_path
            self.src_display_var.set(f"[Nieuw geselecteerd: {os.path.basename(source_path)}]")

    def on_ok(self, event=None):
        alt_text = self.alt_entry.get().strip()
        if not alt_text:
            messagebox.showwarning("Invoer Vereist", "Alt tekst mag niet leeg zijn.", parent=self)
            self.alt_entry.focus_set()
            return

        self.result = {'alt': alt_text, 'selected_local_path': self.selected_local_path}
        if self.callback:
            self.callback(self.result)
        self.destroy()

    def on_cancel(self, event=None):
        if self.callback:
            self.callback(None)
        self.destroy()

class GroupImageManagerDialog(tk.Toplevel):
    def __init__(self, parent, group_data_ref, app_instance, callback):
        super().__init__(parent)
        self.transient(parent)
        self.group_data_ref = group_data_ref
        self.group_name_for_display = group_data_ref.get('groupName', "Onbekende Groep")
        self.title(f"Afbeeldingen Beheren - {self.group_name_for_display}")
        self.app_instance = app_instance
        self.callback = callback

        self.TARGET_IMG_DIR_ABS = os.path.join(config.APP_BASE_DIR, 'images', 'personen')
        self.TARGET_IMG_HREF_BASE = '/images/personen'

        self.current_main_photo_details = copy.deepcopy(self.group_data_ref.get('mainPhoto', {}))
        self.current_thumbnails_list = copy.deepcopy(self.group_data_ref.get('thumbnails', []))

        # UI Layout
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Main Photo Section
        main_photo_frame = ttk.Labelframe(main_frame, text=" Hoofdafbeelding ", padding=15)
        main_photo_frame.pack(fill=tk.X, pady=(0, 15))
        main_photo_frame.columnconfigure(1, weight=1)

        ttk.Label(main_photo_frame, text="Bron:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        self.main_photo_src_var = tk.StringVar()
        self.main_photo_src_label = ttk.Label(main_photo_frame, textvariable=self.main_photo_src_var, wraplength=400, justify=tk.LEFT, cursor="hand2", foreground="blue")
        self.main_photo_src_label.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.main_photo_src_label.bind("<Button-1>", self._preview_main_photo_handler)

        ttk.Label(main_photo_frame, text="Alt tekst:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.main_photo_alt_var = tk.StringVar()
        ttk.Entry(main_photo_frame, textvariable=self.main_photo_alt_var, width=50, state="readonly").grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        self._update_main_photo_display()

        ttk.Button(main_photo_frame, text="Hoofdafbeelding Wijzigen...", command=self._edit_main_photo).grid(row=0, column=2, rowspan=2, sticky="ns", padx=10, pady=5)

        # Thumbnails Section
        thumbs_frame = ttk.Labelframe(main_frame, text=" Thumbnails ", padding=10)
        thumbs_frame.pack(expand=True, fill=tk.BOTH)
        thumbs_frame.rowconfigure(0, weight=1)
        thumbs_frame.columnconfigure(0, weight=1)

        # Thumbnails Treeview
        self.thumbs_tree = ttk.Treeview(thumbs_frame, columns=('thumb_src', 'thumb_alt'), show='headings', selectmode='browse', height=8)
        self.thumbs_tree.heading('thumb_src', text='Bron (Web Pad)')
        self.thumbs_tree.column('thumb_src', width=300, anchor=tk.W)
        self.thumbs_tree.heading('thumb_alt', text='Alt Tekst')
        self.thumbs_tree.column('thumb_alt', width=250, anchor=tk.W)

        thumbs_vsb = ttk.Scrollbar(thumbs_frame, orient="vertical", command=self.thumbs_tree.yview)
        self.thumbs_tree.configure(yscrollcommand=thumbs_vsb.set)

        self.thumbs_tree.grid(row=0, column=0, sticky='nsew')
        thumbs_vsb.grid(row=0, column=1, sticky='ns')

        self.thumbs_tree.bind("<<TreeviewSelect>>", self._on_thumbnail_select)
        self.thumbs_tree.bind("<Double-1>", self._preview_selected_thumbnail_handler)

        # Add striped rows
        self.thumbs_tree.tag_configure('odd', background='#F5F5F5')
        self.thumbs_tree.tag_configure('even', background='#FFFFFF')

        # Thumbnail Action Buttons
        thumb_buttons_frame = ttk.Frame(thumbs_frame)
        thumb_buttons_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(10, 0))

        ttk.Button(thumb_buttons_frame, text="+ Toevoegen", command=self._add_thumbnail).pack(side=tk.LEFT, padx=(0,5))
        self.edit_thumb_button = ttk.Button(thumb_buttons_frame, text="Bewerken...", command=self._edit_thumbnail, state=tk.DISABLED)
        self.edit_thumb_button.pack(side=tk.LEFT, padx=5)
        self.delete_thumb_button = ttk.Button(thumb_buttons_frame, text="Verwijderen", command=self._delete_thumbnail, state=tk.DISABLED)
        self.delete_thumb_button.pack(side=tk.LEFT, padx=5)

        self._populate_thumbnails_tree()

        # Footer Buttons
        dialog_button_frame = ttk.Frame(main_frame)
        dialog_button_frame.pack(fill=tk.X, pady=(20, 0), side=tk.BOTTOM)

        ttk.Button(dialog_button_frame, text="OK & Opslaan", command=self.on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(dialog_button_frame, text="Annuleren", command=self.on_cancel).pack(side=tk.RIGHT)

        center_window(self, parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.bind("<Escape>", self.on_cancel)
        self.wait_window(self)

    def _resolve_image_path_for_preview(self, path_or_uri):
        if not path_or_uri: return None
        if os.path.isabs(path_or_uri) and os.path.exists(path_or_uri): return path_or_uri

        if path_or_uri.startswith('/'):
            # Convert web path to local filesystem path
            local_path = os.path.normpath(os.path.join(config.APP_BASE_DIR, 'public_html', path_or_uri.lstrip('/')))
            if os.path.exists(local_path): return local_path

            # Fallback checks
            filename = os.path.basename(path_or_uri)
            for base_dir in [self.TARGET_IMG_DIR_ABS, config.CONTACTS_IMG_DIR_ABS]:
                fallback_path = os.path.normpath(os.path.join(base_dir, filename))
                if os.path.exists(fallback_path): return fallback_path

            messagebox.showwarning("Preview Fout", f"Kan web afbeelding niet vinden:\n{path_or_uri}", parent=self)

        return None

    def _preview_main_photo_handler(self, event=None):
        path = self.current_main_photo_details.get('_source_path_to_copy') or self.current_main_photo_details.get('src')
        resolved = self._resolve_image_path_for_preview(path)
        if path and resolved:
            ImagePreviewDialog(self, resolved)
        else:
            messagebox.showinfo("Geen afbeelding", "Geen hoofdafbeelding ingesteld.", parent=self)

    def _preview_selected_thumbnail_handler(self, event=None):
        sel = self.thumbs_tree.selection()
        if not sel: return
        idx = int(sel[0])
        if 0 <= idx < len(self.current_thumbnails_list):
            thumb = self.current_thumbnails_list[idx]
            path = thumb.get('_source_path_to_copy') or thumb.get('src')
            resolved = self._resolve_image_path_for_preview(path)
            if path and resolved:
                ImagePreviewDialog(self, resolved)
            else:
                messagebox.showinfo("Geen afbeelding", "Geen thumbnail afbeelding ingesteld.", parent=self)

    def _update_main_photo_display(self):
        src = self.current_main_photo_details.get('src', "Nog geen afbeelding ingesteld.")
        if self.current_main_photo_details.get('_source_path_to_copy'):
            src = f"[Nieuw: {os.path.basename(self.current_main_photo_details['_source_path_to_copy'])}]"
        self.main_photo_src_var.set(src)
        self.main_photo_alt_var.set(self.current_main_photo_details.get('alt', ""))

    def _edit_main_photo(self):
        src_display = self.current_main_photo_details.get('src', '')
        if self.current_main_photo_details.get('_source_path_to_copy'):
            src_display = f"[Selectie: {os.path.basename(self.current_main_photo_details['_source_path_to_copy'])}]"

        alt = self.current_main_photo_details.get('alt') or config.DEFAULT_TRAINER_GROUP_MAIN_IMG_ALT_TEMPLATE.format(category_name=self.group_name_for_display)

        EditSingleImageDialog(
            self,
            f"Hoofdafbeelding voor {self.group_name_for_display}",
            initial_alt=alt,
            initial_src_display=src_display,
            callback=self._process_main_photo_edit_result
        )

    def _process_main_photo_edit_result(self, result):
        if result:
            self.current_main_photo_details['alt'] = result['alt']
            if result.get('selected_local_path'):
                local_path = result['selected_local_path']
                filename = os.path.basename(local_path)
                dest_path = os.path.join(self.TARGET_IMG_DIR_ABS, filename)
                web_path = str(pathlib.PurePosixPath(self.TARGET_IMG_HREF_BASE) / filename).replace('\\', '/')

                self.current_main_photo_details.update({
                    '_source_path_to_copy': local_path,
                    '_dest_path_abs_for_copy': dest_path,
                    '_prospective_web_src': web_path
                })
            self._update_main_photo_display()

    def _populate_thumbnails_tree(self):
        self.thumbs_tree.delete(*self.thumbs_tree.get_children())
        for idx, thumb in enumerate(self.current_thumbnails_list):
            src = thumb.get('src', 'Geen bron')
            if thumb.get('_source_path_to_copy'):
                src = f"[Nieuw: {os.path.basename(thumb['_source_path_to_copy'])}]"

            tag = 'odd' if idx % 2 else 'even'
            self.thumbs_tree.insert('', tk.END, iid=str(idx), values=(src, thumb.get('alt', '')), tags=(tag,))

        self._on_thumbnail_select()

    def _on_thumbnail_select(self, event=None):
        state = tk.NORMAL if self.thumbs_tree.selection() else tk.DISABLED
        self.edit_thumb_button.config(state=state)
        self.delete_thumb_button.config(state=state)

    def _add_thumbnail(self):
        alt = config.DEFAULT_TRAINER_GROUP_THUMB_ALT_TEMPLATE.format(category_name=self.group_name_for_display, index=len(self.current_thumbnails_list) + 1)
        EditSingleImageDialog(self, f"Thumbnail Toevoegen - {self.group_name_for_display}", initial_alt=alt, callback=lambda r: self._process_thumbnail_edit_result(r, is_new=True))

    def _edit_thumbnail(self):
        sel = self.thumbs_tree.selection()
        if not sel: return
        idx = int(sel[0])
        thumb = self.current_thumbnails_list[idx]
        src_display = thumb.get('src', '')
        if thumb.get('_source_path_to_copy'):
            src_display = f"[Selectie: {os.path.basename(thumb['_source_path_to_copy'])}]"

        EditSingleImageDialog(
            self,
            f"Thumbnail Bewerken - {self.group_name_for_display}",
            initial_alt=thumb.get('alt', ''),
            initial_src_display=src_display,
            callback=lambda r: self._process_thumbnail_edit_result(r, index_to_edit=idx)
        )

    def _process_thumbnail_edit_result(self, result, is_new=False, index_to_edit=None):
        if result:
            entry = {} if is_new else self.current_thumbnails_list[index_to_edit]
            entry['alt'] = result['alt']
            if result.get('selected_local_path'):
                local_path = result['selected_local_path']
                filename = os.path.basename(local_path)
                dest_path = os.path.join(self.TARGET_IMG_DIR_ABS, filename)
                web_path = str(pathlib.PurePosixPath(self.TARGET_IMG_HREF_BASE) / filename).replace('\\', '/')
                entry.update({
                    '_source_path_to_copy': local_path,
                    '_dest_path_abs_for_copy': dest_path,
                    '_prospective_web_src': web_path
                })

            if is_new:
                self.current_thumbnails_list.append(entry)
            self._populate_thumbnails_tree()

    def _delete_thumbnail(self):
        sel = self.thumbs_tree.selection()
        if not sel: return
        idx = int(sel[0])
        alt = self.current_thumbnails_list[idx].get('alt', f"Thumbnail {idx+1}")
        if messagebox.askyesno("Verwijderen", f"Thumbnail '{alt}' verwijderen?", parent=self):
            del self.current_thumbnails_list[idx]
            self._populate_thumbnails_tree()

    def _handle_file_copy(self, img_dict):
        src = img_dict.get('_source_path_to_copy')
        dest = img_dict.get('_dest_path_abs_for_copy')
        web_src = img_dict.get('_prospective_web_src')

        if src and dest and web_src:
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                dest = utils.copy_new_asset(src, dest, owner=self)
                web_src = str(pathlib.PurePosixPath(web_src).parent / os.path.basename(dest))

                img_dict['src'] = web_src
                if self.app_instance: self.app_instance.set_status(f"Afbeelding '{os.path.basename(dest)}' gekopieerd.", duration_ms=3000)
            except Exception as e:
                messagebox.showerror("Kopieer Fout", f"Kon afbeelding niet kopiëren:\n{e}", parent=self)
                return False

        # Cleanup temporary keys
        for key in ['_source_path_to_copy', '_dest_path_abs_for_copy', '_prospective_web_src']:
            img_dict.pop(key, None)
        return True

    def on_ok(self):
        # Process Main Photo
        if not self._handle_file_copy(self.current_main_photo_details):
            return

        # Process Thumbnails
        for thumb in self.current_thumbnails_list:
            if not self._handle_file_copy(thumb):
                return

        # Update Reference
        self.group_data_ref['mainPhoto'] = {k:v for k,v in self.current_main_photo_details.items() if not k.startswith('_')}
        self.group_data_ref['thumbnails'] = [{k:v for k,v in thumb.items() if not k.startswith('_')} for thumb in self.current_thumbnails_list]

        if self.callback:
            self.callback(True)
        self.destroy()
        utils.cleanup_pending_assets(self.app_instance)

    def on_cancel(self):
        if self.callback:
            self.callback(False)
        self.destroy()
        utils.cleanup_pending_assets(self.app_instance)

class LargeTextDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_text=""):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.result = None
        self.minsize(600, 400)

        frame = ttk.Frame(self, padding="15")
        frame.pack(expand=True, fill=tk.BOTH)

        text_frame = ttk.Frame(frame)
        text_frame.pack(expand=True, fill=tk.BOTH)

        self.text = tk.Text(text_frame, wrap="word", font=("Segoe UI", 10))
        vsb = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=vsb.set)

        self.text.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.text.insert("1.0", initial_text or "")

        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))
        ttk.Button(button_frame, text="OK", command=self.on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Annuleren", command=self.on_cancel).pack(side=tk.RIGHT)

        center_window(self, parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.bind("<Escape>", self.on_cancel)
        self.text.focus_set()
        self.wait_window(self)

    def on_ok(self, event=None):
        self.result = self.text.get("1.0", "end-1c")
        self.destroy()

    def on_cancel(self, event=None):
        self.destroy()

# --- Main Application Logic ---

class TrainersTab:
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance
        self.trainers_data = {}
        self.trainers_file_loaded = False
        self._dnd_dragged_item = None

        # Styles
        s = ttk.Style()
        s.configure("Small.TButton", padding=1)
        s.configure("Bold.TLabel", font=tkFont.Font(family="Segoe UI", size=9, weight="bold"))
        # Treeview styling
        s.configure("Treeview", rowheight=25)

        self._create_widgets()
        self._trainers_load()

    def _create_widgets(self):
        self.parent.grid_rowconfigure(1, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        # Top Bar
        top_bar = ttk.Frame(self.parent, padding=(10, 10, 10, 0))
        top_bar.grid(row=0, column=0, sticky='ew')

        self.load_button = ttk.Button(top_bar, text="Herlaad Data (JSON)", command=self._trainers_load)
        self.load_button.pack(side=tk.LEFT, padx=(0, 5))

        self.save_button = ttk.Button(top_bar, text="Alle Wijzigingen Opslaan (JSON)", command=self._trainers_save, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT)

        # Tabs
        self.notebook = ttk.Notebook(self.parent)
        self.notebook.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)

        trainers_tab_frame = ttk.Frame(self.notebook, padding=10)
        times_tab_frame = ttk.Frame(self.notebook, padding=10)
        contacts_tab_frame = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(trainers_tab_frame, text=' Trainers & Groepen ')
        self.notebook.add(times_tab_frame, text=' Trainingstijden ')
        self.notebook.add(contacts_tab_frame, text=' Contactpersonen ')

        self._create_trainers_tab(trainers_tab_frame)
        self._create_times_tab(times_tab_frame)
        self._create_contacts_tab(contacts_tab_frame)

    def _create_trainers_tab(self, parent):
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        pw_trainers = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        pw_trainers.grid(row=0, column=0, sticky='nsew')

        # Treeview
        tree_frame = ttk.Frame(pw_trainers)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        pw_trainers.add(tree_frame, weight=3)

        trainer_cols = ('name', 'email', 'phone')
        self.trainers_tree = ttk.Treeview(tree_frame, columns=trainer_cols, show='tree headings', selectmode='browse')

        self.trainers_tree.heading('#0', text='Groep / Trainer')
        self.trainers_tree.column('#0', width=250, stretch=tk.YES)
        self.trainers_tree.heading('name', text='Naam')
        self.trainers_tree.column('name', width=200, stretch=tk.YES)
        self.trainers_tree.heading('email', text='E-mail')
        self.trainers_tree.column('email', width=180)
        self.trainers_tree.heading('phone', text='Telefoon')
        self.trainers_tree.column('phone', width=120)

        # Tags for striping
        self.trainers_tree.tag_configure('odd', background='#F5F5F5')
        self.trainers_tree.tag_configure('even', background='#FFFFFF')

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.trainers_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.trainers_tree.xview)
        self.trainers_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.trainers_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        self.trainers_tree.bind("<<TreeviewSelect>>", self._on_trainer_tree_select)
        self.trainers_tree.bind("<Double-1>", self._on_trainer_double_click)
        self.trainers_tree.bind("<ButtonPress-1>", self._dnd_start_drag_trainers)
        self.trainers_tree.bind("<B1-Motion>", self._dnd_drag_motion_trainers)
        self.trainers_tree.bind("<ButtonRelease-1>", self._dnd_drop_trainers)

        # Actions Panel
        actions_frame = ttk.Frame(pw_trainers, padding=(10, 0, 0, 0))
        pw_trainers.add(actions_frame, weight=1)

        group_actions = ttk.LabelFrame(actions_frame, text=" Groep Acties ", padding=10)
        group_actions.pack(fill=tk.X, expand=False)

        self.add_trainer_button = ttk.Button(group_actions, text="Trainer Toevoegen...", command=self._add_trainer_dialog)
        self.add_trainer_button.pack(fill=tk.X, pady=2)
        self.rename_trainer_group_button = ttk.Button(group_actions, text="Groep Hernoemen...", command=self._rename_trainer_group_dialog)
        self.rename_trainer_group_button.pack(fill=tk.X, pady=2)
        self.manage_group_images_button = ttk.Button(group_actions, text="Afbeeldingen Beheren...", command=self._manage_trainer_group_images_dialog)
        self.manage_group_images_button.pack(fill=tk.X, pady=2)
        self.edit_group_desc_button = ttk.Button(group_actions, text="Beschrijving Bewerken...", command=self._edit_trainer_group_description)
        self.edit_group_desc_button.pack(fill=tk.X, pady=2)
        self.delete_trainer_group_button = ttk.Button(group_actions, text="Groep Verwijderen", command=self._delete_trainer_group_dialog)
        self.delete_trainer_group_button.pack(fill=tk.X, pady=2)

        trainer_actions = ttk.LabelFrame(actions_frame, text=" Trainer Acties ", padding=10)
        trainer_actions.pack(fill=tk.X, expand=False, pady=(15, 0))

        self.edit_trainer_button = ttk.Button(trainer_actions, text="Trainer Bewerken...", command=self._edit_trainer_dialog)
        self.edit_trainer_button.pack(fill=tk.X, pady=2)
        self.delete_trainer_button = ttk.Button(trainer_actions, text="Trainer Verwijderen", command=self._delete_trainer)
        self.delete_trainer_button.pack(fill=tk.X, pady=2)

    def _create_times_tab(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        buttons_frame = ttk.Frame(parent)
        buttons_frame.grid(row=0, column=0, sticky='w', pady=(0, 10))

        self.add_time_cat_button = ttk.Button(buttons_frame, text="+ Categorie Toevoegen", command=self._add_time_category)
        self.add_time_cat_button.pack(side=tk.LEFT, padx=(0,5))
        self.rename_time_cat_button = ttk.Button(buttons_frame, text="Categorie Hernoemen", command=self._rename_time_category)
        self.rename_time_cat_button.pack(side=tk.LEFT, padx=5)
        self.edit_times_button = ttk.Button(buttons_frame, text="Tijden Bewerken...", command=self._edit_selected_times)
        self.edit_times_button.pack(side=tk.LEFT, padx=5)
        self.delete_time_cat_button = ttk.Button(buttons_frame, text="Categorie Verwijderen", command=self._delete_time_category)
        self.delete_time_cat_button.pack(side=tk.LEFT, padx=5)

        tree_frame = ttk.Frame(parent)
        tree_frame.grid(row=1, column=0, sticky='nsew')
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        times_cols = ('category_display', 'times_display')
        self.times_tree = ttk.Treeview(tree_frame, columns=times_cols, show='headings', selectmode='browse')

        self.times_tree.heading('category_display', text='Categorie')
        self.times_tree.column('category_display', width=200, anchor=tk.W)
        self.times_tree.heading('times_display', text='Dagen & Tijden')
        self.times_tree.column('times_display', width=500, anchor=tk.W)

        # Tags
        self.times_tree.tag_configure('odd', background='#F5F5F5')
        self.times_tree.tag_configure('even', background='#FFFFFF')

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.times_tree.yview)
        self.times_tree.configure(yscrollcommand=vsb.set)

        self.times_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')

        self.times_tree.bind("<<TreeviewSelect>>", self._on_times_category_select)
        self.times_tree.bind("<Double-1>", lambda e: self._edit_selected_times())
        self.times_tree.bind("<ButtonPress-1>", self._dnd_start_drag_times)
        self.times_tree.bind("<B1-Motion>", self._dnd_drag_motion_times)
        self.times_tree.bind("<ButtonRelease-1>", self._dnd_drop_times)

    def _create_contacts_tab(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        buttons_frame = ttk.Frame(parent)
        buttons_frame.grid(row=0, column=0, sticky='w', pady=(0, 10))

        self.add_contact_button = ttk.Button(buttons_frame, text="+ Contact Toevoegen", command=self._add_contact_dialog)
        self.add_contact_button.pack(side=tk.LEFT, padx=(0,5))
        self.edit_contact_button = ttk.Button(buttons_frame, text="Contact Bewerken...", command=self._edit_contact_dialog)
        self.edit_contact_button.pack(side=tk.LEFT, padx=5)
        self.delete_contact_button = ttk.Button(buttons_frame, text="Contact Verwijderen", command=self._delete_contact)
        self.delete_contact_button.pack(side=tk.LEFT, padx=5)

        tree_frame = ttk.Frame(parent)
        tree_frame.grid(row=1, column=0, sticky='nsew')
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        contact_cols = ('role', 'name', 'email', 'phone')
        self.contacts_tree = ttk.Treeview(tree_frame, columns=contact_cols, show='headings', selectmode='browse')

        self.contacts_tree.heading('role', text='Rol')
        self.contacts_tree.column('role', width=150, anchor=tk.W)
        self.contacts_tree.heading('name', text='Naam')
        self.contacts_tree.column('name', width=200, anchor=tk.W)
        self.contacts_tree.heading('email', text='E-mail')
        self.contacts_tree.column('email', width=250, anchor=tk.W)
        self.contacts_tree.heading('phone', text='Tel')
        self.contacts_tree.column('phone', width=120, anchor=tk.W)

        # Tags
        self.contacts_tree.tag_configure('odd', background='#F5F5F5')
        self.contacts_tree.tag_configure('even', background='#FFFFFF')

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.contacts_tree.yview)
        self.contacts_tree.configure(yscrollcommand=vsb.set)

        self.contacts_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')

        self.contacts_tree.bind("<<TreeviewSelect>>", self._on_contact_select)
        self.contacts_tree.bind("<Double-1>", lambda e: self._edit_contact_dialog())

    def _trainers_load(self):
        if not utils.confirm_discard_changes(self):
            return
        json_filepath = config.TRAINERS_JSON_FILE_PATH
        if not os.path.exists(json_filepath):
            self.trainers_file_loaded = False
            messagebox.showerror("Bestand Niet Gevonden", f"JSON-bestand niet gevonden:\n{json_filepath}", parent=self.app.root)
            self._set_ui_state(loaded=False)
            return

        self.app.set_status(f"Laden trainers data uit {os.path.basename(json_filepath)}...")
        loaded_data, error_msg = utils.trainers_load_json_data(json_filepath)

        if error_msg:
            self.trainers_file_loaded = False
            self.app.set_status(f"Fout bij laden JSON: {error_msg}", is_error=True)
            messagebox.showerror("Laad Fout JSON", f"Kon data niet laden:\n{error_msg}", parent=self.app.root)
        else:
            default_structure = {
                "pageTitle": "",
                "trainingTimes": [],
                "contacts": [],
                "trainerGroups": [],
                "times_category_order": [],
                "trainer_category_order": []
            }
            self.trainers_data = loaded_data or default_structure
            for key, default in default_structure.items():
                self.trainers_data.setdefault(key, default)
            self.trainers_file_loaded = True
            self.app.set_status(f"Data uit {os.path.basename(json_filepath)} succesvol geladen.", duration_ms=5000)

        self._populate_ui()
        self._set_ui_state(loaded=self.trainers_file_loaded)
        if self.trainers_file_loaded:
            utils.remember_editor_state(self, self.trainers_data)
        return self.trainers_file_loaded

    def has_unsaved_changes(self):
        return utils.editor_state_changed(self, self.trainers_data)

    def _set_ui_state(self, loaded):
        global_state = tk.NORMAL if loaded else tk.DISABLED
        self.save_button.config(state=global_state)
        self.add_time_cat_button.config(state=global_state)
        self.add_contact_button.config(state=global_state)
        self._on_trainer_tree_select()
        self._on_times_category_select()
        self._on_contact_select()

        if not loaded:
            self._clear_ui()

    def _clear_ui(self):
        for tree in [self.contacts_tree, self.times_tree, self.trainers_tree]:
            tree.delete(*tree.get_children())

    def _populate_ui(self):
        self._clear_ui()
        if self.trainers_file_loaded:
            self._populate_contacts_treeview()
            self._populate_times_treeview()
            self._populate_trainers_treeview()

    def _populate_trainers_treeview(self):
        self.trainers_tree.delete(*self.trainers_tree.get_children())
        groups = self.trainers_data.get('trainerGroups', [])
        order = self.trainers_data.get('trainer_category_order', [])
        order_map = {name: i for i, name in enumerate(order)}
        sorted_groups = sorted(groups, key=lambda g: order_map.get(g.get('groupName'), 999))

        for i, group_data in enumerate(sorted_groups):
            group_name = group_data.get('groupName', 'Onbekende Groep')

            # Insert Group
            group_iid = self.trainers_tree.insert('', 'end', text=group_name, open=True, tags=('group',), iid=group_name)

            # Insert Trainers
            trainers = group_data.get('trainers', [])
            for trainer_index, trainer in enumerate(trainers):
                trainer_iid = f"{group_name}_{trainer_index}"
                tag = 'odd' if trainer_index % 2 else 'even'
                self.trainers_tree.insert(
                    group_iid, 'end', iid=trainer_iid,
                    text=trainer.get('name', ''),
                    values=(trainer.get('name', ''), trainer.get('email', ''), trainer.get('phone', '')),
                    tags=('trainer', group_name, str(trainer_index), tag)
                )

    def _on_trainer_tree_select(self, event=None):
        selected_iids = self.trainers_tree.selection()
        group_state, trainer_state = tk.DISABLED, tk.DISABLED

        if self.trainers_file_loaded and selected_iids:
            tags = self.trainers_tree.item(selected_iids[0], 'tags')
            if 'group' in tags:
                group_state = tk.NORMAL
            elif 'trainer' in tags:
                trainer_state = tk.NORMAL
                group_state = tk.NORMAL # Can still add trainer to this group

        for btn, state in [
            (self.add_trainer_button, group_state),
            (self.rename_trainer_group_button, group_state),
            (self.manage_group_images_button, group_state),
            (self.edit_group_desc_button, group_state),
            (self.delete_trainer_group_button, group_state),
            (self.edit_trainer_button, trainer_state),
            (self.delete_trainer_button, trainer_state)
            ]:
            btn.config(state=state)

    def _on_trainer_double_click(self, event=None):
        if self.edit_trainer_button['state'] == tk.NORMAL:
            self._edit_trainer_dialog()

    def _edit_trainer_group_description(self):
        group_name = self._get_selected_group_name()
        if not group_name: return
        group_index = self._find_group_index(group_name)
        if group_index is None: return

        current = self.trainers_data['trainerGroups'][group_index].get('description', '')
        dlg = LargeTextDialog(self.parent, f"Groepsbeschrijving - {group_name}", current)

        if dlg.result is not None:
            self.trainers_data['trainerGroups'][group_index]['description'] = dlg.result.strip()
            if self.app:
                self.app.set_status(f"Beschrijving voor '{group_name}' bijgewerkt (nog niet opgeslagen).", duration_ms=4000)

    def _populate_times_treeview(self):
        self.times_tree.delete(*self.times_tree.get_children())
        training_times = self.trainers_data.get('trainingTimes', [])
        order = self.trainers_data.get('times_category_order', [])
        order_map = {cat: i for i, cat in enumerate(order)}
        sorted_times = sorted(training_times, key=lambda item: order_map.get(item.get('category'), 999))

        for idx, item in enumerate(sorted_times):
            category_html = item.get('category')
            if not category_html: continue
            display_category = utils.strip_html(category_html)

            schedule = sorted(item.get('schedule', []), key=lambda x: config.DAYS_ORDER.get(x.get('day', '').capitalize(), 99))
            display_str = " | ".join(f"{s['day']}: {s['time']} {s.get('note', '')}".strip() for s in schedule)

            tag = 'odd' if idx % 2 else 'even'
            self.times_tree.insert('', 'end', iid=category_html, values=(display_category, display_str), tags=(tag,))

    def _on_times_category_select(self, event=None):
        is_selected = bool(self.times_tree.selection())
        state = tk.NORMAL if is_selected and self.trainers_file_loaded else tk.DISABLED
        for btn in [self.rename_time_cat_button, self.delete_time_cat_button, self.edit_times_button]:
            btn.config(state=state)

    def _populate_contacts_treeview(self):
        self.contacts_tree.delete(*self.contacts_tree.get_children())
        contacts = self.trainers_data.get('contacts', [])
        for idx, contact in enumerate(sorted(contacts, key=lambda x: x.get('role', ''))):
            role = contact.get('role', 'N/A')
            tag = 'odd' if idx % 2 else 'even'
            self.contacts_tree.insert('', 'end', iid=role, values=(role, contact.get('name', ''), contact.get('email', ''), contact.get('phone', '')), tags=(tag,))

    def _on_contact_select(self, event=None):
        is_selected = bool(self.contacts_tree.selection())
        state = tk.NORMAL if is_selected and self.trainers_file_loaded else tk.DISABLED
        self.edit_contact_button.config(state=state)
        self.delete_contact_button.config(state=state)

    def _add_contact_dialog(self):
        if not self.trainers_file_loaded: return
        existing_roles = [c.get('role') for c in self.trainers_data.get('contacts', []) if c.get('role')]
        ContactDialog(self.parent, "Contact Toevoegen", existing_roles=existing_roles, callback=self._process_contact_edit)

    def _add_trainer_dialog(self):
        selected_iids = self.trainers_tree.selection()
        if not selected_iids: return
        tags = self.trainers_tree.item(selected_iids[0], 'tags')

        group_name = None
        if 'group' in tags:
            group_name = self.trainers_tree.item(selected_iids[0], 'text')
        elif 'trainer' in tags:
            # tags are ('trainer', group_name, index, stripe)
            group_name = tags[1]

        if not group_name: return

        initial_data = {'groupName': group_name}
        all_groups = self._get_trainer_group_names()
        TrainerDialog(self.parent, "Trainer Toevoegen", all_groups, initial_data, self._process_trainer_edit)

    def _edit_trainer_dialog(self):
        selected_iids = self.trainers_tree.selection()
        if not selected_iids: return
        tags = self.trainers_tree.item(selected_iids[0], 'tags')
        if 'trainer' not in tags: return

        group_name = tags[1]
        trainer_index = int(tags[2])

        trainer_data = self.trainers_data['trainerGroups'][self._find_group_index(group_name)]['trainers'][trainer_index]
        initial_data = {**trainer_data, 'groupName': group_name, 'original_trainer_index': trainer_index}
        all_groups = self._get_trainer_group_names()

        TrainerDialog(self.parent, "Trainer Bewerken", all_groups, initial_data, self._process_trainer_edit)

    def _delete_trainer(self):
        selected_iids = self.trainers_tree.selection()
        if not selected_iids: return
        tags = self.trainers_tree.item(selected_iids[0], 'tags')
        if 'trainer' not in tags: return

        group_name = tags[1]
        trainer_index = int(tags[2])
        trainer_name = self.trainers_tree.item(selected_iids[0], 'text')

        if not messagebox.askyesno("Verwijderen Bevestigen", f"Trainer '{trainer_name}' uit groep '{group_name}' verwijderen?", icon='warning', parent=self.parent):
            return

        group_index = self._find_group_index(group_name)
        if group_index is not None:
            del self.trainers_data['trainerGroups'][group_index]['trainers'][trainer_index]
            self._populate_trainers_treeview()
            self.app.set_status(f"Trainer '{trainer_name}' verwijderd (nog niet opgeslagen).", duration_ms=4000)

    def _rename_trainer_group_dialog(self):
        group_name = self._get_selected_group_name()
        if not group_name: return

        new_name = simpledialog.askstring("Groep Hernoemen", f"Nieuwe naam voor groep '{group_name}':", initialvalue=group_name, parent=self.parent)

        if not new_name or not new_name.strip() or new_name.strip() == group_name: return
        new_name = new_name.strip()

        if new_name in self._get_trainer_group_names():
            messagebox.showwarning("Groep Bestaat Al", f"Een groep met de naam '{new_name}' bestaat al.", parent=self.parent)
            return

        group_index = self._find_group_index(group_name)
        if group_index is not None:
            self.trainers_data['trainerGroups'][group_index]['groupName'] = new_name
            order = self.trainers_data.setdefault('trainer_category_order', [])
            if group_name in order:
                order[order.index(group_name)] = new_name
            self._populate_trainers_treeview()
            self.app.set_status(f"Groep '{group_name}' hernoemd naar '{new_name}' (nog niet opgeslagen).", duration_ms=4000)

    def _delete_trainer_group_dialog(self):
        group_name = self._get_selected_group_name()
        if not group_name: return

        if not messagebox.askyesno("Groep Verwijderen", f"Groep '{group_name}' en alle bijbehorende trainers definitief verwijderen?", icon='warning', parent=self.parent):
            return

        group_index = self._find_group_index(group_name)
        if group_index is not None:
            del self.trainers_data['trainerGroups'][group_index]
            order = self.trainers_data.setdefault('trainer_category_order', [])
            if group_name in order:
                order.remove(group_name)
            self._populate_trainers_treeview()
            self.app.set_status(f"Groep '{group_name}' verwijderd (nog niet opgeslagen).", duration_ms=4000)

    def _manage_trainer_group_images_dialog(self):
        group_name = self._get_selected_group_name()
        if not group_name: return
        group_index = self._find_group_index(group_name)
        if group_index is None: return

        group_data_ref = self.trainers_data['trainerGroups'][group_index]
        GroupImageManagerDialog(self.parent, group_data_ref, self.app, self._handle_group_image_management_result)

    def _get_selected_group_name(self):
        sel = self.trainers_tree.selection()
        if not sel: return None
        tags = self.trainers_tree.item(sel[0], 'tags')

        if 'group' in tags:
            return self.trainers_tree.item(sel[0], 'text')
        elif 'trainer' in tags:
            return tags[1]
        return None

    def _find_group_index(self, group_name):
        return next((i for i, g in enumerate(self.trainers_data.get('trainerGroups', [])) if g.get('groupName') == group_name), None)

    def _get_trainer_group_names(self):
        return sorted([g.get('groupName') for g in self.trainers_data.get('trainerGroups', []) if g.get('groupName')])

    def _edit_contact_dialog(self):
        selected = self.contacts_tree.selection();
        if not selected: return
        role_iid = selected[0]

        contact_to_edit = next((c for c in self.trainers_data.get('contacts', []) if c.get('role') == role_iid), None)
        if not contact_to_edit:
            messagebox.showerror("Fout", f"Contact met rol '{role_iid}' niet gevonden.", parent=self.parent)
            return

        initial_data = copy.deepcopy(contact_to_edit)
        initial_data['is_edit_mode'] = True
        existing_roles = [c.get('role') for c in self.trainers_data.get('contacts', []) if c.get('role') != role_iid]

        ContactDialog(self.parent, "Contact Bewerken", initial_data, existing_roles=existing_roles, callback=self._process_contact_edit)

    def _process_contact_edit(self, result_data, original_role_on_edit_start):
        if result_data is None: return

        new_role = result_data['role']
        img_source_path_to_copy = result_data.pop('_source_path_to_copy', None)
        current_web_img_path = result_data.get('image')
        final_web_img_path = current_web_img_path

        if img_source_path_to_copy:
            target_dir_abs = config.CONTACTS_IMG_DIR_ABS
            target_href_base = config.CONTACTS_IMG_HREF_BASE
            filename = os.path.basename(img_source_path_to_copy)
            dest_path_abs = os.path.join(target_dir_abs, filename)

            try:
                os.makedirs(target_dir_abs, exist_ok=True)
                dest_path_abs = utils.copy_new_asset(img_source_path_to_copy, dest_path_abs, owner=self)
                filename = os.path.basename(dest_path_abs)

                final_web_img_path = str(pathlib.PurePosixPath(target_href_base) / filename).replace('\\', '/')
            except Exception as e:
                messagebox.showerror("Afbeelding Kopieer Fout", f"Kon afbeelding niet kopiëren:\n{e}", parent=self.parent)
                return False
        elif not current_web_img_path:
            final_web_img_path = config.DEFAULT_CONTACT_IMG_SRC

        contact_for_json = {
            'role': new_role,
            'name': result_data['name'],
            'email': result_data.get('email'),
            'phone': result_data.get('phone'),
            'image': final_web_img_path,
            'imageAlt': result_data.get('imageAlt', f"Foto {result_data['name']}")
        }

        contacts_list = self.trainers_data.setdefault('contacts', [])

        if original_role_on_edit_start:
            found_idx = next((i for i, c in enumerate(contacts_list) if c.get('role') == original_role_on_edit_start), -1)
            if found_idx != -1:
                contacts_list[found_idx] = contact_for_json
                status_msg = f"Contact '{new_role}' bijgewerkt."
            else:
                contacts_list.append(contact_for_json)
                status_msg = f"Contact '{new_role}' toegevoegd (originele niet gevonden)."
        else:
            contacts_list.append(contact_for_json)
            status_msg = f"Contact '{new_role}' toegevoegd."

        self._populate_contacts_treeview()
        if self.app: self.app.set_status(status_msg + " (Wijzigingen nog niet opgeslagen)", duration_ms=4000)
        if self.contacts_tree.exists(new_role):
            self.contacts_tree.selection_set(new_role)
            self.contacts_tree.focus(new_role)
            self.contacts_tree.see(new_role)

    def _delete_contact(self):
        selected = self.contacts_tree.selection();
        if not selected: return
        role_to_delete = selected[0]

        if not messagebox.askyesno("Contact Verwijderen", f"Contactpersoon met rol '{role_to_delete}' definitief verwijderen?", icon='warning', parent=self.parent): return

        contacts_list = self.trainers_data.get('contacts', [])
        self.trainers_data['contacts'] = [c for c in contacts_list if c.get('role') != role_to_delete]

        if len(self.trainers_data['contacts']) < len(contacts_list):
            self._populate_contacts_treeview()
            if self.app: self.app.set_status(f"Contact '{role_to_delete}' verwijderd (nog niet opgeslagen).", duration_ms=4000)

    def _add_time_category(self):
        if not self.trainers_file_loaded: return
        new_name = simpledialog.askstring("Nieuwe Trainings Categorie", "Naam nieuwe categorie (zonder HTML):", parent=self.parent)
        if not new_name or not new_name.strip(): return

        new_name = new_name.strip()
        new_html = f"<strong>{html.escape(new_name)}</strong>"

        if any(t.get('category') == new_html for t in self.trainers_data.get('trainingTimes', [])):
            messagebox.showwarning("Categorie Bestaat Al", f"Categorie '{new_name}' bestaat al.", parent=self.parent)
            return

        self.trainers_data.setdefault('trainingTimes', []).append({"category": new_html, "schedule": []})
        self.trainers_data.setdefault('times_category_order', []).append(new_html)

        self._populate_times_treeview()
        if self.app: self.app.set_status(f"Categorie '{new_name}' toegevoegd (nog niet opgeslagen).", duration_ms=4000)

        if self.times_tree.exists(new_html):
            self.times_tree.selection_set(new_html)
            self.times_tree.focus(new_html)
            self.times_tree.see(new_html)

    def _rename_time_category(self):
        selected = self.times_tree.selection();
        if not selected: return
        old_html = selected[0]

        item = next((i for i in self.trainers_data.get('trainingTimes', []) if i.get('category') == old_html), None)
        if not item: return

        old_name = utils.strip_html(old_html)
        new_name = simpledialog.askstring("Categorie Hernoemen", f"Nieuwe naam voor '{old_name}' (zonder HTML):", initialvalue=old_name, parent=self.parent)

        if not new_name or not new_name.strip(): return
        new_name = new_name.strip()
        new_html = f"<strong>{html.escape(new_name)}</strong>"

        if new_html == old_html: return

        if any(t.get('category') == new_html for t in self.trainers_data.get('trainingTimes', []) if t.get('category') != old_html):
            messagebox.showwarning("Categorie Bestaat Al", f"Categorie '{new_name}' bestaat al.", parent=self.parent)
            return

        item['category'] = new_html
        order = self.trainers_data.setdefault('times_category_order', [])
        if old_html in order:
            order[order.index(old_html)] = new_html

        self._populate_times_treeview()
        if self.app: self.app.set_status(f"Categorie '{old_name}' hernoemd (nog niet opgeslagen).", duration_ms=4000)

        if self.times_tree.exists(new_html):
            self.times_tree.selection_set(new_html)
            self.times_tree.focus(new_html)
            self.times_tree.see(new_html)

    def _delete_time_category(self):
        selected = self.times_tree.selection();
        if not selected: return
        cat_html = selected[0]
        cat_name = utils.strip_html(cat_html)

        if not messagebox.askyesno("Categorie Verwijderen", f"Categorie '{cat_name}' en alle tijden verwijderen?", icon='warning', parent=self.parent): return

        times_list = self.trainers_data.get('trainingTimes', [])
        self.trainers_data['trainingTimes'] = [t for t in times_list if t.get('category') != cat_html]

        order = self.trainers_data.setdefault('times_category_order', [])
        if cat_html in order:
            order.remove(cat_html)

        self._populate_times_treeview()
        if self.app: self.app.set_status(f"Categorie '{cat_name}' verwijderd (nog niet opgeslagen).", duration_ms=4000)

    def _edit_selected_times(self):
        selected = self.times_tree.selection();
        if not selected: return
        cat_html = selected[0]

        item = next((i for i in self.trainers_data.get('trainingTimes', []) if i.get('category') == cat_html), None)
        if not item: return

        EditTimeDialog(self.parent, "Trainingstijden Bewerken", cat_html, copy.deepcopy(item.get('schedule', [])), self._update_times_data)

    def _update_times_data(self, category_html_id, new_schedule_list):
        if new_schedule_list is not None:
            item = next((i for i in self.trainers_data.setdefault('trainingTimes', []) if i.get('category') == category_html_id), None)
            if item:
                item['schedule'] = new_schedule_list
                self._populate_times_treeview()
                if self.app: self.app.set_status(f"Tijden voor '{utils.strip_html(category_html_id)}' bijgewerkt (nog niet opgeslagen).", duration_ms=4000)
                if self.times_tree.exists(category_html_id):
                    self.times_tree.selection_set(category_html_id)

    # Drag and Drop handlers
    def _dnd_start_drag_times(self, event):
        if self.times_tree.identify_region(event.x, event.y) not in ("cell", "tree"):
            self._dnd_dragged_item = None
            return
        self._dnd_dragged_item = self.times_tree.identify_row(event.y)

    def _dnd_drag_motion_times(self, event):
        if not self._dnd_dragged_item: return
        target_iid = self.times_tree.identify_row(event.y)
        if target_iid and target_iid != self._dnd_dragged_item:
            try:
                self.times_tree.move(self._dnd_dragged_item, '', self.times_tree.index(target_iid))
            except tk.TclError: pass

    def _dnd_drop_times(self, event):
        if not self._dnd_dragged_item: return
        self._dnd_dragged_item = None
        self.trainers_data['times_category_order'] = list(self.times_tree.get_children(''))
        if self.app: self.app.set_status("Volgorde trainingstijden aangepast (nog niet opgeslagen).", duration_ms=4000)

    def _dnd_start_drag_trainers(self, event):
        if self.trainers_tree.identify_region(event.x, event.y) not in ("cell", "tree"):
            self._dnd_dragged_item = None
            return
        item = self.trainers_tree.identify_row(event.y)
        if item and self.trainers_tree.parent(item) == '':
            self._dnd_dragged_item = item
        else:
            self._dnd_dragged_item = None

    def _dnd_drag_motion_trainers(self, event):
        if not self._dnd_dragged_item: return
        target_iid = self.trainers_tree.identify_row(event.y)
        if target_iid and target_iid != self._dnd_dragged_item and self.trainers_tree.parent(target_iid) == '':
            try:
                self.trainers_tree.move(self._dnd_dragged_item, '', self.trainers_tree.index(target_iid))
            except tk.TclError: pass

    def _dnd_drop_trainers(self, event):
        if not self._dnd_dragged_item: return
        self._dnd_dragged_item = None
        self.trainers_data['trainer_category_order'] = list(self.trainers_tree.get_children(''))
        if self.app: self.app.set_status("Volgorde trainergroepen aangepast (nog niet opgeslagen).", duration_ms=4000)

    def _process_trainer_edit(self, new_trainer_data, original_group_name=None, original_trainer_index=None, tree_iid=None):
        if new_trainer_data is None: return

        target_group_name = new_trainer_data['groupName']
        trainer_entry = {
            'name': new_trainer_data['name'],
            'email': new_trainer_data.get('email'),
            'phone': new_trainer_data.get('phone')
        }

        all_groups = self.trainers_data.setdefault('trainerGroups', [])
        target_group = next((g for g in all_groups if g.get('groupName') == target_group_name), None)

        if target_group is None:
            # Create new group
            placeholder = config.DEFAULT_TRAINER_GROUP_MAIN_IMG_SRC
            if not os.path.isfile(utils.get_abs_path(placeholder)):
                placeholder = config.DEFAULT_CONTACT_IMG_SRC
            main_photo = {'src': placeholder, 'alt': f"Hoofdfoto {target_group_name}"}
            thumbs = []

            target_group = {
                'groupName': target_group_name,
                'description': f"Info voor groep {target_group_name}",
                'mainPhoto': main_photo,
                'thumbnails': thumbs,
                'trainers': []
            }
            all_groups.append(target_group)
            self.trainers_data.setdefault('trainer_category_order', []).append(target_group_name)

        if original_group_name is not None and original_trainer_index is not None:
            original_group = next((g for g in all_groups if g.get('groupName') == original_group_name), None)
            if original_group and 0 <= original_trainer_index < len(original_group.get('trainers', [])):
                if original_group is target_group:
                    original_group['trainers'][original_trainer_index] = trainer_entry
                    self._populate_trainers_treeview()
                    if self.app: self.app.set_status("Trainer bijgewerkt (nog niet opgeslagen).", duration_ms=4000)
                    return
                del original_group['trainers'][original_trainer_index]

        target_group.setdefault('trainers', []).append(trainer_entry)
        self._populate_trainers_treeview()
        if self.app: self.app.set_status("Trainer lijst bijgewerkt (nog niet opgeslagen).", duration_ms=4000)

    def _handle_group_image_management_result(self, changes_made):
        if changes_made:
            if self.app: self.app.set_status("Groep afbeeldingen bijgewerkt (nog niet opgeslagen).", duration_ms=4000)

    def _get_current_data_from_ui(self):
        data = copy.deepcopy(self.trainers_data)
        data.setdefault('pageTitle', "Training & Trainers - Atletiekclub Sparta Bornem")
        return data

    def _trainers_save(self):
        if not self.trainers_file_loaded: return
        data_to_save = self._get_current_data_from_ui()
        json_filepath = config.TRAINERS_JSON_FILE_PATH

        if self.app: self.app.set_status(f"Opslaan naar {os.path.basename(json_filepath)}...")
        error_msg = utils.trainers_save_json_data(json_filepath, data_to_save)

        if not error_msg:
            if self.app: self.app.set_status(f"Succesvol opgeslagen naar {os.path.basename(json_filepath)}.", duration_ms=5000)
            self.trainers_data = copy.deepcopy(data_to_save)
            utils.remember_editor_state(self, self.trainers_data)
        else:
            if self.app: self.app.set_status(f"Fout bij opslaan JSON: {error_msg}", is_error=True)
            messagebox.showerror("Opslag Fout JSON", f"Kon niet opslaan:\n{error_msg}", parent=self.parent)

def create_trainers_tab(parent_frame, app_instance):
    return TrainersTab(parent_frame, app_instance)

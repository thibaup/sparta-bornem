import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, font as tkFont
import os
import html
import re
import traceback
import sys

# --- Mock/Placeholder Imports for Context ---
# In a real scenario, these import from your project files.
try:
    import config
    import utils
except ImportError:
    # Fallback if running standalone for testing UI
    class Config:
        RECORDS_BASE_DIR_ABSOLUTE = "."
    class Utils:
        def records_discover_files(self, path): return {}
        def records_parse_html(self, path): return {}
        def records_save_html(self, *args): return True, ""
        def records_header_append_type(self, *args): pass
        def records_header_remove_type(self, *args): pass
        def records_header_set_order(self, *args): pass
    config = Config()
    utils = Utils()

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    class DummyBs4Type: pass
    BeautifulSoup, NavigableString, Tag = (DummyBs4Type,) * 3

# --- Constants & Templates ---

NEW_RECORD_HTML_TEMPLATE_FOR_TAB = """<!DOCTYPE html>
<html lang="nl-NL"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Clubrecords {record_type_title} - Sparta Bornem</title>
<link rel="stylesheet" href="/css/style.css"></head><body>
<div id="header-placeholder"><p style="text-align:center; padding: 20px;">Loading header...</p></div>
<main class="container"><h1 style="color: #1774b4;">{record_type_title}</h1>
<div class="table-responsive"><table class="records-table"><thead><tr>
<th>Discipline</th><th>Naam</th><th>Prestatie</th><th>Plaats</th><th>Datum</th>
</tr></thead><tbody></tbody></table></div>
<p class="record-notice">{record_contact_prefix_text} <a href="mailto:{record_contact_email}">{record_contact_email}</a></p>
</main>
<div id="footer-placeholder"><p style="text-align:center; padding: 20px;">Loading footer...</p></div>
<script defer src="/js/script.js"></script>
</body></html>"""

DEFAULT_NEW_RECORD_CONTACT_PREFIX = "Je clubrecord niet opgenomen? Mail naar"
DEFAULT_NEW_RECORD_CONTACT_EMAIL = "j_permentier@hotmail.com"

# --- Helper Functions ---

def center_window(window, parent=None):
    """Centers a Toplevel window relative to its parent or the screen."""
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

def _split_names(raw, split_commas=False):
    """Splits a string of names into a list based on common separators."""
    if not raw:
        return []
    # Ordinary names are plain text. The editor joins existing member lists with bullets.
    if not split_commas:
        return [part.strip() for part in str(raw).split(' • ') if part.strip()]
    # Only explicit bulk relay paste interprets these separators.
    s = re.sub(r'<br\s*/?>|&(?:amp;)*lt;br\s*/?&(?:amp;)*gt;', '\n', str(raw), flags=re.IGNORECASE)
    separators = r'[\n\r•·|/;,]'
    return [part.strip() for part in re.split(separators, s) if part.strip()]

def _join_names(names):
    """Joins a list of names into a single string."""
    return " • ".join([n.strip() for n in names if n and n.strip()])

def _record_to_dict(record):
    """Normalizes current and legacy record shapes to a complete dict."""
    if isinstance(record, dict):
        names = record.get("names", [])
        if isinstance(names, str):
            names = _split_names(names)
        elif not isinstance(names, (list, tuple)):
            names = []
        if not names and record.get("name"):
            names = _split_names(record.get("name"))
        return {
            "discipline": str(record.get("discipline", "") or "").strip(),
            "names": [str(n).strip() for n in names if str(n).strip()],
            "performance": str(record.get("performance", "") or "").strip(),
            "place": str(record.get("place", "") or "").strip(),
            "date": str(record.get("date", "") or "").strip(),
        }

    if isinstance(record, (list, tuple)):
        padded = (list(record) + [""] * 5)[:5]
        return {
            "discipline": str(padded[0] or "").strip(),
            "names": _split_names(padded[1]),
            "performance": str(padded[2] or "").strip(),
            "place": str(padded[3] or "").strip(),
            "date": str(padded[4] or "").strip(),
        }

    return {"discipline": "", "names": [], "performance": "", "place": "", "date": ""}

# --- Dialog Classes ---

class RelayDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_record, callback):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.callback = callback
        self.result = None
        self._drag_index = None

        data = _record_to_dict(initial_record)

        # Variables
        self.var_discipline = tk.StringVar(value=data.get("discipline", ""))
        self.var_perf = tk.StringVar(value=data.get("performance", ""))
        self.var_place = tk.StringVar(value=data.get("place", ""))
        self.var_date = tk.StringVar(value=data.get("date", ""))

        # Handle name data input (could be list or string)
        raw_names = data.get("names", [])
        if not raw_names and data.get("name"):
            raw_names = _split_names(data.get("name"))

        # Main Layout
        frame = ttk.Frame(self, padding=15)
        frame.pack(expand=True, fill=tk.BOTH)

        # Grid Configuration
        frame.columnconfigure(1, weight=1)

        # Form Fields
        self._create_field(frame, 0, "Discipline:*", self.var_discipline, focus=True)
        self._create_field(frame, 1, "Prestatie:", self.var_perf)
        self._create_field(frame, 2, "Plaats:", self.var_place)
        self._create_field(frame, 3, "Datum:", self.var_date)

        # Team Members Section
        members_box = ttk.LabelFrame(frame, text="Teamleden (Drag & Drop om te sorteren)", padding=8)
        members_box.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        members_box.columnconfigure(0, weight=1)
        members_box.rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(members_box, height=6, activestyle="dotbox", selectmode=tk.SINGLE)
        self.listbox.grid(row=0, column=0, rowspan=4, sticky="nsew", padx=(0, 5))

        sb = ttk.Scrollbar(members_box, orient="vertical", command=self.listbox.yview)
        sb.grid(row=0, column=1, rowspan=4, sticky="ns")
        self.listbox.configure(yscrollcommand=sb.set)

        # Buttons for Listbox
        btns = ttk.Frame(members_box)
        btns.grid(row=0, column=2, sticky="n")

        ttk.Button(btns, text="Toevoegen", command=self._add_member).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Bewerken", command=self._edit_member).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Verwijderen", command=self._del_member).pack(fill=tk.X, pady=2)
        ttk.Button(btns, text="Plakken...", command=self._paste_bulk).pack(fill=tk.X, pady=2)

        # Populate Listbox
        for n in raw_names:
            if n: self.listbox.insert(tk.END, n)

        # Bindings
        self.listbox.bind("<Double-1>", lambda e: self._edit_member())
        self.listbox.bind("<Button-1>", self._drag_start)
        self.listbox.bind("<B1-Motion>", self._drag_motion)
        self.listbox.bind("<ButtonRelease-1>", self._drag_stop)
        self.listbox.bind("<Delete>", lambda e: self._del_member())

        # Action Buttons
        action_frame = ttk.Frame(frame)
        action_frame.grid(row=5, column=0, columnspan=2, sticky="e", pady=(15, 0))
        ttk.Button(action_frame, text="OK", command=self._ok).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(action_frame, text="Annuleren", command=self._cancel).pack(side=tk.RIGHT)

        # Window Settings
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())

        center_window(self, parent)

    def _create_field(self, parent, row, label, var, focus=False):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=4)
        entry = ttk.Entry(parent, textvariable=var)
        entry.grid(row=row, column=1, sticky="ew", padx=5, pady=4)
        if focus:
            entry.focus_set()

    def _add_member(self):
        name = simpledialog.askstring("Lid toevoegen", "Naam:", parent=self)
        if name and name.strip():
            self.listbox.insert(tk.END, name.strip())

    def _edit_member(self):
        sel = self.listbox.curselection()
        if not sel: return
        idx = sel[0]
        current = self.listbox.get(idx)
        name = simpledialog.askstring("Naam bewerken", "Naam:", initialvalue=current, parent=self)
        if name is not None:
            self.listbox.delete(idx)
            if name.strip():
                self.listbox.insert(idx, name.strip())
                self.listbox.selection_set(idx)

    def _del_member(self):
        sel = list(self.listbox.curselection())
        for i in reversed(sel):
            self.listbox.delete(i)

    def _paste_bulk(self):
        txt = simpledialog.askstring("Plakken", "Plak namen (gescheiden door komma, slash of nieuwe lijn):", parent=self)
        if txt:
            names = _split_names(txt, split_commas=True)
            for n in names:
                self.listbox.insert(tk.END, n)

    # --- Drag and Drop Logic ---
    def _drag_start(self, event):
        self._drag_index = self.listbox.nearest(event.y)
        self.listbox.selection_clear(0, tk.END)
        if 0 <= self._drag_index < self.listbox.size():
            self.listbox.selection_set(self._drag_index)

    def _drag_motion(self, event):
        if self._drag_index is None: return
        new_idx = self.listbox.nearest(event.y)

        if 0 <= new_idx < self.listbox.size() and new_idx != self._drag_index:
            text = self.listbox.get(self._drag_index)
            self.listbox.delete(self._drag_index)
            self.listbox.insert(new_idx, text)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(new_idx)
            self._drag_index = new_idx

    def _drag_stop(self, event):
        self._drag_index = None

    def _ok(self):
        disc = self.var_discipline.get().strip()
        if not disc:
            messagebox.showwarning("Invoer Vereist", "Discipline is verplicht.", parent=self)
            return

        names = [self.listbox.get(i) for i in range(self.listbox.size())]
        names = [n.strip() for n in names if n.strip()]

        if not names:
            messagebox.showwarning("Invoer Vereist", "Voeg minstens één naam toe.", parent=self)
            return

        self.result = {
            "discipline": disc,
            "names": names,
            "performance": self.var_perf.get().strip(),
            "place": self.var_place.get().strip(),
            "date": self.var_date.get().strip(),
        }
        if self.callback:
            self.callback(self.result)
        self.destroy()

    def _cancel(self):
        self.destroy()


class RecordDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_data=None, callback=None):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.callback = callback
        self.result = None

        # Prepare Data
        if isinstance(initial_data, dict):
            # Dict input
            initial_data = _record_to_dict(initial_data)
            d_disc = initial_data.get("discipline", "")
            d_names = initial_data.get("names", [])
            if not d_names and initial_data.get("name"):
                d_names = _split_names(initial_data.get("name"))
            d_name_str = _join_names(d_names)
            d_perf = initial_data.get("performance", "")
            d_place = initial_data.get("place", "")
            d_date = initial_data.get("date", "")
        elif isinstance(initial_data, (list, tuple)):
            # List input (legacy or flat)
            padded = (list(initial_data) + [""] * 5)
            d_disc, d_name_str, d_perf, d_place, d_date = padded[:5]
        else:
            d_disc, d_name_str, d_perf, d_place, d_date = "", "", "", "", ""

        # Layout
        frame = ttk.Frame(self, padding="15")
        frame.pack(expand=True, fill=tk.BOTH)
        frame.columnconfigure(1, weight=1)

        self.entries = {}
        fields = [
            ("discipline", "Discipline:*", d_disc),
            ("name", "Naam:*", d_name_str),
            ("performance", "Prestatie:", d_perf),
            ("place", "Plaats:", d_place),
            ("date", "Datum:", d_date)
        ]

        for i, (key, label, val) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky=tk.W, padx=5, pady=5)
            entry = ttk.Entry(frame, width=40)
            entry.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
            entry.insert(0, str(val))
            self.entries[key] = entry

        # Relay Editor Link
        link_frame = ttk.Frame(frame)
        link_frame.grid(row=len(fields), column=1, sticky="w", pady=(5, 0))
        link_label = ttk.Label(link_frame, text="Meer opties / estafette...", foreground="blue", cursor="hand2")
        link_label.pack(side=tk.LEFT)
        link_label.bind("<Button-1>", lambda e: self._open_relay_editor())

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=len(fields) + 1, column=0, columnspan=2, pady=(15, 0), sticky="e")
        ttk.Button(btn_frame, text="OK", command=self.on_ok).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="Annuleren", command=self.on_cancel).pack(side=tk.RIGHT)

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.bind("<Return>", self.on_ok)
        self.bind("<Escape>", self.on_cancel)

        center_window(self, parent)
        self.entries["discipline"].focus_set()

    def _open_relay_editor(self):
        current_data = {
            "discipline": self.entries["discipline"].get(),
            "names": _split_names(self.entries["name"].get()),
            "performance": self.entries["performance"].get(),
            "place": self.entries["place"].get(),
            "date": self.entries["date"].get(),
        }

        def on_relay_back(updated):
            if not updated: return
            self.entries["discipline"].delete(0, tk.END); self.entries["discipline"].insert(0, updated["discipline"])
            self.entries["name"].delete(0, tk.END); self.entries["name"].insert(0, _join_names(updated["names"]))
            self.entries["performance"].delete(0, tk.END); self.entries["performance"].insert(0, updated["performance"])
            self.entries["place"].delete(0, tk.END); self.entries["place"].insert(0, updated["place"])
            self.entries["date"].delete(0, tk.END); self.entries["date"].insert(0, updated["date"])

        relay = RelayDialog(self, "Uitgebreid Bewerken", current_data, on_relay_back)
        self.wait_window(relay)
        self.grab_set()

    def on_ok(self, event=None):
        disc = self.entries["discipline"].get().strip()
        names_str = self.entries["name"].get().strip()

        if not disc:
            messagebox.showwarning("Invoer Vereist", "Veld 'Discipline' is verplicht.", parent=self)
            self.entries["discipline"].focus_set()
            return
        if not names_str:
            messagebox.showwarning("Invoer Vereist", "Veld 'Naam' is verplicht.", parent=self)
            self.entries["name"].focus_set()
            return

        self.result = {
            "discipline": disc,
            "names": _split_names(names_str),
            "performance": self.entries["performance"].get().strip(),
            "place": self.entries["place"].get().strip(),
            "date": self.entries["date"].get().strip(),
        }
        if self.callback:
            self.callback(self.result)
        self.destroy()

    def on_cancel(self, event=None):
        self.destroy()


class AddNewTypeDialog(tk.Toplevel):
    def __init__(self, parent, title, existing_categories, callback):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.callback = callback

        frame = ttk.Frame(self, padding="15")
        frame.pack(expand=True, fill=tk.BOTH)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Kies Categorie:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(frame, textvariable=self.category_var, values=existing_categories, state="readonly")
        if existing_categories: self.category_combo.set(existing_categories[0])
        self.category_combo.grid(row=0, column=1, sticky='ew', padx=5, pady=2)

        ttk.Label(frame, text="Nieuwe Type Naam:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.type_entry = ttk.Entry(frame, width=30)
        self.type_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=2)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(15,0), sticky=tk.E)
        ttk.Button(btn_frame, text="Aanmaken", command=self.on_ok).pack(side=tk.RIGHT, padx=(5,0))
        ttk.Button(btn_frame, text="Annuleren", command=self.on_cancel).pack(side=tk.RIGHT)

        self.grab_set()
        center_window(self, parent)
        self.type_entry.focus_set()
        self.bind("<Return>", self.on_ok)
        self.bind("<Escape>", self.on_cancel)

    def on_ok(self, event=None):
        cat = self.category_var.get()
        type_n = self.type_entry.get().strip()

        if not cat:
            messagebox.showwarning("Selectie Vereist", "Selecteer een categorie.", parent=self); return
        if not type_n:
            messagebox.showwarning("Invoer Vereist", "Voer een naam in.", parent=self); return
        if any(c in r'/\:*?"<>|' for c in type_n):
            messagebox.showwarning("Ongeldige Tekens", "Naam bevat ongeldige tekens voor een bestandsnaam.", parent=self); return

        self.callback((cat, type_n))
        self.destroy()

    def on_cancel(self, event=None):
        self.destroy()

# --- Main Tab Class ---

class RecordsTab:
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance

        # Data Models
        self.records_structure = {}
        self.nav_tree_map = {}
        self.records_current_file_path = None
        self.records_current_type_name = ""
        self.records_current_data = [] # List of dicts
        self._data_dirty = False
        self._loading_data = False

        # Drag and Drop State
        self._drag_data = {"item": None, "y": 0}
        self._nav_drag = {"item": None, "parent": None, "moved": False}

        # UI Variables
        self.title_var = tk.StringVar(value="Selecteer een record type")
        self.current_contact_prefix_var = tk.StringVar()
        self.current_contact_email_var = tk.StringVar()

        # Config
        self.tree_columns = {
            'discipline': 'Discipline', 'name': 'Naam',
            'performance': 'Prestatie', 'place': 'Plaats', 'date': 'Datum'
        }
        self.tree_column_ids = list(self.tree_columns.keys())

        # Style Setup
        self._setup_styles()
        self._create_widgets()
        self._records_discover_and_populate_categories()

    def _setup_styles(self):
        style = ttk.Style()
        style.configure("Bold.TLabel", font=("Segoe UI", 9, "bold"))
        style.configure("Desc.TLabel", foreground="#555555", font=("Segoe UI", 10, "italic"))
        # Increase Treeview row height for readability
        style.configure("Treeview", rowheight=24)

    def _create_widgets(self):
        # Main Layout
        self.paned_window = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Panes
        left_pane = self._create_left_pane()
        self.paned_window.add(left_pane, weight=1)

        right_pane = self._create_right_pane()
        self.paned_window.add(right_pane, weight=4)

        self._show_placeholder()

    def _create_left_pane(self):
        pane = ttk.Frame(self.paned_window, padding=5)
        pane.grid_rowconfigure(1, weight=1)
        pane.grid_columnconfigure(0, weight=1)

        ttk.Label(pane, text="Record Categorieën", style="Bold.TLabel").grid(row=0, column=0, sticky='w', pady=(0, 5))

        # Nav Tree
        tree_frame = ttk.Frame(pane)
        tree_frame.grid(row=1, column=0, sticky='nsew')
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.nav_tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        self.nav_tree.grid(row=0, column=0, sticky='nsew')

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.nav_tree.yview)
        vsb.grid(row=0, column=1, sticky='ns')
        self.nav_tree.configure(yscrollcommand=vsb.set)

        # Bindings
        self.nav_tree.bind("<<TreeviewSelect>>", self._on_nav_tree_select)
        self.nav_tree.bind("<Button-1>", self._nav_dnd_start)
        self.nav_tree.bind("<B1-Motion>", self._nav_dnd_motion)
        self.nav_tree.bind("<ButtonRelease-1>", self._nav_dnd_drop)

        # Buttons
        actions_frame = ttk.Frame(pane)
        actions_frame.grid(row=2, column=0, sticky='ew', pady=(5, 0))

        self.add_type_button = ttk.Button(actions_frame, text="Nieuw Type...", command=self._add_new_type)
        self.add_type_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        self.delete_type_button = ttk.Button(actions_frame, text="Verwijder", command=self._delete_selected_type)
        self.delete_type_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        if not BS4_AVAILABLE:
            self.add_type_button.config(state=tk.DISABLED)
            self.delete_type_button.config(state=tk.DISABLED)

        return pane

    def _create_right_pane(self):
        pane = ttk.Frame(self.paned_window, padding=5)
        pane.grid_rowconfigure(1, weight=1)
        pane.grid_columnconfigure(0, weight=1)

        # Title
        title_font = tkFont.Font(family="Segoe UI", size=14, weight="bold")
        self.title_label = ttk.Label(pane, textvariable=self.title_var, font=title_font, anchor="w")
        self.title_label.grid(row=0, column=0, sticky='ew', pady=(0, 10))

        # Content Area (swaps between Placeholder and Data Table)
        self.content_frame = ttk.Frame(pane)
        self.content_frame.grid(row=1, column=0, sticky='nsew')
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        self.placeholder_label = ttk.Label(self.content_frame, text="Selecteer een record type links om te beginnen.", style="Desc.TLabel", anchor="center")

        self._create_records_tree()

        # Bottom Controls
        bottom_frame = ttk.Frame(pane)
        bottom_frame.grid(row=2, column=0, sticky='ew', pady=(10, 0))
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.columnconfigure(1, weight=1)

        self._create_messages_box(bottom_frame)
        self._create_contact_box(bottom_frame)
        self._create_action_bar(pane)

        return pane

    def _create_records_tree(self):
        self.records_tree_frame = ttk.Frame(self.content_frame)
        self.records_tree_frame.grid_rowconfigure(0, weight=1)
        self.records_tree_frame.grid_columnconfigure(0, weight=1)

        self.records_tree = ttk.Treeview(self.records_tree_frame, columns=self.tree_column_ids, show='tree headings', selectmode='browse')

        # Configure Columns
        self.records_tree.heading('#0', text='')
        self.records_tree.column('#0', width=30, stretch=False, anchor=tk.W) # Expander icon column

        for cid, ctext in self.tree_columns.items():
            w = 180 if cid == 'discipline' else (300 if cid == 'name' else 110)
            a = tk.W if cid not in ['performance', 'date'] else tk.CENTER
            self.records_tree.heading(cid, text=ctext)
            self.records_tree.column(cid, width=w, anchor=a, minwidth=80)

        # Scrollbars
        vsb = ttk.Scrollbar(self.records_tree_frame, orient="vertical", command=self.records_tree.yview)
        hsb = ttk.Scrollbar(self.records_tree_frame, orient="horizontal", command=self.records_tree.xview)
        self.records_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.records_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        # Formatting Tags
        self.records_tree.tag_configure("member", foreground="#666666")
        self.records_tree.tag_configure("parent", font=("Segoe UI", 9, "bold"))

        # Bindings
        self.records_tree.bind("<<TreeviewSelect>>", lambda e: self._update_button_states())
        self.records_tree.bind("<Double-1>", self._on_tree_double_click)
        # Drag and Drop
        self.records_tree.bind("<ButtonPress-1>", self._dnd_start_drag)
        self.records_tree.bind("<B1-Motion>", self._dnd_drag_motion)
        self.records_tree.bind("<ButtonRelease-1>", self._dnd_drop)

    def _create_messages_box(self, parent):
        frame = ttk.LabelFrame(parent, text="Extra Berichten", padding=5)
        frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        self.messages_text = tk.Text(frame, height=4, width=40, wrap=tk.WORD, undo=True, font=("Segoe UI", 9))
        self.messages_text.grid(row=0, column=0, sticky='nsew')

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.messages_text.yview)
        vsb.grid(row=0, column=1, sticky='ns')
        self.messages_text.configure(yscrollcommand=vsb.set)

        self.messages_text.bind("<<Modified>>", self._on_messages_modified)

    def _create_contact_box(self, parent):
        frame = ttk.LabelFrame(parent, text="Contact Info (Footer)", padding=5)
        frame.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Tekst:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.contact_prefix_entry = ttk.Entry(frame, textvariable=self.current_contact_prefix_var)
        self.contact_prefix_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        self.current_contact_prefix_var.trace_add("write", self._mark_dirty)

        ttk.Label(frame, text="Email:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.contact_email_entry = ttk.Entry(frame, textvariable=self.current_contact_email_var)
        self.contact_email_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        self.current_contact_email_var.trace_add("write", self._mark_dirty)

    def _create_action_bar(self, parent):
        bar = ttk.Frame(parent)
        bar.grid(row=3, column=0, sticky='ew', pady=(10, 0))
        bar.columnconfigure(0, weight=1)

        # Left: Edit actions
        actions_f = ttk.Frame(bar)
        actions_f.grid(row=0, column=0, sticky='w')

        self.records_add_button = ttk.Button(actions_f, text="Toevoegen", command=self._records_add)
        self.records_add_button.pack(side=tk.LEFT, padx=(0, 5))

        self.records_add_relay_button = ttk.Button(actions_f, text="Nieuwe Estafette", command=self._records_add_relay)
        self.records_add_relay_button.pack(side=tk.LEFT, padx=5)

        self.records_edit_button = ttk.Button(actions_f, text="Bewerken", command=self._records_edit)
        self.records_edit_button.pack(side=tk.LEFT, padx=5)

        self.records_delete_button = ttk.Button(actions_f, text="Verwijderen", command=self._records_delete)
        self.records_delete_button.pack(side=tk.LEFT, padx=5)

        # Right: Save
        self.records_save_button = ttk.Button(bar, text="Wijzigingen Opslaan", command=self._records_save)
        self.records_save_button.grid(row=0, column=1, sticky='e')

    # --- UI Logic ---

    def _show_placeholder(self):
        self.records_tree_frame.grid_forget()
        self.placeholder_label.grid(row=0, column=0, sticky='nsew')
        self.title_var.set("Selecteer een record type")
        self.records_current_file_path = None
        self.records_current_type_name = ""
        self.records_current_data = []
        self._data_dirty = False
        self._clear_ui_data()
        self._update_button_states()

    def _show_content(self):
        self.placeholder_label.grid_forget()
        self.records_tree_frame.grid(row=0, column=0, sticky='nsew')

    def _update_button_states(self):
        nav_sel = self.nav_tree.selection()
        is_type_selected = nav_sel and self.nav_tree.parent(nav_sel[0]) != ''
        self.delete_type_button.config(state=tk.NORMAL if is_type_selected and BS4_AVAILABLE else tk.DISABLED)

        is_loaded = bool(self.records_current_file_path)
        has_rec_sel = bool(self.records_tree.selection())

        self.records_add_button.config(state=tk.NORMAL if is_loaded else tk.DISABLED)
        self.records_add_relay_button.config(state=tk.NORMAL if is_loaded else tk.DISABLED)
        self.records_edit_button.config(state=tk.NORMAL if is_loaded and has_rec_sel else tk.DISABLED)
        self.records_delete_button.config(state=tk.NORMAL if is_loaded and has_rec_sel else tk.DISABLED)
        self.records_save_button.config(state=tk.NORMAL if is_loaded and self._data_dirty else tk.DISABLED)

        widget_state = tk.NORMAL if is_loaded else tk.DISABLED
        self.messages_text.config(state=widget_state)
        self.contact_prefix_entry.config(state=widget_state)
        self.contact_email_entry.config(state=widget_state)

    def _mark_dirty(self, *args):
        if self.records_current_file_path and not self._loading_data and not self._data_dirty:
            self._data_dirty = True
            self._update_button_states()
            if not self.title_var.get().endswith("*"):
                self.title_var.set(self.title_var.get() + "*")

    def _on_messages_modified(self, event=None):
        if self.messages_text.edit_modified():
            self.messages_text.edit_modified(False)
            self._mark_dirty()

    # --- Data Loading / Navigation ---

    def has_unsaved_changes(self):
        return self._data_dirty

    def _records_discover_and_populate_categories(self, select_path=None):
        # Rebuilding navigation must keep the loaded page and any unsaved edits.
        if select_path and select_path != self.records_current_file_path and self._data_dirty:
            if messagebox.askyesno("Niet Opgeslagen", "Er zijn wijzigingen. Doorgaan zonder opslaan?", icon='warning'):
                self._data_dirty = False
            else:
                select_path = self.records_current_file_path
        select_path = select_path or self.records_current_file_path
        self.nav_tree.delete(*self.nav_tree.get_children())
        self.nav_tree_map.clear()

        self.records_structure = utils.records_discover_files(config.RECORDS_BASE_DIR_ABSOLUTE)

        item_to_select = None
        for category in self.records_structure.keys():
            cat_iid = self.nav_tree.insert('', 'end', text=category, open=True)
            for type_name, path in self.records_structure[category].items():
                type_iid = self.nav_tree.insert(cat_iid, 'end', text=type_name)
                self.nav_tree_map[type_iid] = {'path': path, 'type': type_name, 'category': category}

                if path == select_path:
                    item_to_select = type_iid

        if item_to_select:
            self.nav_tree.selection_set(item_to_select)
            self.nav_tree.focus(item_to_select)
            self.nav_tree.see(item_to_select)
            if not self._data_dirty or getattr(self.app, '_discarding_changes', False):
                self._records_load(select_path, self.nav_tree_map[item_to_select]['type'])

    def _on_nav_tree_select(self, event=None):
        selection = self.nav_tree.selection()
        selected_data = self.nav_tree_map.get(selection[0]) if selection else None
        if selected_data and selected_data['path'] == self.records_current_file_path:
            self._update_button_states()
            return

        if self._data_dirty:
            if not messagebox.askyesno("Niet Opgeslagen", "Er zijn wijzigingen. Doorgaan zonder opslaan?", icon='warning'):
                for iid, data in self.nav_tree_map.items():
                    if data['path'] == self.records_current_file_path:
                        self.nav_tree.selection_set(iid)
                        self.nav_tree.focus(iid)
                        break
                return
        if selected_data:
            self._records_load(selected_data['path'], selected_data['type'])
        else:
            self._show_placeholder()

    def _records_load(self, file_path, type_name):
        self.app.set_status(f"Laden van {os.path.basename(file_path)}...")

        parsed = utils.records_parse_html(file_path)
        if parsed is not None:
            self._loading_data = True
            self.records_current_file_path = file_path
            self.records_current_type_name = type_name
            self._update_button_states()
            self._clear_ui_data()
            self.records_current_data = [_record_to_dict(record) for record in parsed.get("records", []) or []]

            # Metadata
            self.current_contact_prefix_var.set(parsed.get("prefix", ""))
            self.current_contact_email_var.set(parsed.get("email", ""))

            messages = parsed.get("general_messages", [])
            self.messages_text.insert("1.0", "\n".join(messages))
            self.messages_text.edit_modified(False)

            self._populate_treeview()
            self.title_var.set(f"Records: {type_name}")
            self.app.set_status(f"{len(self.records_current_data)} records geladen.")
            self._data_dirty = False
            self._loading_data = False
            self._show_content()
        else:
            messagebox.showerror("Laad Fout", f"Kon '{os.path.basename(file_path)}' niet lezen.")
            self._show_placeholder()

        self._update_button_states()

    def _clear_ui_data(self):
        self.records_tree.delete(*self.records_tree.get_children())
        self.current_contact_prefix_var.set("")
        self.current_contact_email_var.set("")
        self.messages_text.delete("1.0", tk.END)

    def _populate_treeview(self):
        self.records_tree.delete(*self.records_tree.get_children())
        for i, rec in enumerate(self.records_current_data):
            self._insert_record_row(i, rec)
        self._update_button_states()

    def _insert_record_row(self, idx, rec):
        names = rec.get("names", [])
        display_names = [n for n in names if n and n.strip()]

        # Display Logic:
        # If multiple names, show first name in parent row or generic text, then children.
        # If single name, show in parent row.

        if not display_names:
            main_name = ""
        elif len(display_names) == 1:
            main_name = display_names[0]
        else:
            main_name = f"{display_names[0]} (+{len(display_names)-1})"

        iid = f"p{idx}"
        self.records_tree.insert('', tk.END, iid=iid, text="", values=(
            rec.get("discipline", ""),
            main_name if len(display_names) <= 1 else f"[{len(display_names)} atleten] - zie detail",
            rec.get("performance", ""),
            rec.get("place", ""),
            rec.get("date", ""),
        ), tags=("parent",))

        if len(display_names) > 1:
            for j, n in enumerate(display_names):
                self.records_tree.insert(iid, tk.END, iid=f"{iid}m{j}", text="", values=(
                    "", f"↳ {n}", "", "", ""
                ), tags=("member",))
            # Keep relays open by default? No, cleaner closed.
            # self.records_tree.item(iid, open=True)

    # --- CRUD Operations ---

    def _records_add(self):
        RecordDialog(self.app.root, "Nieuw Record", None, self._process_new_record)

    def _records_add_relay(self):
        RelayDialog(self.app.root, "Nieuw Relay", {"names": ["", "", "", ""]}, self._process_new_record)

    def _records_edit(self):
        sel = self.records_tree.selection()
        if not sel: return

        iid = sel[0]
        # If child selected, find parent index
        if "m" in iid:
            iid = iid.split("m")[0]

        idx = int(iid[1:]) # remove 'p'
        rec = self.records_current_data[idx]

        def save_callback(data):
            self._process_edited_record(idx, data)

        # Open appropriate dialog
        if len([n for n in rec.get("names", []) if n.strip()]) > 1:
            RelayDialog(self.app.root, "Estafette Bewerken", rec, save_callback)
        else:
            RecordDialog(self.app.root, "Record Bewerken", rec, save_callback)

    def _process_new_record(self, new_rec):
        if not new_rec: return
        new_rec = _record_to_dict(new_rec)

        if not new_rec.get("names"): new_rec["names"] = [""]

        self.records_current_data.append(new_rec)
        self._populate_treeview()
        self._mark_dirty()
        # Scroll to bottom
        last_id = f"p{len(self.records_current_data)-1}"
        self.records_tree.see(last_id)
        self.records_tree.selection_set(last_id)

    def _process_edited_record(self, idx, updated_rec):
        if not updated_rec: return
        updated_rec = _record_to_dict(updated_rec)
        if not updated_rec.get("names"): updated_rec["names"] = [""]
        self.records_current_data[idx] = updated_rec
        self._populate_treeview()
        self._mark_dirty()
        # Reselect
        self.records_tree.selection_set(f"p{idx}")

    def _records_delete(self):
        sel = self.records_tree.selection()
        if not sel: return

        iid = sel[0]
        if "m" in iid: iid = iid.split("m")[0]
        idx = int(iid[1:])

        rec = self.records_current_data[idx]
        details = f"{rec.get('discipline','')} | {_join_names(rec.get('names',[]))}"

        if messagebox.askyesno("Verwijderen", f"Record verwijderen?\n\n'{details}'"):
            del self.records_current_data[idx]
            self._populate_treeview()
            self._mark_dirty()

    def _on_tree_double_click(self, event):
        region = self.records_tree.identify_region(event.x, event.y)
        if region == "cell":
            self._records_edit()

    def _records_save(self):
        if not self.records_current_file_path: return

        prefix = self.current_contact_prefix_var.get()
        email = self.current_contact_email_var.get()
        messages = self.messages_text.get("1.0", tk.END).strip().splitlines()

        title = self.records_current_type_name

        self.app.set_status("Opslaan...")

        # Keep record boundaries and names as data; the utility creates real BR tags.
        rows = [_record_to_dict(rec) for rec in self.records_current_data]

        try:
            success, err = utils.records_save_html(self.records_current_file_path, rows, prefix, email, messages, title)
            if success:
                self.app.set_status("Succesvol opgeslagen.", duration_ms=5000)
                self._data_dirty = False
                self.title_var.set(f"Records: {title}")
                self._update_button_states()
            else:
                self.app.set_status("Fout bij opslaan.", is_error=True)
                messagebox.showerror("Opslag Fout", f"Fout bij opslaan:\n{err}")
        except Exception as e:
            traceback.print_exc()
            self.app.set_status("Critical Error Save", is_error=True)
            messagebox.showerror("Critical Error", str(e))

    # --- Type Management ---

    def _add_new_type(self):
        cats = list(self.records_structure.keys())
        if not cats:
            messagebox.showerror("Fout", "Geen categorie mappen gevonden.")
            return
        AddNewTypeDialog(self.app.root, "Nieuw Record Type", cats, self._process_new_type)

    def _process_new_type(self, result):
        if not result: return
        cat_folder, type_name = result

        new_fpath = os.path.join(config.RECORDS_BASE_DIR_ABSOLUTE, cat_folder, f"{type_name}.html")

        if os.path.exists(new_fpath):
            messagebox.showerror("Fout", f"Bestand '{os.path.basename(new_fpath)}' bestaat al.")
            return

        try:
            html_content = NEW_RECORD_HTML_TEMPLATE_FOR_TAB.format(
                record_type_title=html.escape(type_name),
                record_contact_prefix_text=html.escape(DEFAULT_NEW_RECORD_CONTACT_PREFIX),
                record_contact_email=html.escape(DEFAULT_NEW_RECORD_CONTACT_EMAIL)
            )

            with utils.atomic_text_writer(new_fpath) as f:
                f.write(html_content)

            utils.records_header_append_type(config.RECORDS_BASE_DIR_ABSOLUTE, cat_folder, type_name)

            self.app.set_status(f"Type '{type_name}' aangemaakt.", duration_ms=4000)
            self._records_discover_and_populate_categories(select_path=new_fpath)

        except Exception as e:
            messagebox.showerror("Fout bij Aanmaken", f"Kon bestand niet aanmaken:\n{e}")

    def _delete_selected_type(self):
        selection = self.nav_tree.selection()
        if not selection or self.nav_tree.parent(selection[0]) == '':
            return

        selected_data = self.nav_tree_map.get(selection[0])
        if not selected_data: return

        type_name = selected_data['type']
        fpath = selected_data['path']
        category = selected_data['category']

        if not messagebox.askyesno("Verwijderen", f"Weet u zeker dat u '{type_name}' permanent wilt verwijderen?\nDit kan niet ongedaan gemaakt worden.", icon='warning'):
            return

        try:
            if os.path.exists(fpath):
                os.remove(fpath)

            utils.records_header_remove_type(config.RECORDS_BASE_DIR_ABSOLUTE, category, type_name)

            self.app.set_status(f"Type '{type_name}' verwijderd.", duration_ms=4000)

            if self.records_current_file_path == fpath:
                self._show_placeholder()

            self._records_discover_and_populate_categories()

        except OSError as e:
            messagebox.showerror("Fout bij Verwijderen", f"Kon bestand niet verwijderen:\n{e}")

    # --- Treeview Drag and Drop ---

    def _dnd_start_drag(self, event):
        region = self.records_tree.identify_region(event.x, event.y)
        if region not in ("cell", "tree"): return

        iid = self.records_tree.identify_row(event.y)
        # Prevent dragging children separately
        if not iid or "m" in iid: return

        self._drag_data = {"item": iid, "y": event.y}

    def _dnd_drag_motion(self, event):
        item = self._drag_data.get("item")
        if not item: return

        target_iid = self.records_tree.identify_row(event.y)
        if not target_iid or "m" in target_iid: return

        if target_iid != item:
            try:
                # Visual feedback only - actual data move happens on drop
                self.records_tree.move(item, '', self.records_tree.index(target_iid))
            except tk.TclError:
                pass

    def _dnd_drop(self, event):
        item = self._drag_data.get("item")
        if not item: return

        self._drag_data["item"] = None # Reset

        # Get new visual order from Treeview
        new_visual_iids = self.records_tree.get_children('')
        if not new_visual_iids: return

        try:
            # iids are like 'p0', 'p1'. Extract int index.
            idxs = [int(iid[1:]) for iid in new_visual_iids if iid.startswith('p')]

            # Reorder internal list based on new visual order
            reordered = [self.records_current_data[i] for i in idxs]

            if reordered != self.records_current_data:
                self.records_current_data = reordered
                self._mark_dirty()
                self.app.set_status("Volgorde van records gewijzigd.", duration_ms=3000)
                # Full repaint to ensure indices match iids again
                self._populate_treeview()

        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Fout bij Verplaatsen", f"Fout bij wijzigen volgorde:\n{e}")
            self._populate_treeview() # Restore

    # --- Navigation Tree Drag and Drop ---

    def _nav_dnd_start(self, event):
        iid = self.nav_tree.identify_row(event.y)
        if not iid: return

        parent = self.nav_tree.parent(iid)
        # Only allow dragging files (items with a parent), not categories
        if parent == '':
            self._nav_drag = {"item": None, "parent": None}
            return

        self._nav_drag = {"item": iid, "parent": parent, "moved": False}

    def _nav_dnd_motion(self, event):
        d = self._nav_drag
        if not d.get("item"): return

        over = self.nav_tree.identify_row(event.y)
        # Ensure dragging within same category
        if not over or self.nav_tree.parent(over) != d["parent"]:
            return

        if over != d["item"]:
            try:
                self.nav_tree.move(d["item"], d["parent"], self.nav_tree.index(over))
                d["moved"] = True
            except tk.TclError:
                pass

    def _nav_dnd_drop(self, event):
        d = self._nav_drag
        item = d.get("item")

        # Reset immediately
        self._nav_drag = {"item": None, "parent": None, "moved": False}

        if not item or not d.get("moved"): return

        parent = d["parent"]
        cat_name = self.nav_tree.item(parent, 'text')

        # Determine new order
        children = self.nav_tree.get_children(parent)
        order = [self.nav_tree.item(i, 'text') for i in children]

        if cat_name in self.records_structure:
            # Sync internal structure
            old_map = self.records_structure[cat_name]
            new_map = {}
            for t in order:
                if t in old_map: new_map[t] = old_map[t]
            # Safety for missing items
            for t, p in old_map.items():
                if t not in new_map: new_map[t] = p

            self.records_structure[cat_name] = new_map

            try:
                utils.records_header_set_order(config.RECORDS_BASE_DIR_ABSOLUTE, {cat_name: order})
                self.app.set_status("Volgorde van tabs bijgewerkt.", duration_ms=3000)
            except Exception as e:
                messagebox.showerror("Fout", f"Kon volgorde niet opslaan in header:\n{e}")

        # Restore focus
        self.nav_tree.selection_set(item)
        self.nav_tree.focus(item)

def create_records_tab(parent_frame, app_instance):
    return RecordsTab(parent_frame, app_instance)

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import os
import pathlib
import shutil
import config
import utils

class DocumentsTab:
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance
        self.reports_data = {}
        self.reports_loaded = False
        self._rep_sort_col = 'year'
        self._rep_sort_reverse = True
        self.downloads = []
        self.downloads_loaded = False
        self._dl_sort_col = 'text'
        self._dl_sort_reverse = False
        self._create_widgets()
        self._rep_load()
        self._dl_load()

    def has_unsaved_changes(self):
        return (utils.editor_state_changed(self, self.reports_data, '_saved_reports') or
                utils.editor_state_changed(self, self.downloads, '_saved_downloads'))

    def _create_widgets(self):
        self.parent.grid_rowconfigure(1, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        rep_frame = ttk.LabelFrame(self.parent, text="Verslagen")
        rep_frame.grid(row=0, column=0, sticky='nsew', padx=6, pady=(6,3))
        rep_top = ttk.Frame(rep_frame)
        rep_top.grid(row=0, column=0, sticky='ew', pady=(6,6))
        rep_mid = ttk.Frame(rep_frame)
        rep_mid.grid(row=1, column=0, sticky='nsew')
        rep_bot = ttk.Frame(rep_frame)
        rep_bot.grid(row=2, column=0, sticky='ew', pady=(6,6))
        rep_frame.grid_rowconfigure(1, weight=1)
        rep_frame.grid_columnconfigure(0, weight=1)

        self.rep_refresh = ttk.Button(rep_top, text="Vernieuw Verslagen", command=self._rep_load)
        self.rep_refresh.grid(row=0, column=0, rowspan=4, padx=5, pady=5, sticky=tk.W+tk.N)
        ttk.Separator(rep_top, orient=tk.VERTICAL).grid(row=0, column=1, rowspan=4, sticky="ns", padx=15, pady=5)
        ttk.Label(rep_top, text="Jaar:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.rep_year_var = tk.StringVar()
        self.rep_year_combo = ttk.Combobox(rep_top, textvariable=self.rep_year_var, width=12, state=tk.DISABLED)
        self.rep_year_combo.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        self.rep_year_combo.bind("<<ComboboxSelected>>", self._rep_toggle_new_year)
        self.rep_new_year = ttk.Entry(rep_top, width=8, state=tk.DISABLED)
        self.rep_new_year.grid(row=0, column=4, sticky=tk.W, padx=5, pady=2)
        self.rep_new_year.insert(0, "JJJJ")
        self.rep_new_year.bind("<FocusIn>", lambda e: self.rep_new_year.delete(0, tk.END) if self.rep_new_year.get() == "JJJJ" else None)
        self.rep_new_year.bind("<FocusOut>", lambda e: self.rep_new_year.insert(0, "JJJJ") if not self.rep_new_year.get() else None)
        ttk.Label(rep_top, text="Link tekst:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.rep_link_text = ttk.Entry(rep_top, width=45, state=tk.DISABLED)
        self.rep_link_text.grid(row=1, column=3, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=2)
        self.rep_upload = ttk.Button(rep_top, text="Blader Document & Voeg Link Toe", command=self._rep_browse_upload, state=tk.DISABLED)
        self.rep_upload.grid(row=2, column=3, columnspan=2, sticky=tk.W, padx=5, pady=5)
        rep_top.columnconfigure(3, weight=1)

        rep_cols = ('year', 'text', 'filename')
        self.rep_tree = ttk.Treeview(rep_mid, columns=rep_cols, show='headings', selectmode='browse')
        self.rep_tree.heading('year', text='Jaar', anchor=tk.W, command=lambda: self._rep_sort('year'))
        self.rep_tree.column('year', width=80, anchor=tk.W, stretch=tk.NO)
        self.rep_tree.heading('text', text='Link Tekst', anchor=tk.W, command=lambda: self._rep_sort('text'))
        self.rep_tree.column('text', width=420, minwidth=260, anchor=tk.W)
        self.rep_tree.heading('filename', text='Bestandsnaam (in docs map)', anchor=tk.W, command=lambda: self._rep_sort('filename'))
        self.rep_tree.column('filename', width=360, minwidth=220, anchor=tk.W)
        rep_vsb = ttk.Scrollbar(rep_mid, orient="vertical", command=self.rep_tree.yview)
        rep_hsb = ttk.Scrollbar(rep_mid, orient="horizontal", command=self.rep_tree.xview)
        self.rep_tree.configure(yscrollcommand=rep_vsb.set, xscrollcommand=rep_hsb.set)
        rep_mid.grid_rowconfigure(0, weight=1)
        rep_mid.grid_columnconfigure(0, weight=1)
        self.rep_tree.grid(row=0, column=0, sticky='nsew')
        rep_vsb.grid(row=0, column=1, sticky='ns')
        rep_hsb.grid(row=1, column=0, sticky='ew')
        self.rep_tree.bind("<<TreeviewSelect>>", self._rep_on_select)

        rep_left = ttk.Frame(rep_bot)
        rep_left.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.rep_delete = ttk.Button(rep_left, text="Verwijder Geselecteerde Link", command=self._rep_delete, state=tk.DISABLED)
        self.rep_delete.pack(side=tk.LEFT, padx=(0,5))
        self.rep_save = ttk.Button(rep_left, text="Wijzigingen Opslaan naar HTML", command=self._rep_save, state=tk.DISABLED)
        self.rep_save.pack(side=tk.RIGHT, padx=(5,0))

        rep_right = ttk.Frame(rep_bot)
        rep_right.pack(side=tk.RIGHT, fill=tk.X, expand=False, padx=5)
        self.rep_update_text_btn = ttk.Button(rep_right, text="Update Tekst", command=self._rep_update_text, state=tk.DISABLED)
        self.rep_update_text_btn.pack(side=tk.LEFT, padx=5)

        dl_frame = ttk.LabelFrame(self.parent, text="Downloads")
        dl_frame.grid(row=1, column=0, sticky='nsew', padx=6, pady=(3,6))
        dl_top = ttk.Frame(dl_frame)
        dl_top.grid(row=0, column=0, sticky='ew', pady=(6,6))
        dl_mid = ttk.Frame(dl_frame)
        dl_mid.grid(row=1, column=0, sticky='nsew')
        dl_bot = ttk.Frame(dl_frame)
        dl_bot.grid(row=2, column=0, sticky='ew', pady=(6,6))
        dl_frame.grid_rowconfigure(1, weight=1)
        dl_frame.grid_columnconfigure(0, weight=1)

        self.dl_refresh = ttk.Button(dl_top, text="Vernieuw Downloads", command=self._dl_load)
        self.dl_refresh.grid(row=0, column=0, rowspan=3, padx=5, pady=5, sticky=tk.W+tk.N)
        ttk.Separator(dl_top, orient=tk.VERTICAL).grid(row=0, column=1, rowspan=3, sticky="ns", padx=15, pady=5)
        ttk.Label(dl_top, text="Link tekst:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.dl_text = ttk.Entry(dl_top, width=45, state=tk.DISABLED)
        self.dl_text.grid(row=0, column=3, sticky=tk.W+tk.E, padx=5, pady=2)
        self.dl_add = ttk.Button(dl_top, text="Blader & Voeg Toe", command=self._dl_browse_add, state=tk.DISABLED)
        self.dl_add.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        dl_top.columnconfigure(3, weight=1)

        dl_cols = ('text', 'filename')
        self.dl_tree = ttk.Treeview(dl_mid, columns=dl_cols, show='headings', selectmode='browse')
        self.dl_tree.heading('text', text='Link Tekst', anchor=tk.W, command=lambda: self._dl_sort('text'))
        self.dl_tree.column('text', width=420, minwidth=260, anchor=tk.W)
        self.dl_tree.heading('filename', text='Bestandsnaam', anchor=tk.W, command=lambda: self._dl_sort('filename'))
        self.dl_tree.column('filename', width=360, minwidth=220, anchor=tk.W)
        dl_vsb = ttk.Scrollbar(dl_mid, orient="vertical", command=self.dl_tree.yview)
        dl_hsb = ttk.Scrollbar(dl_mid, orient="horizontal", command=self.dl_tree.xview)
        self.dl_tree.configure(yscrollcommand=dl_vsb.set, xscrollcommand=dl_hsb.set)
        dl_mid.grid_rowconfigure(0, weight=1)
        dl_mid.grid_columnconfigure(0, weight=1)
        self.dl_tree.grid(row=0, column=0, sticky='nsew')
        dl_vsb.grid(row=0, column=1, sticky='ns')
        dl_hsb.grid(row=1, column=0, sticky='ew')
        self.dl_tree.bind("<<TreeviewSelect>>", self._dl_on_select)

        dl_left = ttk.Frame(dl_bot)
        dl_left.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.dl_delete = ttk.Button(dl_left, text="Verwijder", command=self._dl_delete, state=tk.DISABLED)
        self.dl_delete.pack(side=tk.LEFT, padx=(0,5))
        self.dl_save = ttk.Button(dl_left, text="Opslaan naar HTML", command=self._dl_save, state=tk.DISABLED)
        self.dl_save.pack(side=tk.RIGHT, padx=(5,0))
        dl_right = ttk.Frame(dl_bot)
        dl_right.pack(side=tk.RIGHT, fill=tk.X, expand=False, padx=5)
        self.dl_update_text = ttk.Button(dl_right, text="Update Tekst", command=self._dl_update_text, state=tk.DISABLED)
        self.dl_update_text.pack(side=tk.LEFT, padx=5)
        self.dl_replace = ttk.Button(dl_right, text="Vervang Bestand", command=self._dl_replace_file, state=tk.DISABLED)
        self.dl_replace.pack(side=tk.LEFT, padx=5)

    def _rep_update_states(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.rep_save.config(state=state)
        self.rep_upload.config(state=state)
        self.rep_year_combo.config(state="readonly" if enabled else tk.DISABLED)
        self.rep_link_text.config(state=state)
        self.rep_delete.config(state=tk.DISABLED)
        self.rep_update_text_btn.config(state=tk.DISABLED)
        self._rep_toggle_new_year()

    def _rep_on_select(self, event=None):
        has = self.reports_loaded and bool(self.rep_tree.selection())
        self.rep_delete.config(state=tk.NORMAL if has else tk.DISABLED)
        self.rep_update_text_btn.config(state=tk.NORMAL if has else tk.DISABLED)
        if has:
            iid = self.rep_tree.selection()[0]
            year, idx_str = iid.split('-', 1)
            idx = int(idx_str)
            if year in self.reports_data and 0 <= idx < len(self.reports_data[year]):
                self.rep_year_var.set(year)
                self.rep_link_text.delete(0, tk.END)
                self.rep_link_text.insert(0, self.reports_data[year][idx]['text'])

    def _rep_update_year_dropdown(self):
        if not self.reports_loaded:
            self.rep_year_combo['values'] = []
            self.rep_year_var.set("")
            return
        years = sorted([y for y in self.reports_data.keys() if y.isdigit()], key=int, reverse=True)
        current_year = str(datetime.date.today().year)
        new_opt = "<Nieuw Jaar>"
        options = [new_opt]
        if current_year not in years:
            options.append(current_year)
        options.extend(years)
        unique = []
        for o in options:
            if o not in unique:
                unique.append(o)
        self.rep_year_combo['values'] = unique
        sel = self.rep_year_var.get()
        if sel not in unique:
            if current_year in unique:
                self.rep_year_var.set(current_year)
            elif years:
                self.rep_year_var.set(years[0])
            else:
                self.rep_year_var.set(new_opt)
        self._rep_toggle_new_year()

    def _rep_toggle_new_year(self, event=None):
        is_new = self.rep_year_var.get() == "<Nieuw Jaar>"
        st = tk.NORMAL if self.reports_loaded and is_new else tk.DISABLED
        self.rep_new_year.config(state=st)
        if st == tk.NORMAL and self.rep_new_year.get() == "JJJJ":
            self.rep_new_year.delete(0, tk.END)
        elif st == tk.DISABLED and not self.rep_new_year.get():
            self.rep_new_year.insert(0, "JJJJ")

    def _rep_clear_tree(self):
        for i in self.rep_tree.get_children():
            self.rep_tree.delete(i)

    def _extract_date_from_string(self, s):
        if not s:
            return None
        s = s.lower()
        months = {
            'januari':1,'jan':1,'februari':2,'feb':2,'maart':3,'mrt':3,'march':3,
            'april':4,'apr':4,'mei':5,'may':5,'juni':6,'jun':6,'july':7,'juli':7,'jul':7,
            'augustus':8,'aug':8,'september':9,'sep':9,'sept':9,
            'oktober':10,'okt':10,'october':10,'oct':10,
            'november':11,'nov':11,'december':12,'dec':12
        }
        import re
        m = re.search(r'(\d{4})[._/\-](\d{1,2})[._/\-](\d{1,2})', s)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try: return datetime.date(y, mo, d)
            except: pass
        m = re.search(r'(\d{1,2})[._/\-](\d{1,2})[._/\-](\d{4})', s)
        if m:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try: return datetime.date(y, mo, d)
            except: pass
        m = re.search(r'(\d{1,2})\s+([a-zäëïöüé]+)\s+(\d{4})', s)
        if m:
            d, mon, y = int(m.group(1)), m.group(2), int(m.group(3))
            mo = months.get(mon, 0)
            if mo:
                try: return datetime.date(y, mo, d)
                except: pass
        m = re.search(r'\b(20\d{2})(\d{2})(\d{2})\b', s)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try: return datetime.date(y, mo, d)
            except: pass
        return None

    def _rep_item_date(self, year, item):
        y = int(year) if str(year).isdigit() else datetime.date.today().year
        t = item.get('text', '')
        f = item.get('filename', '')
        d = self._extract_date_from_string(t) or self._extract_date_from_string(f)
        if d:
            return d
        return datetime.date(y, 1, 1)

    def _rep_sort_reports_by_date(self):
        for year, lst in self.reports_data.items():
            lst.sort(key=lambda it: self._rep_item_date(year, it), reverse=True)

    def _rep_populate(self):
        self._rep_clear_tree()
        flat = []
        for year, lst in self.reports_data.items():
            for idx, r in enumerate(lst):
                flat.append({'year': year, 'text': r['text'], 'filename': r['filename'], 'path': r['path'], 'original_index': idx})
        def key_func(item):
            v = item.get(self._rep_sort_col, "")
            if self._rep_sort_col == 'year' and isinstance(v, str) and v.isdigit():
                return int(v)
            return v.lower() if isinstance(v, str) else v
        flat.sort(key=key_func, reverse=self._rep_sort_reverse)
        for it in flat:
            iid = f"{it['year']}-{it['original_index']}"
            self.rep_tree.insert('', tk.END, iid=iid, values=(it['year'], it['text'], it['filename']))

    def _rep_sort(self, col):
        if col == self._rep_sort_col:
            self._rep_sort_reverse = not self._rep_sort_reverse
        else:
            self._rep_sort_col = col
            self._rep_sort_reverse = (col == 'year')
        self._rep_populate()

    def _rep_load(self):
        if not utils.confirm_discard_changes(self, utils.editor_state_changed(self, self.reports_data, '_saved_reports')):
            return
        if not os.path.exists(config.REPORTS_HTML_FILE_PATH):
            messagebox.showerror("Bestand Niet Gevonden", f"Verslagen HTML niet gevonden:\n{config.REPORTS_HTML_FILE_PATH}", parent=self.app.root)
            self.app.set_status("Fout: Verslagen HTML niet gevonden.", is_error=True)
            self._rep_update_states(False)
            self.reports_loaded = False
            return
        self.app.set_status("Laden/Vernieuwen verslagen...")
        self.app.root.update_idletasks()
        self._rep_clear_tree()
        self.reports_loaded = False
        data, err = utils.reports_parse_html(config.REPORTS_HTML_FILE_PATH)
        if err is None:
            self.reports_data = data or {}
            self._rep_sort_reports_by_date()
            self.reports_loaded = True
            self._rep_sort_col = 'year'
            self._rep_sort_reverse = True
            self._rep_populate()
            self._rep_update_states(True)
            self._rep_update_year_dropdown()
            cnt = sum(len(v) for v in self.reports_data.values())
            self.app.set_status(f"{cnt} verslag links geladen.", duration_ms=5000)
            utils.remember_editor_state(self, self.reports_data, '_saved_reports')
        else:
            self._rep_populate()
            self._rep_update_states(False)
            self.app.set_status(f"Fout bij laden verslagen: {err}", is_error=True)
            messagebox.showerror("Laad Fout", f"Kon verslagen niet parsen:\n{err}", parent=self.app.root)
        return self.reports_loaded

    def _rep_browse_upload(self):
        if not self.reports_loaded:
            messagebox.showwarning("Laden Vereist", "Laad a.u.b. verslagen.", parent=self.app.root)
            self.app.set_status("Fout: Laad eerst verslagen.", is_error=True)
            return
        sel_year = self.rep_year_var.get()
        target_year = None
        if sel_year == "<Nieuw Jaar>":
            y = self.rep_new_year.get().strip()
            if not y.isdigit() or len(y) != 4:
                messagebox.showerror("Ongeldige Invoer", "Voer geldig jaar in.", parent=self.app.root)
                self.rep_new_year.focus()
                return
            target_year = y
        elif sel_year and sel_year.isdigit():
            target_year = sel_year
        else:
            messagebox.showerror("Ongeldige Invoer", "Selecteer een jaar.", parent=self.app.root)
            self.rep_year_combo.focus()
            return
        text = self.rep_link_text.get().strip()
        if not text:
            messagebox.showerror("Ongeldige Invoer", "Voer link tekst in.", parent=self.app.root)
            self.rep_link_text.focus()
            return
        ftypes = (("Document Bestanden", "*.pdf *.doc *.docx *.odt *.xls *.xlsx *.ppt *.pptx"), ("Alle bestanden", "*.*"))
        init_dir = config.REPORTS_DOCS_DEST_DIR_ABSOLUTE if os.path.isdir(config.REPORTS_DOCS_DEST_DIR_ABSOLUTE) else config.APP_BASE_DIR
        src = filedialog.askopenfilename(title="Selecteer Verslag Document", filetypes=ftypes, initialdir=init_dir)
        if not src:
            self.app.set_status("Document selectie geannuleerd.", duration_ms=3000)
            return
        filename = os.path.basename(src)
        try: os.makedirs(config.REPORTS_DOCS_DEST_DIR_ABSOLUTE, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Map Fout", f"Kon map niet aanmaken:\n{config.REPORTS_DOCS_DEST_DIR_ABSOLUTE}\nFout: {e}", parent=self.app.root)
            self.app.set_status(f"Fout bij aanmaken map: {e}", is_error=True)
            return
        dst = os.path.join(config.REPORTS_DOCS_DEST_DIR_ABSOLUTE, filename)
        href = str(pathlib.PurePosixPath(config.REPORTS_DOCS_HREF_DIR_RELATIVE) / filename)
        try:
            dst = utils.copy_new_asset(src, dst, owner=self)
            filename = os.path.basename(dst)
            href = str(pathlib.PurePosixPath(config.REPORTS_DOCS_HREF_DIR_RELATIVE) / filename)
        except Exception as e:
            messagebox.showerror("Upload Fout", f"Kon document niet kopiëren:\n{dst}\nFout: {e}", parent=self.app.root)
            self.app.set_status(f"Fout bij kopiëren: {e}", is_error=True)
            return
        if target_year not in self.reports_data:
            self.reports_data[target_year] = []
            self._rep_update_year_dropdown()
            self.rep_year_var.set(target_year)
        self.reports_data[target_year].append({'text': text, 'filename': filename, 'path': href})
        self._rep_sort_reports_by_date()
        self._rep_populate()
        self.app.set_status(f"Verslag link '{text}' toegevoegd (niet opgeslagen).", duration_ms=5000)
        self.rep_link_text.delete(0, tk.END)

    def _rep_update_text(self):
        sel = self.rep_tree.selection()
        if not sel:
            messagebox.showwarning("Selectie Vereist", "Selecteer een verslag link.", parent=self.app.root)
            return
        new_text = self.rep_link_text.get().strip()
        if not new_text:
            messagebox.showerror("Ongeldige Invoer", "Voer nieuwe link tekst in.", parent=self.app.root)
            return
        item_id = sel[0]
        try:
            year, idx_str = item_id.split('-', 1)
            idx = int(idx_str)
            if year not in self.reports_data or idx >= len(self.reports_data[year]):
                raise ValueError("Item niet gevonden.")
            self.reports_data[year][idx]['text'] = new_text
            self._rep_sort_reports_by_date()
            self._rep_populate()
            self.app.set_status("Link tekst bijgewerkt (niet opgeslagen).", duration_ms=4000)
            self.rep_link_text.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Fout", f"Kon link niet bijwerken:\n{e}", parent=self.app.root)

    def _rep_delete(self):
        sel = self.rep_tree.selection()
        if not sel:
            messagebox.showwarning("Selectie Vereist", "Selecteer een verslag link.", parent=self.app.root)
            return
        item_id = sel[0]
        try:
            year, idx_str = item_id.split('-', 1)
            idx = int(idx_str)
            if year not in self.reports_data or idx >= len(self.reports_data[year]):
                raise ValueError("Item niet gevonden.")
            r = self.reports_data[year][idx]
            if messagebox.askyesno("Bevestig Verwijderen", f"Verwijder link:\n{r['text']}?", icon='warning', parent=self.app.root):
                del self.reports_data[year][idx]
                if not self.reports_data[year]:
                    del self.reports_data[year]
                    self._rep_update_year_dropdown()
                self._rep_populate()
                self.app.set_status("Verslag link verwijderd (niet opgeslagen).", duration_ms=5000)
        except Exception as e:
            messagebox.showerror("Fout", f"Kon link niet verwijderen:\n{e}", parent=self.app.root)

    def _rep_save(self):
        if not self.reports_loaded:
            messagebox.showwarning("Eerst Laden", "Laad verslagen data.", parent=self.app.root)
            self.app.set_status("Opslaan mislukt: geen data.", is_error=True)
            return
        data = self.reports_data
        file_short = os.path.basename(config.REPORTS_HTML_FILE_PATH)
        if not data:
            if not messagebox.askyesno("Bevestig Leeg Opslaan", f"Lijst is leeg. Opslaan naar {file_short}?", icon='warning', parent=self.app.root):
                self.app.set_status("Opslaan geannuleerd.", duration_ms=4000)
                return
        self._rep_sort_reports_by_date()
        ordered = {}
        years = sorted([y for y in data.keys() if str(y).isdigit()], key=lambda y: int(y), reverse=True)
        for y in years:
            ordered[y] = list(data[y])
        self.app.set_status(f"Opslaan verslagen naar {file_short}...")
        self.app.root.update_idletasks()
        ok, err = utils.reports_save_html(config.REPORTS_HTML_FILE_PATH, ordered)
        if ok:
            self.app.set_status(f"Verslag links opgeslagen naar {file_short}.", duration_ms=5000)
            utils.remember_editor_state(self, self.reports_data, '_saved_reports')
        else:
            self.app.set_status(f"Fout bij opslaan verslagen: {err}.", is_error=True)
            messagebox.showerror("Opslag Fout", f"Kon wijzigingen niet opslaan:\n{config.REPORTS_HTML_FILE_PATH}\nFout: {err}", parent=self.app.root)

    def _dl_update_states(self, enabled):
        st = tk.NORMAL if enabled else tk.DISABLED
        self.dl_save.config(state=st)
        self.dl_add.config(state=st)
        self.dl_text.config(state=st)
        self.dl_delete.config(state=tk.DISABLED)
        self.dl_update_text.config(state=tk.DISABLED)
        self.dl_replace.config(state=tk.DISABLED)

    def _dl_on_select(self, event=None):
        has = self.downloads_loaded and bool(self.dl_tree.selection())
        self.dl_delete.config(state=tk.NORMAL if has else tk.DISABLED)
        self.dl_update_text.config(state=tk.NORMAL if has else tk.DISABLED)
        self.dl_replace.config(state=tk.NORMAL if has else tk.DISABLED)

    def _dl_clear_tree(self):
        for i in self.dl_tree.get_children():
            self.dl_tree.delete(i)

    def _dl_populate(self):
        self._dl_clear_tree()
        data = list(enumerate(self.downloads))
        key = (lambda pair: pair[1].get(self._dl_sort_col, '').lower())
        data.sort(key=key, reverse=self._dl_sort_reverse)
        for idx, item in data:
            iid = str(idx)
            self.dl_tree.insert('', tk.END, iid=iid, values=(item['text'], item['filename']))

    def _dl_sort(self, col):
        if col == self._dl_sort_col:
            self._dl_sort_reverse = not self._dl_sort_reverse
        else:
            self._dl_sort_col = col
            self._dl_sort_reverse = False
        self._dl_populate()

    def _dl_load(self):
        if not utils.confirm_discard_changes(self, utils.editor_state_changed(self, self.downloads, '_saved_downloads')):
            return
        if not os.path.exists(config.DOWNLOADS_HTML_FILE_PATH):
            messagebox.showerror("Bestand Niet Gevonden", f"Downloads HTML niet gevonden:\n{config.DOWNLOADS_HTML_FILE_PATH}", parent=self.app.root)
            self.app.set_status("Fout: Downloads HTML niet gevonden.", is_error=True)
            self._dl_update_states(False)
            self.downloads_loaded = False
            return
        self.app.set_status("Laden/Vernieuwen downloads...")
        self.app.root.update_idletasks()
        self._dl_clear_tree()
        self.downloads_loaded = False
        data, err = utils.downloads_parse_html(config.DOWNLOADS_HTML_FILE_PATH)
        if err is None:
            self.downloads = data
            self.downloads_loaded = True
            self._dl_populate()
            self._dl_update_states(True)
            self.app.set_status(f"{len(self.downloads)} downloads geladen.", duration_ms=5000)
            utils.remember_editor_state(self, self.downloads, '_saved_downloads')
        else:
            self._dl_populate()
            self._dl_update_states(False)
            self.app.set_status(f"Fout bij laden downloads: {err}", is_error=True)
            messagebox.showerror("Laad Fout", f"Kon downloads niet parsen:\n{err}", parent=self.app.root)
        return self.downloads_loaded

    def _dl_browse_add(self):
        if not self.downloads_loaded:
            messagebox.showwarning("Laden Vereist", "Laad a.u.b. downloads.", parent=self.app.root)
            self.app.set_status("Fout: Laad eerst downloads.", is_error=True)
            return
        text = self.dl_text.get().strip()
        if not text:
            messagebox.showerror("Ongeldige Invoer", "Voer link tekst in.", parent=self.app.root)
            self.dl_text.focus()
            return
        ftypes = (("Document Bestanden", "*.pdf *.doc *.docx *.odt *.xls *.xlsx *.ppt *.pptx"), ("Alle bestanden", "*.*"))
        init_dir = config.DOWNLOADS_DOCS_DEST_DIR_ABSOLUTE if os.path.isdir(config.DOWNLOADS_DOCS_DEST_DIR_ABSOLUTE) else config.APP_BASE_DIR
        src = filedialog.askopenfilename(title="Selecteer Document", filetypes=ftypes, initialdir=init_dir)
        if not src:
            self.app.set_status("Document selectie geannuleerd.", duration_ms=3000)
            return
        filename = os.path.basename(src)
        try: os.makedirs(config.DOWNLOADS_DOCS_DEST_DIR_ABSOLUTE, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Map Fout", f"Kon map niet aanmaken:\n{config.DOWNLOADS_DOCS_DEST_DIR_ABSOLUTE}\nFout: {e}", parent=self.app.root)
            self.app.set_status(f"Fout bij aanmaken map: {e}", is_error=True)
            return
        dst = os.path.join(config.DOWNLOADS_DOCS_DEST_DIR_ABSOLUTE, filename)
        href = str(pathlib.PurePosixPath(config.DOWNLOADS_DOCS_HREF_DIR_RELATIVE) / filename)
        try:
            dst = utils.copy_new_asset(src, dst, owner=self)
            filename = os.path.basename(dst)
            href = str(pathlib.PurePosixPath(config.DOWNLOADS_DOCS_HREF_DIR_RELATIVE) / filename)
        except Exception as e:
            messagebox.showerror("Upload Fout", f"Kon document niet kopiëren:\n{dst}\nFout: {e}", parent=self.app.root)
            self.app.set_status(f"Fout bij kopiëren: {e}", is_error=True)
            return
        self.downloads.append({'text': text, 'filename': filename, 'path': href})
        self._dl_populate()
        self.app.set_status(f"Download '{text}' toegevoegd (niet opgeslagen).", duration_ms=5000)
        self.dl_text.delete(0, tk.END)

    def _dl_delete(self):
        sel = self.dl_tree.selection()
        if not sel:
            messagebox.showwarning("Selectie Vereist", "Selecteer een download.", parent=self.app.root)
            return
        values = self.dl_tree.item(sel[0])['values']
        text = values[0] if values else ''
        idx = self._dl_index(values)
        if idx is None:
            messagebox.showerror("Fout", "Kon item niet vinden. Vernieuw en probeer opnieuw.", parent=self.app.root)
            return
        if messagebox.askyesno("Bevestig Verwijderen", f"Verwijder download:\n{text}?", icon='warning', parent=self.app.root):
            del self.downloads[idx]
            self._dl_populate()
            self.app.set_status("Download verwijderd (niet opgeslagen).", duration_ms=5000)

    def _dl_update_text(self):
        sel = self.dl_tree.selection()
        if not sel:
            messagebox.showwarning("Selectie Vereist", "Selecteer een download.", parent=self.app.root)
            return
        new_text = self.dl_text.get().strip()
        if not new_text:
            messagebox.showerror("Ongeldige Invoer", "Voer nieuwe link tekst in.", parent=self.app.root)
            return
        values = self.dl_tree.item(sel[0])['values']
        idx = self._dl_index(values)
        if idx is None:
            messagebox.showerror("Fout", "Kon item niet vinden. Vernieuw en probeer opnieuw.", parent=self.app.root)
            return
        self.downloads[idx]['text'] = new_text
        self._dl_populate()
        self.app.set_status("Link tekst bijgewerkt (niet opgeslagen).", duration_ms=4000)
        self.dl_text.delete(0, tk.END)

    def _dl_replace_file(self):
        sel = self.dl_tree.selection()
        if not sel:
            messagebox.showwarning("Selectie Vereist", "Selecteer een download.", parent=self.app.root)
            return
        values = self.dl_tree.item(sel[0])['values']
        idx = self._dl_index(values)
        if idx is None:
            messagebox.showerror("Fout", "Kon item niet vinden. Vernieuw en probeer opnieuw.", parent=self.app.root)
            return
        ftypes = (("Document Bestanden", "*.pdf *.doc *.docx *.odt *.xls *.xlsx *.ppt *.pptx"), ("Alle bestanden", "*.*"))
        init_dir = config.DOWNLOADS_DOCS_DEST_DIR_ABSOLUTE if os.path.isdir(config.DOWNLOADS_DOCS_DEST_DIR_ABSOLUTE) else config.APP_BASE_DIR
        src = filedialog.askopenfilename(title="Selecteer Nieuw Document", filetypes=ftypes, initialdir=init_dir)
        if not src:
            self.app.set_status("Document selectie geannuleerd.", duration_ms=3000)
            return
        filename = os.path.basename(src)
        try: os.makedirs(config.DOWNLOADS_DOCS_DEST_DIR_ABSOLUTE, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Map Fout", f"Kon map niet aanmaken:\n{config.DOWNLOADS_DOCS_DEST_DIR_ABSOLUTE}\nFout: {e}", parent=self.app.root)
            self.app.set_status(f"Fout bij aanmaken map: {e}", is_error=True)
            return
        dst = os.path.join(config.DOWNLOADS_DOCS_DEST_DIR_ABSOLUTE, filename)
        href = str(pathlib.PurePosixPath(config.DOWNLOADS_DOCS_HREF_DIR_RELATIVE) / filename)
        try:
            dst = utils.copy_new_asset(src, dst, owner=self)
            filename = os.path.basename(dst)
            href = str(pathlib.PurePosixPath(config.DOWNLOADS_DOCS_HREF_DIR_RELATIVE) / filename)
        except Exception as e:
            messagebox.showerror("Upload Fout", f"Kon document niet kopiëren:\n{dst}\nFout: {e}", parent=self.app.root)
            self.app.set_status(f"Fout bij kopiëren: {e}", is_error=True)
            return
        self.downloads[idx]['filename'] = filename
        self.downloads[idx]['path'] = href
        self._dl_populate()
        self.app.set_status("Bestand vervangen (niet opgeslagen).", duration_ms=5000)

    def _dl_index(self, values):
        selection = self.dl_tree.selection()
        if selection:
            try:
                index = int(selection[0])
                if 0 <= index < len(self.downloads):
                    return index
            except (ValueError, TypeError):
                pass
        text = values[0] if values else ''
        filename = values[1] if len(values) > 1 else ''
        for i, item in enumerate(self.downloads):
            if item['text'] == text and item['filename'] == filename:
                return i
        return None

    def _dl_save(self):
        if not self.downloads_loaded:
            messagebox.showwarning("Eerst Laden", "Laad downloads data.", parent=self.app.root)
            self.app.set_status("Opslaan mislukt: geen data.", is_error=True)
            return
        file_short = os.path.basename(config.DOWNLOADS_HTML_FILE_PATH)
        self.app.set_status(f"Opslaan downloads naar {file_short}...")
        self.app.root.update_idletasks()
        ok, err = utils.downloads_save_html(config.DOWNLOADS_HTML_FILE_PATH, self.downloads)
        if ok:
            self.app.set_status(f"Downloads opgeslagen naar {file_short}.", duration_ms=5000)
            utils.remember_editor_state(self, self.downloads, '_saved_downloads')
        else:
            self.app.set_status(f"Fout bij opslaan downloads: {err}.", is_error=True)
            messagebox.showerror("Opslag Fout", f"Kon wijzigingen niet opslaan:\n{config.DOWNLOADS_HTML_FILE_PATH}\nFout: {err}", parent=self.app.root)

def create_documents_tab(parent_frame, app_instance):
    return DocumentsTab(parent_frame, app_instance)

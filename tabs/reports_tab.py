import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import os
import shutil
import pathlib
import config
import utils

class ReportsTab:
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance
        self.reports_data = {}
        self.reports_file_loaded = False
        self._reports_sort_column = 'year'
        self._reports_sort_reverse = True
        self._create_widgets()
        self._reports_load()

    def _create_widgets(self):
        self.parent.grid_rowconfigure(1, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        rep_controls_frame = ttk.Frame(self.parent); rep_controls_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        rep_tree_frame = ttk.Frame(self.parent); rep_tree_frame.grid(row=1, column=0, sticky='nsew', pady=5)
        rep_actions_frame = ttk.Frame(self.parent); rep_actions_frame.grid(row=2, column=0, sticky='ew', pady=(10, 0))

        self.reports_refresh_button = ttk.Button(rep_controls_frame, text="Vernieuw Verslagen Lijst", command=self._reports_load); self.reports_refresh_button.grid(row=0, column=0, rowspan=4, padx=5, pady=5, sticky=tk.W+tk.N); ttk.Separator(rep_controls_frame, orient=tk.VERTICAL).grid(row=0, column=1, rowspan=4, sticky="ns", padx=15, pady=5)
        ttk.Label(rep_controls_frame, text="Nieuwe Verslag Link Toevoegen:", style="Bold.TLabel").grid(row=0, column=2, columnspan=3, sticky=tk.W, padx=5, pady=(5,2)); ttk.Label(rep_controls_frame, text="Jaar:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2); self.reports_year_var = tk.StringVar(); self.reports_year_combo = ttk.Combobox(rep_controls_frame, textvariable=self.reports_year_var, width=12, state=tk.DISABLED); self.reports_year_combo.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2); self.reports_year_combo.bind("<<ComboboxSelected>>", self._reports_toggle_new_year_entry)
        self.reports_new_year_entry = ttk.Entry(rep_controls_frame, width=8, state=tk.DISABLED); self.reports_new_year_entry.grid(row=1, column=4, sticky=tk.W, padx=5, pady=2); self.reports_new_year_entry.insert(0, "JJJJ"); self.reports_new_year_entry.bind("<FocusIn>", lambda e: self.reports_new_year_entry.delete(0, tk.END) if self.reports_new_year_entry.get() == "JJJJ" else None); self.reports_new_year_entry.bind("<FocusOut>", lambda e: self.reports_new_year_entry.insert(0, "JJJJ") if not self.reports_new_year_entry.get() else None)
        ttk.Label(rep_controls_frame, text="Link Tekst:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2); self.reports_link_text_entry = ttk.Entry(rep_controls_frame, width=45, state=tk.DISABLED); self.reports_link_text_entry.grid(row=2, column=3, columnspan=3, sticky=tk.W+tk.E, padx=5, pady=2); self.reports_upload_button = ttk.Button(rep_controls_frame, text="Blader Document & Voeg Link Toe", command=self._reports_browse_and_upload, state=tk.DISABLED); self.reports_upload_button.grid(row=3, column=3, columnspan=3, sticky=tk.W, padx=5, pady=(5,5)); rep_controls_frame.columnconfigure(3, weight=1)

        rep_columns = ('year', 'text', 'filename'); self.reports_tree = ttk.Treeview(rep_tree_frame, columns=rep_columns, show='headings', selectmode='browse')
        self.reports_tree.heading('year', text='Jaar', anchor=tk.W, command=lambda: self._reports_sort_treeview('year')); self.reports_tree.column('year', width=80, anchor=tk.W, stretch=tk.NO); self.reports_tree.heading('text', text='Link Tekst', anchor=tk.W, command=lambda: self._reports_sort_treeview('text')); self.reports_tree.column('text', width=400, minwidth=250, anchor=tk.W); self.reports_tree.heading('filename', text='Bestandsnaam (in docs map)', anchor=tk.W, command=lambda: self._reports_sort_treeview('filename')); self.reports_tree.column('filename', width=350, minwidth=200, anchor=tk.W)
        rep_vsb = ttk.Scrollbar(rep_tree_frame, orient="vertical", command=self.reports_tree.yview); rep_hsb = ttk.Scrollbar(rep_tree_frame, orient="horizontal", command=self.reports_tree.xview); self.reports_tree.configure(yscrollcommand=rep_vsb.set, xscrollcommand=rep_hsb.set)
        rep_tree_frame.grid_rowconfigure(0, weight=1); rep_tree_frame.grid_columnconfigure(0, weight=1); self.reports_tree.grid(row=0, column=0, sticky='nsew'); rep_vsb.grid(row=0, column=1, sticky='ns'); rep_hsb.grid(row=1, column=0, sticky='ew')

        rep_button_area = ttk.Frame(rep_actions_frame); rep_button_area.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.reports_delete_button = ttk.Button(rep_button_area, text="Verwijder Geselecteerde Link", command=self._reports_delete, state=tk.DISABLED); self.reports_delete_button.pack(side=tk.LEFT, padx=(0,5)); self.reports_save_button = ttk.Button(rep_button_area, text="Wijzigingen Opslaan naar HTML", command=self._reports_save, state=tk.DISABLED); self.reports_save_button.pack(side=tk.RIGHT, padx=(5,0))

    def _reports_update_ui_states(self, loaded=False):
        add_form_state = tk.NORMAL if loaded else tk.DISABLED; combo_state = "readonly" if loaded else tk.DISABLED
        try:
            self.reports_save_button.config(state=add_form_state); self.reports_upload_button.config(state=add_form_state)
            self.reports_delete_button.config(state=tk.DISABLED); self.reports_year_combo.config(state=combo_state)
            self.reports_link_text_entry.config(state=add_form_state)
            is_new_year_selected = self.reports_year_var.get() == "<Nieuw Jaar>"
            self.reports_new_year_entry.config(state=tk.NORMAL if loaded and is_new_year_selected else tk.DISABLED)
            if loaded:
                self._reports_update_year_dropdown(); self.reports_tree.bind("<<TreeviewSelect>>", self._reports_on_selection_change)
            else:
                self.reports_year_combo['values'] = []; self.reports_year_var.set(""); self.reports_link_text_entry.delete(0, tk.END)
                self.reports_new_year_entry.delete(0, tk.END); self.reports_new_year_entry.insert(0, "JJJJ")
                self.reports_tree.unbind("<<TreeviewSelect>>")
        except Exception as e: pass

    def _reports_on_selection_change(self, event=None):
        self.reports_delete_button.config(state=tk.NORMAL if self.reports_tree.selection() else tk.DISABLED)

    def _reports_update_year_dropdown(self):
        if not self.reports_file_loaded:
            self.reports_year_combo['values'] = []; self.reports_year_var.set(""); return
        years = sorted([y for y in self.reports_data.keys() if y.isdigit()], key=int, reverse=True)
        current_system_year = str(datetime.date.today().year); new_year_option = "<Nieuw Jaar>"; options = [new_year_option]; unique_options = []
        if current_system_year not in years: options.append(current_system_year)
        options.extend(years);
        for opt in options:
            if opt not in unique_options: unique_options.append(opt)
        self.reports_year_combo['values'] = unique_options; current_selection = self.reports_year_var.get()
        if current_selection not in unique_options:
             if current_system_year in unique_options: self.reports_year_var.set(current_system_year)
             elif years: self.reports_year_var.set(years[0])
             else: self.reports_year_var.set(new_year_option)
        self._reports_toggle_new_year_entry()

    def _reports_toggle_new_year_entry(self, event=None):
        is_new_year = self.reports_year_var.get() == "<Nieuw Jaar>"
        new_state = tk.NORMAL if self.reports_file_loaded and is_new_year else tk.DISABLED
        self.reports_new_year_entry.config(state=new_state)
        if new_state == tk.NORMAL and self.reports_new_year_entry.get() == "JJJJ": self.reports_new_year_entry.delete(0, tk.END)
        elif new_state == tk.DISABLED and not self.reports_new_year_entry.get(): self.reports_new_year_entry.insert(0, "JJJJ")

    def _reports_clear_treeview(self):
        self.reports_tree.unbind("<<TreeviewSelect>>");
        for item in self.reports_tree.get_children(): self.reports_tree.delete(item)

    def _reports_populate_treeview(self):
        self._reports_clear_treeview(); flat_reports = []
        for year, reports_list in self.reports_data.items():
            for index, report_dict in enumerate(reports_list):
                flat_reports.append({'year': year, 'text': report_dict['text'], 'filename': report_dict['filename'], 'path': report_dict['path'], 'original_index': index})
        def sort_key_func(item):
            col_value = item.get(self._reports_sort_column, "")
            return int(col_value) if self._reports_sort_column == 'year' and isinstance(col_value, str) and col_value.isdigit() else 0 if self._reports_sort_column == 'year' else col_value.lower() if isinstance(col_value, str) else col_value
        sorted_flat_reports = sorted(flat_reports, key=sort_key_func, reverse=self._reports_sort_reverse)
        for item_data in sorted_flat_reports:
            item_id = f"{item_data['year']}-{item_data['original_index']}"; values = (item_data['year'], item_data['text'], item_data['filename'])
            try: self.reports_tree.insert('', tk.END, iid=item_id, values=values, tags=('report_row',))
            except Exception as e: pass
        self._reports_update_sort_indicator(); self._reports_on_selection_change()
        if self.reports_data: self.reports_tree.bind("<<TreeviewSelect>>", self._reports_on_selection_change)

    def _reports_sort_treeview(self, col):
        if col == self._reports_sort_column: self._reports_sort_reverse = not self._reports_sort_reverse
        else: self._reports_sort_column = col; self._reports_sort_reverse = (col == 'year')
        self._reports_populate_treeview()

    def _reports_update_sort_indicator(self):
         arrow = ' ↓' if self._reports_sort_reverse else ' ↑'
         headings = {'year': "Jaar", 'text': "Link Tekst", 'filename': "Bestandsnaam (in docs map)"}
         for c, base_text in headings.items(): self.reports_tree.heading(c, text=base_text + (arrow if c == self._reports_sort_column else ""))

    def _reports_load(self):
        if not os.path.exists(config.REPORTS_HTML_FILE_PATH):
            messagebox.showerror("Bestand Niet Gevonden", f"Verslagen HTML bestand niet gevonden:\n{config.REPORTS_HTML_FILE_PATH}", parent=self.app.root)
            self.app.set_status("Fout: Verslagen HTML bestand niet gevonden.", is_error=True); self._reports_update_ui_states(loaded=False); self.reports_file_loaded = False; return
        self.app.set_status("Laden/Vernieuwen verslagen van HTML..."); self.app.root.update_idletasks()
        self._reports_clear_treeview(); self.reports_data = {}; self.reports_file_loaded = False
        loaded_data, error_msg = utils.reports_parse_html(config.REPORTS_HTML_FILE_PATH)
        if error_msg is None:
            self.reports_data = loaded_data; self.reports_file_loaded = True
            self._reports_sort_column = 'year'; self._reports_sort_reverse = True; self._reports_populate_treeview()
            self._reports_update_ui_states(loaded=True); report_count = sum(len(v) for v in self.reports_data.values())
            self.app.set_status(f"{report_count} verslag links succesvol geladen.", duration_ms=5000)
        else:
            self._reports_update_ui_states(loaded=False); self.app.set_status(f"Fout bij laden verslagen: {error_msg}", is_error=True)
            messagebox.showerror("Laad Fout", f"Kon verslagen niet parsen van HTML:\n{error_msg}", parent=self.app.root)

    def _reports_browse_and_upload(self):
        if not self.reports_file_loaded:
            messagebox.showwarning("Laden Vereist", "Laad a.u.b. verslagen voor toevoegen links.", parent=self.app.root)
            self.app.set_status("Fout: Laad eerst verslagen.", is_error=True); return
        selected_year_str = self.reports_year_var.get(); target_year = None
        if selected_year_str == "<Nieuw Jaar>":
            new_year_input = self.reports_new_year_entry.get().strip();
            if not new_year_input.isdigit() or len(new_year_input) != 4:
                messagebox.showerror("Ongeldige Invoer", "Voer een geldig 4-cijferig jaar in voor '<Nieuw Jaar>'.", parent=self.app.root); self.reports_new_year_entry.focus(); return
            target_year = new_year_input
        elif selected_year_str and selected_year_str.isdigit(): target_year = selected_year_str
        else: messagebox.showerror("Ongeldige Invoer", "Selecteer doeljaar of '<Nieuw Jaar>'.", parent=self.app.root); self.reports_year_combo.focus(); return
        link_text = self.reports_link_text_entry.get().strip()
        if not link_text: messagebox.showerror("Ongeldige Invoer", "Voer link tekst in.", parent=self.app.root); self.reports_link_text_entry.focus(); return
        filetypes = (("Document Bestanden", "*.pdf *.doc *.docx *.odt *.xls *.xlsx *.ppt *.pptx"), ("Alle bestanden", "*.*"))
        initial_dir = config.REPORTS_DOCS_DEST_DIR_ABSOLUTE if os.path.isdir(config.REPORTS_DOCS_DEST_DIR_ABSOLUTE) else config.APP_BASE_DIR
        source_path = filedialog.askopenfilename(title="Selecteer Verslag Document", filetypes=filetypes, initialdir=initial_dir)
        if not source_path: self.app.set_status("Document selectie geannuleerd.", duration_ms=3000); return
        filename = os.path.basename(source_path);
        try: os.makedirs(config.REPORTS_DOCS_DEST_DIR_ABSOLUTE, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Map Fout", f"Kon bestemmingsmap niet aanmaken:\n{config.REPORTS_DOCS_DEST_DIR_ABSOLUTE}\nFout: {e}", parent=self.app.root)
            self.app.set_status(f"Fout bij aanmaken best. map: {e}", is_error=True); return
        dest_path_absolute = os.path.join(config.REPORTS_DOCS_DEST_DIR_ABSOLUTE, filename)
        href_path_relative = str(pathlib.PurePosixPath(config.REPORTS_DOCS_HREF_DIR_RELATIVE) / filename)
        if os.path.exists(dest_path_absolute):
            if not messagebox.askyesno("Bevestig Overschrijven", f"Bestand '{filename}' bestaat al.\nVervang bestaand bestand?", icon='warning', parent=self.app.root):
                self.app.set_status("Upload geannuleerd (overschrijven geweigerd).", duration_ms=4000); return
        try: shutil.copy2(source_path, dest_path_absolute)
        except Exception as e:
            messagebox.showerror("Upload Fout", f"Kon document niet kopiëren:\n{dest_path_absolute}\nFout: {e}", parent=self.app.root)
            self.app.set_status(f"Fout bij kopiëren document: {e}", is_error=True); return
        new_report_entry = {'text': link_text, 'filename': filename, 'path': href_path_relative}
        if target_year not in self.reports_data:
            self.reports_data[target_year] = []
            self._reports_update_year_dropdown(); self.reports_year_var.set(target_year)
        existing_filenames = [item['filename'] for item in self.reports_data[target_year]]
        self.reports_data[target_year].append(new_report_entry); self._reports_populate_treeview()
        self.app.set_status(f"Verslag link '{link_text}' toegevoegd voor {target_year} (niet opgeslagen).", duration_ms=5000); self.reports_link_text_entry.delete(0, tk.END)

    def _reports_delete(self):
        selected_items = self.reports_tree.selection();
        if not selected_items: messagebox.showwarning("Selectie Vereist", "Selecteer een verslag link om te verwijderen.", parent=self.app.root); return
        item_id = selected_items[0];
        try:
            year, original_index_str = item_id.split('-', 1); original_index = int(original_index_str);
            if year not in self.reports_data or not isinstance(self.reports_data[year], list) or original_index >= len(self.reports_data[year]): raise ValueError(f"Data voor item ID '{item_id}' niet gevonden.")
            report_to_delete = self.reports_data[year][original_index]
            details = f"Jaar: {year}\nLink Tekst: {report_to_delete['text']}\nBestandsnaam: {report_to_delete['filename']}";
            if messagebox.askyesno("Bevestig Link Verwijdering", f"Deze link ingang verwijderen?\n\n{details}\n\n(Verwijdert NIET het bestand '{report_to_delete['filename']}')", icon='warning', parent=self.app.root):
                del self.reports_data[year][original_index]
                if not self.reports_data[year]: del self.reports_data[year]; self._reports_update_year_dropdown()
                self._reports_populate_treeview()
                self.app.set_status("Verslag link verwijderd (niet opgeslagen). Klik 'Wijzigingen Opslaan'.", duration_ms=5000)
        except (ValueError, KeyError, IndexError, TypeError) as e:
            messagebox.showerror("Fout", f"Kon link niet verwijderen.\nFout: {e}\nProbeer opnieuw te laden.", parent=self.app.root)

    def _reports_save(self):
        if not self.reports_file_loaded:
            messagebox.showwarning("Eerst Laden", "Laad verslagen data voor opslaan.", parent=self.app.root)
            self.app.set_status("Opslaan mislukt: Verslagen data niet geladen.", is_error=True); return
        data_to_save = self.reports_data; report_count = sum(len(v) for v in data_to_save.values())
        filename_short = os.path.basename(config.REPORTS_HTML_FILE_PATH)
        if not data_to_save:
            if not messagebox.askyesno("Bevestig Leeg Opslaan", f"Verslagen lijst is leeg.\nWijzigingen opslaan naar:\n{filename_short}?\n(Verwijdert #reports-section inhoud)", icon='warning', parent=self.app.root):
                self.app.set_status("Opslaan geannuleerd (lege lijst).", duration_ms=4000); return
        self.app.set_status(f"Opslaan verslag links naar {filename_short}..."); self.app.root.update_idletasks()
        success, error_msg = utils.reports_save_html(config.REPORTS_HTML_FILE_PATH, data_to_save)
        if success:
            self.app.set_status(f"Verslag links opgeslagen naar {filename_short}.", duration_ms=5000)
        else:
            self.app.set_status(f"Fout bij opslaan verslag links: {error_msg}. Controleer console.", is_error=True)
            messagebox.showerror("Opslag Fout", f"Kon wijzigingen niet opslaan naar:\n{config.REPORTS_HTML_FILE_PATH}\nFout: {error_msg}\nControleer console.", parent=self.app.root)

def create_reports_tab(parent_frame, app_instance):
    return ReportsTab(parent_frame, app_instance)
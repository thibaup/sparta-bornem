import tkinter as tk
from tkinter import ttk, messagebox
import os
import config
import utils

class RecordDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_data=None, callback=None):
        super().__init__(parent); self.transient(parent); self.title(title); self.callback = callback
        self.initial_data = (list(initial_data) + [""] * 5)[:5] if initial_data and isinstance(initial_data, (list, tuple)) else ["", "", "", "", ""]
        self.result = None
        frame = ttk.Frame(self, padding="15"); frame.pack(expand=True, fill=tk.BOTH)
        labels = ["Discipline:*", "Naam:*", "Prestatie:", "Plaats:", "Datum (bv. JJJJ.MM.DD):"]; self.entries = []
        for i, label_text in enumerate(labels):
            ttk.Label(frame, text=label_text).grid(row=i, column=0, sticky=tk.W, padx=5, pady=5)
            entry = ttk.Entry(frame, width=40); entry.grid(row=i, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
            entry.insert(0, str(self.initial_data[i]) if self.initial_data[i] is not None else "")
            self.entries.append(entry)
        frame.columnconfigure(1, weight=1)
        button_frame = ttk.Frame(frame); button_frame.grid(row=len(labels), column=0, columnspan=2, pady=(15, 0), sticky=tk.E)
        ok_button = ttk.Button(button_frame, text="OK", command=self.on_ok); ok_button.pack(side=tk.RIGHT, padx=(5, 0))
        cancel_button = ttk.Button(button_frame, text="Annuleren", command=self.on_cancel); cancel_button.pack(side=tk.RIGHT)
        self.grab_set(); self.protocol("WM_DELETE_WINDOW", self.on_cancel); self.bind("<Return>", self.on_ok); self.bind("<Escape>", self.on_cancel)
        self.entries[0].focus_set(); self.wait_window(self)
    def on_ok(self, event=None):
        data = [entry.get().strip() for entry in self.entries]
        if not data[0]: messagebox.showwarning("Invoer Vereist", "'Discipline' mag niet leeg zijn.", parent=self); self.entries[0].focus_set(); return
        if not data[1]: messagebox.showwarning("Invoer Vereist", "'Naam' mag niet leeg zijn.", parent=self); self.entries[1].focus_set(); return
        self.result = data
        if self.callback: self.callback(self.result)
        self.destroy()
    def on_cancel(self, event=None):
        if self.callback: self.callback(None)
        self.destroy()

class RecordsTab:
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance
        self.records_structure = {}
        self.records_current_file_path = None
        self.records_current_data = []
        self._create_widgets()
        self._records_discover_and_populate_categories()

    def _create_widgets(self):
        self.parent.grid_rowconfigure(1, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        top_frame = ttk.Frame(self.parent); top_frame.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        middle_frame = ttk.Frame(self.parent); middle_frame.grid(row=1, column=0, sticky='nsew', pady=5)
        bottom_frame = ttk.Frame(self.parent); bottom_frame.grid(row=2, column=0, sticky='ew', pady=(5, 0))

        ttk.Label(top_frame, text="Categorie:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky=tk.W); self.records_category_var = tk.StringVar(); self.records_category_combo = ttk.Combobox(top_frame, textvariable=self.records_category_var, state="disabled", width=30); self.records_category_combo.grid(row=0, column=1, padx=(0, 10), pady=5, sticky=tk.W); self.records_category_combo.bind("<<ComboboxSelected>>", self._records_update_type_dropdown)
        ttk.Label(top_frame, text="Record Type:").grid(row=0, column=2, padx=(10, 5), pady=5, sticky=tk.W); self.records_type_var = tk.StringVar(); self.records_type_combo = ttk.Combobox(top_frame, textvariable=self.records_type_var, state="disabled", width=40); self.records_type_combo.grid(row=0, column=3, padx=(0, 10), pady=5, sticky=tk.W); top_frame.columnconfigure(3, weight=1)
        self.records_load_button = ttk.Button(top_frame, text="Laad Records", command=self._records_load, state=tk.DISABLED); self.records_load_button.grid(row=0, column=4, padx=(10, 0), pady=5)

        columns = ('discipline', 'name', 'performance', 'place', 'date'); self.records_tree = ttk.Treeview(middle_frame, columns=columns, show='headings', selectmode='browse')
        self.records_tree.heading('discipline', text='Discipline'); self.records_tree.column('discipline', width=150, minwidth=100, anchor=tk.W); self.records_tree.heading('name', text='Naam'); self.records_tree.column('name', width=200, minwidth=120, anchor=tk.W); self.records_tree.heading('performance', text='Prestatie'); self.records_tree.column('performance', width=100, minwidth=80, anchor=tk.CENTER); self.records_tree.heading('place', text='Plaats'); self.records_tree.column('place', width=120, minwidth=100, anchor=tk.W); self.records_tree.heading('date', text='Datum'); self.records_tree.column('date', width=100, minwidth=90, anchor=tk.CENTER)
        vsb = ttk.Scrollbar(middle_frame, orient="vertical", command=self.records_tree.yview); hsb = ttk.Scrollbar(middle_frame, orient="horizontal", command=self.records_tree.xview); self.records_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.records_tree.grid(row=0, column=0, sticky='nsew'); vsb.grid(row=0, column=1, sticky='ns'); hsb.grid(row=1, column=0, sticky='ew'); middle_frame.grid_rowconfigure(0, weight=1); middle_frame.grid_columnconfigure(0, weight=1); self.records_tree.bind("<Double-1>", self._records_on_double_click_edit)

        button_area = ttk.Frame(bottom_frame); button_area.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.records_add_button = ttk.Button(button_area, text="Record Toevoegen", command=self._records_add_dialog, state=tk.DISABLED); self.records_add_button.pack(side=tk.LEFT, padx=(0,5)); self.records_edit_button = ttk.Button(button_area, text="Selectie Bewerken", command=self._records_edit_dialog, state=tk.DISABLED); self.records_edit_button.pack(side=tk.LEFT, padx=5); self.records_delete_button = ttk.Button(button_area, text="Selectie Verwijderen", command=self._records_delete, state=tk.DISABLED); self.records_delete_button.pack(side=tk.LEFT, padx=5); self.records_save_button = ttk.Button(button_area, text="Wijzigingen Opslaan", command=self._records_save, state=tk.DISABLED); self.records_save_button.pack(side=tk.RIGHT, padx=(5,0))

    def _records_discover_and_populate_categories(self):
        self.records_structure = utils.records_discover_files(config.RECORDS_BASE_DIR_ABSOLUTE); categories = sorted(self.records_structure.keys())
        if not categories:
            self.app.set_status("Fout: Geen record categorie mappen gevonden!", is_error=True)
            messagebox.showerror("Installatie Fout", f"Geen categorie mappen gevonden binnen:\n{config.RECORDS_BASE_DIR_ABSOLUTE}", parent=self.app.root)
            self.records_category_combo['values'] = []; self.records_category_var.set("")
            self.records_type_combo['values'] = []; self.records_type_var.set("")
            self.records_category_combo.config(state=tk.DISABLED); self.records_type_combo.config(state=tk.DISABLED); self.records_load_button.config(state=tk.DISABLED); self._records_update_button_states(loaded=False); return
        self.records_category_combo['values'] = categories; self.records_category_var.set(categories[0])
        self.records_category_combo.config(state="readonly"); self._records_update_type_dropdown()
        if self.records_type_combo['values']: self.records_load_button.config(state=tk.NORMAL)
        else: self.records_load_button.config(state=tk.DISABLED)

    def _records_update_type_dropdown(self, event=None):
        selected_category = self.records_category_var.get(); record_types = sorted(self.records_structure.get(selected_category, {}).keys())
        if record_types:
            self.records_type_combo['values'] = record_types; self.records_type_var.set(record_types[0])
            self.records_type_combo.config(state="readonly"); self.records_load_button.config(state=tk.NORMAL)
        else:
            self.records_type_combo['values'] = []; self.records_type_var.set("")
            self.records_type_combo.config(state=tk.DISABLED); self.records_load_button.config(state=tk.DISABLED)
        self._records_clear_treeview(); self._records_update_button_states(loaded=False)
        self.records_current_file_path = None; self.records_current_data = []
        self.app.set_status("Selecteer categorie/type en klik 'Laad Records'.", duration_ms=4000)

    def _records_update_button_states(self, loaded=False):
        state = tk.NORMAL if loaded else tk.DISABLED
        try:
            self.records_add_button.config(state=state); self.records_edit_button.config(state=tk.DISABLED)
            self.records_delete_button.config(state=tk.DISABLED); self.records_save_button.config(state=state);
        except tk.TclError: pass
        if loaded: self.records_tree.bind("<<TreeviewSelect>>", self._records_on_selection_change)
        else: self.records_tree.unbind("<<TreeviewSelect>>")

    def _records_on_selection_change(self, event=None):
        state = tk.NORMAL if self.records_tree.selection() else tk.DISABLED
        self.records_edit_button.config(state=state); self.records_delete_button.config(state=state)

    def _records_clear_treeview(self):
        self.records_tree.unbind("<<TreeviewSelect>>");
        for item in self.records_tree.get_children(): self.records_tree.delete(item)

    def _records_populate_treeview(self, data):
        self._records_clear_treeview()
        for i, record_row in enumerate(data):
            try:
                padded_row = (list(record_row) + [""] * 5)[:5]
                self.records_tree.insert('', tk.END, iid=i, values=padded_row)
            except Exception as e:
                print(f"[RECORDS GUI FOUT] Kon rij {i} niet invoegen: {record_row}\nFout: {e}")
        self._records_on_selection_change()
        if data: self.records_tree.bind("<<TreeviewSelect>>", self._records_on_selection_change)

    def _records_load(self):
        category = self.records_category_var.get(); record_type = self.records_type_var.get()
        if not category or not record_type:
            messagebox.showwarning("Selectie Ontbreekt", "Selecteer a.u.b. categorie en record type.", parent=self.app.root); return
        try: self.records_current_file_path = self.records_structure[category][record_type]
        except KeyError:
            messagebox.showerror("Fout", f"Interne Fout: Pad niet gevonden voor {category} - {record_type}.", parent=self.app.root)
            self.records_current_file_path = None; self._records_clear_treeview(); self._records_update_button_states(loaded=False)
            self.app.set_status(f"Fout bij vinden pad voor {category} / {record_type}", is_error=True); return

        self.app.set_status(f"Laden records van {os.path.basename(self.records_current_file_path)}..."); self.app.root.update_idletasks()
        self.records_current_data = utils.records_parse_html(self.records_current_file_path); self._records_clear_treeview()
        if self.records_current_data is not None:
            self._records_populate_treeview(self.records_current_data); self._records_update_button_states(loaded=True)
            self.app.set_status(f"{len(self.records_current_data)} records geladen van {os.path.basename(self.records_current_file_path)}.", duration_ms=5000)
        else:
            self.records_current_data = []
            self.app.set_status(f"Fout bij laden records van {os.path.basename(self.records_current_file_path)}. Controleer console.", is_error=True)
            messagebox.showerror("Laad Fout", f"Kon records niet parsen van:\n{self.records_current_file_path}\nControleer console log.", parent=self.app.root)
            self._records_update_button_states(loaded=False); self.records_current_file_path = None

    def _records_on_double_click_edit(self, event):
        if not self.records_current_file_path or not self.records_tree.selection(): return
        if self.records_edit_button['state'] == tk.NORMAL: self._records_edit_dialog()

    def _records_add_dialog(self):
        if not self.records_current_file_path:
            messagebox.showwarning("Laden Vereist", "Laad a.u.b. een record bestand voor toevoegen.", parent=self.app.root); return
        RecordDialog(self.app.root, "Nieuw Record Toevoegen", None, self._records_process_new)

    def _records_edit_dialog(self):
        selected_items = self.records_tree.selection();
        if not selected_items:
            messagebox.showwarning("Selectie Vereist", "Selecteer a.u.b. een record om te bewerken.", parent=self.app.root); return
        item_id = selected_items[0]
        try:
            record_index = int(item_id); initial_data = self.records_current_data[record_index]
            RecordDialog(self.app.root, "Record Bewerken", initial_data, lambda data: self._records_process_edited(record_index, data))
        except (IndexError, ValueError) as e:
            messagebox.showerror("Fout", "Kon geselecteerde record data niet ophalen voor bewerken.", parent=self.app.root)

    def _records_process_new(self, new_data):
        if new_data and len(new_data) == 5:
            self.records_current_data.append(new_data); new_item_index = len(self.records_current_data) - 1; new_item_iid = str(new_item_index)
            try:
                self.records_tree.insert('', tk.END, iid=new_item_iid, values=new_data)
                self.app.set_status("Nieuw record toegevoegd (niet opgeslagen). Klik 'Wijzigingen Opslaan'.", duration_ms=5000)
                self.records_tree.selection_set(new_item_iid); self.records_tree.focus(new_item_iid); self.records_tree.see(new_item_iid)
            except Exception as e:
                self._records_populate_treeview(self.records_current_data)
        elif new_data: pass # Invalid data

    def _records_process_edited(self, record_index, updated_data):
        if updated_data and len(updated_data) == 5:
            try:
                self.records_current_data[record_index] = updated_data; item_iid = str(record_index)
                self.records_tree.item(item_iid, values=updated_data)
                self.app.set_status("Record bijgewerkt (niet opgeslagen). Klik 'Wijzigingen Opslaan'.", duration_ms=5000)
                self.records_tree.selection_set(item_iid); self.records_tree.focus(item_iid); self.records_tree.see(item_iid)
            except IndexError:
                messagebox.showerror("Fout", "Kon record niet bijwerken (interne index fout). Herlaad.", parent=self.app.root)
            except Exception as e:
                self._records_populate_treeview(self.records_current_data)
        elif updated_data: pass # Invalid data

    def _records_delete(self):
        selected_items = self.records_tree.selection();
        if not selected_items:
            messagebox.showwarning("Selectie Vereist", "Selecteer a.u.b. een record om te verwijderen.", parent=self.app.root); return
        item_id = selected_items[0];
        try:
            record_index = int(item_id); record_details_list = self.records_current_data[record_index][:3]
            record_details = " | ".join(map(str, record_details_list))
            if messagebox.askyesno("Verwijderen Bevestigen", f"Dit record verwijderen?\n\n{record_details}", parent=self.app.root):
                del self.records_current_data[record_index]
                self._records_populate_treeview(self.records_current_data)
                self.app.set_status("Record verwijderd (niet opgeslagen). Klik 'Wijzigingen Opslaan'.", duration_ms=5000)
        except (IndexError, ValueError) as e:
            messagebox.showerror("Fout", "Kon geselecteerd record niet vinden om te verwijderen.", parent=self.app.root)

    def _records_save(self):
        if not self.records_current_file_path:
            messagebox.showerror("Fout", "Geen record bestand geladen. Kan niet opslaan.", parent=self.app.root)
            self.app.set_status("Opslaan mislukt: Geen bestand geladen.", is_error=True); return
        data_to_save = self.records_current_data; filename_short = os.path.basename(self.records_current_file_path)
        if not data_to_save:
            if not messagebox.askyesno("Bevestig Leeg Opslaan", f"Lege lijst opslaan naar:\n{filename_short}?\nDit verwijdert alle records.", icon='warning', parent=self.app.root):
                self.app.set_status("Opslaan geannuleerd (lege lijst).", duration_ms=4000); return
        self.app.set_status(f"Wijzigingen opslaan naar {filename_short}..."); self.app.root.update_idletasks()
        success = utils.records_save_html(self.records_current_file_path, data_to_save)
        if success:
            self.app.set_status(f"Wijzigingen opgeslagen naar {filename_short}.", duration_ms=5000)
        else:
            self.app.set_status(f"Fout bij opslaan wijzigingen naar {filename_short}. Controleer console.", is_error=True)
            messagebox.showerror("Opslag Fout", f"Kon wijzigingen niet opslaan naar:\n{self.records_current_file_path}\nControleer console.", parent=self.app.root)

def create_records_tab(parent_frame, app_instance):
    return RecordsTab(parent_frame, app_instance)
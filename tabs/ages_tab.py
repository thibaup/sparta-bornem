import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import config
import utils
import copy

class AgesDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_data=None, callback=None):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.callback = callback
        self.initial_data = initial_data or {}
        self.result = None

        frame = ttk.Frame(self, padding="15")
        frame.pack(expand=True, fill=tk.BOTH)
        row_index = 0

        ttk.Label(frame, text="Categorie:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.category_entry = ttk.Entry(frame, width=40)
        self.category_entry.grid(row=row_index, column=1, sticky="ew", padx=5, pady=2)
        self.category_entry.insert(0, self.initial_data.get('category', ''))
        row_index += 1

        ttk.Label(frame, text="Geboortejaar(en):*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.years_entry = ttk.Entry(frame, width=40)
        self.years_entry.grid(row=row_index, column=1, sticky="ew", padx=5, pady=2)
        self.years_entry.insert(0, self.initial_data.get('years', ''))
        row_index += 1

        frame.columnconfigure(1, weight=1)
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row_index, column=0, columnspan=2, pady=(15, 0), sticky=tk.E)
        ok_button = ttk.Button(button_frame, text="OK", command=self.on_ok)
        ok_button.pack(side=tk.RIGHT, padx=(5, 0))
        cancel_button = ttk.Button(button_frame, text="Annuleren", command=self.on_cancel)
        cancel_button.pack(side=tk.RIGHT)

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.bind("<Return>", self.on_ok)
        self.bind("<Escape>", self.on_cancel)
        self.category_entry.focus_set()
        self.wait_window()

    def on_ok(self, event=None):
        category = self.category_entry.get().strip()
        years = self.years_entry.get().strip()
        if not category:
            messagebox.showwarning("Invoer Vereist", "Categorie mag niet leeg zijn.", parent=self)
            self.category_entry.focus_set()
            return
        if not years:
            messagebox.showwarning("Invoer Vereist", "Geboortejaar(en) mag niet leeg zijn.", parent=self)
            self.years_entry.focus_set()
            return
        self.result = {'category': category, 'years': years}
        if self.callback:
            original_index = self.initial_data.get('original_index')
            tree_iid = self.initial_data.get('iid')
            self.callback(self.result, original_index, tree_iid)
        self.destroy()

    def on_cancel(self, event=None):
        self.destroy()


class AgesTab:
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance
        self.age_data = []
        self.top_text = ""
        self.ages_file_loaded = False
        self._create_widgets()
        self._load_ages()

    def _create_widgets(self):
        self.parent.grid_rowconfigure(1, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        top_frame = ttk.Frame(self.parent, padding=(10, 10, 10, 0))
        top_frame.grid(row=0, column=0, sticky="ew")
        top_frame.columnconfigure(1, weight=1)

        self.refresh_button = ttk.Button(top_frame, text="Herlaad Leeftijden", command=self._load_ages)
        self.refresh_button.grid(row=0, column=0, padx=(0,10), pady=5, rowspan=2, sticky="w")

        ttk.Label(top_frame, text="Tekst boven tabel:").grid(row=0, column=1, sticky="w", padx=5, pady=(5,0))
        self.top_entry = ttk.Entry(top_frame, width=30)
        self.top_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=(0,5))

        self.save_button = ttk.Button(top_frame, text="Leeftijden Opslaan", command=self._save_ages, state=tk.DISABLED)
        self.save_button.grid(row=0, column=2, padx=10, pady=5, rowspan=2, sticky="e")

        tree_frame = ttk.Frame(self.parent, padding=(10, 5, 10, 5))
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        cols = ('category', 'years')
        self.ages_tree = ttk.Treeview(tree_frame, columns=cols, show='headings', selectmode='browse')
        self.ages_tree.heading('category', text='Categorie')
        self.ages_tree.column('category', width=200, anchor=tk.W)
        self.ages_tree.heading('years', text='Geboortejaar(en)')
        self.ages_tree.column('years', width=300, anchor=tk.W)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.ages_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.ages_tree.xview)
        self.ages_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.ages_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.ages_tree.bind("<<TreeviewSelect>>", self._on_age_selected)
        self.ages_tree.bind("<Double-1>", self._on_age_double_click)

        button_frame = ttk.Frame(self.parent, padding=(10, 5, 10, 10))
        button_frame.grid(row=2, column=0, sticky="ew")

        self.add_button = ttk.Button(button_frame, text="Categorie Toevoegen...", command=self._add_dialog, state=tk.DISABLED)
        self.add_button.pack(side=tk.LEFT, padx=(0,5))
        self.edit_button = ttk.Button(button_frame, text="Geselecteerde Bewerken...", command=self._edit_dialog, state=tk.DISABLED)
        self.edit_button.pack(side=tk.LEFT, padx=5)
        self.delete_button = ttk.Button(button_frame, text="Geselecteerde Verwijderen", command=self._delete_category, state=tk.DISABLED)
        self.delete_button.pack(side=tk.LEFT, padx=5)

    def _load_ages(self):
        if not utils.confirm_discard_changes(self):
            return
        previous_top_text = self.top_entry.get()
        self.app.set_status("Laden leeftijden data...")
        self.app.root.update_idletasks()
        if not os.path.exists(config.AGES_HTML_FILE_PATH):
            messagebox.showerror("Bestand Niet Gevonden", f"Leeftijden bestand niet gevonden:\n{config.AGES_HTML_FILE_PATH}", parent=self.app.root)
            self.app.set_status("Fout: Leeftijden HTML niet gevonden.", is_error=True)
            self.ages_file_loaded = False
        else:
            parsed_list, top_text, error_msg = utils.ages_parse_html(config.AGES_HTML_FILE_PATH)
            if error_msg:
                messagebox.showerror("Laad Fout", f"Fout bij laden leeftijden:\n{error_msg}", parent=self.app.root)
                self.app.set_status(f"Fout bij laden leeftijden: {error_msg}", is_error=True)
                self.ages_file_loaded = False
            else:
                self.age_data = parsed_list if parsed_list is not None else []
                self.top_text = top_text if top_text is not None else ""
                self.ages_file_loaded = True
                self.app.set_status(f"{len(self.age_data)} leeftijdscategorieën geladen.", duration_ms=5000)

        if not self.ages_file_loaded:
            self.top_text = previous_top_text
        self._populate_ui()
        self._update_ui_states()
        if self.ages_file_loaded:
            utils.remember_editor_state(self, (self.age_data, self.top_entry.get()))
        return self.ages_file_loaded

    def has_unsaved_changes(self):
        return utils.editor_state_changed(self, (self.age_data, self.top_entry.get()))

    def _populate_ui(self):
        self.top_entry.delete(0, tk.END)
        self.top_entry.insert(0, self.top_text)
        self._populate_treeview()

    def _populate_treeview(self):
        self.ages_tree.delete(*self.ages_tree.get_children())
        for index, item in enumerate(self.age_data):
            iid = str(index)
            values = (item.get('category', ''), item.get('years', ''))
            self.ages_tree.insert('', tk.END, iid=iid, values=values)
        self.edit_button.config(state=tk.DISABLED)
        self.delete_button.config(state=tk.DISABLED)

    def _update_ui_states(self):
        state = tk.NORMAL if self.ages_file_loaded else tk.DISABLED
        self.save_button.config(state=state)
        self.add_button.config(state=state)

    def _on_age_selected(self, event=None):
        is_selected = bool(self.ages_tree.selection())
        state = tk.NORMAL if is_selected else tk.DISABLED
        self.edit_button.config(state=state)
        self.delete_button.config(state=state)

    def _on_age_double_click(self, event=None):
        if self.edit_button['state'] == tk.NORMAL:
            self._edit_dialog()

    def _add_dialog(self):
        if not self.ages_file_loaded:
            return
        AgesDialog(self.app.root, "Nieuwe Categorie Toevoegen",
                   callback=lambda data, idx, tid: self._process_edit(data, None, None))

    def _edit_dialog(self):
        if not self.ages_file_loaded:
            return
        selected_items = self.ages_tree.selection()
        if not selected_items:
            return
        iid = selected_items[0]
        try:
            index = int(iid)
            if 0 <= index < len(self.age_data):
                initial_data = copy.deepcopy(self.age_data[index])
                initial_data['original_index'] = index
                initial_data['iid'] = iid
                AgesDialog(self.app.root, "Categorie Bewerken", initial_data,
                           callback=lambda data, idx, tid: self._process_edit(data, idx, tid))
            else:
                raise IndexError("Index out of bounds")
        except (ValueError, IndexError) as e:
            messagebox.showerror("Fout", f"Kon data niet laden voor bewerken: {e}", parent=self.app.root)

    def _process_edit(self, result_data, original_index, tree_iid):
        if result_data is None:
            return
        is_edit = original_index is not None
        if is_edit:
            if 0 <= original_index < len(self.age_data):
                self.age_data[original_index] = result_data
            else:
                messagebox.showerror("Fout", "Interne indexfout bij bijwerken.", parent=self.app.root)
                return
        else:
            self.age_data.append(result_data)
        self._populate_treeview()
        self.app.set_status("Categorie bijgewerkt (niet opgeslagen)." if is_edit else "Categorie toegevoegd (niet opgeslagen).", duration_ms=4000)
        new_index = original_index if is_edit else len(self.age_data) - 1
        new_iid = str(new_index)
        if self.ages_tree.exists(new_iid):
            self.ages_tree.selection_set(new_iid)
            self.ages_tree.focus(new_iid)
            self.ages_tree.see(new_iid)

    def _delete_category(self):
        if not self.ages_file_loaded:
            return
        selected_items = self.ages_tree.selection()
        if not selected_items:
            return
        iid = selected_items[0]
        try:
            index = int(iid)
            if 0 <= index < len(self.age_data):
                category_name = self.age_data[index].get('category', 'Onbekend')
                if messagebox.askyesno("Verwijderen Bevestigen", f"Categorie '{category_name}' verwijderen?", icon='warning', parent=self.app.root):
                    del self.age_data[index]
                    self._populate_treeview()
                    self.app.set_status(f"Categorie '{category_name}' verwijderd (niet opgeslagen).", duration_ms=4000)
            else:
                raise IndexError("Index out of bounds")
        except (ValueError, IndexError) as e:
            messagebox.showerror("Fout", f"Kon categorie niet vinden om te verwijderen: {e}", parent=self.app.root)

    def _save_ages(self):
        if not self.ages_file_loaded:
            messagebox.showwarning("Data niet geladen", "Kan niet opslaan, data is niet geladen.", parent=self.app.root)
            return
        current_top_text = self.top_entry.get().strip()
        if not current_top_text:
            messagebox.showwarning("Invoer Vereist", "Tekst boven tabel mag niet leeg zijn.", parent=self.app.root)
            self.top_entry.focus_set()
            return
        self.app.set_status("Leeftijden opslaan...")
        self.app.root.update_idletasks()
        success, error_msg = utils.ages_save_html(config.AGES_HTML_FILE_PATH, self.age_data, current_top_text)
        if success:
            self.app.set_status("Leeftijden succesvol opgeslagen.", duration_ms=5000)
            self.top_text = current_top_text
            utils.remember_editor_state(self, (self.age_data, self.top_entry.get()))
        else:
            self.app.set_status(f"Fout bij opslaan leeftijden: {error_msg}", is_error=True)
            messagebox.showerror("Opslag Fout", f"Kon leeftijden niet opslaan:\n{config.AGES_HTML_FILE_PATH}\nFout: {error_msg}", parent=self.app.root)

def create_ages_tab(parent_frame, app_instance):
    return AgesTab(parent_frame, app_instance)

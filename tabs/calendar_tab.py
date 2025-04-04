import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import os
import config
import utils

class CalendarEventDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_event_dict=None, callback=None):
        super().__init__(parent); self.transient(parent); self.title(title); self.callback = callback; self.result = None
        self.initial_data = initial_event_dict or {}; default_date = datetime.date.today().isoformat(); default_color = config.CALENDAR_EVENT_COLORS[0] if config.CALENDAR_EVENT_COLORS else "black"
        frame = ttk.Frame(self, padding="15"); frame.pack(expand=True, fill=tk.BOTH); row_index = 0
        ttk.Label(frame, text="Datum (JJJJ-MM-DD):*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5); self.entry_date = ttk.Entry(frame, width=20); self.entry_date.grid(row=row_index, column=1, sticky=tk.W, padx=5, pady=2); self.entry_date.insert(0, self.initial_data.get('date', default_date)); row_index += 1
        ttk.Label(frame, text="Event Naam:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5); self.entry_name = ttk.Entry(frame, width=45); self.entry_name.grid(row=row_index, column=1, sticky=(tk.W, tk.E), padx=5, pady=2); self.entry_name.insert(0, self.initial_data.get('name', '')); row_index += 1
        ttk.Label(frame, text="Kleur:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5); self.color_var = tk.StringVar(value=self.initial_data.get('color', default_color)); self.combo_color = ttk.Combobox(frame, textvariable=self.color_var, values=config.CALENDAR_EVENT_COLORS, state="readonly", width=18); self.combo_color.grid(row=row_index, column=1, sticky=tk.W, padx=5, pady=2)
        if self.initial_data.get('color') in config.CALENDAR_EVENT_COLORS: self.combo_color.set(self.initial_data['color'])
        else: self.combo_color.set(default_color)
        row_index += 1
        ttk.Label(frame, text="Link (Optioneel):").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5); self.entry_link = ttk.Entry(frame, width=45); self.entry_link.grid(row=row_index, column=1, sticky=(tk.W, tk.E), padx=5, pady=2); self.entry_link.insert(0, self.initial_data.get('link') or ''); row_index += 1
        frame.columnconfigure(1, weight=1)
        button_frame = ttk.Frame(frame); button_frame.grid(row=row_index, column=0, columnspan=2, pady=(15, 0), sticky=tk.E)
        ok_button = ttk.Button(button_frame, text="OK", command=self.on_ok); ok_button.pack(side=tk.RIGHT, padx=(5, 0)); cancel_button = ttk.Button(button_frame, text="Annuleren", command=self.on_cancel); cancel_button.pack(side=tk.RIGHT)
        self.grab_set(); self.protocol("WM_DELETE_WINDOW", self.on_cancel); self.bind("<Return>", self.on_ok); self.bind("<Escape>", self.on_cancel); self.entry_date.focus_set(); self.wait_window(self)
    def on_ok(self, event=None):
        date_str = self.entry_date.get().strip(); name = self.entry_name.get().strip(); color = self.color_var.get(); link = self.entry_link.get().strip() or None
        if not date_str: messagebox.showwarning("Invoer Vereist", "'Datum' mag niet leeg zijn.", parent=self); self.entry_date.focus_set(); return
        try: normalized_date_str = datetime.datetime.strptime(date_str, '%Y-%m-%d').date().isoformat()
        except ValueError: messagebox.showwarning("Ongeldig Formaat", "'Datum' moet JJJJ-MM-DD zijn.", parent=self); self.entry_date.focus_set(); return
        if not name: messagebox.showwarning("Invoer Vereist", "'Event Naam' mag niet leeg zijn.", parent=self); self.entry_name.focus_set(); return
        if not color or color not in config.CALENDAR_EVENT_COLORS: messagebox.showerror("Interne Fout", "Ongeldige kleur geselecteerd.", parent=self); return
        if link and not (link.startswith(('http://', 'https://', '/', '#', 'mailto:'))):
             if not messagebox.askyesno("Link Formaat Controle", f"Ongewoon link formaat:\n'{link}'\nIs dit correct?", icon='question', parent=self): self.entry_link.focus_set(); return
        self.result = {'date': normalized_date_str, 'name': name, 'color': color, 'link': link}
        if self.callback: self.callback(self.result)
        self.destroy()
    def on_cancel(self, event=None):
        if self.callback: self.callback(None)
        self.destroy()

class CalendarTab:
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance
        self.calendar_events_data = []
        self.calendar_file_loaded = False
        self._calendar_sort_column = 'date'
        self._calendar_sort_reverse = False
        self._create_widgets()
        self._calendar_load()

    def _create_widgets(self):
        self.parent.grid_rowconfigure(1, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        cal_top_frame = ttk.Frame(self.parent); cal_top_frame.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        cal_middle_frame = ttk.Frame(self.parent); cal_middle_frame.grid(row=1, column=0, sticky='nsew', pady=5)
        cal_bottom_frame = ttk.Frame(self.parent); cal_bottom_frame.grid(row=2, column=0, sticky='ew', pady=(5, 0))

        self.calendar_refresh_button = ttk.Button(cal_top_frame, text="Vernieuw Kalender Events", command=self._calendar_load); self.calendar_refresh_button.pack(side=tk.LEFT, padx=5, pady=5)
        cal_columns = ('date', 'name', 'color', 'link'); self.calendar_tree = ttk.Treeview(cal_middle_frame, columns=cal_columns, show='headings', selectmode='browse')
        self.calendar_tree.heading('date', text='Datum (JJJJ-MM-DD)', anchor=tk.W, command=lambda: self._calendar_sort_treeview('date')); self.calendar_tree.column('date', width=130, minwidth=110, anchor=tk.W, stretch=tk.NO)
        self.calendar_tree.heading('name', text='Event Naam', anchor=tk.W, command=lambda: self._calendar_sort_treeview('name')); self.calendar_tree.column('name', width=350, minwidth=200, anchor=tk.W)
        self.calendar_tree.heading('color', text='Kleur', anchor=tk.W, command=lambda: self._calendar_sort_treeview('color')); self.calendar_tree.column('color', width=80, minwidth=60, anchor=tk.W, stretch=tk.NO)
        self.calendar_tree.heading('link', text='Link (Optioneel)', anchor=tk.W, command=lambda: self._calendar_sort_treeview('link')); self.calendar_tree.column('link', width=250, minwidth=150, anchor=tk.W)
        cal_vsb = ttk.Scrollbar(cal_middle_frame, orient="vertical", command=self.calendar_tree.yview); cal_hsb = ttk.Scrollbar(cal_middle_frame, orient="horizontal", command=self.calendar_tree.xview); self.calendar_tree.configure(yscrollcommand=cal_vsb.set, xscrollcommand=cal_hsb.set)
        cal_middle_frame.grid_rowconfigure(0, weight=1); cal_middle_frame.grid_columnconfigure(0, weight=1); self.calendar_tree.grid(row=0, column=0, sticky='nsew'); cal_vsb.grid(row=0, column=1, sticky='ns'); cal_hsb.grid(row=1, column=0, sticky='ew')
        self.calendar_tree.bind("<Double-1>", self._calendar_on_double_click_edit)

        cal_button_area = ttk.Frame(cal_bottom_frame); cal_button_area.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.calendar_add_button = ttk.Button(cal_button_area, text="Event Toevoegen", command=self._calendar_add_dialog, state=tk.DISABLED); self.calendar_add_button.pack(side=tk.LEFT, padx=(0,5)); self.calendar_edit_button = ttk.Button(cal_button_area, text="Selectie Bewerken", command=self._calendar_edit_dialog, state=tk.DISABLED); self.calendar_edit_button.pack(side=tk.LEFT, padx=5); self.calendar_delete_button = ttk.Button(cal_button_area, text="Selectie Verwijderen", command=self._calendar_delete, state=tk.DISABLED); self.calendar_delete_button.pack(side=tk.LEFT, padx=5); self.calendar_save_button = ttk.Button(cal_button_area, text="Kalender Wijzigingen Opslaan", command=self._calendar_save, state=tk.DISABLED); self.calendar_save_button.pack(side=tk.RIGHT, padx=(5,0))

    def _calendar_update_button_states(self, loaded=False):
        state = tk.NORMAL if loaded else tk.DISABLED
        try:
            self.calendar_add_button.config(state=state); self.calendar_edit_button.config(state=tk.DISABLED)
            self.calendar_delete_button.config(state=tk.DISABLED); self.calendar_save_button.config(state=state);
        except tk.TclError: pass
        if loaded: self.calendar_tree.bind("<<TreeviewSelect>>", self._calendar_on_selection_change)
        else: self.calendar_tree.unbind("<<TreeviewSelect>>")

    def _calendar_on_selection_change(self, event=None):
        state = tk.NORMAL if self.calendar_tree.selection() else tk.DISABLED
        self.calendar_edit_button.config(state=state); self.calendar_delete_button.config(state=state)

    def _calendar_clear_treeview(self):
        self.calendar_tree.unbind("<<TreeviewSelect>>");
        for item in self.calendar_tree.get_children(): self.calendar_tree.delete(item)

    def _calendar_populate_treeview(self):
        self._calendar_clear_treeview()
        key_map = {'date': 'date', 'name': 'name', 'color': 'color', 'link': 'link'}
        sort_key_name = key_map.get(self._calendar_sort_column, 'date')
        def sort_func(event_dict):
            val = event_dict.get(sort_key_name); return (val.lower() if sort_key_name != 'date' else val) if isinstance(val, str) else "" if val is None else str(val).lower()
        display_data_dicts = sorted(self.calendar_events_data, key=sort_func, reverse=self._calendar_sort_reverse)
        original_indices = {id(event): index for index, event in enumerate(self.calendar_events_data)}
        for event_dict in display_data_dicts:
            try:
                original_index = original_indices[id(event_dict)]; item_iid = str(original_index)
                values = [event_dict['date'], event_dict['name'], event_dict['color'], event_dict.get('link') or ""]
                self.calendar_tree.insert('', tk.END, iid=item_iid, values=values, tags=('event_row',))
            except KeyError: pass
            except Exception as e: pass
        self._calendar_update_sort_indicator(); self._calendar_on_selection_change()
        if self.calendar_events_data: self.calendar_tree.bind("<<TreeviewSelect>>", self._calendar_on_selection_change)

    def _calendar_sort_treeview(self, col):
        if col == self._calendar_sort_column: self._calendar_sort_reverse = not self._calendar_sort_reverse
        else: self._calendar_sort_column = col; self._calendar_sort_reverse = False
        self._calendar_populate_treeview()

    def _calendar_update_sort_indicator(self):
         arrow = ' ↓' if self._calendar_sort_reverse else ' ↑'
         headings = {'date': "Datum (JJJJ-MM-DD)", 'name': "Event Naam", 'color': "Kleur", 'link': "Link (Optioneel)"}
         for c, base_text in headings.items(): self.calendar_tree.heading(c, text=base_text + (arrow if c == self._calendar_sort_column else ""))

    def _calendar_load(self):
        if not os.path.exists(config.CALENDAR_HTML_FILE_PATH):
            messagebox.showerror("Bestand Niet Gevonden", f"Kalender bestand niet gevonden:\n{config.CALENDAR_HTML_FILE_PATH}", parent=self.app.root)
            self.app.set_status("Fout: Kalender HTML bestand niet gevonden.", is_error=True); self._calendar_update_button_states(loaded=False); self.calendar_file_loaded = False; return
        self.app.set_status("Laden/Vernieuwen kalender events van HTML..."); self.app.root.update_idletasks()
        loaded_events = utils.calendar_parse_html(config.CALENDAR_HTML_FILE_PATH)
        self._calendar_clear_treeview(); self.calendar_events_data = []
        if loaded_events is not None:
            self.calendar_events_data = loaded_events; self.calendar_file_loaded = True
            self._calendar_sort_column = 'date'; self._calendar_sort_reverse = False; self._calendar_populate_treeview()
            self._calendar_update_button_states(loaded=True); self.app.set_status(f"{len(self.calendar_events_data)} kalender events geladen.", duration_ms=5000)
        else:
            self.calendar_file_loaded = False; self._calendar_update_button_states(loaded=False)
            self.app.set_status("Fout bij laden kalender events. Controleer console.", is_error=True)
            messagebox.showerror("Laad Fout", f"Kon events niet parsen van:\n{config.CALENDAR_HTML_FILE_PATH}\nControleer console log.", parent=self.app.root)

    def _calendar_on_double_click_edit(self, event):
        if not self.calendar_file_loaded or not self.calendar_tree.selection(): return
        if self.calendar_edit_button['state'] == tk.NORMAL: self._calendar_edit_dialog()

    def _calendar_add_dialog(self):
        if not self.calendar_file_loaded:
            messagebox.showwarning("Laden Vereist", "Laad a.u.b. kalender data voor toevoegen.", parent=self.app.root); return
        CalendarEventDialog(self.app.root, "Kalender Event Toevoegen", None, self._calendar_process_new)

    def _calendar_edit_dialog(self):
        selected_items = self.calendar_tree.selection();
        if not selected_items:
            messagebox.showwarning("Selectie Vereist", "Selecteer a.u.b. een event om te bewerken.", parent=self.app.root); return
        item_iid = selected_items[0];
        try:
            record_index = int(item_iid); initial_data = self.calendar_events_data[record_index]
            CalendarEventDialog(self.app.root, "Kalender Event Bewerken", initial_data, lambda data: self._calendar_process_edited(record_index, data))
        except (IndexError, ValueError) as e:
            messagebox.showerror("Fout", "Kon geselecteerde event data niet vinden voor bewerken.", parent=self.app.root)

    def _calendar_process_new(self, new_event_dict):
        if new_event_dict:
            self.calendar_events_data.append(new_event_dict); new_original_index = len(self.calendar_events_data) - 1; new_item_iid = str(new_original_index)
            self._calendar_populate_treeview(); self.app.set_status("Nieuw event toegevoegd (niet opgeslagen). Klik 'Kalender Wijzigingen Opslaan'.", duration_ms=5000)
            try:
                self.calendar_tree.selection_set(new_item_iid); self.calendar_tree.focus(new_item_iid); self.calendar_tree.see(new_item_iid)
            except tk.TclError: pass

    def _calendar_process_edited(self, record_index, updated_event_dict):
        if updated_event_dict:
            try:
                self.calendar_events_data[record_index] = updated_event_dict; self._calendar_populate_treeview()
                self.app.set_status("Event bijgewerkt (niet opgeslagen). Klik 'Kalender Wijzigingen Opslaan'.", duration_ms=5000); item_iid = str(record_index)
                try:
                    if self.calendar_tree.exists(item_iid):
                        self.calendar_tree.selection_set(item_iid); self.calendar_tree.focus(item_iid); self.calendar_tree.see(item_iid)
                except tk.TclError: pass
            except IndexError:
                messagebox.showerror("Fout", "Kon event niet bijwerken (index fout).", parent=self.app.root)

    def _calendar_delete(self):
        selected_items = self.calendar_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selectie Vereist", "Selecteer a.u.b. een event om te verwijderen.", parent=self.app.root); return
        item_iid = selected_items[0]
        try:
            record_index = int(item_iid);
            event_details = f"{self.calendar_events_data[record_index]['date']} | {self.calendar_events_data[record_index]['name']}";
            if messagebox.askyesno("Verwijderen Bevestigen", f"Dit event verwijderen?\n\n{event_details}", parent=self.app.root):
                del self.calendar_events_data[record_index]
                self._calendar_populate_treeview()
                self.app.set_status("Event verwijderd (niet opgeslagen). Klik 'Kalender Wijzigingen Opslaan'.", duration_ms=5000)
        except (IndexError, ValueError) as e:
            messagebox.showerror("Fout", "Kon geselecteerd event niet vinden om te verwijderen.", parent=self.app.root)

    def _calendar_save(self):
        if not self.calendar_file_loaded:
            messagebox.showwarning("Eerst Laden", "Laad a.u.b. kalender data voor opslaan.", parent=self.app.root)
            self.app.set_status("Opslaan mislukt: Kalender data niet geladen.", is_error=True); return
        self.calendar_events_data.sort(key=lambda x: x['date'])
        data_to_save = self.calendar_events_data; filename_short = os.path.basename(config.CALENDAR_HTML_FILE_PATH)
        self.app.set_status(f"Opslaan kalender wijzigingen naar {filename_short}..."); self.app.root.update_idletasks()
        success = utils.calendar_save_html(config.CALENDAR_HTML_FILE_PATH, data_to_save)
        if success:
            self.app.set_status(f"Kalender wijzigingen opgeslagen naar {filename_short}.", duration_ms=5000)
        else:
            self.app.set_status(f"Fout bij opslaan kalender wijzigingen naar {filename_short}. Controleer console.", is_error=True)
            messagebox.showerror("Opslag Fout", f"Kon wijzigingen niet opslaan naar:\n{config.CALENDAR_HTML_FILE_PATH}\nControleer console.", parent=self.app.root)

def create_calendar_tab(parent_frame, app_instance):
    return CalendarTab(parent_frame, app_instance)
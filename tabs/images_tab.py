import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil
import pathlib
import config
import utils

try:
    from PIL import Image, ImageTk
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    Image = None; ImageTk = None

class ImageAddDialog(tk.Toplevel):
    def __init__(self, parent, title, callback=None):
        super().__init__(parent); self.transient(parent); self.title(title); self.callback = callback; self.result = None
        frame = ttk.Frame(self, padding="15"); frame.pack(expand=True, fill=tk.BOTH); row_index = 0

        ttk.Label(frame, text="Bron Afbeeldingsbestand:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.source_path_var = tk.StringVar()
        source_entry = ttk.Entry(frame, textvariable=self.source_path_var, width=50, state="readonly")
        source_entry.grid(row=row_index, column=1, sticky="ew", padx=5, pady=2)
        browse_button = ttk.Button(frame, text="Bladeren...", command=self._browse_source)
        browse_button.grid(row=row_index, column=2, sticky="w", padx=5, pady=2)
        row_index += 1

        ttk.Label(frame, text="Doelmap:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.dest_rel_path_var = tk.StringVar()
        dest_options = sorted(list(config.IMAGE_COMMON_DIRS_ABSOLUTE.keys())) + ["<Andere...>"]
        self.dest_combo = ttk.Combobox(frame, textvariable=self.dest_rel_path_var, values=dest_options, state="readonly", width=48)
        self.dest_combo.grid(row=row_index, column=1, sticky="ew", padx=5, pady=2)
        if dest_options[0] != "<Andere...>": self.dest_combo.set(dest_options[0])
        else: self.dest_combo.set("")
        self.dest_combo.bind("<<ComboboxSelected>>", self._toggle_other_dest)
        self.other_dest_button = ttk.Button(frame, text="Bladeren...", command=self._browse_dest, state=tk.DISABLED)
        self.other_dest_button.grid(row=row_index, column=2, sticky="w", padx=5, pady=2)
        row_index += 1
        ttk.Label(frame, text="Map relatief t.o.v. website root", style="Desc.TLabel").grid(row=row_index, column=1, sticky="w", padx=5)
        row_index += 1

        frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(frame); button_frame.grid(row=row_index, column=0, columnspan=3, pady=(15, 0), sticky=tk.E)
        ok_button = ttk.Button(button_frame, text="Voeg Afbeelding Toe", command=self.on_ok); ok_button.pack(side=tk.RIGHT, padx=(5, 0))
        cancel_button = ttk.Button(button_frame, text="Annuleren", command=self.on_cancel); cancel_button.pack(side=tk.RIGHT)

        self.grab_set(); self.protocol("WM_DELETE_WINDOW", self.on_cancel); self.bind("<Escape>", self.on_cancel)
        self.wait_window(self)

    def _browse_source(self):
        filetypes = (("Afbeeldingsbestanden", "*.jpg *.jpeg *.png *.gif *.webp *.bmp"), ("Alle bestanden", "*.*"))
        source_path = filedialog.askopenfilename(title="Selecteer Bron Afbeelding", filetypes=filetypes)
        if source_path:
            self.source_path_var.set(source_path)

    def _toggle_other_dest(self, event=None):
        if self.dest_rel_path_var.get() == "<Andere...>":
            self.other_dest_button.config(state=tk.NORMAL)
        else:
            self.other_dest_button.config(state=tk.DISABLED)

    def _browse_dest(self):
        dest_dir_abs = filedialog.askdirectory(title="Selecteer Doelmap (binnen website structuur)", initialdir=config.APP_BASE_DIR)
        if dest_dir_abs:
            try:
                 dest_rel_path = os.path.relpath(dest_dir_abs, config.APP_BASE_DIR)
                 dest_rel_path_posix = str(pathlib.Path(dest_rel_path).as_posix())
                 self.dest_rel_path_var.set(dest_rel_path_posix)
            except ValueError:
                 messagebox.showwarning("Pad Waarschuwing", "Doelmap is buiten de website basis map. Gebruik absoluut pad.", parent=self)
                 self.dest_rel_path_var.set(dest_dir_abs)

    def on_ok(self, event=None):
        source_path = self.source_path_var.get()
        dest_rel_path = self.dest_rel_path_var.get()
        if not source_path: messagebox.showwarning("Invoer Vereist", "Selecteer een bron afbeeldingsbestand.", parent=self); return
        if not dest_rel_path or dest_rel_path == "<Andere...>": messagebox.showwarning("Invoer Vereist", "Selecteer een doelmap.", parent=self); return

        dest_abs_path = ""
        if dest_rel_path in config.IMAGE_COMMON_DIRS_ABSOLUTE:
            dest_abs_path = config.IMAGE_COMMON_DIRS_ABSOLUTE[dest_rel_path]
        elif os.path.isabs(dest_rel_path):
            dest_abs_path = dest_rel_path
        else:
            dest_abs_path = os.path.abspath(os.path.join(config.APP_BASE_DIR, dest_rel_path))

        if not dest_abs_path:
             messagebox.showerror("Fout", "Kon absoluut doelpad niet bepalen.", parent=self); return
        if self.callback: self.callback(source_path, dest_abs_path, dest_rel_path)
        self.destroy()

    def on_cancel(self, event=None):
        if self.callback: self.callback(None, None, None)
        self.destroy()

class ImagesTab:
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance
        self.images_found_list = []
        self.images_by_abs_path = {}
        self.images_selected_abs_path = None
        self._images_scan_running = False
        self._image_preview_widget = None
        self._create_widgets()
        self._images_scan_files()

    def _create_widgets(self):
        self.parent.grid_rowconfigure(0, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        pw_main = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        pw_main.grid(row=0, column=0, sticky='nsew')

        left_frame = ttk.Frame(pw_main, padding=(0, 0, 5, 0))
        left_frame.grid_rowconfigure(1, weight=1); left_frame.grid_columnconfigure(0, weight=1)

        img_scan_frame = ttk.Frame(left_frame); img_scan_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.images_refresh_button = ttk.Button(img_scan_frame, text="Scan HTML voor Afbeeldingen", command=self._images_scan_files)
        self.images_refresh_button.pack(side=tk.LEFT, padx=(0, 5))

        img_tree_frame = ttk.Frame(left_frame); img_tree_frame.grid(row=1, column=0, sticky="nsew")
        img_tree_frame.grid_rowconfigure(0, weight=1); img_tree_frame.grid_columnconfigure(0, weight=1)

        img_columns = ('filename', 'path', 'exists', 'usage')
        self.images_tree = ttk.Treeview(img_tree_frame, columns=img_columns, show='headings', selectmode='browse')
        self.images_tree.heading('filename', text='Bestandsnaam', anchor=tk.W); self.images_tree.column('filename', width=200, minwidth=150, anchor=tk.W)
        self.images_tree.heading('path', text='Relatief Pad', anchor=tk.W); self.images_tree.column('path', width=300, minwidth=200, anchor=tk.W)
        self.images_tree.heading('exists', text='Bestaat?', anchor=tk.CENTER); self.images_tree.column('exists', width=60, minwidth=50, anchor=tk.CENTER, stretch=tk.NO)
        self.images_tree.heading('usage', text='Gebruik', anchor=tk.CENTER); self.images_tree.column('usage', width=50, minwidth=40, anchor=tk.CENTER, stretch=tk.NO)

        img_vsb = ttk.Scrollbar(img_tree_frame, orient="vertical", command=self.images_tree.yview); img_hsb = ttk.Scrollbar(img_tree_frame, orient="horizontal", command=self.images_tree.xview)
        self.images_tree.configure(yscrollcommand=img_vsb.set, xscrollcommand=img_hsb.set)
        img_tree_frame.grid_rowconfigure(0, weight=1); img_tree_frame.grid_columnconfigure(0, weight=1)
        self.images_tree.grid(row=0, column=0, sticky='nsew'); img_vsb.grid(row=0, column=1, sticky='ns'); img_hsb.grid(row=1, column=0, sticky='ew')
        self.images_tree.bind("<<TreeviewSelect>>", self._images_on_select)
        self.images_tree.tag_configure('missing', foreground='red')

        pw_main.add(left_frame, weight=2)

        right_frame = ttk.Frame(pw_main, padding=(5, 0, 0, 0))
        right_frame.grid_rowconfigure(1, weight=1); right_frame.grid_columnconfigure(0, weight=1)

        img_actions_frame = ttk.Labelframe(right_frame, text=" Afbeelding Acties ", padding=10)
        img_actions_frame.grid(row=0, column=0, sticky="new"); img_actions_frame.columnconfigure(0, weight=1)

        self.images_add_button = ttk.Button(img_actions_frame, text="Nieuwe Afbeelding Toevoegen...", command=self._images_add_dialog); self.images_add_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.images_change_button = ttk.Button(img_actions_frame, text="Wijzig Geselecteerd Afbeeldingsbestand...", command=self._images_change, state=tk.DISABLED); self.images_change_button.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.images_delete_button = ttk.Button(img_actions_frame, text="Verwijder Geselecteerd Afbeeldingsbestand...", command=self._images_delete, state=tk.DISABLED); self.images_delete_button.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        ttk.Label(img_actions_frame, text="Let op: 'Wijzig' en 'Verwijder' \nwerken direct op bestanden!", justify=tk.LEFT, style="Warning.TLabel").grid(row=3, column=0, padx=5, pady=(10, 5), sticky="w")

        img_preview_frame = ttk.Labelframe(right_frame, text=" Voorvertoning ", padding=10)
        img_preview_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0)); img_preview_frame.grid_rowconfigure(0, weight=1); img_preview_frame.grid_columnconfigure(0, weight=1)

        preview_outer_frame = ttk.Frame(img_preview_frame, width=config.IMAGE_PREVIEW_MAX_WIDTH+10, height=config.IMAGE_PREVIEW_MAX_HEIGHT+10)
        preview_outer_frame.grid(row=0, column=0, sticky="nsew"); preview_outer_frame.grid_propagate(False)
        preview_outer_frame.grid_rowconfigure(0, weight=1); preview_outer_frame.grid_columnconfigure(0, weight=1)

        self.images_preview_label = ttk.Label(preview_outer_frame, text="Selecteer een afbeelding uit de lijst", anchor=tk.CENTER, relief=tk.GROOVE, background="lightgrey")
        self.images_preview_label.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.images_path_label = ttk.Label(img_preview_frame, text="Pad: ", wraplength=config.IMAGE_PREVIEW_MAX_WIDTH+50, justify=tk.LEFT, style="Desc.TLabel")
        self.images_path_label.grid(row=1, column=0, sticky="ew", padx=5, pady=(5, 0))

        pw_main.add(right_frame, weight=1)

    def _images_scan_files(self):
        if self._images_scan_running: return
        self._images_scan_running = True
        self.images_refresh_button.config(state=tk.DISABLED, text="Scannen...")
        self.app.set_status("Scannen HTML bestanden voor afbeeldingen..."); self.app.root.update_idletasks()

        self.images_found_list = []
        self._images_clear_treeview(); self._images_reset_preview_area()

        html_files, file_count = utils.general_html_find_files(config.HTML_SCAN_TARGET_PATHS_ABSOLUTE)
        processed_files = 0; total_images_found = 0

        for i, file_path in enumerate(html_files):
            self.app.set_status(f"Scannen bestand {i+1}/{file_count} voor afbeeldingen: {os.path.basename(file_path)}..."); self.app.root.update_idletasks()
            images_in_file = utils.images_parse_file(file_path, self.app.text_editor_parsed_soups, self.images_found_list)
            if images_in_file > 0:
                processed_files += 1; total_images_found += images_in_file

        self._images_process_found_list(); self._images_populate_treeview()

        self.images_refresh_button.config(state=tk.NORMAL, text="Scan HTML voor Afbeeldingen"); self._images_scan_running = False
        status_msg = f"Afbeelding scan voltooid. {len(self.images_by_abs_path)} unieke lokale afbeeldingsbestanden gevonden in {processed_files} HTML bestanden."
        self.app.set_status(status_msg, duration_ms=8000)

    def _images_process_found_list(self):
        self.images_by_abs_path = {}
        for img_ref in self.images_found_list:
            abs_path = img_ref['abs_path']
            if not abs_path or abs_path == "Fout bij Oplossen Pad": continue
            if abs_path not in self.images_by_abs_path:
                self.images_by_abs_path[abs_path] = {
                    'usage_count': 0, 'src_list': set(), 'html_files': set(),
                    'exists': img_ref['exists'], 'treeview_iid': None
                }
            entry = self.images_by_abs_path[abs_path]
            entry['usage_count'] += 1; entry['src_list'].add(img_ref['src'])
            entry['html_files'].add(img_ref['html_file'])
            if not entry['exists'] and img_ref['exists']: entry['exists'] = True

    def _images_clear_treeview(self):
        self.images_tree.unbind("<<TreeviewSelect>>")
        for item in self.images_tree.get_children(): self.images_tree.delete(item)
        self.images_by_abs_path = {k: {**v, 'treeview_iid': None} for k, v in self.images_by_abs_path.items()}

    def _images_populate_treeview(self):
        self._images_clear_treeview(); sorted_abs_paths = sorted(self.images_by_abs_path.keys())
        for abs_path in sorted_abs_paths:
            img_data = self.images_by_abs_path[abs_path]
            try:
                filename = os.path.basename(abs_path)
                try: display_path = os.path.relpath(abs_path, config.APP_BASE_DIR)
                except ValueError: display_path = abs_path
                display_path = str(pathlib.Path(display_path).as_posix())
                exists_str = "Ja" if img_data['exists'] else "NEE"; usage_count = img_data['usage_count']
                values = (filename, display_path, exists_str, usage_count); item_iid = abs_path
                tags = ('image_row',);
                if not img_data['exists']: tags += ('missing',)
                self.images_tree.insert('', tk.END, iid=item_iid, values=values, tags=tags)
                img_data['treeview_iid'] = item_iid
            except Exception as e: pass
        if self.images_by_abs_path: self.images_tree.bind("<<TreeviewSelect>>", self._images_on_select)

    def _images_reset_preview_area(self):
        self.images_selected_abs_path = None
        self.images_preview_label.config(image='', text="Selecteer een afbeelding uit de lijst")
        self.images_path_label.config(text="Pad: "); self._image_preview_widget = None
        self.images_change_button.config(state=tk.DISABLED); self.images_delete_button.config(state=tk.DISABLED)

    def _images_on_select(self, event=None):
        selected_items = self.images_tree.selection()
        if not selected_items: self._images_reset_preview_area(); return
        selected_iid = selected_items[0]; self.images_selected_abs_path = selected_iid
        if selected_iid not in self.images_by_abs_path:
             messagebox.showerror("Fout", "Geselecteerde afbeelding data niet gevonden. Scan a.u.b. opnieuw.", parent=self.app.root)
             self._images_reset_preview_area(); return
        img_data = self.images_by_abs_path[selected_iid]; abs_path = selected_iid
        exists = img_data['exists']; display_path = self.images_tree.item(selected_iid, 'values')[1]
        self.images_path_label.config(text=f"Pad: {display_path}")
        photo = None; preview_text = "Voorvertoning N/B"
        if exists:
            try:
                if HAS_PILLOW:
                    with Image.open(abs_path) as img:
                        img.thumbnail((config.IMAGE_PREVIEW_MAX_WIDTH, config.IMAGE_PREVIEW_MAX_HEIGHT))
                        photo = ImageTk.PhotoImage(img); preview_text = ""
                else:
                    try: photo = tk.PhotoImage(file=abs_path); preview_text = ""
                    except tk.TclError: preview_text = "Voorvertoning N/B\n(Installeer Pillow voor meer formaten)"; photo = None
            except FileNotFoundError:
                preview_text = "Bestand Niet Gevonden"; img_data['exists'] = False
                self.images_tree.item(selected_iid, values=(os.path.basename(abs_path), display_path, "NEE", img_data['usage_count']), tags=('image_row', 'missing'))
            except Exception as e: preview_text = f"Fout Laden Voorvertoning:\n{e}"
        else: preview_text = "Afbeeldingsbestand Niet Gevonden"
        self.images_preview_label.config(image=photo, text=preview_text); self._image_preview_widget = photo
        action_state = tk.NORMAL if exists else tk.DISABLED
        self.images_change_button.config(state=action_state); self.images_delete_button.config(state=action_state)

    def _images_add_dialog(self):
        ImageAddDialog(self.app.root, "Nieuw Afbeeldingsbestand Toevoegen", self._images_process_add)

    def _images_process_add(self, source_path, dest_dir_abs, dest_dir_rel):
        if not source_path or not dest_dir_abs or not dest_dir_rel: return
        filename = os.path.basename(source_path); dest_path_abs = os.path.join(dest_dir_abs, filename)
        try: os.makedirs(dest_dir_abs, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Map Fout", f"Kon bestemmingsmap niet aanmaken:\n{dest_dir_abs}\nFout: {e}", parent=self.app.root)
            self.app.set_status(f"Fout bij aanmaken map '{dest_dir_rel}': {e}", is_error=True); return
        if os.path.exists(dest_path_abs):
            if not messagebox.askyesno("Bevestig Overschrijven", f"Bestand '{filename}' bestaat al in '{dest_dir_rel}'.\nVervang bestaand bestand?", icon='warning', parent=self.app.root):
                self.app.set_status("Toevoegen afbeelding geannuleerd (overschrijven geweigerd).", duration_ms=4000); return
        try:
            shutil.copy2(source_path, dest_path_abs)
            self.app.set_status(f"Afbeelding '{filename}' toegevoegd aan '{dest_dir_rel}'. Scan HTML opnieuw om gebruik te zien.", duration_ms=8000)
            if dest_path_abs in self.images_by_abs_path:
                img_data = self.images_by_abs_path[dest_path_abs]; img_data['exists'] = True
                if img_data.get('treeview_iid') and self.images_tree.exists(img_data['treeview_iid']):
                    values = self.images_tree.item(img_data['treeview_iid'], 'values')
                    self.images_tree.item(img_data['treeview_iid'], values=(values[0], values[1], "Ja", values[3]), tags=('image_row',))
                    self.images_tree.selection_set(img_data['treeview_iid'])
            else:
                 new_img_data = { 'usage_count': 0, 'src_list': set(), 'html_files': set(), 'exists': True, 'treeview_iid': dest_path_abs }
                 self.images_by_abs_path[dest_path_abs] = new_img_data
                 try: display_path = str(pathlib.Path(os.path.relpath(dest_path_abs, config.APP_BASE_DIR)).as_posix())
                 except ValueError: display_path = dest_path_abs
                 values = (filename, display_path, "Ja", 0)
                 self.images_tree.insert('', tk.END, iid=dest_path_abs, values=values, tags=('image_row',))
                 self.images_tree.selection_set(dest_path_abs)
            self._images_on_select()
        except Exception as e:
            messagebox.showerror("Fout bij Toevoegen Afbeelding", f"Kon afbeelding niet kopiëren naar:\n{dest_path_abs}\nFout: {e}", parent=self.app.root)
            self.app.set_status(f"Fout bij toevoegen afbeelding '{filename}': {e}", is_error=True)

    def _images_change(self):
        if not self.images_selected_abs_path:
            messagebox.showwarning("Selectie Vereist", "Selecteer a.u.b. een afbeelding uit de lijst om te wijzigen.", parent=self.app.root); return
        target_abs_path = self.images_selected_abs_path
        if not os.path.isfile(target_abs_path):
             messagebox.showerror("Fout", f"Geselecteerd afbeeldingsbestand niet gevonden:\n{target_abs_path}\nKan het niet wijzigen.", parent=self.app.root)
             self._images_reset_preview_area(); return
        filename = os.path.basename(target_abs_path)
        if not messagebox.askyesno("Bevestig Afbeelding Wijzigen", f"Dit VERVANGT het bestaande bestand:\n'{filename}'\n\nMet een nieuwe afbeelding die u selecteert.\nDe bestandsnaam blijft hetzelfde.\nDit kan NIET eenvoudig ongedaan gemaakt worden.\n\nDoorgaan?", icon='warning', parent=self.app.root):
            self.app.set_status("Wijzigen afbeelding geannuleerd.", duration_ms=3000); return
        filetypes = (("Afbeeldingsbestanden", "*.jpg *.jpeg *.png *.gif *.webp *.bmp"), ("Alle bestanden", "*.*"))
        new_source_path = filedialog.askopenfilename(title=f"Selecteer NIEUWE Afbeelding ter Vervanging van '{filename}'", filetypes=filetypes)
        if not new_source_path:
            self.app.set_status("Wijzigen afbeelding geannuleerd (geen nieuw bestand geselecteerd).", duration_ms=3000); return
        self.app.set_status(f"Vervangen '{filename}'..."); self.app.root.update_idletasks()
        try:
            shutil.copy2(new_source_path, target_abs_path)
            self.app.set_status(f"Afbeeldingsbestand '{filename}' succesvol vervangen.", duration_ms=5000); self._images_on_select()
        except Exception as e:
            messagebox.showerror("Fout bij Wijzigen Afbeelding", f"Kon bestand niet vervangen:\n{target_abs_path}\nFout: {e}", parent=self.app.root)
            self.app.set_status(f"Fout bij vervangen afbeelding '{filename}': {e}", is_error=True)

    def _images_delete(self):
        if not self.images_selected_abs_path:
            messagebox.showwarning("Selectie Vereist", "Selecteer a.u.b. een afbeelding uit de lijst om te verwijderen.", parent=self.app.root); return
        target_abs_path = self.images_selected_abs_path; img_data = self.images_by_abs_path.get(target_abs_path)
        if not img_data or not img_data['exists']:
             messagebox.showerror("Fout", f"Geselecteerd afbeeldingsbestand niet gevonden of al gemarkeerd als ontbrekend:\n{target_abs_path}\nKan niet verwijderen.", parent=self.app.root)
             self._images_reset_preview_area(); return
        filename = os.path.basename(target_abs_path); usage_count = img_data['usage_count']
        warning_msg = f"Permanent VERWIJDEREN het afbeeldingsbestand:\n'{filename}'\nvan uw computer?\n\n"
        if usage_count > 0: warning_msg += f"WAARSCHUWING: Deze afbeelding wordt {usage_count} keer gebruikt in uw HTML bestanden.\nVerwijderen van het bestand ZAL leiden tot gebroken afbeeldingen op uw website.\n\n"
        warning_msg += "Deze actie kan NIET ongedaan gemaakt worden.\nWeet u het absoluut zeker?"
        if not messagebox.askyesno("Bevestig Verwijdering Afbeeldingsbestand", warning_msg, icon='error', parent=self.app.root):
            self.app.set_status("Verwijderen afbeelding geannuleerd.", duration_ms=3000); return
        self.app.set_status(f"Verwijderen '{filename}'..."); self.app.root.update_idletasks()
        try:
            os.remove(target_abs_path); self.app.set_status(f"Afbeeldingsbestand '{filename}' succesvol verwijderd.", duration_ms=5000)
            img_data['exists'] = False; img_data['usage_count'] = 0
            if img_data.get('treeview_iid') and self.images_tree.exists(img_data['treeview_iid']):
                 values = self.images_tree.item(img_data['treeview_iid'], 'values')
                 self.images_tree.item(img_data['treeview_iid'], values=(values[0], values[1], "NEE", 0), tags=('image_row', 'missing'))
            self._images_reset_preview_area()
        except FileNotFoundError:
             messagebox.showwarning("Verwijder Waarschuwing", f"Bestand was al weg voor verwijdering:\n{target_abs_path}", parent=self.app.root)
             img_data['exists'] = False
             if img_data.get('treeview_iid') and self.images_tree.exists(img_data['treeview_iid']):
                  values = self.images_tree.item(img_data['treeview_iid'], 'values')
                  self.images_tree.item(img_data['treeview_iid'], values=(values[0], values[1], "NEE", 0), tags=('image_row', 'missing'))
             self._images_reset_preview_area()
        except Exception as e:
            messagebox.showerror("Fout bij Verwijderen Afbeelding", f"Kon bestand niet verwijderen:\n{target_abs_path}\nFout: {e}", parent=self.app.root)
            self.app.set_status(f"Fout bij verwijderen afbeelding '{filename}': {e}", is_error=True)

def create_images_tab(parent_frame, app_instance):
    return ImagesTab(parent_frame, app_instance)
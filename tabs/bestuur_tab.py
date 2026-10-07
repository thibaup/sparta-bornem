import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil
import pathlib
import config
import utils
import copy

# Attempt to import Pillow for image preview
try:
    from PIL import Image, ImageTk
    HAS_PILLOW_BESTUUR = True
except ImportError:
    HAS_PILLOW_BESTUUR = False
    Image = None
    ImageTk = None


class BestuurDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_data=None, callback=None, image_select_title="Selecteer Afbeelding", image_initial_dir=None):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.callback = callback
        self.initial_data = initial_data or {}
        self.result = None
        self.selected_image_source_path = None
        self.image_select_title = image_select_title
        self.image_initial_dir = image_initial_dir

        frame = ttk.Frame(self, padding="15"); frame.pack(expand=True, fill=tk.BOTH)
        row_index = 0
        ttk.Label(frame, text="Naam:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=3)
        self.name_entry = ttk.Entry(frame, width=45)
        self.name_entry.grid(row=row_index, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        self.name_entry.insert(0, self.initial_data.get('name') or '')
        row_index += 1
        ttk.Label(frame, text="Rol:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=3)
        self.role_entry = ttk.Entry(frame, width=45)
        self.role_entry.grid(row=row_index, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        self.role_entry.insert(0, self.initial_data.get('role') or '')
        row_index += 1
        ttk.Label(frame, text="Adres:").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=3)
        self.address_entry = ttk.Entry(frame, width=45)
        self.address_entry.grid(row=row_index, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        self.address_entry.insert(0, self.initial_data.get('address') or '')
        row_index += 1
        ttk.Label(frame, text="Tel/Gsm:").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=3)
        self.phone_entry = ttk.Entry(frame, width=45)
        self.phone_entry.grid(row=row_index, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        self.phone_entry.insert(0, self.initial_data.get('phone') or '')
        row_index += 1
        ttk.Label(frame, text="E-mail:").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=3)
        self.email_entry = ttk.Entry(frame, width=45)
        self.email_entry.grid(row=row_index, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        self.email_entry.insert(0, self.initial_data.get('email') or '')
        row_index += 1
        ttk.Label(frame, text="Afbeelding:").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=3)
        self.img_src_display_var = tk.StringVar()
        current_image_web_path = self.initial_data.get('imageSrc') or ''
        self.img_src_display_var.set(current_image_web_path)
        img_entry = ttk.Entry(frame, textvariable=self.img_src_display_var, width=40, state="readonly")
        img_entry.grid(row=row_index, column=1, sticky="ew", padx=5, pady=3)
        browse_button = ttk.Button(frame, text="Bladeren...", command=self._browse_image)
        browse_button.grid(row=row_index, column=2, sticky="w", padx=5, pady=3)
        row_index += 1
        frame.columnconfigure(1, weight=1)
        button_frame = ttk.Frame(frame); button_frame.grid(row=row_index, column=0, columnspan=3, pady=(15, 0), sticky=tk.E)
        ok_button = ttk.Button(button_frame, text="OK", command=self.on_ok); ok_button.pack(side=tk.RIGHT, padx=(5, 0))
        cancel_button = ttk.Button(button_frame, text="Annuleren", command=self.on_cancel); cancel_button.pack(side=tk.RIGHT)
        self.grab_set(); self.protocol("WM_DELETE_WINDOW", self.on_cancel); self.bind("<Escape>", self.on_cancel)
        self.name_entry.focus_set()
        self.wait_window()

    def _browse_image(self):
        filetypes = (("Afbeeldingsbestanden", "*.jpg *.jpeg *.png *.gif *.webp *.bmp *.svg"), ("Alle bestanden", "*.*"))
        initial_dir_config = self.image_initial_dir if self.image_initial_dir else getattr(config, 'BESTUUR_IMAGE_DEST_DIR_ABSOLUTE', config.APP_BASE_DIR)
        initial_dir = initial_dir_config if os.path.isdir(initial_dir_config) else config.APP_BASE_DIR
        source_path = filedialog.askopenfilename(title=self.image_select_title, filetypes=filetypes, initialdir=initial_dir)
        if source_path:
            self.selected_image_source_path = source_path
            filename = os.path.basename(source_path)
            self.img_src_display_var.set(f"[Nieuw geselecteerd: {filename}]")


    def on_ok(self, event=None):
        name = self.name_entry.get().strip()
        role = self.role_entry.get().strip()
        address = self.address_entry.get().strip()
        phone = self.phone_entry.get().strip()
        email = self.email_entry.get().strip()

        if not name:
            messagebox.showwarning("Invoer Vereist", "Naam mag niet leeg zijn.", parent=self)
            self.name_entry.focus_set(); return
        if not role:
            messagebox.showwarning("Invoer Vereist", "Rol mag niet leeg zijn.", parent=self)
            self.role_entry.focus_set(); return

        current_web_image_path = self.initial_data.get('imageSrc') # Path from JSON
        final_web_image_path_to_save = current_web_image_path # Default to existing
        os_path_of_newly_selected_image = None

        if self.selected_image_source_path: # User browsed for a new image
            os_path_of_newly_selected_image = self.selected_image_source_path
            # final_web_image_path_to_save will be determined after copy in _process_edit
            # For now, we pass the OS path to indicate a new file needs processing.

        image_alt_text = self.initial_data.get('imageAlt', f"Foto {name}")
        if name != self.initial_data.get('name'): # If name changed, update alt text
            image_alt_text = f"Foto {name}"


        self.result = {
            'name': name,
            'role': role,
            'address': address or None,
            'phone': phone or None,
            'email': email or None,
            'imageSrc': final_web_image_path_to_save, # This might be None if a new img is selected
            'imageAlt': image_alt_text,
            '_os_path_of_newly_selected_image': os_path_of_newly_selected_image # Pass temp OS path
        }

        if self.callback:
            # Pass original index for editing, or None for adding
            original_index = self.initial_data.get('original_index')
            # tree_iid is not strictly needed by callback if using index, but good for consistency
            tree_iid = self.initial_data.get('iid')
            if self.callback(self.result, original_index, tree_iid) is False:
                return
        self.destroy()

    def on_cancel(self, event=None):
        self.destroy()


class BestuurTab:
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance
        # This will store the entire loaded JSON structure, e.g.
        # {"pageTitle": "...", "mainHeading": "...", "boardMembers": []}
        self.full_bestuur_data = {}
        self.bestuur_file_loaded = False
        self._preview_photo = None # For image preview reference (Tkinter PhotoImage)
        self._create_widgets()
        self._load_bestuur()

    def _create_widgets(self):
        self.parent.grid_rowconfigure(1, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        top_frame = ttk.Frame(self.parent)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        self.refresh_button = ttk.Button(top_frame, text="Herlaad Bestuur (JSON)", command=self._load_bestuur)
        self.refresh_button.pack(side=tk.LEFT, padx=5)
        self.save_button = ttk.Button(top_frame, text="Bestuur Opslaan (JSON)", command=self._save_bestuur, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)

        pw_main = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        pw_main.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        tree_frame = ttk.Frame(pw_main, padding=5)
        tree_frame.grid_rowconfigure(0, weight=1); tree_frame.grid_columnconfigure(0, weight=1)
        cols = ('name', 'role', 'email', 'phone')
        self.bestuur_tree = ttk.Treeview(tree_frame, columns=cols, show='headings', selectmode='browse')
        self.bestuur_tree.heading('name', text='Naam'); self.bestuur_tree.column('name', width=180, anchor=tk.W, stretch=tk.YES)
        self.bestuur_tree.heading('role', text='Rol'); self.bestuur_tree.column('role', width=150, anchor=tk.W, stretch=tk.YES)
        self.bestuur_tree.heading('email', text='E-mail'); self.bestuur_tree.column('email', width=200, anchor=tk.W, stretch=tk.YES)
        self.bestuur_tree.heading('phone', text='Tel/Gsm'); self.bestuur_tree.column('phone', width=120, anchor=tk.W, stretch=tk.NO)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.bestuur_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.bestuur_tree.xview)
        self.bestuur_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.bestuur_tree.grid(row=0, column=0, sticky="nsew"); vsb.grid(row=0, column=1, sticky="ns"); hsb.grid(row=1, column=0, sticky="ew")
        self.bestuur_tree.bind("<<TreeviewSelect>>", self._on_bestuur_selected)
        self.bestuur_tree.bind("<Double-1>", self._on_bestuur_double_click)
        self.bestuur_tree.bind("<ButtonPress-1>", self._on_bestuur_drag_start, add="+")
        self.bestuur_tree.bind("<B1-Motion>", self._on_bestuur_drag_motion, add="+")
        self.bestuur_tree.bind("<ButtonRelease-1>", self._on_bestuur_drag_drop, add="+")

        self._drag_iid = None
        self._drag_start_index = None


        pw_main.add(tree_frame, weight=2)

        action_preview_frame = ttk.Frame(pw_main, padding=5)
        action_preview_frame.grid_rowconfigure(1, weight=1); action_preview_frame.grid_columnconfigure(0, weight=1)
        action_frame = ttk.Labelframe(action_preview_frame, text=" Acties ", padding=10)
        action_frame.grid(row=0, column=0, sticky="new"); action_frame.columnconfigure(0, weight=1)
        self.add_button = ttk.Button(action_frame, text="Nieuw Bestuurslid Toevoegen...", command=self._add_dialog, state=tk.DISABLED)
        self.add_button.grid(row=0, column=0, sticky="ew", padx=5, pady=3)
        self.edit_button = ttk.Button(action_frame, text="Geselecteerde Bewerken...", command=self._edit_dialog, state=tk.DISABLED)
        self.edit_button.grid(row=1, column=0, sticky="ew", padx=5, pady=3)
        self.delete_button = ttk.Button(action_frame, text="Geselecteerde Verwijderen", command=self._delete_member, state=tk.DISABLED)
        self.delete_button.grid(row=2, column=0, sticky="ew", padx=5, pady=3)
        preview_frame = ttk.Labelframe(action_preview_frame, text=" Voorvertoning Afbeelding ", padding=10)
        preview_frame.grid(row=1, column=0, sticky="nsew", pady=(10,0)); preview_frame.grid_rowconfigure(0, weight=1); preview_frame.grid_columnconfigure(0, weight=1)
        preview_outer = ttk.Frame(preview_frame, width=config.IMAGE_PREVIEW_MAX_WIDTH+10, height=config.IMAGE_PREVIEW_MAX_HEIGHT+10)
        preview_outer.grid(row=0, column=0, sticky="nsew"); preview_outer.grid_propagate(False); preview_outer.grid_rowconfigure(0, weight=1); preview_outer.grid_columnconfigure(0, weight=1)
        self.preview_label = ttk.Label(preview_outer, text="Selecteer bestuurslid\nvoor afbeelding", relief=tk.GROOVE, anchor=tk.CENTER, background="lightgrey", justify=tk.CENTER)
        self.preview_label.grid(sticky="nsew", padx=5, pady=5)
        pw_main.add(action_preview_frame, weight=1)

    def _load_bestuur(self):
        if not utils.confirm_discard_changes(self):
            return
        self.app.set_status("Laden bestuur data (JSON)..."); self.app.root.update_idletasks()

        json_filepath = config.BESTUUR_JSON_FILE_PATH # Ensure this is defined in config.py
        if not os.path.exists(json_filepath):
            messagebox.showerror("Bestand Niet Gevonden", f"Bestuur JSON-bestand niet gevonden:\n{json_filepath}", parent=self.app.root)
            self.app.set_status("Fout: Bestuur JSON niet gevonden.", is_error=True)
            self.bestuur_file_loaded = False
        else:
            loaded_data, error_msg = utils.bestuur_load_json_data(json_filepath)
            if error_msg:
                messagebox.showerror("Laad Fout", f"Fout bij laden bestuur JSON:\n{error_msg}", parent=self.app.root)
                self.app.set_status(f"Fout bij laden bestuur JSON: {error_msg}", is_error=True)
                self.bestuur_file_loaded = False
            else:
                self.full_bestuur_data = loaded_data if loaded_data else {"pageTitle": "Bestuur", "mainHeading": "Bestuur", "boardMembers": []}
                # Ensure boardMembers key exists as a list
                self.full_bestuur_data.setdefault("boardMembers", [])
                self.bestuur_file_loaded = True
                self.app.set_status(f"{len(self.full_bestuur_data.get('boardMembers',[]))} bestuursleden geladen.", duration_ms=5000)

        self._populate_treeview()
        self._update_ui_states()
        if self.bestuur_file_loaded:
            utils.remember_editor_state(self, self.full_bestuur_data)
        return self.bestuur_file_loaded

    def has_unsaved_changes(self):
        return utils.editor_state_changed(self, self.full_bestuur_data)

    def _populate_treeview(self):
        self.bestuur_tree.delete(*self.bestuur_tree.get_children())
        self._update_preview(None)

        board_members_list = self.full_bestuur_data.get("boardMembers", [])
        for index, member in enumerate(board_members_list):
            iid = str(index)
            values = (
                member.get('name', ''), member.get('role', ''),
                member.get('email', ''), member.get('phone', '')
            )
            self.bestuur_tree.insert('', tk.END, iid=iid, values=values)
        self._on_bestuur_selected() # Update button states based on (no) selection

    def _update_ui_states(self):
        state = tk.NORMAL if self.bestuur_file_loaded else tk.DISABLED
        self.save_button.config(state=state)
        self.add_button.config(state=state)
        # Edit/delete state depends on selection, handled in _on_bestuur_selected

    def _on_bestuur_selected(self, event=None):
        if not self.bestuur_file_loaded:
            self.edit_button.config(state=tk.DISABLED)
            self.delete_button.config(state=tk.DISABLED)
            return
        selected_items = self.bestuur_tree.selection()
        if not selected_items:
            self.edit_button.config(state=tk.DISABLED)
            self.delete_button.config(state=tk.DISABLED)
            self._update_preview(None)
            return

        iid = selected_items[0]
        try:
             index = int(iid)
             board_members_list = self.full_bestuur_data.get("boardMembers", [])
             if 0 <= index < len(board_members_list):
                 member_data = board_members_list[index]
                 self.edit_button.config(state=tk.NORMAL)
                 self.delete_button.config(state=tk.NORMAL)
                 self._update_preview(member_data)
             else: # Index out of bounds after data change but before tree refresh
                 self.edit_button.config(state=tk.DISABLED); self.delete_button.config(state=tk.DISABLED); self._update_preview(None)
        except (ValueError, IndexError) as e:
             print(f"Error finding bestuur data for selection: iid='{iid}', Error='{e}'")
             self.edit_button.config(state=tk.DISABLED); self.delete_button.config(state=tk.DISABLED); self._update_preview(None)

    def _on_bestuur_drag_start(self, event):
        if not self.bestuur_file_loaded:
            return
        iid = self.bestuur_tree.identify_row(event.y)
        self._drag_iid = iid if iid else None
        self._drag_start_index = self.bestuur_tree.index(iid) if iid else None

    def _on_bestuur_drag_motion(self, event):
        if not self._drag_iid:
            return
        target_iid = self.bestuur_tree.identify_row(event.y)
        if target_iid:
            target_index = self.bestuur_tree.index(target_iid)
            if target_index != self.bestuur_tree.index(self._drag_iid):
                self.bestuur_tree.move(self._drag_iid, "", target_index)
        else:
            self.bestuur_tree.move(self._drag_iid, "", "end")

    def _on_bestuur_drag_drop(self, event):
        if not self._drag_iid or self._drag_start_index is None:
            self._drag_iid = None
            self._drag_start_index = None
            return
        final_index = self.bestuur_tree.index(self._drag_iid)
        if final_index != self._drag_start_index:
            lst = self.full_bestuur_data.get("boardMembers", [])
            if 0 <= self._drag_start_index < len(lst):
                item = lst.pop(self._drag_start_index)
                insert_at = final_index if final_index <= len(lst) else len(lst)
                if insert_at < 0:
                    insert_at = 0
                lst.insert(insert_at, item)
                self._populate_treeview()
                new_iid = str(insert_at)
                if self.bestuur_tree.exists(new_iid):
                    self.bestuur_tree.selection_set(new_iid)
                    self.bestuur_tree.focus(new_iid)
                    self.bestuur_tree.see(new_iid)
                    self._on_bestuur_selected()
                self.app.set_status("Volgorde aangepast (nog niet opgeslagen).", duration_ms=4000)
        self._drag_iid = None
        self._drag_start_index = None


    def _on_bestuur_double_click(self, event=None):
        if self.edit_button['state'] == tk.NORMAL: self._edit_dialog()

    def _update_preview(self, member_data):
         if member_data and member_data.get('imageSrc'): # field from JSON is 'imageSrc'
             img_web_path = member_data['imageSrc']
             # Convert web path to absolute OS path for local display
             if img_web_path.startswith('/'): img_web_path = img_web_path[1:] # Remove leading slash for os.path.join
             img_abs_path = os.path.join(config.APP_BASE_DIR, img_web_path)

             if os.path.isfile(img_abs_path):
                 try:
                     if HAS_PILLOW_BESTUUR and Image and ImageTk:
                         with Image.open(img_abs_path) as img:
                             img.thumbnail((config.IMAGE_PREVIEW_MAX_WIDTH, config.IMAGE_PREVIEW_MAX_HEIGHT))
                             self._preview_photo = ImageTk.PhotoImage(img)
                             self.preview_label.config(image=self._preview_photo, text="")
                             return
                     # Fallback if Pillow not available or failed (Tkinter PhotoImage has limited support)
                     elif not HAS_PILLOW_BESTUUR and img_abs_path.lower().endswith(('.png', '.gif')): # Tkinter supports fewer types
                         self._preview_photo = tk.PhotoImage(file=img_abs_path)
                         # Basic resize check (no actual resizing with tk.PhotoImage)
                         if self._preview_photo.width() > config.IMAGE_PREVIEW_MAX_WIDTH or \
                            self._preview_photo.height() > config.IMAGE_PREVIEW_MAX_HEIGHT:
                              self.preview_label.config(image='', text=f"Preview N/B\n(Afbeelding te groot)\n{os.path.basename(img_web_path)}")
                         else:
                             self.preview_label.config(image=self._preview_photo, text="")
                         return
                     else:
                         self.preview_label.config(image='', text=f"Preview N/B\n(Formaat niet ondersteund\nzonder Pillow)\n{os.path.basename(img_web_path)}")
                     return
                 except Exception as e:
                     print(f"Error loading preview for {img_abs_path}: {e}")
                     self.preview_label.config(image='', text=f"Fout laden preview\n{os.path.basename(img_web_path)}")
                     return
             else:
                  self.preview_label.config(image='', text=f"Afbeeldingsbestand\nniet gevonden:\n{os.path.basename(img_web_path)}")
         else: # No member_data or no imageSrc
             self._preview_photo = None # Clear reference
             self.preview_label.config(image='', text="Selecteer bestuurslid\nvoor afbeelding")

    def _add_dialog(self):
        if not self.bestuur_file_loaded: return
        BestuurDialog(self.app.root, "Nieuw Bestuurslid", callback=self._process_edit)

    def _edit_dialog(self):
        if not self.bestuur_file_loaded: return
        selected_items = self.bestuur_tree.selection()
        if not selected_items: return
        iid = selected_items[0]
        try:
            index = int(iid)
            board_members_list = self.full_bestuur_data.get("boardMembers", [])
            if 0 <= index < len(board_members_list):
                initial_data_for_dialog = copy.deepcopy(board_members_list[index])
                initial_data_for_dialog['original_index'] = index
                initial_data_for_dialog['iid'] = iid
                BestuurDialog(self.app.root, "Bestuurslid Bewerken", initial_data_for_dialog, callback=self._process_edit)
            else: raise IndexError("Index out of bounds for boardMembers list.")
        except (ValueError, IndexError) as e:
             messagebox.showerror("Fout", f"Kon data niet laden voor bewerken: {e}", parent=self.app.root)

    def _process_edit(self, result_data_from_dialog, original_index=None, tree_iid=None): # original_index now passed correctly
        if result_data_from_dialog is None: return # Dialog cancelled

        os_path_of_newly_selected_image = result_data_from_dialog.pop('_os_path_of_newly_selected_image', None)
        final_web_image_path = result_data_from_dialog.get('imageSrc') # Path from dialog (could be old or None)

        if os_path_of_newly_selected_image: # A new image was selected via browse
            # Define target directory and web base path from config
            target_dir_abs = getattr(config, 'BESTUUR_IMAGE_DEST_DIR_ABSOLUTE', os.path.join(config.APP_BASE_DIR, 'images', 'personen', 'bestuur'))
            target_href_base = getattr(config, 'BESTUUR_IMAGE_HREF_BASE', '/images/personen/bestuur/') # Web path

            filename = os.path.basename(os_path_of_newly_selected_image)
            # Optionally sanitize filename here
            # filename = config.sanitize_filename(filename)

            dest_path_abs = os.path.join(target_dir_abs, filename)
            try:
                os.makedirs(target_dir_abs, exist_ok=True)
                dest_path_abs = utils.copy_new_asset(os_path_of_newly_selected_image, dest_path_abs, owner=self)
                filename = os.path.basename(dest_path_abs)

                # Construct the web-relative path to store in JSON
                final_web_image_path = str(pathlib.PurePosixPath(target_href_base) / filename).replace('\\', '/')
            except Exception as e:
                messagebox.showerror("Afbeelding Kopieer Fout", f"Kon afbeelding niet kopiëren naar '{target_dir_abs}'.\nFout: {e}", parent=self.app.root)
                self.app.set_status(f"Fout bij kopiëren afbeelding: {e}", is_error=True)
                return False
        elif not final_web_image_path: # No existing image and no new one selected
            final_web_image_path = getattr(config, 'DEFAULT_BESTUUR_IMAGE_SRC', '/images/personen/trainer-leeg.png')


        # Update the imageSrc in the result data for JSON
        result_data_from_dialog['imageSrc'] = final_web_image_path

        # The JSON structure for a board member
        member_data_for_json = {
            'name': result_data_from_dialog['name'],
            'role': result_data_from_dialog['role'],
            'imageSrc': result_data_from_dialog['imageSrc'], # This is now the web path
            'imageAlt': result_data_from_dialog.get('imageAlt', f"Foto {result_data_from_dialog['name']}"),
            'address': result_data_from_dialog.get('address'),
            'phone': result_data_from_dialog.get('phone'),
            'email': result_data_from_dialog.get('email')
        }

        board_members_list = self.full_bestuur_data.setdefault("boardMembers", [])
        is_edit = original_index is not None

        if is_edit:
             if 0 <= original_index < len(board_members_list):
                  board_members_list[original_index] = member_data_for_json
                  status_msg = "Bestuurslid bijgewerkt."
             else: # Should not happen if iid/index logic is correct
                  messagebox.showerror("Fout", "Interne indexfout bij bijwerken.", parent=self.app.root)
                  return False
        else: # Adding new
            board_members_list.append(member_data_for_json)
            status_msg = "Bestuurslid toegevoegd."

        self._populate_treeview()
        self.app.set_status(status_msg + " (Wijzigingen nog niet opgeslagen)", duration_ms=4000)

        # Try re-selecting the added/edited item
        new_index_to_select = original_index if is_edit else len(board_members_list) - 1
        new_iid_to_select = str(new_index_to_select)
        if self.bestuur_tree.exists(new_iid_to_select):
            self.bestuur_tree.selection_set(new_iid_to_select)
            self.bestuur_tree.focus(new_iid_to_select)
            self.bestuur_tree.see(new_iid_to_select)
            self._on_bestuur_selected() # Update preview for the new selection


    def _delete_member(self):
        if not self.bestuur_file_loaded: return
        selected_items = self.bestuur_tree.selection()
        if not selected_items: return
        iid = selected_items[0]

        try:
            index = int(iid)
            board_members_list = self.full_bestuur_data.get("boardMembers", [])
            if 0 <= index < len(board_members_list):
                member_name = board_members_list[index].get('name', 'Onbekend')
                if messagebox.askyesno("Verwijderen Bevestigen",
                                       f"Bestuurslid '{member_name}' verwijderen?",
                                       icon='warning', parent=self.app.root):
                    del board_members_list[index]
                    # No need to directly update self.full_bestuur_data['boardMembers']
                    # as we deleted from the list obtained by reference.
                    self._populate_treeview()
                    self.app.set_status(f"Bestuurslid '{member_name}' verwijderd (nog niet opgeslagen).", duration_ms=4000)
            else: raise IndexError("Index out of bounds for deletion.")
        except (ValueError, IndexError) as e:
             messagebox.showerror("Fout", f"Kon bestuurslid niet vinden om te verwijderen: {e}", parent=self.app.root)


    def _save_bestuur(self):
        if not self.bestuur_file_loaded:
            messagebox.showwarning("Data niet geladen", "Kan niet opslaan, bestuur data is niet geladen.", parent=self.app.root)
            return

        # The self.full_bestuur_data should be up-to-date due to in-place modifications of the list
        data_to_save = copy.deepcopy(self.full_bestuur_data) # Save a copy

        # Ensure the main keys are present, even if boardMembers is empty
        data_to_save.setdefault("pageTitle", "Bestuur - Atletiekclub Sparta Bornem")
        data_to_save.setdefault("mainHeading", "Bestuur")
        data_to_save.setdefault("boardMembers", [])


        json_filepath = config.BESTUUR_JSON_FILE_PATH
        filename_short = os.path.basename(json_filepath)
        self.app.set_status(f"Bestuur opslaan naar {filename_short}..."); self.app.root.update_idletasks()

        error_msg = utils.bestuur_save_json_data(json_filepath, data_to_save)

        if not error_msg: # Success if error_msg is None
            utils.remember_editor_state(self, self.full_bestuur_data)
            self.app.set_status(f"Bestuur succesvol opgeslagen naar {filename_short}.", duration_ms=5000)
            # self.full_bestuur_data is already up-to-date, but making a fresh copy from saved data is safer
            # self.full_bestuur_data = copy.deepcopy(data_to_save) # This was done before save
        else:
            self.app.set_status(f"Fout bij opslaan bestuur JSON: {error_msg}", is_error=True)
            messagebox.showerror("Opslag Fout", f"Kon bestuur niet opslaan naar '{json_filepath}'.\nFout: {error_msg}", parent=self.app.root)

class JuryTab:
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance
        self.full_jury_data = {}
        self.jury_file_loaded = False
        self._preview_photo = None
        self._create_widgets()
        self._load_jury()

    def _create_widgets(self):
        self.parent.grid_rowconfigure(1, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)
        top_frame = ttk.Frame(self.parent)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        self.refresh_button = ttk.Button(top_frame, text="Herlaad Jury (JSON)", command=self._load_jury)
        self.refresh_button.pack(side=tk.LEFT, padx=5)
        self.save_button = ttk.Button(top_frame, text="Jury Opslaan (JSON)", command=self._save_jury, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)
        pw_main = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        pw_main.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        tree_frame = ttk.Frame(pw_main, padding=5)
        tree_frame.grid_rowconfigure(0, weight=1); tree_frame.grid_columnconfigure(0, weight=1)
        cols = ('name', 'role', 'email', 'phone')
        self.jury_tree = ttk.Treeview(tree_frame, columns=cols, show='headings', selectmode='browse')
        self.jury_tree.heading('name', text='Naam'); self.jury_tree.column('name', width=180, anchor=tk.W, stretch=tk.YES)
        self.jury_tree.heading('role', text='Rol'); self.jury_tree.column('role', width=150, anchor=tk.W, stretch=tk.YES)
        self.jury_tree.heading('email', text='E-mail'); self.jury_tree.column('email', width=200, anchor=tk.W, stretch=tk.YES)
        self.jury_tree.heading('phone', text='Tel/Gsm'); self.jury_tree.column('phone', width=120, anchor=tk.W, stretch=tk.NO)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.jury_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.jury_tree.xview)
        self.jury_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.jury_tree.grid(row=0, column=0, sticky="nsew"); vsb.grid(row=0, column=1, sticky="ns"); hsb.grid(row=1, column=0, sticky="ew")
        self.jury_tree.bind("<<TreeviewSelect>>", self._on_jury_selected)
        self.jury_tree.bind("<Double-1>", self._on_jury_double_click)
        self.jury_tree.bind("<ButtonPress-1>", self._on_jury_drag_start, add="+")
        self.jury_tree.bind("<B1-Motion>", self._on_jury_drag_motion, add="+")
        self.jury_tree.bind("<ButtonRelease-1>", self._on_jury_drag_drop, add="+")

        self._drag_iid = None
        self._drag_start_index = None


        pw_main.add(tree_frame, weight=2)
        action_preview_frame = ttk.Frame(pw_main, padding=5)
        action_preview_frame.grid_rowconfigure(1, weight=1); action_preview_frame.grid_columnconfigure(0, weight=1)
        action_frame = ttk.Labelframe(action_preview_frame, text=" Acties ", padding=10)
        action_frame.grid(row=0, column=0, sticky="new"); action_frame.columnconfigure(0, weight=1)
        self.add_button = ttk.Button(action_frame, text="Nieuw Jurylid Toevoegen...", command=self._add_dialog, state=tk.DISABLED)
        self.add_button.grid(row=0, column=0, sticky="ew", padx=5, pady=3)
        self.edit_button = ttk.Button(action_frame, text="Geselecteerde Bewerken...", command=self._edit_dialog, state=tk.DISABLED)
        self.edit_button.grid(row=1, column=0, sticky="ew", padx=5, pady=3)
        self.delete_button = ttk.Button(action_frame, text="Geselecteerde Verwijderen", command=self._delete_member, state=tk.DISABLED)
        self.delete_button.grid(row=2, column=0, sticky="ew", padx=5, pady=3)
        preview_frame = ttk.Labelframe(action_preview_frame, text=" Voorvertoning Afbeelding ", padding=10)
        preview_frame.grid(row=1, column=0, sticky="nsew", pady=(10,0)); preview_frame.grid_rowconfigure(0, weight=1); preview_frame.grid_columnconfigure(0, weight=1)
        preview_outer = ttk.Frame(preview_frame, width=getattr(config, 'IMAGE_PREVIEW_MAX_WIDTH', 150)+10, height=getattr(config, 'IMAGE_PREVIEW_MAX_HEIGHT', 150)+10)
        preview_outer.grid(row=0, column=0, sticky="nsew"); preview_outer.grid_propagate(False); preview_outer.grid_rowconfigure(0, weight=1); preview_outer.grid_columnconfigure(0, weight=1)
        self.preview_label = ttk.Label(preview_outer, text="Selecteer jurylid\nvoor afbeelding", relief=tk.GROOVE, anchor=tk.CENTER, background="lightgrey", justify=tk.CENTER)
        self.preview_label.grid(sticky="nsew", padx=5, pady=5)
        pw_main.add(action_preview_frame, weight=1)

    def _load_jury(self):
        if not utils.confirm_discard_changes(self):
            return
        self.app.set_status("Laden jury data (JSON)..."); self.app.root.update_idletasks()
        json_filepath = config.JURY_JSON_FILE_PATH
        if not os.path.exists(json_filepath):
            messagebox.showerror("Bestand Niet Gevonden", f"Jury JSON-bestand niet gevonden:\n{json_filepath}", parent=self.app.root)
            self.app.set_status("Fout: Jury JSON niet gevonden.", is_error=True)
            self.jury_file_loaded = False
        else:
            loaded_data, error_msg = utils.jury_load_json_data(json_filepath)
            if error_msg:
                messagebox.showerror("Laad Fout", f"Fout bij laden jury JSON:\n{error_msg}", parent=self.app.root)
                self.app.set_status(f"Fout bij laden jury JSON: {error_msg}", is_error=True)
                self.jury_file_loaded = False
            else:
                self.full_jury_data = loaded_data if loaded_data else {"pageTitle": "Juryleden", "mainHeading": "Juryleden", "juryMembers": []}
                self.full_jury_data.setdefault("juryMembers", [])
                self.jury_file_loaded = True
                self.app.set_status(f"{len(self.full_jury_data.get('juryMembers',[]))} juryleden geladen.", duration_ms=5000)
        self._populate_treeview()
        self._update_ui_states()
        if self.jury_file_loaded:
            utils.remember_editor_state(self, self.full_jury_data)
        return self.jury_file_loaded

    def has_unsaved_changes(self):
        return utils.editor_state_changed(self, self.full_jury_data)

    def _populate_treeview(self):
        self.jury_tree.delete(*self.jury_tree.get_children())
        self._update_preview(None)
        jury_members_list = self.full_jury_data.get("juryMembers", [])
        for index, member in enumerate(jury_members_list):
            iid = str(index)
            values = (member.get('name', ''), member.get('role', ''), member.get('email', ''), member.get('phone', ''))
            self.jury_tree.insert('', tk.END, iid=iid, values=values)
        self._on_jury_selected()

    def _update_ui_states(self):
        state = tk.NORMAL if self.jury_file_loaded else tk.DISABLED
        self.save_button.config(state=state)
        self.add_button.config(state=state)

    def _on_jury_selected(self, event=None):
        if not self.jury_file_loaded:
            self.edit_button.config(state=tk.DISABLED)
            self.delete_button.config(state=tk.DISABLED)
            return
        selected_items = self.jury_tree.selection()
        if not selected_items:
            self.edit_button.config(state=tk.DISABLED)
            self.delete_button.config(state=tk.DISABLED)
            self._update_preview(None)
            return
        iid = selected_items[0]
        try:
            index = int(iid)
            jury_members_list = self.full_jury_data.get("juryMembers", [])
            if 0 <= index < len(jury_members_list):
                member_data = jury_members_list[index]
                self.edit_button.config(state=tk.NORMAL)
                self.delete_button.config(state=tk.NORMAL)
                self._update_preview(member_data)
            else:
                self.edit_button.config(state=tk.DISABLED); self.delete_button.config(state=tk.DISABLED); self._update_preview(None)
        except (ValueError, IndexError):
            self.edit_button.config(state=tk.DISABLED); self.delete_button.config(state=tk.DISABLED); self._update_preview(None)

    def _on_jury_drag_start(self, event):
        if not self.jury_file_loaded:
            return
        iid = self.jury_tree.identify_row(event.y)
        self._drag_iid = iid if iid else None
        self._drag_start_index = self.jury_tree.index(iid) if iid else None

    def _on_jury_drag_motion(self, event):
        if not self._drag_iid:
            return
        target_iid = self.jury_tree.identify_row(event.y)
        if target_iid:
            target_index = self.jury_tree.index(target_iid)
            if target_index != self.jury_tree.index(self._drag_iid):
                self.jury_tree.move(self._drag_iid, "", target_index)
        else:
            self.jury_tree.move(self._drag_iid, "", "end")

    def _on_jury_drag_drop(self, event):
        if not self._drag_iid or self._drag_start_index is None:
            self._drag_iid = None
            self._drag_start_index = None
            return
        final_index = self.jury_tree.index(self._drag_iid)
        if final_index != self._drag_start_index:
            lst = self.full_jury_data.get("juryMembers", [])
            if 0 <= self._drag_start_index < len(lst):
                item = lst.pop(self._drag_start_index)
                insert_at = final_index if final_index <= len(lst) else len(lst)
                if insert_at < 0:
                    insert_at = 0
                lst.insert(insert_at, item)
                self._populate_treeview()
                new_iid = str(insert_at)
                if self.jury_tree.exists(new_iid):
                    self.jury_tree.selection_set(new_iid)
                    self.jury_tree.focus(new_iid)
                    self.jury_tree.see(new_iid)
                    self._on_jury_selected()
                self.app.set_status("Volgorde aangepast (nog niet opgeslagen).", duration_ms=4000)
        self._drag_iid = None
        self._drag_start_index = None


    def _on_jury_double_click(self, event=None):
        if self.edit_button['state'] == tk.NORMAL:
            self._edit_dialog()

    def _update_preview(self, member_data):
        if member_data and member_data.get('imageSrc'):
            img_web_path = member_data['imageSrc']
            if img_web_path.startswith('/'):
                img_web_path = img_web_path[1:]
            img_abs_path = os.path.join(config.APP_BASE_DIR, img_web_path)
            if os.path.isfile(img_abs_path):
                try:
                    if HAS_PILLOW_BESTUUR and Image and ImageTk:
                        with Image.open(img_abs_path) as img:
                            img.thumbnail((getattr(config, 'IMAGE_PREVIEW_MAX_WIDTH', 150), getattr(config, 'IMAGE_PREVIEW_MAX_HEIGHT', 150)))
                            self._preview_photo = ImageTk.PhotoImage(img)
                            self.preview_label.config(image=self._preview_photo, text="")
                            return
                    elif not HAS_PILLOW_BESTUUR and img_abs_path.lower().endswith(('.png', '.gif')):
                        self._preview_photo = tk.PhotoImage(file=img_abs_path)
                        if self._preview_photo.width() > getattr(config, 'IMAGE_PREVIEW_MAX_WIDTH', 150) or self._preview_photo.height() > getattr(config, 'IMAGE_PREVIEW_MAX_HEIGHT', 150):
                            self.preview_label.config(image='', text=f"Preview N/B\n(Afbeelding te groot)\n{os.path.basename(img_web_path)}")
                        else:
                            self.preview_label.config(image=self._preview_photo, text="")
                        return
                    else:
                        self.preview_label.config(image='', text=f"Preview N/B\n(Formaat niet ondersteund)\n{os.path.basename(img_web_path)}")
                    return
                except Exception:
                    self.preview_label.config(image='', text=f"Fout laden preview\n{os.path.basename(img_web_path)}")
                    return
            else:
                self.preview_label.config(image='', text=f"Afbeeldingsbestand\nniet gevonden:\n{os.path.basename(img_web_path)}")
        else:
            self._preview_photo = None
            self.preview_label.config(image='', text="Selecteer jurylid\nvoor afbeelding")

    def _add_dialog(self):
        if not self.jury_file_loaded:
            return
        BestuurDialog(
            self.app.root,
            "Nieuw Jurylid",
            callback=self._process_edit,
            image_select_title="Selecteer Jurylid Afbeelding",
            image_initial_dir=getattr(config, 'JURY_IMAGE_DEST_DIR_ABSOLUTE', config.APP_BASE_DIR)
        )

    def _edit_dialog(self):
        if not self.jury_file_loaded:
            return
        selected_items = self.jury_tree.selection()
        if not selected_items:
            return
        iid = selected_items[0]
        try:
            index = int(iid)
            jury_members_list = self.full_jury_data.get("juryMembers", [])
            if 0 <= index < len(jury_members_list):
                initial_data_for_dialog = copy.deepcopy(jury_members_list[index])
                initial_data_for_dialog['original_index'] = index
                initial_data_for_dialog['iid'] = iid
                BestuurDialog(
                    self.app.root,
                    "Jurylid Bewerken",
                    initial_data_for_dialog,
                    callback=self._process_edit,
                    image_select_title="Selecteer Jurylid Afbeelding",
                    image_initial_dir=getattr(config, 'JURY_IMAGE_DEST_DIR_ABSOLUTE', config.APP_BASE_DIR)
                )
            else:
                raise IndexError("Index out of bounds for juryMembers list.")
        except (ValueError, IndexError) as e:
            messagebox.showerror("Fout", f"Kon data niet laden voor bewerken: {e}", parent=self.app.root)




    def _process_edit(self, result_data_from_dialog, original_index=None, tree_iid=None):
        if result_data_from_dialog is None:
            return False
        os_path_of_newly_selected_image = result_data_from_dialog.pop('_os_path_of_newly_selected_image', None)
        final_web_image_path = result_data_from_dialog.get('imageSrc')
        if os_path_of_newly_selected_image:
            target_dir_abs = getattr(config, 'JURY_IMAGE_DEST_DIR_ABSOLUTE', os.path.join(config.APP_BASE_DIR, 'images', 'personen', 'jury'))
            target_href_base = getattr(config, 'JURY_IMAGE_HREF_BASE', '/images/personen/jury/')
            filename = os.path.basename(os_path_of_newly_selected_image)
            dest_path_abs = os.path.join(target_dir_abs, filename)
            try:
                os.makedirs(target_dir_abs, exist_ok=True)
                dest_path_abs = utils.copy_new_asset(os_path_of_newly_selected_image, dest_path_abs, owner=self)
                filename = os.path.basename(dest_path_abs)
                final_web_image_path = str(pathlib.PurePosixPath(target_href_base) / filename).replace('\\', '/')
            except Exception as e:
                messagebox.showerror("Afbeelding Kopieer Fout", f"Kon afbeelding niet kopiëren naar '{target_dir_abs}'.\nFout: {e}", parent=self.app.root)
                self.app.set_status(f"Fout bij kopiëren afbeelding: {e}", is_error=True)
                return False
        elif not final_web_image_path:
            final_web_image_path = getattr(config, 'DEFAULT_JURY_IMAGE_SRC', '/images/personen/trainer-leeg.png')
        result_data_from_dialog['imageSrc'] = final_web_image_path
        member_data_for_json = {
            'name': result_data_from_dialog['name'],
            'role': result_data_from_dialog['role'],
            'imageSrc': result_data_from_dialog['imageSrc'],
            'imageAlt': result_data_from_dialog.get('imageAlt', f"Foto {result_data_from_dialog['name']}"),
            'address': result_data_from_dialog.get('address'),
            'phone': result_data_from_dialog.get('phone'),
            'email': result_data_from_dialog.get('email')
        }
        jury_members_list = self.full_jury_data.setdefault("juryMembers", [])
        is_edit = original_index is not None
        if is_edit:
            if 0 <= original_index < len(jury_members_list):
                jury_members_list[original_index] = member_data_for_json
                status_msg = "Jurylid bijgewerkt."
            else:
                messagebox.showerror("Fout", "Interne indexfout bij bijwerken.", parent=self.app.root)
                return False
        else:
            jury_members_list.append(member_data_for_json)
            status_msg = "Jurylid toegevoegd."
        self._populate_treeview()
        self.app.set_status(status_msg + " (Wijzigingen nog niet opgeslagen)", duration_ms=4000)
        new_index_to_select = original_index if is_edit else len(jury_members_list) - 1
        new_iid_to_select = str(new_index_to_select)
        if self.jury_tree.exists(new_iid_to_select):
            self.jury_tree.selection_set(new_iid_to_select)
            self.jury_tree.focus(new_iid_to_select)
            self.jury_tree.see(new_iid_to_select)
            self._on_jury_selected()

    def _delete_member(self):
        if not self.jury_file_loaded:
            return
        selected_items = self.jury_tree.selection()
        if not selected_items:
            return
        iid = selected_items[0]
        try:
            index = int(iid)
            jury_members_list = self.full_jury_data.get("juryMembers", [])
            if 0 <= index < len(jury_members_list):
                member_name = jury_members_list[index].get('name', 'Onbekend')
                if messagebox.askyesno("Verwijderen Bevestigen", f"Jurylid '{member_name}' verwijderen?", icon='warning', parent=self.app.root):
                    del jury_members_list[index]
                    self._populate_treeview()
                    self.app.set_status(f"Jurylid '{member_name}' verwijderd (nog niet opgeslagen).", duration_ms=4000)
            else:
                raise IndexError("Index out of bounds for deletion.")
        except (ValueError, IndexError) as e:
            messagebox.showerror("Fout", f"Kon jurylid niet vinden om te verwijderen: {e}", parent=self.app.root)

    def _save_jury(self):
        if not self.jury_file_loaded:
            messagebox.showwarning("Data niet geladen", "Kan niet opslaan, jury data is niet geladen.", parent=self.app.root)
            return
        data_to_save = copy.deepcopy(self.full_jury_data)
        data_to_save.setdefault("pageTitle", "Juryleden - Atletiekclub Sparta Bornem")
        data_to_save.setdefault("mainHeading", "Juryleden")
        data_to_save.setdefault("juryMembers", [])
        json_filepath = config.JURY_JSON_FILE_PATH
        filename_short = os.path.basename(json_filepath)
        self.app.set_status(f"Jury opslaan naar {filename_short}..."); self.app.root.update_idletasks()
        error_msg = utils.jury_save_json_data(json_filepath, data_to_save)
        if not error_msg:
            utils.remember_editor_state(self, self.full_jury_data)
            self.app.set_status(f"Jury succesvol opgeslagen naar {filename_short}.", duration_ms=5000)
        else:
            self.app.set_status(f"Fout bij opslaan jury JSON: {error_msg}", is_error=True)
            messagebox.showerror("Opslag Fout", f"Kon jury niet opslaan naar '{json_filepath}'.\nFout: {error_msg}", parent=self.app.root)

class PeopleTabsContainer:
    def __init__(self, bestuur, jury):
        self.bestuur = bestuur
        self.jury = jury

    def has_unsaved_changes(self):
        return self.bestuur.has_unsaved_changes() or self.jury.has_unsaved_changes()

    def reload(self):
        if hasattr(self.bestuur, "_load_bestuur"):
            self.bestuur._load_bestuur()
        if hasattr(self.jury, "_load_jury"):
            self.jury._load_jury()

def create_jury_tab(parent_frame, app_instance):
    if not hasattr(config, 'IMAGE_PREVIEW_MAX_WIDTH'):
        config.IMAGE_PREVIEW_MAX_WIDTH = 150
    if not hasattr(config, 'IMAGE_PREVIEW_MAX_HEIGHT'):
        config.IMAGE_PREVIEW_MAX_HEIGHT = 150
    return JuryTab(parent_frame, app_instance)


def create_bestuur_tab(parent_frame, app_instance):
    # Ensure config has necessary IMAGE_PREVIEW_MAX_WIDTH/HEIGHT or provide defaults
    if not hasattr(config, 'IMAGE_PREVIEW_MAX_WIDTH'):
        config.IMAGE_PREVIEW_MAX_WIDTH = 150 # Example default
    if not hasattr(config, 'IMAGE_PREVIEW_MAX_HEIGHT'):
        config.IMAGE_PREVIEW_MAX_HEIGHT = 150 # Example default
    return BestuurTab(parent_frame, app_instance)


def create_people_tab(parent_frame, app_instance):
    parent_frame.grid_rowconfigure(0, weight=1)
    parent_frame.grid_columnconfigure(0, weight=1)

    nb = ttk.Notebook(parent_frame)
    nb.grid(row=0, column=0, sticky="nsew")

    frame_bestuur = ttk.Frame(nb, padding=10)
    frame_jury = ttk.Frame(nb, padding=10)

    nb.add(frame_bestuur, text="Bestuur")
    nb.add(frame_jury, text="Jury")

    best_tab = create_bestuur_tab(frame_bestuur, app_instance)
    jury_tab = create_jury_tab(frame_jury, app_instance)

    return PeopleTabsContainer(best_tab, jury_tab)

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil
import pathlib
import config
import utils
import copy

# --- ADD Pillow Import Attempt HERE ---
try:
    from PIL import Image, ImageTk
    HAS_PILLOW_SPONSORS = True # Use a local flag for this tab
except ImportError:
    HAS_PILLOW_SPONSORS = False
    Image = None # Define as None if import fails
    ImageTk = None # Define as None if import fails
# --- End Pillow Import ---


class SponsorDialog(tk.Toplevel):
    """Dialog for adding/editing a sponsor."""
    def __init__(self, parent, title, categories, initial_data=None, callback=None):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.callback = callback
        # initial_data now includes 'original_category' if editing
        self.initial_data = initial_data or {}
        self.result = None
        self.selected_image_source_path = None # Store full path of browsed image
        self.categories = categories # List of category names

        frame = ttk.Frame(self, padding="15"); frame.pack(expand=True, fill=tk.BOTH)
        row_index = 0

        # Category Selection
        ttk.Label(frame, text="Categorie:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(frame, textvariable=self.category_var, values=self.categories, state="readonly", width=38)
        self.category_combo.grid(row=row_index, column=1, columnspan=2, sticky="ew", padx=5, pady=2)
        # Set initial category (either the one passed in for add/edit, or the first available)
        preselected_category = self.initial_data.get('category') # This is the one to display initially
        if preselected_category in self.categories:
            self.category_var.set(preselected_category)
        elif self.categories:
            self.category_var.set(self.categories[0])
        row_index += 1

        # Image Selection
        ttk.Label(frame, text="Afbeelding:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.img_src_var = tk.StringVar()
        self.img_src_var.set(self.initial_data.get('img_src', '')) # Display current src
        img_entry = ttk.Entry(frame, textvariable=self.img_src_var, width=40, state="readonly")
        img_entry.grid(row=row_index, column=1, sticky="ew", padx=5, pady=2)
        browse_button = ttk.Button(frame, text="Bladeren...", command=self._browse_image)
        browse_button.grid(row=row_index, column=2, sticky="w", padx=5, pady=2)
        row_index += 1

        # Link URL
        ttk.Label(frame, text="Link URL (optioneel):").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.link_entry = ttk.Entry(frame, width=40)
        self.link_entry.grid(row=row_index, column=1, columnspan=2, sticky="ew", padx=5, pady=2)
        self.link_entry.insert(0, self.initial_data.get('link_href', '') or '')
        row_index += 1

        # Alt Text
        ttk.Label(frame, text="Alt Tekst (voor afbeelding):").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.alt_entry = ttk.Entry(frame, width=40)
        self.alt_entry.grid(row=row_index, column=1, columnspan=2, sticky="ew", padx=5, pady=2)
        self.alt_entry.insert(0, self.initial_data.get('alt', ''))
        row_index += 1

        frame.columnconfigure(1, weight=1)
        button_frame = ttk.Frame(frame); button_frame.grid(row=row_index, column=0, columnspan=3, pady=(15, 0), sticky=tk.E)
        ok_button = ttk.Button(button_frame, text="OK", command=self.on_ok); ok_button.pack(side=tk.RIGHT, padx=(5, 0))
        cancel_button = ttk.Button(button_frame, text="Annuleren", command=self.on_cancel); cancel_button.pack(side=tk.RIGHT)

        self.grab_set(); self.protocol("WM_DELETE_WINDOW", self.on_cancel); self.bind("<Escape>", self.on_cancel)
        self.wait_window()

    def _browse_image(self):
        filetypes = (("Afbeeldingsbestanden", "*.jpg *.jpeg *.png *.gif *.webp *.bmp *.svg"), ("Alle bestanden", "*.*"))
        source_path = filedialog.askopenfilename(title="Selecteer Sponsor Afbeelding", filetypes=filetypes)
        if source_path:
            self.selected_image_source_path = source_path
            filename = os.path.basename(source_path)
            self.img_src_var.set(f"[Nieuw: {filename}]")

    # --- MODIFIED on_ok ---
    def on_ok(self, event=None):
        # Get data from fields
        selected_category_in_dialog = self.category_var.get() # This is the potentially NEW category
        link_href = self.link_entry.get().strip() or None
        alt_text = self.alt_entry.get().strip()

        # --- Validation ---
        if not selected_category_in_dialog or selected_category_in_dialog == "<Kies Categorie>":
            messagebox.showwarning("Invoer Vereist", "Selecteer een categorie.", parent=self)
            self.category_combo.focus_set(); return

        # --- Determine image source ---
        new_img_src_to_save = None # Relative path for HTML
        img_source_to_copy = None # Absolute path if new file browsed

        if self.selected_image_source_path: # User browsed for a new image
            img_source_to_copy = self.selected_image_source_path
            filename = os.path.basename(img_source_to_copy)
            if not alt_text: alt_text = os.path.splitext(filename)[0]
        elif self.initial_data.get('img_src'): # Editing, keep old src if no new browse
            new_img_src_to_save = self.initial_data['img_src']
            if not alt_text:
                 filename = os.path.basename(new_img_src_to_save)
                 alt_text = os.path.splitext(filename)[0]
        else: # Adding new, but no image selected
            messagebox.showwarning("Invoer Vereist", "Selecteer een afbeelding.", parent=self)
            return

        # --- Prepare result dictionary ---
        self.result = {
            'category': selected_category_in_dialog, # The category chosen in THIS dialog
            'link_href': link_href,
            'alt': alt_text,
            'img_src': new_img_src_to_save, # May be None initially if new image
            '_source_path_to_copy': img_source_to_copy, # Temp path if needed
            '_source_html': self.initial_data.get('_source_html')
        }

        # --- Pass data back via callback ---
        if self.callback:
            # Get original data passed INTO the dialog
            original_index = self.initial_data.get('original_index') # Index in original list
            tree_iid = self.initial_data.get('iid') # Treeview item ID
            original_category = self.initial_data.get('original_category') # Category item CAME FROM

            # Call the callback with NEW data and ORIGINAL context
            if self.callback(self.result, original_index, tree_iid, original_category) is False:
                return

        self.destroy()

    def on_cancel(self, event=None):
        self.destroy()


class SponsorsTab:
    # --- Keep __init__, _init_data_structure, _create_widgets, _load_sponsors, _populate_category_combobox ---
    # --- _on_category_selected, _display_sponsors_for_category, _update_ui_states ---
    # --- _on_sponsor_selected, _on_sponsor_double_click, _update_preview ---
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance
        self.sponsor_data = {}
        self._init_data_structure()
        self.sponsors_loaded = False
        self._selected_category = None # Category currently displayed in the treeview
        self._create_widgets()
        self._load_sponsors()

    def _init_data_structure(self):
        """Initializes self.sponsor_data based on config."""
        self.sponsor_data = {}
        for cat_name, cat_info in config.SPONSOR_CATEGORIES.items():
            self.sponsor_data[cat_name] = {
                'html_path': cat_info['html_path_abs'],
                'img_dir': cat_info['img_dir_abs'],
                'img_href': cat_info['img_href_base'],
                'data': [] # Parsed sponsor items will go here
            }

    def _create_widgets(self):
        self.parent.grid_rowconfigure(1, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        # Top Frame for controls
        top_frame = ttk.Frame(self.parent)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        ttk.Label(top_frame, text="Sponsor Categorie:").pack(side=tk.LEFT, padx=(0, 5))
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(top_frame, textvariable=self.category_var, state="readonly", width=25)
        self.category_combo.pack(side=tk.LEFT, padx=5)
        self.category_combo.bind("<<ComboboxSelected>>", self._on_category_selected)

        self.refresh_button = ttk.Button(top_frame, text="Herlaad Data", command=self._load_sponsors)
        self.refresh_button.pack(side=tk.LEFT, padx=5)

        self.save_button = ttk.Button(top_frame, text="Sponsor Wijzigingen Opslaan", command=self._save_all_sponsors, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)

        # Main area using PanedWindow for Treeview and Edit/Preview
        pw_main = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        pw_main.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        # Left: Treeview
        tree_frame = ttk.Frame(pw_main, padding=5)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        cols = ('filename', 'link', 'alt')
        self.sponsors_tree = ttk.Treeview(tree_frame, columns=cols, show='headings', selectmode='browse')
        self.sponsors_tree.heading('filename', text='Afbeelding Bestand'); self.sponsors_tree.column('filename', width=250, anchor=tk.W)
        self.sponsors_tree.heading('link', text='Link URL'); self.sponsors_tree.column('link', width=300, anchor=tk.W)
        self.sponsors_tree.heading('alt', text='Alt Tekst'); self.sponsors_tree.column('alt', width=150, anchor=tk.W)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.sponsors_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.sponsors_tree.xview)
        self.sponsors_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.sponsors_tree.grid(row=0, column=0, sticky="nsew"); vsb.grid(row=0, column=1, sticky="ns"); hsb.grid(row=1, column=0, sticky="ew")
        self.sponsors_tree.bind("<<TreeviewSelect>>", self._on_sponsor_selected)
        self.sponsors_tree.bind("<Double-1>", self._on_sponsor_double_click)

        pw_main.add(tree_frame, weight=2)

        # Right: Actions and Preview
        action_preview_frame = ttk.Frame(pw_main, padding=5)
        action_preview_frame.grid_rowconfigure(1, weight=1) # Allow preview to expand
        action_preview_frame.grid_columnconfigure(0, weight=1)

        action_frame = ttk.Labelframe(action_preview_frame, text=" Acties ", padding=10)
        action_frame.grid(row=0, column=0, sticky="new")
        action_frame.columnconfigure(0, weight=1)

        self.add_button = ttk.Button(action_frame, text="Nieuwe Sponsor Toevoegen...", command=self._add_sponsor_dialog, state=tk.DISABLED)
        self.add_button.grid(row=0, column=0, sticky="ew", padx=5, pady=3)
        self.edit_button = ttk.Button(action_frame, text="Geselecteerde Bewerken...", command=self._edit_sponsor_dialog, state=tk.DISABLED)
        self.edit_button.grid(row=1, column=0, sticky="ew", padx=5, pady=3)
        self.delete_button = ttk.Button(action_frame, text="Geselecteerde Verwijderen", command=self._delete_sponsor, state=tk.DISABLED)
        self.delete_button.grid(row=2, column=0, sticky="ew", padx=5, pady=3)

        preview_frame = ttk.Labelframe(action_preview_frame, text=" Voorvertoning ", padding=10)
        preview_frame.grid(row=1, column=0, sticky="nsew", pady=(10,0))
        preview_frame.grid_rowconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)

        preview_outer = ttk.Frame(preview_frame, width=config.IMAGE_PREVIEW_MAX_WIDTH+10, height=config.IMAGE_PREVIEW_MAX_HEIGHT+10)
        preview_outer.grid(row=0, column=0, sticky="nsew"); preview_outer.grid_propagate(False)
        preview_outer.grid_rowconfigure(0, weight=1); preview_outer.grid_columnconfigure(0, weight=1)
        self.preview_label = ttk.Label(preview_outer, text="Selecteer sponsor", relief=tk.GROOVE, anchor=tk.CENTER, background="lightgrey")
        self.preview_label.grid(sticky="nsew", padx=5, pady=5)
        self._preview_photo = None

        pw_main.add(action_preview_frame, weight=1)

    def _load_sponsors(self):
        if not utils.confirm_discard_changes(self):
            return
        self.app.set_status("Laden sponsor data..."); self.app.root.update_idletasks()
        success = True
        previous = self.sponsor_data
        self._init_data_structure()
        candidate = self.sponsor_data
        self.sponsor_data = previous

        for cat_name, cat_info in candidate.items():
            html_path = cat_info['html_path']
            if not os.path.exists(html_path):
                print(f"Warning: Sponsor file not found, skipping: {html_path}")
                success = False
                continue

            parsed_list, error_msg = utils.sponsors_parse_html(html_path)
            if error_msg:
                messagebox.showerror("Laad Fout", f"Fout bij laden {cat_name}:\n{error_msg}", parent=self.app.root)
                cat_info['data'] = []
                success = False
            else:
                cat_info['data'] = parsed_list if parsed_list is not None else []

        if success:
            self.sponsor_data = candidate
        self.sponsors_loaded = success
        self._populate_category_combobox()

        # Display sponsors for the currently selected category in the combobox
        current_combo_selection = self.category_var.get()
        if current_combo_selection:
             self._display_sponsors_for_category(current_combo_selection)
             self._selected_category = current_combo_selection # Set initial category
        elif self.sponsor_data: # If combo was empty but we have data, select first
             first_cat = list(self.sponsor_data.keys())[0]
             self.category_var.set(first_cat)
             self._display_sponsors_for_category(first_cat)
             self._selected_category = first_cat
        else: # No data at all
             self._display_sponsors_for_category(None)
             self._selected_category = None

        self._update_ui_states()
        self.app.set_status("Sponsor data geladen." if success else "Fout bij laden sponsor data.", is_error=not success, duration_ms=5000)
        if success:
            utils.remember_editor_state(self, self.sponsor_data)
        return success

    def has_unsaved_changes(self):
        return utils.editor_state_changed(self, self.sponsor_data)

    def _populate_category_combobox(self):
        categories = list(self.sponsor_data.keys())
        current_selection = self.category_var.get() # Remember current selection
        self.category_combo['values'] = categories
        if current_selection in categories:
            self.category_var.set(current_selection) # Restore if still valid
        elif categories:
            self.category_var.set(categories[0]) # Default to first
        else:
            self.category_var.set("") # Clear if no categories

    def _on_category_selected(self, event=None):
        selected_cat = self.category_var.get()
        if selected_cat:
            # Only update if category actually changed from the one displayed
            if selected_cat != self._selected_category:
                self._display_sponsors_for_category(selected_cat)
                # _selected_category is updated within _display_sponsors_for_category

    def _display_sponsors_for_category(self, category_name):
        self.sponsors_tree.delete(*self.sponsors_tree.get_children())
        self._update_preview(None)
        self._selected_category = category_name # Update the currently displayed category

        if category_name and category_name in self.sponsor_data:
            sponsors = self.sponsor_data[category_name]['data']
            for index, sponsor in enumerate(sponsors):
                 img_src = sponsor.get('img_src', '')
                 filename = os.path.basename(img_src) if img_src else "Geen afbeelding"
                 link = sponsor.get('link_href', '') or ''
                 alt = sponsor.get('alt', '')
                 iid = str(index) # Use index within this category as iid
                 self.sponsors_tree.insert('', tk.END, iid=iid, values=(filename, link, alt))

        # Reset button states after changing category display
        self.edit_button.config(state=tk.DISABLED)
        self.delete_button.config(state=tk.DISABLED)
        # Enable Add button only if a category is selected
        self.add_button.config(state=tk.NORMAL if category_name else tk.DISABLED)

    def _update_ui_states(self):
        state = tk.NORMAL if self.sponsors_loaded else tk.DISABLED
        self.save_button.config(state=state)
        # Add button state depends on category selection, handled in _display_sponsors_for_category
        # Edit/Delete depend on tree selection, handled in _on_sponsor_selected

    def _on_sponsor_selected(self, event=None):
        selected_items = self.sponsors_tree.selection()
        if not selected_items:
            self.edit_button.config(state=tk.DISABLED)
            self.delete_button.config(state=tk.DISABLED)
            self._update_preview(None)
            return

        iid = selected_items[0] # Index as string
        category = self._selected_category # Use the currently displayed category
        if not category or category not in self.sponsor_data:
             print(f"Error: Invalid or missing category '{category}' during selection.")
             self.edit_button.config(state=tk.DISABLED); self.delete_button.config(state=tk.DISABLED); self._update_preview(None); return

        try:
             index = int(iid)
             # Check index bounds for the *currently displayed* category
             if 0 <= index < len(self.sponsor_data[category]['data']):
                 sponsor_data = self.sponsor_data[category]['data'][index]
                 self.edit_button.config(state=tk.NORMAL)
                 self.delete_button.config(state=tk.NORMAL)
                 self._update_preview(sponsor_data)
             else:
                 print(f"Error: Index {index} out of bounds for category '{category}' (size {len(self.sponsor_data[category]['data'])}).")
                 self.edit_button.config(state=tk.DISABLED); self.delete_button.config(state=tk.DISABLED); self._update_preview(None);
        except (ValueError, KeyError) as e:
             print(f"Error finding sponsor data for selection: Cat='{category}', iid='{iid}', Error='{e}'")
             self.edit_button.config(state=tk.DISABLED); self.delete_button.config(state=tk.DISABLED); self._update_preview(None);

    def _on_sponsor_double_click(self, event=None):
        if self.edit_button['state'] == tk.NORMAL:
            self._edit_sponsor_dialog()

    def _update_preview(self, sponsor_data):
         if sponsor_data and sponsor_data.get('img_src'):
             img_rel_path = sponsor_data['img_src']
             # Use the utility function to get absolute path robustly
             try:
                 img_abs_path = utils.get_abs_path(img_rel_path)
             except (ValueError, OSError):
                 img_abs_path = None

             if img_abs_path and os.path.isfile(img_abs_path):
                 try:
                     if HAS_PILLOW_SPONSORS:
                         with Image.open(img_abs_path) as img:
                             img.thumbnail((config.IMAGE_PREVIEW_MAX_WIDTH, config.IMAGE_PREVIEW_MAX_HEIGHT))
                             self._preview_photo = ImageTk.PhotoImage(img)
                             self.preview_label.config(image=self._preview_photo, text="")
                             return
                     else: # Fallback if Pillow not installed
                         self._preview_photo = tk.PhotoImage(file=img_abs_path)
                         if self._preview_photo.width() > config.IMAGE_PREVIEW_MAX_WIDTH or self._preview_photo.height() > config.IMAGE_PREVIEW_MAX_HEIGHT:
                             self.preview_label.config(image='', text=f"Preview N/B\n(Te groot)\n{os.path.basename(img_rel_path)}")
                         else: self.preview_label.config(image=self._preview_photo, text="")
                         return
                 except Exception as e:
                     print(f"Error loading preview for {img_abs_path}: {e}")
                     self.preview_label.config(image='', text=f"Fout laden preview\n{os.path.basename(img_rel_path)}")
                     return
             else:
                 self.preview_label.config(image='', text=f"Bestand niet\ngevonden:\n{img_rel_path}")
         else:
             self._preview_photo = None
             self.preview_label.config(image='', text="Selecteer sponsor" if self._selected_category else "Kies categorie")

    def _add_sponsor_dialog(self):
        if not self.sponsors_loaded: return
        # Use the currently selected category from the combobox as default
        category = self.category_var.get()
        if not category:
            messagebox.showwarning("Selectie Vereist", "Selecteer eerst een categorie waaraan u wilt toevoegen.", parent=self.app.root)
            return

        categories = list(self.sponsor_data.keys())
        # Pass category pre-selected, index=None for adding
        SponsorDialog(self.app.root, "Nieuwe Sponsor Toevoegen", categories,
                      initial_data={'category': category}, # Pass category to pre-select in dialog
                      # Define callback correctly, original_category will be None for add
                      callback=lambda data, idx, tid, orig_cat: self._process_sponsor_edit(data, None, None, None))

    # --- MODIFIED _edit_sponsor_dialog ---
    def _edit_sponsor_dialog(self):
        if not self.sponsors_loaded: return
        selected_items = self.sponsors_tree.selection()
        if not selected_items: return
        iid = selected_items[0] # Index as string
        # Use the category currently displayed in the treeview!
        original_category = self._selected_category
        if not original_category or original_category not in self.sponsor_data:
             messagebox.showerror("Fout", "Kon de huidige categorie niet bepalen voor bewerken.", parent=self.app.root)
             return

        try:
            index = int(iid)
            # Ensure index is valid for the original category
            if 0 <= index < len(self.sponsor_data[original_category]['data']):
                # Make a deep copy to avoid modifying original data if dialog cancelled
                initial_data = copy.deepcopy(self.sponsor_data[original_category]['data'][index])
                # Store original context for the dialog/callback
                initial_data['original_category'] = original_category # Store category it came FROM
                initial_data['category'] = original_category # Pre-select this category in dialog
                initial_data['original_index'] = index # Store original index within that category
                initial_data['iid'] = iid # Store treeview item ID

                categories = list(self.sponsor_data.keys()) # All available categories for dropdown
                SponsorDialog(self.app.root, "Sponsor Bewerken", categories, initial_data,
                              # Define callback correctly
                              callback=lambda data, idx, tid, orig_cat: self._process_sponsor_edit(data, idx, tid, orig_cat))
            else:
                raise IndexError("Sponsor index out of bounds for original category.")
        except (ValueError, IndexError, KeyError) as e:
             messagebox.showerror("Fout", f"Kon sponsor data niet laden voor bewerken:\n{e}", parent=self.app.root)

    # --- MODIFIED _process_sponsor_edit ---
    def _process_sponsor_edit(self, result_data, original_index, tree_iid, original_category):
        """
        Handles adding or updating sponsor data after dialog closes.
        Correctly handles moving sponsors between categories.

        Args:
            result_data: Dictionary with data from the dialog ({'category': NEW_CAT, ...}).
            original_index: The index the item had in the original_category list (or None if adding).
            tree_iid: The iid of the item in the treeview (or None if adding).
            original_category: The category name the item CAME FROM (or None if adding).
        """
        if result_data is None: return # Dialog cancelled

        new_category = result_data['category'] # Category selected in dialog
        if new_category not in self.sponsor_data:
             messagebox.showerror("Fout", f"Ongeldige doelcategorie '{new_category}'.", parent=self.app.root)
             return False

        img_source_path = result_data.pop('_source_path_to_copy', None) # Get temp path
        final_img_src = result_data['img_src'] # Existing rel path or None

        # --- Handle Image Copying/Path Generation ---
        if img_source_path:
            target_dir_abs = self.sponsor_data[new_category]['img_dir']
            target_href_base = self.sponsor_data[new_category]['img_href']
            filename = os.path.basename(img_source_path)
            dest_path_abs = os.path.join(target_dir_abs, filename)

            try:
                os.makedirs(target_dir_abs, exist_ok=True)
                dest_path_abs = utils.copy_new_asset(img_source_path, dest_path_abs, owner=self)
                filename = os.path.basename(dest_path_abs)
                # Generate the relative path for HTML src
                final_img_src = str(pathlib.PurePosixPath(target_href_base) / filename).replace('\\', '/') # Ensure forward slashes
            except Exception as e:
                messagebox.showerror("Afbeelding Fout", f"Kon afbeelding niet kopiëren naar doelmap.\nFout: {e}", parent=self.app.root)
                self.app.set_status(f"Fout bij kopiëren afbeelding: {e}", is_error=True)
                return False # Abort

        # Update the final img_src in the result data (must have a value now)
        if not final_img_src:
             messagebox.showerror("Fout", "Geen afbeelding bron bepaald na verwerking.", parent=self.app.root)
             return False
        result_data['img_src'] = final_img_src

        # --- Update Internal Data ---
        is_edit = original_index is not None and original_category is not None

        try:
            if is_edit:
                # --- Editing Existing Sponsor ---
                print(f"Processing edit: original_cat='{original_category}', new_cat='{new_category}', original_index={original_index}") # Debug

                if new_category == original_category:
                    # Category UNCHANGED: Update in place
                    if 0 <= original_index < len(self.sponsor_data[original_category]['data']):
                        self.sponsor_data[original_category]['data'][original_index] = result_data
                        print(f"Updated sponsor at index {original_index} in category '{original_category}'")
                    else:
                        raise IndexError(f"Originele index {original_index} ongeldig voor categorie '{original_category}' (size {len(self.sponsor_data[original_category]['data'])}).")
                else:
                    # Category CHANGED: Delete from old, Add to new
                    # 1. Delete from original category
                    if 0 <= original_index < len(self.sponsor_data[original_category]['data']):
                        del self.sponsor_data[original_category]['data'][original_index]
                        print(f"Deleted sponsor from index {original_index} in category '{original_category}'")
                    else:
                         # This case should ideally not happen if UI is consistent, but log it
                         print(f"Warning: Originele index {original_index} was ongeldig voor categorie '{original_category}' bij verwijderen. Overslaan.")

                    # 2. Add to new category
                    self.sponsor_data[new_category]['data'].append(result_data)
                    print(f"Added sponsor to category '{new_category}'")

            else:
                # --- Adding New Sponsor ---
                print(f"Processing add: new_cat='{new_category}'")
                self.sponsor_data[new_category]['data'].append(result_data)

            # --- Refresh UI ---
            # Refresh the category that was *last displayed* or the one it was moved *to*
            category_to_refresh = self.category_var.get() # Refresh the one selected in the combo
            if category_to_refresh:
                 self._display_sponsors_for_category(category_to_refresh)
                 # Try to reselect the modified/added item if it's in the refreshed view
                 if new_category == category_to_refresh:
                     new_index = original_index if is_edit and new_category == original_category else len(self.sponsor_data[new_category]['data']) - 1
                     new_iid = str(new_index)
                     if self.sponsors_tree.exists(new_iid):
                         self.sponsors_tree.selection_set(new_iid)
                         self.sponsors_tree.focus(new_iid)
                         self.sponsors_tree.see(new_iid)
            else: # Fallback if somehow no category is selected
                 self._display_sponsors_for_category(new_category)


            self.app.set_status("Sponsor bijgewerkt (nog niet opgeslagen)." if is_edit else "Sponsor toegevoegd (nog niet opgeslagen).", duration_ms=4000)

        except (KeyError, IndexError) as e:
            messagebox.showerror("Interne Fout", f"Fout bij verwerken sponsor update:\n{e}", parent=self.app.root)
            print(f"Error during sponsor data update: {e}")
            # Optionally reload data fully if state seems inconsistent
            # self._load_sponsors()
            return False


    def _delete_sponsor(self):
        if not self.sponsors_loaded: return
        selected_items = self.sponsors_tree.selection()
        if not selected_items: return
        iid = selected_items[0] # Index as string
        category = self._selected_category # Use the currently displayed category
        if not category or category not in self.sponsor_data: return

        try:
            index = int(iid)
            if 0 <= index < len(self.sponsor_data[category]['data']):
                sponsor_to_delete = self.sponsor_data[category]['data'][index]
                filename = os.path.basename(sponsor_to_delete.get('img_src', ''))
                confirm_msg = f"Sponsor verwijderen?\n\nAfbeelding: {filename}\nCategorie: {category}\n\n(Verwijdert alleen uit HTML, niet het afbeeldingsbestand)"

                if messagebox.askyesno("Verwijderen Bevestigen", confirm_msg, icon='warning', parent=self.app.root):
                    del self.sponsor_data[category]['data'][index]
                    self._display_sponsors_for_category(category) # Refresh tree
                    self.app.set_status(f"Sponsor '{filename}' verwijderd (nog niet opgeslagen).", duration_ms=4000)
            else:
                raise IndexError("Sponsor index out of bounds for deletion.")
        except (ValueError, IndexError, KeyError) as e:
             messagebox.showerror("Fout", f"Kon sponsor data niet vinden om te verwijderen: {e}", parent=self.app.root)


    def _save_all_sponsors(self):
        if not self.sponsors_loaded:
            messagebox.showwarning("Data niet geladen", "Kan niet opslaan, sponsor data is niet (succesvol) geladen.", parent=self.app.root)
            return

        self.app.set_status("Sponsor wijzigingen opslaan..."); self.app.root.update_idletasks()
        try:
            outputs = {info['html_path']: utils.sponsors_render_html(info['html_path'], info['data'])
                       for info in self.sponsor_data.values()}
            utils.atomic_write_many(outputs)
        except (OSError, ValueError) as error:
            self.app.set_status("Sponsorbestanden niet opgeslagen; concepten zijn behouden.", is_error=True)
            messagebox.showerror("Opslag Fout", str(error), parent=self.app.root)
            return False
        utils.remember_editor_state(self, self.sponsor_data)
        self.app.set_status(f"Alle {len(outputs)} sponsorbestanden opgeslagen.", duration_ms=5000)
        return True


def create_sponsors_tab(parent_frame, app_instance):
    return SponsorsTab(parent_frame, app_instance)

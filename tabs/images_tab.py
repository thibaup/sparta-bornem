import copy
import os
import pathlib
import shutil
import stat
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

import config
import utils

try:
    from PIL import Image, ImageTk, ImageOps
    Image.MAX_IMAGE_PIXELS = None
    HAS_PILLOW = True
except ImportError:
    Image = None
    ImageTk = None
    ImageOps = None
    HAS_PILLOW = False


def _path_is_inside(base_dir, candidate_path):
    try:
        base_abs = os.path.normcase(os.path.realpath(base_dir))
        candidate_abs = os.path.normcase(os.path.realpath(candidate_path))
        return os.path.commonpath([base_abs, candidate_abs]) == base_abs
    except ValueError:
        return False


class ImagesTab:
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance
        self.data = utils.images_gallery_default_data()
        self._loaded = False
        self.selected_folder_id = None
        self.selected_image_index = None
        self._preview_photo = None
        self._dragged_folder_iid = None
        self._dragged_image_iid = None

        self._create_widgets()
        self.reload_data()

    def _create_widgets(self):
        self.parent.grid_rowconfigure(1, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        top_bar = ttk.Frame(self.parent)
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(top_bar, text="Herlaad", command=self.reload_data).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(top_bar, text="Opslaan", command=self._save_data).pack(side=tk.LEFT)
        ttk.Label(
            top_bar,
            text="Beheer de Images pagina. Sleep mappen of afbeeldingen om de volgorde te wijzigen.",
            style="Desc.TLabel"
        ).pack(side=tk.LEFT, padx=(12, 0))

        paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        paned.grid(row=1, column=0, sticky="nsew")

        folder_frame = ttk.Labelframe(paned, text=" Mappen ", padding=10)
        folder_frame.grid_rowconfigure(0, weight=1)
        folder_frame.grid_columnconfigure(0, weight=1)

        folder_columns = ("title", "count")
        self.folder_tree = ttk.Treeview(folder_frame, columns=folder_columns, show="headings", selectmode="browse")
        self.folder_tree.heading("title", text="Naam", anchor=tk.W)
        self.folder_tree.column("title", width=260, minwidth=180, anchor=tk.W, stretch=tk.YES)
        self.folder_tree.heading("count", text="Afbeeldingen", anchor=tk.CENTER)
        self.folder_tree.column("count", width=100, minwidth=80, anchor=tk.CENTER, stretch=tk.NO)
        folder_vsb = ttk.Scrollbar(folder_frame, orient="vertical", command=self.folder_tree.yview)
        self.folder_tree.configure(yscrollcommand=folder_vsb.set)
        self.folder_tree.grid(row=0, column=0, sticky="nsew")
        folder_vsb.grid(row=0, column=1, sticky="ns")
        self.folder_tree.bind("<<TreeviewSelect>>", self._on_folder_select)
        self.folder_tree.bind("<ButtonPress-1>", self._folder_drag_start, add="+")
        self.folder_tree.bind("<B1-Motion>", self._folder_drag_motion, add="+")
        self.folder_tree.bind("<ButtonRelease-1>", self._folder_drag_drop, add="+")

        folder_buttons = ttk.Frame(folder_frame)
        folder_buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        folder_buttons.columnconfigure((0, 1), weight=1)
        self.add_folder_btn = ttk.Button(folder_buttons, text="+ Map", command=self._add_folder)
        self.rename_folder_btn = ttk.Button(folder_buttons, text="Hernoem", command=self._rename_folder, state=tk.DISABLED)
        self.delete_folder_btn = ttk.Button(folder_buttons, text="Verwijder", command=self._delete_folder, state=tk.DISABLED)
        self.add_folder_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=(0, 6))
        self.rename_folder_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=(0, 6))
        self.delete_folder_btn.grid(row=1, column=0, columnspan=2, sticky="ew")

        paned.add(folder_frame, weight=1)

        image_frame = ttk.Labelframe(paned, text=" Afbeeldingen in geselecteerde map ", padding=10)
        image_frame.grid_rowconfigure(1, weight=1)
        image_frame.grid_columnconfigure(0, weight=1)

        self.selected_folder_label = ttk.Label(image_frame, text="Selecteer een map.", style="Bold.TLabel")
        self.selected_folder_label.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        image_tree_frame = ttk.Frame(image_frame)
        image_tree_frame.grid(row=1, column=0, sticky="nsew")
        image_tree_frame.grid_rowconfigure(0, weight=1)
        image_tree_frame.grid_columnconfigure(0, weight=1)

        image_columns = ("filename", "alt", "path", "size")
        self.image_tree = ttk.Treeview(image_tree_frame, columns=image_columns, show="headings", selectmode="browse")
        self.image_tree.heading("filename", text="Bestand", anchor=tk.W)
        self.image_tree.column("filename", width=180, minwidth=140, anchor=tk.W, stretch=tk.YES)
        self.image_tree.heading("alt", text="Alt tekst", anchor=tk.W)
        self.image_tree.column("alt", width=180, minwidth=120, anchor=tk.W, stretch=tk.YES)
        self.image_tree.heading("path", text="Websitepad", anchor=tk.W)
        self.image_tree.column("path", width=320, minwidth=220, anchor=tk.W, stretch=tk.YES)
        self.image_tree.heading("size", text="Grootte", anchor=tk.W)
        self.image_tree.column("size", width=90, minwidth=70, anchor=tk.W, stretch=tk.NO)
        image_vsb = ttk.Scrollbar(image_tree_frame, orient="vertical", command=self.image_tree.yview)
        image_hsb = ttk.Scrollbar(image_tree_frame, orient="horizontal", command=self.image_tree.xview)
        self.image_tree.configure(yscrollcommand=image_vsb.set, xscrollcommand=image_hsb.set)
        self.image_tree.grid(row=0, column=0, sticky="nsew")
        image_vsb.grid(row=0, column=1, sticky="ns")
        image_hsb.grid(row=1, column=0, sticky="ew")
        self.image_tree.tag_configure("missing", foreground="red")
        self.image_tree.bind("<<TreeviewSelect>>", self._on_image_select)
        self.image_tree.bind("<Double-1>", lambda _event: self._edit_image_alt())
        self.image_tree.bind("<ButtonPress-1>", self._image_drag_start, add="+")
        self.image_tree.bind("<B1-Motion>", self._image_drag_motion, add="+")
        self.image_tree.bind("<ButtonRelease-1>", self._image_drag_drop, add="+")

        actions = ttk.Frame(image_frame)
        actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        actions.columnconfigure((0, 1, 2), weight=1)
        self.add_images_btn = ttk.Button(actions, text="+ Afbeeldingen toevoegen", command=self._add_images, state=tk.DISABLED)
        self.remove_image_btn = ttk.Button(actions, text="Verwijder afbeelding", command=self._remove_image, state=tk.DISABLED)
        self.edit_alt_btn = ttk.Button(actions, text="Alt tekst", command=self._edit_image_alt, state=tk.DISABLED)
        self.add_images_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.remove_image_btn.grid(row=0, column=1, sticky="ew", padx=4)
        self.edit_alt_btn.grid(row=0, column=2, sticky="ew", padx=(4, 0))

        preview_frame = ttk.Labelframe(image_frame, text=" Voorvertoning ", padding=10)
        preview_frame.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        preview_frame.columnconfigure(0, weight=1)
        self.preview_label = ttk.Label(preview_frame, text="Selecteer een afbeelding", anchor=tk.CENTER, relief=tk.GROOVE, background="lightgrey")
        self.preview_label.grid(row=0, column=0, sticky="ew", ipady=18)

        paned.add(image_frame, weight=3)

    def reload_data(self):
        if not utils.confirm_discard_changes(self):
            return
        loaded, error_msg = utils.images_gallery_load_json_data(config.IMAGES_JSON_FILE_PATH)
        self._loaded = not bool(error_msg)
        if error_msg:
            self.app.set_status(error_msg, is_error=True)
            messagebox.showerror("Images JSON fout", error_msg, parent=self.parent)
            self._update_folder_buttons()
            self._update_image_buttons()
            return False
        self.data = loaded
        utils.remember_editor_state(self, self.data)
        self.selected_folder_id = None
        self.selected_image_index = None
        self._populate_folders()
        self.app.set_status("Images data geladen.", duration_ms=3000)

    def has_unsaved_changes(self):
        return utils.editor_state_changed(self, self.data)

    def _save_data(self):
        if not self._loaded:
            messagebox.showwarning("Laden vereist", "Herstel en herlaad eerst het Images JSON-bestand.", parent=self.parent)
            return False
        error_msg = utils.images_gallery_save_json_data(config.IMAGES_JSON_FILE_PATH, self.data)
        if error_msg:
            self.data = copy.deepcopy(self._saved_editor_state)
            utils.cleanup_pending_assets(self)
            self._populate_folders(select_id=self.selected_folder_id)
            self.app.set_status(error_msg, is_error=True)
            messagebox.showerror("Opslaan mislukt", error_msg, parent=self.parent)
            return False
        utils.remember_editor_state(self, self.data)
        self.app.set_status("Images data opgeslagen.", duration_ms=4000)
        return True

    def _folders(self):
        return self.data.setdefault("folders", [])

    def _selected_folder(self):
        if not self.selected_folder_id:
            return None
        return next((folder for folder in self._folders() if folder.get("id") == self.selected_folder_id), None)

    def _folder_titles(self, exclude_id=None):
        return {
            (folder.get("title") or "").strip().casefold()
            for folder in self._folders()
            if folder.get("id") != exclude_id
        }

    def _validate_folder_title(self, title, exclude_id=None):
        clean_title = (title or "").strip()
        if not clean_title:
            return None, "Geef een mapnaam in."
        if len(clean_title) > 80:
            return None, "Mapnaam is te lang. Gebruik maximaal 80 tekens."
        if clean_title.casefold() in self._folder_titles(exclude_id=exclude_id):
            return None, "Er bestaat al een map met deze naam."
        return clean_title, None

    def _make_unique_folder_id(self, title):
        base = config.sanitize_for_path(title).strip("._-") or "folder"
        existing = {folder.get("id") for folder in self._folders()}
        candidate = base
        counter = 2
        while candidate in existing:
            candidate = f"{base}-{counter}"
            counter += 1
        return candidate

    def _populate_folders(self, select_id=None):
        self.folder_tree.delete(*self.folder_tree.get_children())
        for folder in self._folders():
            folder_id = folder.get("id") or self._make_unique_folder_id(folder.get("title", "folder"))
            folder["id"] = folder_id
            title = folder.get("title", "Naamloze map")
            count = len(folder.get("images", []))
            self.folder_tree.insert("", tk.END, iid=folder_id, values=(title, count))

        if select_id and self.folder_tree.exists(select_id):
            self.selected_folder_id = select_id
            self.folder_tree.selection_set(select_id)
            self.folder_tree.focus(select_id)
            self.folder_tree.see(select_id)
            self._populate_images()
        else:
            self.selected_folder_id = None
            self._populate_images()
        self._update_folder_buttons()

    def _populate_images(self, select_index=None):
        self.image_tree.delete(*self.image_tree.get_children())
        folder = self._selected_folder()
        if not folder:
            self.selected_folder_label.config(text="Selecteer een map.")
            self._reset_preview("Selecteer een afbeelding")
            self._update_image_buttons()
            return

        images = folder.setdefault("images", [])
        self.selected_folder_label.config(text=f"Map: {folder.get('title', '')} ({len(images)} afbeeldingen)")
        for index, image in enumerate(images):
            src = image.get("src", "")
            abs_path = self._web_path_to_abs(src)
            size = "Ontbreekt"
            tags = ()
            if abs_path and os.path.isfile(abs_path):
                size = self._format_size(os.path.getsize(abs_path))
            else:
                tags = ("missing",)
            filename = image.get("filename") or os.path.basename(src)
            self.image_tree.insert("", tk.END, iid=str(index), values=(filename, image.get("alt", ""), src, size), tags=tags)

        if select_index is not None and self.image_tree.exists(str(select_index)):
            self.image_tree.selection_set(str(select_index))
            self.image_tree.focus(str(select_index))
            self.image_tree.see(str(select_index))
        else:
            self.selected_image_index = None
            self._reset_preview("Selecteer een afbeelding")
        self._update_image_buttons()

    def _on_folder_select(self, event=None):
        selection = self.folder_tree.selection()
        self.selected_folder_id = selection[0] if selection else None
        self.selected_image_index = None
        self._populate_images()
        self._update_folder_buttons()

    def _on_image_select(self, event=None):
        selection = self.image_tree.selection()
        if not selection:
            self.selected_image_index = None
            self._reset_preview("Selecteer een afbeelding")
        else:
            try:
                self.selected_image_index = int(selection[0])
            except ValueError:
                self.selected_image_index = None
            self._show_preview()
        self._update_image_buttons()

    def _update_folder_buttons(self):
        self.add_folder_btn.config(state=tk.NORMAL if self._loaded else tk.DISABLED)
        has_folder = self._loaded and self._selected_folder() is not None
        self.rename_folder_btn.config(state=tk.NORMAL if has_folder else tk.DISABLED)
        self.delete_folder_btn.config(state=tk.NORMAL if has_folder else tk.DISABLED)

    def _update_image_buttons(self):
        folder = self._selected_folder()
        has_folder = self._loaded and folder is not None
        image_count = len(folder.get("images", [])) if folder else 0
        has_image = self._loaded and self.selected_image_index is not None and 0 <= self.selected_image_index < image_count
        self.add_images_btn.config(state=tk.NORMAL if has_folder else tk.DISABLED)
        self.remove_image_btn.config(state=tk.NORMAL if has_image else tk.DISABLED)
        self.edit_alt_btn.config(state=tk.NORMAL if has_image else tk.DISABLED)

    def _selected_folder_index(self):
        if not self.selected_folder_id:
            return -1
        for index, folder in enumerate(self._folders()):
            if folder.get("id") == self.selected_folder_id:
                return index
        return -1

    def _folder_drag_start(self, event):
        if not self._loaded:
            return
        if self.folder_tree.identify_region(event.x, event.y) not in ("cell", "tree"):
            self._dragged_folder_iid = None
            return
        self._dragged_folder_iid = self.folder_tree.identify_row(event.y)

    def _folder_drag_motion(self, event):
        if not self._dragged_folder_iid:
            return
        target_iid = self.folder_tree.identify_row(event.y)
        if target_iid and target_iid != self._dragged_folder_iid:
            try:
                self.folder_tree.move(self._dragged_folder_iid, "", self.folder_tree.index(target_iid))
                self.folder_tree.selection_set(self._dragged_folder_iid)
            except tk.TclError:
                pass

    def _folder_drag_drop(self, event):
        if not self._loaded:
            return
        if not self._dragged_folder_iid:
            return
        dragged_iid = self._dragged_folder_iid
        self._dragged_folder_iid = None

        ordered_ids = list(self.folder_tree.get_children(""))
        folders_by_id = {folder.get("id"): folder for folder in self._folders()}
        if set(ordered_ids) != set(folders_by_id.keys()):
            self._populate_folders(select_id=self.selected_folder_id)
            return

        old_order = [folder.get("id") for folder in self._folders()]
        if ordered_ids == old_order:
            return

        self.data["folders"] = [folders_by_id[folder_id] for folder_id in ordered_ids]
        self.selected_folder_id = dragged_iid
        if self._save_data():
            self._populate_folders(select_id=dragged_iid)
            self.app.set_status("Mapvolgorde aangepast.", duration_ms=4000)

    def _image_drag_start(self, event):
        if not self._loaded:
            return
        if self.image_tree.identify_region(event.x, event.y) not in ("cell", "tree"):
            self._dragged_image_iid = None
            return
        self._dragged_image_iid = self.image_tree.identify_row(event.y)

    def _image_drag_motion(self, event):
        if not self._dragged_image_iid:
            return
        target_iid = self.image_tree.identify_row(event.y)
        if target_iid and target_iid != self._dragged_image_iid:
            try:
                self.image_tree.move(self._dragged_image_iid, "", self.image_tree.index(target_iid))
                self.image_tree.selection_set(self._dragged_image_iid)
            except tk.TclError:
                pass

    def _image_drag_drop(self, event):
        if not self._loaded:
            return
        if not self._dragged_image_iid:
            return
        dragged_iid = self._dragged_image_iid
        self._dragged_image_iid = None

        folder = self._selected_folder()
        if not folder:
            return
        images = folder.get("images", [])
        ordered_iids = list(self.image_tree.get_children(""))

        try:
            ordered_indexes = [int(iid) for iid in ordered_iids]
            dragged_new_index = ordered_iids.index(dragged_iid)
        except (ValueError, IndexError):
            self._populate_images(select_index=self.selected_image_index)
            return

        if sorted(ordered_indexes) != list(range(len(images))):
            self._populate_images(select_index=self.selected_image_index)
            return
        if ordered_indexes == list(range(len(images))):
            return

        folder["images"] = [images[index] for index in ordered_indexes]
        self.selected_image_index = dragged_new_index
        if self._save_data():
            self._populate_images(select_index=dragged_new_index)
            self.app.set_status("Afbeeldingsvolgorde aangepast.", duration_ms=4000)

    def _add_folder(self):
        if not self._loaded:
            return
        title = simpledialog.askstring("Nieuwe map", "Naam van de nieuwe Images map:", parent=self.parent)
        clean_title, error_msg = self._validate_folder_title(title)
        if error_msg:
            if title is not None:
                messagebox.showwarning("Ongeldige mapnaam", error_msg, parent=self.parent)
            return

        folder_id = self._make_unique_folder_id(clean_title)
        folder = {"id": folder_id, "title": clean_title, "images": []}
        self._folders().append(folder)
        os.makedirs(self._folder_asset_dir(folder), exist_ok=True)
        if self._save_data():
            self._populate_folders(select_id=folder_id)
            self.app.set_status(f"Map '{clean_title}' toegevoegd.", duration_ms=4000)

    def _rename_folder(self):
        if not self._loaded:
            return
        folder = self._selected_folder()
        if not folder:
            return
        old_title = folder.get("title", "")
        title = simpledialog.askstring("Map hernoemen", "Nieuwe mapnaam:", initialvalue=old_title, parent=self.parent)
        clean_title, error_msg = self._validate_folder_title(title, exclude_id=folder.get("id"))
        if error_msg:
            if title is not None:
                messagebox.showwarning("Ongeldige mapnaam", error_msg, parent=self.parent)
            return
        if clean_title == old_title:
            return
        folder["title"] = clean_title
        if self._save_data():
            self._populate_folders(select_id=folder.get("id"))
            self.app.set_status(f"Map hernoemd naar '{clean_title}'.", duration_ms=4000)

    def _delete_folder(self):
        if not self._loaded:
            return
        folder = self._selected_folder()
        if not folder:
            return
        title = folder.get("title", "")
        count = len(folder.get("images", []))
        if not messagebox.askyesno(
            "Map verwijderen",
            f"Verwijder map '{title}' en {count} afbeelding(en) uit de Images pagina?\n"
            "De bijbehorende map in /images/images wordt ook verwijderd.",
            icon="warning",
            parent=self.parent
        ):
            return

        self.data["folders"] = [item for item in self._folders() if item.get("id") != folder.get("id")]
        self.selected_folder_id = None
        if self._save_data():
            folder_dir = self._folder_asset_dir(folder)
            shared = any(_path_is_inside(folder_dir, path) for item in self._folders() for image in item.get('images', []) if (path := self._web_path_to_abs(image.get('src', ''))))
            if shared:
                assets_deleted = all(self._delete_owned_image_file(image) for image in folder.get('images', []) if not self._image_is_referenced(image))
            else:
                assets_deleted = self._delete_owned_folder_dir(folder)
            self._populate_folders()
            if assets_deleted:
                self.app.set_status(f"Map '{title}' verwijderd.", duration_ms=4000)
            else:
                self.app.set_status(
                    f"Map '{title}' van de site verwijderd. De map in /images/images kon niet verwijderd worden en blijft staan.",
                    is_error=True,
                    duration_ms=9000
                )

    def _add_images(self):
        if not self._loaded:
            return
        folder = self._selected_folder()
        if not folder:
            messagebox.showwarning("Map vereist", "Selecteer eerst een map.", parent=self.parent)
            return

        extensions = " ".join(f"*{ext}" for ext in config.IMAGES_SUPPORTED_EXTENSIONS)
        paths = filedialog.askopenfilenames(
            title=f"Afbeeldingen toevoegen aan {folder.get('title', '')}",
            filetypes=(("Afbeeldingsbestanden", extensions), ("Alle bestanden", "*.*")),
            parent=self.parent
        )
        if not paths:
            self.app.set_status("Toevoegen afbeeldingen geannuleerd.", duration_ms=3000)
            return

        added = []
        errors = []
        for source_path in paths:
            try:
                entry = self._copy_and_optimize_image(source_path, folder)
                added.append(entry)
            except Exception as e:
                errors.append(f"{os.path.basename(source_path)}: {e}")

        if added:
            folder.setdefault("images", []).extend(added)
            if not self._save_data():
                return
            self._populate_folders(select_id=folder.get("id"))
            first_new_index = len(folder.get("images", [])) - len(added)
            self._populate_images(select_index=first_new_index)

        if errors:
            messagebox.showwarning("Enkele afbeeldingen niet toegevoegd", "\n".join(errors[:8]), parent=self.parent)
            self.app.set_status(f"{len(added)} toegevoegd, {len(errors)} mislukt.", is_error=True, duration_ms=7000)
        else:
            self.app.set_status(f"{len(added)} afbeelding(en) toegevoegd aan '{folder.get('title', '')}'.", duration_ms=5000)

    def _remove_image(self):
        if not self._loaded:
            return
        folder = self._selected_folder()
        if not folder or self.selected_image_index is None:
            return
        images = folder.get("images", [])
        if not (0 <= self.selected_image_index < len(images)):
            return

        image = images[self.selected_image_index]
        label = image.get("filename") or os.path.basename(image.get("src", ""))
        if not messagebox.askyesno(
            "Afbeelding verwijderen",
            f"Verwijder '{label}' uit deze map?\nHet bestand wordt alleen verwijderd als het in de Images assetmap staat.",
            icon="warning",
            parent=self.parent
        ):
            return

        del images[self.selected_image_index]
        new_selection = min(self.selected_image_index, len(images) - 1) if images else None
        if self._save_data():
            if not self._image_is_referenced(image):
                self._delete_owned_image_file(image)
            self._populate_folders(select_id=folder.get("id"))
            self._populate_images(select_index=new_selection)
            self.app.set_status(f"Afbeelding '{label}' verwijderd.", duration_ms=4000)

    def _edit_image_alt(self):
        if not self._loaded:
            return
        folder = self._selected_folder()
        if not folder or self.selected_image_index is None:
            return
        images = folder.get("images", [])
        if not (0 <= self.selected_image_index < len(images)):
            return
        image = images[self.selected_image_index]
        current_alt = image.get("alt", "")
        new_alt = simpledialog.askstring("Alt tekst", "Alt tekst voor deze afbeelding:", initialvalue=current_alt, parent=self.parent)
        if new_alt is None:
            return
        image["alt"] = new_alt.strip() or folder.get("title", "Afbeelding")
        if self._save_data():
            self._populate_images(select_index=self.selected_image_index)

    def _folder_asset_dir(self, folder):
        folder_id = folder.get("id") or self._make_unique_folder_id(folder.get("title", "folder"))
        folder["id"] = folder_id
        path = os.path.abspath(os.path.join(config.IMAGES_ASSET_DIR_ABSOLUTE, folder_id))
        if not _path_is_inside(config.IMAGES_ASSET_DIR_ABSOLUTE, path) or os.path.normcase(os.path.realpath(path)) == os.path.normcase(os.path.realpath(config.IMAGES_ASSET_DIR_ABSOLUTE)):
            raise ValueError('Ongeldig pad voor de Images assetmap.')
        return path

    def _safe_filename_stem(self, source_path):
        stem = pathlib.Path(source_path).stem
        return config.sanitize_for_path(stem).strip("._-") or "image"

    def _unique_path(self, dest_dir, stem, ext):
        clean_ext = ext if ext.startswith(".") else f".{ext}"
        candidate = os.path.join(dest_dir, f"{stem}{clean_ext}")
        counter = 2
        while os.path.exists(candidate):
            candidate = os.path.join(dest_dir, f"{stem}-{counter}{clean_ext}")
            counter += 1
        return candidate

    def _copy_and_optimize_image(self, source_path, folder):
        if not os.path.isfile(source_path):
            raise ValueError("bronbestand bestaat niet")

        ext = os.path.splitext(source_path)[1].lower()
        if ext not in config.IMAGES_SUPPORTED_EXTENSIONS:
            raise ValueError("niet-ondersteund afbeeldingsformaat")

        dest_dir = self._folder_asset_dir(folder)
        if not _path_is_inside(config.IMAGES_ASSET_DIR_ABSOLUTE, dest_dir):
            raise ValueError("doelmap ligt buiten de Images assetmap")
        os.makedirs(dest_dir, exist_ok=True)

        safe_stem = self._safe_filename_stem(source_path)
        if ext == ".svg" or not HAS_PILLOW:
            dest_path = self._unique_path(dest_dir, safe_stem, ext)
            utils.atomic_copy_file(source_path, dest_path)
        else:
            dest_path = self._save_optimized_raster(source_path, dest_dir, safe_stem, ext)

        utils.register_pending_asset(self, dest_path)
        web_path = self._abs_to_web_path(dest_path)
        return {
            "src": web_path,
            "alt": folder.get("title", "Afbeelding"),
            "filename": os.path.basename(dest_path)
        }

    def _save_optimized_raster(self, source_path, dest_dir, safe_stem, original_ext):
        with Image.open(source_path) as original:
            frame_count = getattr(original, "n_frames", 1)
            if frame_count and frame_count > 1:
                dest_path = self._unique_path(dest_dir, safe_stem, original_ext)
                utils.atomic_copy_file(source_path, dest_path)
                return dest_path

            image = ImageOps.exif_transpose(original) if ImageOps else original.copy()
            has_alpha = self._has_alpha(image)

            if max(image.size) > config.IMAGES_MAX_DIMENSION:
                image.thumbnail((config.IMAGES_MAX_DIMENSION, config.IMAGES_MAX_DIMENSION), Image.LANCZOS)

            if has_alpha:
                try:
                    return self._save_with_quality_loop(image.convert("RGBA"), dest_dir, safe_stem, ".webp", "WEBP", transparent=True)
                except Exception:
                    return self._save_png_with_resize_loop(image.convert("RGBA"), dest_dir, safe_stem)
            return self._save_with_quality_loop(image.convert("RGB"), dest_dir, safe_stem, ".jpg", "JPEG", transparent=False)

    def _save_with_quality_loop(self, image, dest_dir, safe_stem, ext, image_format, transparent):
        dest_path = self._unique_path(dest_dir, safe_stem, ext)
        target_bytes = config.IMAGES_MAX_FILE_BYTES
        qualities = [88, 82, 76, 70, 64, 58] if not transparent else [86, 80, 74, 68, 62]
        working = image.copy()
        icc_profile = image.info.get("icc_profile")

        for _ in range(6):
            for quality in qualities:
                save_kwargs = {"quality": quality}
                if image_format == "JPEG":
                    save_kwargs.update({"optimize": True, "progressive": True})
                    if icc_profile:
                        save_kwargs["icc_profile"] = icc_profile
                elif image_format == "WEBP":
                    save_kwargs.update({"method": 6})

                working.save(dest_path, format=image_format, **save_kwargs)
                if os.path.getsize(dest_path) <= target_bytes:
                    return dest_path

            width, height = working.size
            if max(width, height) <= 1200:
                return dest_path
            next_size = (max(1, int(width * 0.86)), max(1, int(height * 0.86)))
            working = working.resize(next_size, Image.LANCZOS)

        return dest_path

    def _save_png_with_resize_loop(self, image, dest_dir, safe_stem):
        dest_path = self._unique_path(dest_dir, safe_stem, ".png")
        working = image.copy()
        for _ in range(6):
            working.save(dest_path, format="PNG", optimize=True)
            if os.path.getsize(dest_path) <= config.IMAGES_MAX_FILE_BYTES:
                return dest_path
            width, height = working.size
            if max(width, height) <= 1200:
                return dest_path
            working = working.resize((max(1, int(width * 0.86)), max(1, int(height * 0.86))), Image.LANCZOS)
        return dest_path

    def _has_alpha(self, image):
        if image.mode in ("RGBA", "LA"):
            return True
        if image.mode == "P" and "transparency" in image.info:
            return True
        return False

    def _abs_to_web_path(self, abs_path):
        rel = os.path.relpath(abs_path, config.APP_BASE_DIR)
        return "/" + pathlib.Path(rel).as_posix()

    def _web_path_to_abs(self, web_path):
        if not web_path:
            return None
        try:
            return utils.resolve_site_path(web_path)
        except (ValueError, OSError):
            return None

    def _image_is_referenced(self, image):
        path = self._web_path_to_abs(image.get('src', ''))
        return any(self._web_path_to_abs(other.get('src', '')) == path for folder in self._folders() for other in folder.get('images', [])) if path else False

    def _delete_owned_image_file(self, image):
        abs_path = self._web_path_to_abs(image.get("src", ""))
        if not abs_path or not _path_is_inside(config.IMAGES_ASSET_DIR_ABSOLUTE, abs_path):
            return False
        try:
            if os.path.isfile(abs_path):
                os.remove(abs_path)
            self._remove_empty_dirs_up_to_root(os.path.dirname(abs_path))
            return True
        except OSError as error:
            self.app.set_status(f"Afbeelding van de site verwijderd; bestand kon niet verwijderd worden: {error}", is_error=True)
            return False

    def _delete_owned_folder_dir(self, folder):
        folder_dir = self._folder_asset_dir(folder)
        root_abs = os.path.normcase(os.path.abspath(config.IMAGES_ASSET_DIR_ABSOLUTE))
        folder_abs = os.path.normcase(os.path.abspath(folder_dir))
        if folder_abs == root_abs or not _path_is_inside(config.IMAGES_ASSET_DIR_ABSOLUTE, folder_dir):
            return False
        if not os.path.isdir(folder_dir):
            return True

        def retry_with_write_permission(func, path, exc_info):
            try:
                os.chmod(path, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
                func(path)
            except Exception:
                raise

        try:
            shutil.rmtree(folder_dir, onerror=retry_with_write_permission)
            return True
        except Exception as e:
            print(f"[ImagesTab] Kon assetmap niet verwijderen '{folder_dir}': {e}")
            return False

    def _remove_empty_dirs_up_to_root(self, start_dir):
        root = os.path.normcase(os.path.abspath(config.IMAGES_ASSET_DIR_ABSOLUTE))
        current = os.path.abspath(start_dir)
        while _path_is_inside(config.IMAGES_ASSET_DIR_ABSOLUTE, current) and os.path.normcase(current) != root:
            try:
                os.rmdir(current)
            except OSError:
                break
            current = os.path.dirname(current)

    def _format_size(self, byte_count):
        if byte_count >= 1024 * 1024:
            return f"{byte_count / (1024 * 1024):.1f} MB"
        return f"{byte_count / 1024:.1f} KB"

    def _reset_preview(self, text):
        self.preview_label.config(image="", text=text)
        self._preview_photo = None

    def _show_preview(self):
        folder = self._selected_folder()
        if not folder or self.selected_image_index is None:
            self._reset_preview("Selecteer een afbeelding")
            return
        images = folder.get("images", [])
        if not (0 <= self.selected_image_index < len(images)):
            self._reset_preview("Selecteer een afbeelding")
            return

        image = images[self.selected_image_index]
        abs_path = self._web_path_to_abs(image.get("src", ""))
        if not abs_path or not os.path.isfile(abs_path):
            self._reset_preview("Bestand ontbreekt")
            return
        if abs_path.lower().endswith(".svg"):
            self._reset_preview("SVG voorvertoning niet beschikbaar")
            return

        try:
            if HAS_PILLOW and ImageTk:
                with Image.open(abs_path) as preview:
                    preview = ImageOps.exif_transpose(preview) if ImageOps else preview
                    preview.thumbnail((420, 220), Image.LANCZOS)
                    self._preview_photo = ImageTk.PhotoImage(preview)
            else:
                self._preview_photo = tk.PhotoImage(file=abs_path)
            self.preview_label.config(image=self._preview_photo, text="")
        except Exception as e:
            self._reset_preview(f"Preview fout: {type(e).__name__}")


def create_images_tab(parent_frame, app_instance):
    return ImagesTab(parent_frame, app_instance)

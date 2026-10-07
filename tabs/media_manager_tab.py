import io
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil
import pathlib
import traceback
import config
import utils

try:
    from PIL import Image, ImageTk, ImageStat, ImageOps
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    Image = None
    ImageTk = None
    ImageStat = None
    ImageOps = None

try:
    import fitz
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    fitz = None


def _path_is_inside(base_dir, candidate_path):
    try:
        base_abs = os.path.normcase(os.path.realpath(base_dir))
        candidate_abs = os.path.normcase(os.path.realpath(candidate_path))
        return os.path.commonpath([base_abs, candidate_abs]) == base_abs
    except ValueError:
        return False


class ImageAddDialog(tk.Toplevel):
    def __init__(self, parent, title, callback=None):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.callback = callback
        self.result = None
        frame = ttk.Frame(self, padding="15")
        frame.pack(expand=True, fill=tk.BOTH)
        row_index = 0

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
        if dest_options and dest_options[0] != "<Andere...>": self.dest_combo.set(dest_options[0])
        else: self.dest_combo.set("")
        self.dest_combo.bind("<<ComboboxSelected>>", self._toggle_other_dest)
        self.other_dest_button = ttk.Button(frame, text="Bladeren...", command=self._browse_dest, state=tk.DISABLED)
        self.other_dest_button.grid(row=row_index, column=2, sticky="w", padx=5, pady=2)
        row_index += 1
        ttk.Label(frame, text="Map relatief t.o.v. website root", style="Desc.TLabel").grid(row=row_index, column=1, sticky="w", padx=5)
        row_index += 1

        frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row_index, column=0, columnspan=3, pady=(15, 0), sticky=tk.E)
        ok_button = ttk.Button(button_frame, text="Voeg Afbeelding Toe", command=self.on_ok)
        ok_button.pack(side=tk.RIGHT, padx=(5, 0))
        cancel_button = ttk.Button(button_frame, text="Annuleren", command=self.on_cancel)
        cancel_button.pack(side=tk.RIGHT)

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.bind("<Escape>", self.on_cancel)
        self.wait_window(self)

    def _browse_source(self):
        filetypes = (("Afbeeldingsbestanden", "*.jpg *.jpeg *.png *.gif *.webp *.bmp *.svg"), ("Alle bestanden", "*.*"))
        source_path = filedialog.askopenfilename(title="Selecteer Bron Afbeelding", filetypes=filetypes)
        if source_path: self.source_path_var.set(source_path)

    def _toggle_other_dest(self, event=None):
        self.other_dest_button.config(state=tk.NORMAL if self.dest_rel_path_var.get() == "<Andere...>" else tk.DISABLED)

    def _browse_dest(self):
        dest_dir_abs = filedialog.askdirectory(title="Selecteer Doelmap (binnen website structuur)", initialdir=config.APP_BASE_DIR)
        if dest_dir_abs:
            if not _path_is_inside(config.APP_BASE_DIR, dest_dir_abs):
                messagebox.showwarning("Pad Waarschuwing", "Geselecteerde doelmap ligt buiten de website basis map.", parent=self)
                self.dest_rel_path_var.set("<Andere...>")
                return
            dest_rel_path_posix = str(pathlib.Path(os.path.relpath(dest_dir_abs, config.APP_BASE_DIR)).as_posix())
            self.dest_rel_path_var.set(dest_rel_path_posix)

    def on_ok(self, event=None):
        source_path = self.source_path_var.get()
        dest_choice = self.dest_rel_path_var.get()
        if not source_path: messagebox.showwarning("Invoer Vereist", "Selecteer een bron afbeeldingsbestand.", parent=self); return
        if not dest_choice or dest_choice == "<Andere...>": messagebox.showwarning("Invoer Vereist", "Selecteer of specificeer een doelmap.", parent=self); return

        dest_abs_path_dir = ""
        dest_rel_path_for_callback = ""

        if dest_choice in config.IMAGE_COMMON_DIRS_ABSOLUTE:
            dest_abs_path_dir = config.IMAGE_COMMON_DIRS_ABSOLUTE[dest_choice]
            dest_rel_path_for_callback = dest_choice
        else:
            dest_rel_path_for_callback = dest_choice
            dest_abs_path_dir = os.path.normpath(os.path.join(config.APP_BASE_DIR, dest_choice.replace('/', os.sep)))

        if not dest_abs_path_dir: messagebox.showerror("Fout", "Kon doelmap niet bepalen.", parent=self); return
        if not _path_is_inside(config.APP_BASE_DIR, dest_abs_path_dir):
            messagebox.showerror("Fout", "Doelmap ligt buiten de website structuur.", parent=self)
            return

        if self.callback: self.callback(source_path, dest_abs_path_dir, dest_rel_path_for_callback)
        self.destroy()

    def on_cancel(self, event=None):
        if self.callback: self.callback(None, None, None)
        self.destroy()

class PdfAddDialog(tk.Toplevel):
    def __init__(self, parent, title, callback=None):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.callback = callback
        self.result = None

        frame = ttk.Frame(self, padding="15")
        frame.pack(expand=True, fill=tk.BOTH)
        row_index = 0

        ttk.Label(frame, text="Bron PDF Bestand:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.source_path_var = tk.StringVar()
        source_entry = ttk.Entry(frame, textvariable=self.source_path_var, width=50, state="readonly")
        source_entry.grid(row=row_index, column=1, sticky="ew", padx=5, pady=2)
        browse_button = ttk.Button(frame, text="Bladeren...", command=self._browse_source)
        browse_button.grid(row=row_index, column=2, sticky="w", padx=5, pady=2)
        row_index += 1

        ttk.Label(frame, text="Doelmap:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.dest_rel_path_var = tk.StringVar()
        dest_options = sorted(list(config.PDF_COMMON_DIRS_ABSOLUTE.keys())) + ["<Andere...>"]
        self.dest_combo = ttk.Combobox(frame, textvariable=self.dest_rel_path_var, values=dest_options, state="readonly", width=48)
        self.dest_combo.grid(row=row_index, column=1, sticky="ew", padx=5, pady=2)
        if dest_options and dest_options[0] != "<Andere...>": self.dest_combo.set(dest_options[0])
        else: self.dest_combo.set("")
        self.dest_combo.bind("<<ComboboxSelected>>", self._toggle_other_dest)
        self.other_dest_button = ttk.Button(frame, text="Bladeren...", command=self._browse_dest, state=tk.DISABLED)
        self.other_dest_button.grid(row=row_index, column=2, sticky="w", padx=5, pady=2)
        row_index += 1
        ttk.Label(frame, text="Map relatief t.o.v. website root", style="Desc.TLabel").grid(row=row_index, column=1, sticky="w", padx=5)
        row_index += 1

        frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row_index, column=0, columnspan=3, pady=(15, 0), sticky=tk.E)
        ok_button = ttk.Button(button_frame, text="Voeg PDF Toe", command=self.on_ok)
        ok_button.pack(side=tk.RIGHT, padx=(5, 0))
        cancel_button = ttk.Button(button_frame, text="Annuleren", command=self.on_cancel)
        cancel_button.pack(side=tk.RIGHT)

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.bind("<Escape>", self.on_cancel)
        self.wait_window(self)

    def _browse_source(self):
        filetypes = (("PDF bestanden", "*.pdf"), ("Alle bestanden", "*.*"))
        source_path = filedialog.askopenfilename(title="Selecteer Bron PDF", filetypes=filetypes)
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
            if not _path_is_inside(config.APP_BASE_DIR, dest_dir_abs):
                messagebox.showwarning("Pad Waarschuwing", "Geselecteerde doelmap ligt buiten de website basis map.", parent=self)
                self.dest_rel_path_var.set("<Andere...>")
                return
            dest_rel_path = os.path.relpath(dest_dir_abs, config.APP_BASE_DIR)
            dest_rel_path_posix = str(pathlib.Path(dest_rel_path).as_posix())
            self.dest_rel_path_var.set(dest_rel_path_posix)

    def on_ok(self, event=None):
        source_path = self.source_path_var.get()
        dest_rel_path_or_key = self.dest_rel_path_var.get()
        if not source_path: messagebox.showwarning("Invoer Vereist", "Selecteer een bron PDF bestand.", parent=self); return
        if not dest_rel_path_or_key or dest_rel_path_or_key == "<Andere...>": messagebox.showwarning("Invoer Vereist", "Selecteer een doelmap.", parent=self); return

        dest_abs_path_dir = ""
        dest_rel_path_str = dest_rel_path_or_key

        if dest_rel_path_or_key in config.PDF_COMMON_DIRS_ABSOLUTE:
            dest_abs_path_dir = config.PDF_COMMON_DIRS_ABSOLUTE[dest_rel_path_or_key]
            dest_rel_path_str = dest_rel_path_or_key
        elif os.path.isabs(dest_rel_path_or_key):
            dest_abs_path_dir = dest_rel_path_or_key
            try:
                dest_rel_path_str = str(pathlib.Path(os.path.relpath(dest_abs_path_dir, config.APP_BASE_DIR)).as_posix())
            except ValueError:
                dest_rel_path_str = dest_abs_path_dir
        else:
            dest_abs_path_dir = os.path.abspath(os.path.join(config.APP_BASE_DIR, dest_rel_path_or_key))
            dest_rel_path_str = dest_rel_path_or_key

        if not dest_abs_path_dir:
            messagebox.showerror("Fout", "Kon absoluut doelpad niet bepalen.", parent=self); return
        if not _path_is_inside(config.APP_BASE_DIR, dest_abs_path_dir):
            messagebox.showerror("Fout", "Doelmap ligt buiten de website structuur.", parent=self); return

        if self.callback: self.callback(source_path, dest_abs_path_dir, dest_rel_path_str)
        self.destroy()

    def on_cancel(self, event=None):
        if self.callback: self.callback(None, None, None)
        self.destroy()

class MediaManagerTab:
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance

        self.images_on_filesystem = []
        self.selected_image_data = None
        self._images_scan_running = False
        self._image_preview_widget = None
        self.images_rotate_button = None

        self.pdfs_found_list = []
        self.pdfs_by_abs_path = {}
        self.pdfs_selected_abs_path = None
        self._pdfs_scan_running = False
        self._pdf_preview_image = None

        self._create_main_layout()
        self.reload_data()

    def reload_data(self):
        self._images_scan_files()
        self._pdfs_scan_files()

    def _create_main_layout(self):
        self.parent.grid_rowconfigure(0, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        self.notebook = ttk.Notebook(self.parent)
        self.notebook.grid(row=0, column=0, sticky='nsew')

        image_frame = ttk.Frame(self.notebook, padding=10)
        pdf_frame = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(image_frame, text=" Afbeeldingen Beheren ")
        self.notebook.add(pdf_frame, text=" PDF Bestanden Beheren ")

        self._images_create_widgets(image_frame)
        self._pdfs_create_widgets(pdf_frame)

    def _images_create_widgets(self, parent_frame):
        parent_frame.grid_rowconfigure(0, weight=1); parent_frame.grid_columnconfigure(0, weight=1)
        pw_main = ttk.PanedWindow(parent_frame, orient=tk.HORIZONTAL); pw_main.grid(row=0, column=0, sticky='nsew')
        left_frame = ttk.Frame(pw_main, padding=(0, 0, 5, 0))
        left_frame.grid_rowconfigure(1, weight=1); left_frame.grid_columnconfigure(0, weight=1)

        img_scan_frame = ttk.Frame(left_frame)
        img_scan_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.scan_dirs_button = ttk.Button(img_scan_frame, text="Scan Afbeelding Mappen", command=self._images_scan_files)
        self.scan_dirs_button.pack(side=tk.LEFT, padx=(0, 5))

        img_tree_frame = ttk.Frame(left_frame); img_tree_frame.grid(row=1, column=0, sticky="nsew")
        img_tree_frame.grid_rowconfigure(0, weight=1); img_tree_frame.grid_columnconfigure(0, weight=1)

        img_columns = ('filename', 'path', 'dimensions', 'size')
        self.images_tree = ttk.Treeview(img_tree_frame, columns=img_columns, show='headings', selectmode='browse')
        self.images_tree.heading('filename', text='Bestandsnaam', anchor=tk.W); self.images_tree.column('filename', width=200, minwidth=150, anchor=tk.W, stretch=tk.YES)
        self.images_tree.heading('path', text='Relatief Pad', anchor=tk.W); self.images_tree.column('path', width=300, minwidth=200, anchor=tk.W, stretch=tk.YES)
        self.images_tree.heading('dimensions', text='Dimensies', anchor=tk.W); self.images_tree.column('dimensions', width=100, minwidth=80, anchor=tk.W, stretch=tk.NO)
        self.images_tree.heading('size', text='Grootte', anchor=tk.W); self.images_tree.column('size', width=80, minwidth=70, anchor=tk.W, stretch=tk.NO)

        img_vsb = ttk.Scrollbar(img_tree_frame, orient="vertical", command=self.images_tree.yview); img_hsb = ttk.Scrollbar(img_tree_frame, orient="horizontal", command=self.images_tree.xview)
        self.images_tree.configure(yscrollcommand=img_vsb.set, xscrollcommand=img_hsb.set)
        self.images_tree.grid(row=0, column=0, sticky='nsew'); img_vsb.grid(row=0, column=1, sticky='ns'); img_hsb.grid(row=1, column=0, sticky='ew')
        self.images_tree.bind("<<TreeviewSelect>>", self._images_on_select)

        pw_main.add(left_frame, weight=3)

        right_frame = ttk.Frame(pw_main, padding=(5, 0, 0, 0))
        right_frame.grid_rowconfigure(1, weight=1); right_frame.grid_columnconfigure(0, weight=1)
        img_actions_frame = ttk.Labelframe(right_frame, text=" Afbeelding Acties ", padding=10)
        img_actions_frame.grid(row=0, column=0, sticky="new"); img_actions_frame.columnconfigure(0, weight=1)
        self.images_add_button = ttk.Button(img_actions_frame, text="Nieuwe Afbeelding Kopiëren...", command=self._images_add_dialog)
        self.images_add_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.images_replace_button = ttk.Button(img_actions_frame, text="Vervang Geselecteerd Bestand...", command=self._images_replace_file, state=tk.DISABLED)
        self.images_replace_button.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.images_delete_button = ttk.Button(img_actions_frame, text="Verwijder Geselecteerd Bestand...", command=self._images_delete_file, state=tk.DISABLED)
        self.images_delete_button.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

        img_preview_frame = ttk.Labelframe(right_frame, text=" Voorvertoning ", padding=10)
        img_preview_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0)); img_preview_frame.grid_rowconfigure(0, weight=1); img_preview_frame.grid_columnconfigure(0, weight=1)
        preview_outer_frame = ttk.Frame(img_preview_frame, width=config.IMAGE_PREVIEW_MAX_WIDTH+10, height=config.IMAGE_PREVIEW_MAX_HEIGHT+10)
        preview_outer_frame.grid(row=0, column=0, sticky="nsew"); preview_outer_frame.grid_propagate(False); preview_outer_frame.grid_rowconfigure(0, weight=1); preview_outer_frame.grid_columnconfigure(0, weight=1)
        self.images_preview_label = ttk.Label(preview_outer_frame, text="Selecteer een afbeelding", anchor=tk.CENTER, relief=tk.GROOVE, background="lightgrey")
        self.images_preview_label.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        img_preview_actions = ttk.Frame(img_preview_frame)
        img_preview_actions.grid(row=1, column=0, sticky="ew", padx=5, pady=(5, 0))
        img_preview_actions.columnconfigure(0, weight=1)
        self.images_rotate_button = ttk.Button(img_preview_actions, text="Draai 90 graden", command=self._images_rotate_selected, state=tk.DISABLED)
        self.images_rotate_button.pack(side=tk.LEFT)
        self.images_path_label = ttk.Label(img_preview_frame, text="Pad: ", wraplength=config.IMAGE_PREVIEW_MAX_WIDTH+50, justify=tk.LEFT, style="Desc.TLabel")
        self.images_path_label.grid(row=2, column=0, sticky="ew", padx=5, pady=(5, 0))
        pw_main.add(right_frame, weight=1)

    def _images_scan_files(self):
        if self._images_scan_running: return
        self._images_scan_running = True
        self.scan_dirs_button.config(state=tk.DISABLED, text="Scannen...")
        self.app.set_status("Scannen afbeeldingsmappen...")
        self.app.root.update_idletasks()

        found_images_dict = {}
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg')

        for rel_dir_key, abs_dir_path in config.IMAGE_COMMON_DIRS_ABSOLUTE.items():
            if os.path.isdir(abs_dir_path):
                for root, _, files in os.walk(abs_dir_path):
                    for filename in files:
                        if filename.lower().endswith(image_extensions):
                            abs_filepath = os.path.normpath(os.path.join(root, filename))
                            if abs_filepath in found_images_dict:
                                continue

                            rel_filepath_to_basedir = os.path.relpath(abs_filepath, config.APP_BASE_DIR)
                            web_path = "/" + str(pathlib.Path(rel_filepath_to_basedir).as_posix())

                            dimensions = "N/B"
                            size_kb = "N/B"
                            try:
                                if HAS_PILLOW and Image:
                                    with Image.open(abs_filepath) as img:
                                        dimensions = f"{img.width}x{img.height}"
                                file_size_bytes = os.path.getsize(abs_filepath)
                                size_kb = f"{file_size_bytes / 1024:.1f} KB"
                            except Exception:
                                pass

                            found_images_dict[abs_filepath] = {
                                'filename': filename,
                                'abs_path': abs_filepath,
                                'web_path': web_path,
                                'dimensions': dimensions,
                                'size': size_kb
                            }

        self.images_on_filesystem = list(found_images_dict.values())

        self._images_populate_treeview()
        self.scan_dirs_button.config(state=tk.NORMAL, text="Scan Afbeelding Mappen")
        self.app.set_status(f"{len(self.images_on_filesystem)} unieke afbeeldingen gevonden op schijf.", duration_ms=5000)
        self._images_scan_running = False
        self._images_reset_selection_and_preview()

    def _images_populate_treeview(self):
        self.images_tree.delete(*self.images_tree.get_children())
        sorted_images = sorted(self.images_on_filesystem, key=lambda x: x.get('web_path', '').lower())
        for img_data in sorted_images:
            values = (
                img_data.get('filename', ''),
                img_data.get('web_path', ''),
                img_data.get('dimensions', 'N/B'),
                img_data.get('size', 'N/B')
            )
            self.images_tree.insert('', tk.END, iid=img_data['abs_path'], values=values)
        self._images_on_select()

    def _images_reset_selection_and_preview(self):
        self.selected_image_data = None
        self.images_preview_label.config(image='', text="Selecteer een afbeelding")
        self.images_path_label.config(text="Pad: ")
        self._image_preview_widget = None
        self.images_replace_button.config(state=tk.DISABLED)
        self.images_delete_button.config(state=tk.DISABLED)
        if self.images_rotate_button:
            self.images_rotate_button.config(state=tk.DISABLED)

    def _images_on_select(self, event=None):
        selected_items = self.images_tree.selection()
        if not selected_items:
            self._images_reset_selection_and_preview()
            return

        selected_iid = selected_items[0]
        self.selected_image_data = next((img for img in self.images_on_filesystem if img['abs_path'] == selected_iid), None)

        if not self.selected_image_data:
            messagebox.showerror("Fout", "Geselecteerde afbeelding data niet gevonden.", parent=self.app.root)
            self._images_reset_selection_and_preview()
            return

        self.images_path_label.config(text=f"Pad: {self.selected_image_data.get('web_path', 'N/B')}")
        photo = None
        preview_text = "Voorvertoning N/B"
        abs_path = self.selected_image_data['abs_path']

        if os.path.isfile(abs_path):
            try:
                if HAS_PILLOW and Image and ImageTk:
                    with Image.open(abs_path) as img:
                        if ImageOps:
                            try:
                                img = ImageOps.exif_transpose(img)
                            except Exception:
                                pass
                        img.thumbnail((config.IMAGE_PREVIEW_MAX_WIDTH, config.IMAGE_PREVIEW_MAX_HEIGHT))
                        photo = ImageTk.PhotoImage(img); preview_text = ""
                elif abs_path.lower().endswith(('.png', '.gif')):
                    photo = tk.PhotoImage(file=abs_path)
                    factor = max(1, photo.width() // config.IMAGE_PREVIEW_MAX_WIDTH, photo.height() // config.IMAGE_PREVIEW_MAX_HEIGHT)
                    if factor > 1: photo = photo.subsample(factor, factor)
                    preview_text = ""
                else:
                     preview_text = "Voorvertoning N/B\n(Installeer Pillow)"
            except Exception as e: preview_text = f"Fout Laden Preview:\n{type(e).__name__}"
        else:
            preview_text = "Bestand Niet Gevonden"

        self.images_preview_label.config(image=photo, text=preview_text)
        self._image_preview_widget = photo

        self.images_replace_button.config(state=tk.NORMAL)
        self.images_delete_button.config(state=tk.NORMAL if os.path.isfile(abs_path) else tk.DISABLED)
        if self.images_rotate_button:
            rotate_state = tk.DISABLED
            if HAS_PILLOW and Image and os.path.isfile(abs_path):
                ext = os.path.splitext(abs_path)[1].lower()
                if ext != '.svg':
                    rotate_state = tk.NORMAL
            self.images_rotate_button.config(state=rotate_state)

    def _images_rotate_selected(self):
        if not self.selected_image_data:
            messagebox.showwarning("Selectie Vereist", "Selecteer een afbeelding om te roteren.", parent=self.app.root); return
        if not (HAS_PILLOW and Image):
            messagebox.showwarning("Pillow Vereist", "Roteren vereist Pillow. Installeer Pillow om te roteren.", parent=self.app.root); return

        target_abs_path = self.selected_image_data['abs_path']
        filename = self.selected_image_data.get('filename', os.path.basename(target_abs_path))

        if not os.path.isfile(target_abs_path):
            messagebox.showerror("Fout", f"Bestand niet gevonden:\n{target_abs_path}", parent=self.app.root)
            self._images_scan_files()
            return

        ext = os.path.splitext(target_abs_path)[1].lower()
        if ext == '.svg':
            messagebox.showwarning("Niet Ondersteund", "SVG bestanden kunnen niet geroteerd worden.", parent=self.app.root); return

        if not messagebox.askyesno("Bevestig Roteren",
                                   f"Draai '{filename}' 90 graden met de klok mee?\nHet bestand wordt overschreven.",
                                   icon='warning', parent=self.app.root):
            self.app.set_status("Roteren geannuleerd.", duration_ms=3000); return

        try:
            with Image.open(target_abs_path) as img:
                frame_count = 1
                try:
                    frame_count = getattr(img, "n_frames", 1)
                except Exception:
                    frame_count = 1
                if frame_count > 1:
                    messagebox.showwarning("Animatie behouden", "Deze afbeelding bevat meerdere frames. Roteren is niet beschikbaar voor animaties.", parent=self.app.root)
                    return
                rotated = img.transpose(Image.ROTATE_270)
                save_kwargs = {}
                save_format = img.format
                if img.format == "JPEG":
                    save_format = "JPEG"
                    save_kwargs = {"quality": 95, "subsampling": 0, "optimize": True}
                elif img.format == "WEBP":
                    save_kwargs = {"quality": 95}
                if hasattr(img, "getexif"):
                    try:
                        exif = img.getexif()
                    except Exception:
                        exif = None
                    if exif:
                        exif[274] = 1
                        save_kwargs["exif"] = exif.tobytes()
                icc_profile = img.info.get("icc_profile")
                if icc_profile:
                    save_kwargs["icc_profile"] = icc_profile
                output = io.BytesIO()
                rotated.save(output, format=save_format, **save_kwargs)
            utils.atomic_write_bytes(target_abs_path, output.getvalue())
        except Exception as e:
            messagebox.showerror("Fout bij Roteren", f"Kon afbeelding niet roteren:\n{e}", parent=self.app.root)
            self.app.set_status(f"Fout bij roteren '{filename}': {e}", is_error=True)
            return

        self.app.set_status(f"Afbeelding '{filename}' geroteerd.", duration_ms=5000)
        self._images_scan_files()
        if self.images_tree.exists(target_abs_path):
            self.images_tree.selection_set(target_abs_path)
            self.images_tree.focus(target_abs_path)
            self.images_tree.see(target_abs_path)
            self._images_on_select()

    def _images_add_dialog(self):
        ImageAddDialog(self.app.root, "Nieuwe Afbeelding Kopiëren", self._images_process_add)

    def _images_process_add(self, source_path_abs, dest_dir_abs, dest_dir_rel_display):
        if not source_path_abs or not dest_dir_abs:
            self.app.set_status("Toevoegen afbeelding geannuleerd.", duration_ms=3000); return

        filename = os.path.basename(source_path_abs)
        final_dest_abs_path = os.path.join(dest_dir_abs, filename)

        try:
            if not os.path.isdir(dest_dir_abs):
                os.makedirs(dest_dir_abs, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Map Fout", f"Kon doelmap niet aanmaken:\n{dest_dir_abs}\nFout: {e}", parent=self.app.root)
            self.app.set_status(f"Fout bij aanmaken map: {e}", is_error=True); return

        if os.path.exists(final_dest_abs_path):
            if not messagebox.askyesno("Bevestig Overschrijven",
                                       f"Bestand '{filename}' bestaat al in '{dest_dir_rel_display}'.\nOverschrijven?",
                                       icon='warning', parent=self.app.root):
                self.app.set_status("Toevoegen geannuleerd (overschrijven geweigerd).", duration_ms=4000); return
        try:
            utils.atomic_copy_file(source_path_abs, final_dest_abs_path)
            self.app.set_status(f"Afbeelding '{filename}' gekopieerd naar '{dest_dir_rel_display}'.", duration_ms=6000)
            self._images_scan_files()
            if self.images_tree.exists(final_dest_abs_path):
                self.images_tree.selection_set(final_dest_abs_path)
                self.images_tree.focus(final_dest_abs_path)
                self.images_tree.see(final_dest_abs_path)
                self._images_on_select()

        except Exception as e:
            messagebox.showerror("Fout bij Kopiëren", f"Kon afbeelding niet kopiëren:\n{e}", parent=self.app.root)
            self.app.set_status(f"Fout bij kopiëren '{filename}': {e}", is_error=True)

    def _images_replace_file(self):
        if not self.selected_image_data:
            messagebox.showwarning("Selectie Vereist", "Selecteer een afbeelding om te vervangen.", parent=self.app.root); return

        target_abs_path = self.selected_image_data['abs_path']
        filename = self.selected_image_data['filename']
        filetypes = (("Afbeeldingsbestanden", "*.jpg *.jpeg *.png *.gif *.webp *.bmp *.svg"), ("Alle bestanden", "*.*"))

        if not os.path.isfile(target_abs_path):
             messagebox.showerror("Fout", f"Origineel bestand niet gevonden:\n{target_abs_path}\nKan niet vervangen.", parent=self.app.root)
             self._images_scan_files()
             return

        if not messagebox.askyesno("Bevestig Vervangen",
                                   f"Dit vervangt het bestand '{filename}'\nmet een nieuwe afbeelding.\nDe webpaden die naar dit bestand verwijzen blijven werken.\n\nDoorgaan?",
                                   icon='warning', parent=self.app.root):
            self.app.set_status("Vervangen geannuleerd.", duration_ms=3000); return

        new_source_path = filedialog.askopenfilename(title=f"Selecteer NIEUW bestand voor '{filename}'", filetypes=filetypes, parent=self.app.root)
        if not new_source_path:
            self.app.set_status("Vervangen geannuleerd (geen bestand geselecteerd).", duration_ms=3000); return

        try:
            extensions = {'.jpeg': '.jpg', '.tif': '.tiff'}
            source_extension = extensions.get(os.path.splitext(new_source_path)[1].lower(), os.path.splitext(new_source_path)[1].lower())
            target_extension = extensions.get(os.path.splitext(target_abs_path)[1].lower(), os.path.splitext(target_abs_path)[1].lower())
            if source_extension != target_extension:
                raise ValueError("Kies een afbeelding in hetzelfde bestandsformaat als het bestaande bestand.")
            if HAS_PILLOW and target_extension != '.svg':
                with Image.open(new_source_path) as source_image, Image.open(target_abs_path) as target_image:
                    if source_image.format != target_image.format:
                        raise ValueError("Het afbeeldingsformaat komt niet overeen met het bestaande bestand.")
            utils.atomic_copy_file(new_source_path, target_abs_path)
            self.app.set_status(f"Bestand '{filename}' succesvol vervangen.", duration_ms=5000)
            self._images_scan_files()
            if self.images_tree.exists(target_abs_path):
                 self.images_tree.selection_set(target_abs_path)
                 self._images_on_select()
        except Exception as e:
            messagebox.showerror("Fout bij Vervangen", f"Kon bestand niet vervangen:\n{e}", parent=self.app.root)
            self.app.set_status(f"Fout bij vervangen '{filename}': {e}", is_error=True)

    def _images_delete_file(self):
        if not self.selected_image_data:
            messagebox.showwarning("Selectie Vereist", "Selecteer een afbeelding om te verwijderen.", parent=self.app.root); return

        target_abs_path = self.selected_image_data['abs_path']
        filename = self.selected_image_data['filename']

        if not os.path.isfile(target_abs_path):
             messagebox.showerror("Fout", f"Bestand niet gevonden:\n{target_abs_path}\nKan niet verwijderen.", parent=self.app.root)
             self._images_scan_files(); return

        warning_msg = (f"VERWIJDER het bestand:\n'{filename}'\nvan de harde schijf?\n\n"
                       "Dit kan gebroken afbeeldingen op uw website veroorzaken als het ergens gebruikt wordt.\n"
                       "Deze actie kan NIET ongedaan gemaakt worden.")
        if not messagebox.askyesno("Bevestig Verwijdering", warning_msg, icon='error', default=messagebox.NO, parent=self.app.root):
            self.app.set_status("Verwijderen geannuleerd.", duration_ms=3000); return

        try:
            os.remove(target_abs_path)
            self.app.set_status(f"Bestand '{filename}' succesvol verwijderd.", duration_ms=5000)
            self._images_scan_files()
        except Exception as e:
            messagebox.showerror("Fout bij Verwijderen", f"Kon bestand niet verwijderen:\n{e}", parent=self.app.root)
            self.app.set_status(f"Fout bij verwijderen '{filename}': {e}", is_error=True)

    def _pdfs_create_widgets(self, parent_frame):
        parent_frame.grid_rowconfigure(0, weight=1)
        parent_frame.grid_columnconfigure(0, weight=1)

        pw_main = ttk.PanedWindow(parent_frame, orient=tk.HORIZONTAL)
        pw_main.grid(row=0, column=0, sticky='nsew')

        left_frame = ttk.Frame(pw_main, padding=(0, 0, 5, 0))
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        pdf_scan_frame = ttk.Frame(left_frame)
        pdf_scan_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.pdfs_refresh_button = ttk.Button(pdf_scan_frame, text="Scan 'docs' Map voor PDFs", command=self._pdfs_scan_files)
        self.pdfs_refresh_button.pack(side=tk.LEFT, padx=(0, 5))

        pdf_tree_frame = ttk.Frame(left_frame)
        pdf_tree_frame.grid(row=1, column=0, sticky="nsew")
        pdf_tree_frame.grid_rowconfigure(0, weight=1)
        pdf_tree_frame.grid_columnconfigure(0, weight=1)
        pdf_columns = ('filename', 'path', 'exists')
        self.pdfs_tree = ttk.Treeview(pdf_tree_frame, columns=pdf_columns, show='headings', selectmode='browse')
        self.pdfs_tree.heading('filename', text='Bestandsnaam', anchor=tk.W); self.pdfs_tree.column('filename', width=200, minwidth=150, anchor=tk.W)
        self.pdfs_tree.heading('path', text='Relatief Pad', anchor=tk.W); self.pdfs_tree.column('path', width=350, minwidth=250, anchor=tk.W)
        self.pdfs_tree.heading('exists', text='Bestaat?', anchor=tk.CENTER); self.pdfs_tree.column('exists', width=60, minwidth=50, anchor=tk.CENTER, stretch=tk.NO)
        pdf_vsb = ttk.Scrollbar(pdf_tree_frame, orient="vertical", command=self.pdfs_tree.yview)
        pdf_hsb = ttk.Scrollbar(pdf_tree_frame, orient="horizontal", command=self.pdfs_tree.xview)
        self.pdfs_tree.configure(yscrollcommand=pdf_vsb.set, xscrollcommand=pdf_hsb.set)
        self.pdfs_tree.grid(row=0, column=0, sticky='nsew'); pdf_vsb.grid(row=0, column=1, sticky='ns'); pdf_hsb.grid(row=1, column=0, sticky='ew')
        self.pdfs_tree.bind("<<TreeviewSelect>>", self._pdfs_on_select)
        self.pdfs_tree.tag_configure('missing', foreground='red')

        pw_main.add(left_frame, weight=2)

        right_frame = ttk.Frame(pw_main, padding=(5, 0, 0, 0))
        right_frame.grid_rowconfigure(0, weight=0)
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        pdf_actions_frame = ttk.Labelframe(right_frame, text=" PDF Acties ", padding=10)
        pdf_actions_frame.grid(row=0, column=0, sticky="new", pady=(0, 10))
        pdf_actions_frame.columnconfigure(0, weight=1)
        self.pdfs_add_button = ttk.Button(pdf_actions_frame, text="Nieuwe PDF Toevoegen...", command=self._pdfs_add_dialog)
        self.pdfs_add_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.pdfs_change_button = ttk.Button(pdf_actions_frame, text="Wijzig/Voeg Geselecteerd Bestand Toe...", command=self._pdfs_change, state=tk.DISABLED)
        self.pdfs_change_button.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.pdfs_delete_button = ttk.Button(pdf_actions_frame, text="Verwijder Geselecteerd PDF Bestand...", command=self._pdfs_delete, state=tk.DISABLED)
        self.pdfs_delete_button.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        ttk.Label(pdf_actions_frame,
                  text=("Selecteer een rij in de lijst.\n"
                        "Gebruik 'Wijzig/Voeg Toe' om:\n"
                        " - Een BESTAAND bestand te vervangen.\n"
                        " - Een ONTBREKEND bestand toe te voegen.\n"
                        "'Verwijder' werkt enkel op bestaande bestanden."),
                  justify=tk.LEFT, style="Warning.TLabel").grid(row=3, column=0, padx=5, pady=(10, 5), sticky="w")

        pdf_preview_frame = ttk.Labelframe(right_frame, text=" Voorvertoning (Pagina 1) ", padding=10)
        pdf_preview_frame.grid(row=1, column=0, sticky="nsew")
        pdf_preview_frame.grid_rowconfigure(0, weight=1)
        pdf_preview_frame.grid_columnconfigure(0, weight=1)

        preview_max_w = getattr(config, 'PDF_PREVIEW_MAX_WIDTH', 300)
        preview_max_h = getattr(config, 'PDF_PREVIEW_MAX_HEIGHT', 400)
        preview_outer_frame = ttk.Frame(pdf_preview_frame, width=preview_max_w + 10, height=preview_max_h + 10)
        preview_outer_frame.grid(row=0, column=0, sticky="nsew")
        preview_outer_frame.grid_propagate(False)
        preview_outer_frame.grid_rowconfigure(0, weight=1)
        preview_outer_frame.grid_columnconfigure(0, weight=1)

        self.pdfs_preview_label = ttk.Label(preview_outer_frame, text="Selecteer een PDF", anchor=tk.CENTER, relief=tk.GROOVE, background="lightgrey")
        self.pdfs_preview_label.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.pdfs_path_label = ttk.Label(pdf_preview_frame, text="Pad: ", wraplength=preview_max_w + 50, justify=tk.LEFT, style="Desc.TLabel")
        self.pdfs_path_label.grid(row=1, column=0, sticky="ew", padx=5, pady=(5, 0))

        pw_main.add(right_frame, weight=1)

    def _pdfs_scan_files(self):
        if self._pdfs_scan_running: return
        self._pdfs_scan_running = True
        self.pdfs_refresh_button.config(state=tk.DISABLED, text="Scannen...")
        self.app.set_status("Scannen 'docs' map voor PDF bestanden...")
        self.app.root.update_idletasks()

        self.pdfs_found_list = []
        self.pdfs_by_abs_path = {}
        self._pdfs_clear_treeview()
        self._pdfs_reset_right_pane()

        try:
            self.pdfs_found_list = utils.pdfs_parse_file(config.APP_BASE_DIR)
        except Exception as e:
            print(f"Fout bij scannen 'docs' map voor PDFs: {e}")
            traceback.print_exc()

        self._pdfs_process_found_list()
        self._pdfs_populate_treeview()

        self.pdfs_refresh_button.config(state=tk.NORMAL, text="Scan 'docs' Map voor PDFs")
        self._pdfs_scan_running = False
        status_msg = f"Scan voltooid. {len(self.pdfs_by_abs_path)} PDF bestanden gevonden in de 'docs' map."
        self.app.set_status(status_msg, duration_ms=8000)

    def _pdfs_process_found_list(self):
        self.pdfs_by_abs_path = {}
        for pdf_ref in self.pdfs_found_list:
            abs_path = pdf_ref.get('abs_path')
            if not abs_path: continue
            if abs_path not in self.pdfs_by_abs_path:
                self.pdfs_by_abs_path[abs_path] = {
                    'exists': pdf_ref.get('exists', False),
                    'treeview_iid': None
                }

    def _pdfs_clear_treeview(self):
        for item in self.pdfs_tree.get_children():
            try: self.pdfs_tree.delete(item)
            except tk.TclError: print(f"Warning: Could not delete pdf tree item {item}")
        for k, v in self.pdfs_by_abs_path.items():
             if isinstance(v, dict): v['treeview_iid'] = None

    def _pdfs_populate_treeview(self):
        self._pdfs_clear_treeview()
        sorted_abs_paths = sorted(self.pdfs_by_abs_path.keys())
        for abs_path in sorted_abs_paths:
            pdf_data = self.pdfs_by_abs_path[abs_path]
            try:
                filename = os.path.basename(abs_path)
                try: display_path = str(pathlib.Path(os.path.relpath(abs_path, config.APP_BASE_DIR)).as_posix())
                except ValueError: display_path = abs_path
                exists_str = "Ja" if pdf_data['exists'] else "NEE"
                values = (filename, display_path, exists_str)
                item_iid = abs_path
                tags = ('pdf_row',)
                if not pdf_data['exists']: tags += ('missing',)
                self.pdfs_tree.insert('', tk.END, iid=item_iid, values=values, tags=tags)
                pdf_data['treeview_iid'] = item_iid
            except Exception as e:
                print(f"Error adding PDF to treeview: {abs_path} - {e}")
                self.app.set_status(f"Fout bij weergeven PDF in lijst: {os.path.basename(abs_path)}", is_error=True)

    def _pdfs_reset_right_pane(self):
        self.pdfs_selected_abs_path = None
        self.pdfs_preview_label.config(image='', text="Selecteer een PDF")
        self.pdfs_path_label.config(text="Pad: ")
        self._pdf_preview_image = None
        self.pdfs_change_button.config(state=tk.DISABLED)
        self.pdfs_delete_button.config(state=tk.DISABLED)

    def _pdfs_on_select(self, event=None):
        selected_items = self.pdfs_tree.selection()
        if not selected_items:
            self._pdfs_reset_right_pane()
            return

        selected_iid = selected_items[0]
        self.pdfs_selected_abs_path = selected_iid

        if selected_iid not in self.pdfs_by_abs_path:
             messagebox.showerror("Fout", "Geselecteerde PDF data niet gevonden.\nScan a.u.b. opnieuw.", parent=self.app.root)
             self._pdfs_reset_right_pane()
             return

        pdf_data = self.pdfs_by_abs_path[selected_iid]
        abs_path = selected_iid
        exists = pdf_data['exists']

        try: display_path = self.pdfs_tree.item(selected_iid, 'values')[1]
        except (tk.TclError, IndexError): display_path = "Pad N/B"
        self.pdfs_path_label.config(text=f"Pad: {display_path}")

        photo = None
        preview_text = "Voorvertoning N/B"

        if exists:
            if HAS_PYMUPDF and HAS_PILLOW:
                try:
                    doc = fitz.open(abs_path)
                    if doc.page_count > 0:
                        page = doc.load_page(0)
                        preview_max_w = getattr(config, 'PDF_PREVIEW_MAX_WIDTH', 300)
                        preview_max_h = getattr(config, 'PDF_PREVIEW_MAX_HEIGHT', 400)
                        page_rect = page.rect
                        zoom_x = preview_max_w / page_rect.width
                        zoom_y = preview_max_h / page_rect.height
                        zoom = min(zoom_x, zoom_y, 1.0)
                        mat = fitz.Matrix(zoom, zoom)
                        pix = page.get_pixmap(matrix=mat, alpha=False)
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        photo = ImageTk.PhotoImage(img)
                        preview_text = ""
                    else:
                        preview_text = "PDF heeft geen pagina's"
                    doc.close()
                except fitz.fitz.FileNotFoundError:
                    preview_text = "Bestand niet gevonden"; exists = False; pdf_data['exists'] = False
                    if self.pdfs_tree.exists(selected_iid):
                        values = list(self.pdfs_tree.item(selected_iid, 'values')); values[2] = "NEE"
                        self.pdfs_tree.item(selected_iid, values=tuple(values), tags=('pdf_row', 'missing'))
                except Exception as e:
                    preview_text = f"Fout bij PDF Voorvertoning:\n{type(e).__name__}"
                    print(f"Error rendering PDF preview for {abs_path}: {e}")
                    traceback.print_exc()
            else:
                preview_text = "Voorvertoning N/B\n(PyMuPDF/Pillow nodig)"
        else:
            preview_text = "PDF Bestand Niet Gevonden\n(Klik 'Wijzig/Voeg Toe...' om toe te voegen)"

        self.pdfs_preview_label.config(image=photo, text=preview_text)
        self._pdf_preview_image = photo

        self.pdfs_change_button.config(state=tk.NORMAL)
        self.pdfs_delete_button.config(state=tk.NORMAL if exists else tk.DISABLED)

    def _pdfs_add_dialog(self):
        PdfAddDialog(self.app.root, "Nieuw PDF Bestand Toevoegen", self._pdfs_process_add)

    def _pdfs_process_add(self, source_path, dest_dir_abs, dest_dir_rel):
        if not source_path or not dest_dir_abs or not dest_dir_rel:
            self.app.set_status("Toevoegen PDF geannuleerd.", duration_ms=3000); return
        filename = os.path.basename(source_path)
        dest_path_abs = os.path.join(dest_dir_abs, filename)
        try: os.makedirs(dest_dir_abs, exist_ok=True)
        except OSError as e: messagebox.showerror("Map Fout", f"Kon map niet maken:\n{dest_dir_abs}\nFout: {e}", parent=self.app.root); return
        if os.path.exists(dest_path_abs):
            if not messagebox.askyesno("Bevestig Overschrijven", f"'{filename}' bestaat al.\nVervangen?", icon='warning', parent=self.app.root):
                self.app.set_status("Toevoegen PDF geannuleerd.", duration_ms=4000); return
        try:
            utils.atomic_copy_file(source_path, dest_path_abs)
            self.app.set_status(f"PDF '{filename}' toegevoegd.", duration_ms=8000)
            if dest_path_abs in self.pdfs_by_abs_path:
                pdf_data = self.pdfs_by_abs_path[dest_path_abs]; pdf_data['exists'] = True
                if pdf_data.get('treeview_iid') and self.pdfs_tree.exists(pdf_data['treeview_iid']):
                    values = list(self.pdfs_tree.item(pdf_data['treeview_iid'], 'values')); values[2] = "Ja"
                    self.pdfs_tree.item(pdf_data['treeview_iid'], values=tuple(values), tags=('pdf_row',))
                    self.pdfs_tree.selection_set(pdf_data['treeview_iid']); self._pdfs_on_select()
            else:
                new_pdf_data = { 'exists': True, 'treeview_iid': dest_path_abs }
                self.pdfs_by_abs_path[dest_path_abs] = new_pdf_data
                try: display_path = str(pathlib.Path(os.path.relpath(dest_path_abs, config.APP_BASE_DIR)).as_posix())
                except ValueError: display_path = dest_path_abs
                values = (filename, display_path, "Ja")
                self.pdfs_tree.insert('', tk.END, iid=dest_path_abs, values=values, tags=('pdf_row',))
                self.pdfs_tree.see(dest_path_abs); self.pdfs_tree.selection_set(dest_path_abs); self._pdfs_on_select()
        except Exception as e: messagebox.showerror("Fout bij Toevoegen", f"Kon PDF niet kopiëren:\n{e}", parent=self.app.root)

    def _pdfs_change(self):
        if not self.pdfs_selected_abs_path: messagebox.showwarning("Selectie Vereist", "Selecteer PDF.", parent=self.app.root); return
        target_abs_path = self.pdfs_selected_abs_path; filename = os.path.basename(target_abs_path)
        filetypes = (("PDF bestanden", "*.pdf"), ("Alle bestanden", "*.*"))
        if target_abs_path not in self.pdfs_by_abs_path: messagebox.showerror("Fout", "PDF data niet gevonden.", parent=self.app.root); self._pdfs_reset_right_pane(); return
        pdf_data = self.pdfs_by_abs_path[target_abs_path]

        if pdf_data['exists']:
            if not os.path.isfile(target_abs_path):
                 messagebox.showerror("Fout", f"PDF niet gevonden op schijf:\n{target_abs_path}", parent=self.app.root)
                 pdf_data['exists'] = False; self._pdfs_on_select(); return
            if not messagebox.askyesno("Bevestig Wijzigen", f"VERVANG bestand '{filename}'?", icon='warning', parent=self.app.root):
                 self.app.set_status("Wijzigen geannuleerd.", duration_ms=3000); return
            new_source_path = filedialog.askopenfilename(title=f"Selecteer NIEUWE PDF voor '{filename}'", filetypes=filetypes, parent=self.app.root)
            if not new_source_path: self.app.set_status("Wijzigen geannuleerd.", duration_ms=3000); return
            self.app.set_status(f"Vervangen '{filename}'..."); self.app.root.update_idletasks()
            try:
                utils.atomic_copy_file(new_source_path, target_abs_path)
                self.app.set_status(f"PDF '{filename}' vervangen.", duration_ms=5000)
                self._pdfs_on_select()
            except Exception as e: messagebox.showerror("Fout bij Wijzigen", f"Kon niet vervangen:\n{e}", parent=self.app.root)
        else:
            source_path = filedialog.askopenfilename(title=f"Selecteer PDF om toe te voegen als '{filename}'", filetypes=filetypes, parent=self.app.root)
            if not source_path: self.app.set_status("Toevoegen geannuleerd.", duration_ms=3000); return
            self.app.set_status(f"Toevoegen '{filename}'..."); self.app.root.update_idletasks()
            try:
                dest_dir = os.path.dirname(target_abs_path); os.makedirs(dest_dir, exist_ok=True)
                utils.atomic_copy_file(source_path, target_abs_path)
                pdf_data['exists'] = True
                if self.pdfs_tree.exists(target_abs_path):
                    values = list(self.pdfs_tree.item(target_abs_path, 'values')); values[2] = "Ja"
                    self.pdfs_tree.item(target_abs_path, values=tuple(values), tags=('pdf_row',))
                self.app.set_status(f"PDF '{filename}' toegevoegd.", duration_ms=5000)
                self.pdfs_tree.selection_set(target_abs_path); self._pdfs_on_select()
            except OSError as e: messagebox.showerror("Map Fout", f"Kon map niet maken:\n{e}", parent=self.app.root)
            except Exception as e: messagebox.showerror("Fout bij Toevoegen", f"Kon niet kopiëren:\n{e}", parent=self.app.root)

    def _pdfs_delete(self):
        if not self.pdfs_selected_abs_path: messagebox.showwarning("Selectie Vereist", "Selecteer PDF.", parent=self.app.root); return
        target_abs_path = self.pdfs_selected_abs_path; pdf_data = self.pdfs_by_abs_path.get(target_abs_path)
        if not pdf_data or not pdf_data['exists']: messagebox.showerror("Fout", "PDF niet gevonden/bestaat niet.", parent=self.app.root); self._pdfs_reset_right_pane(); return
        filename = os.path.basename(target_abs_path)
        warning_msg = f"VERWIJDER bestand '{filename}'?\n\n"
        warning_msg += "WAARSCHUWING: Dit kan gebroken links op de website veroorzaken.\n\n"
        warning_msg += "Deze actie kan NIET ongedaan gemaakt worden. Weet u het zeker?"
        if not messagebox.askyesno("Bevestig Verwijdering", warning_msg, icon='error', parent=self.app.root):
            self.app.set_status("Verwijderen geannuleerd.", duration_ms=3000); return
        self.app.set_status(f"Verwijderen '{filename}'..."); self.app.root.update_idletasks()
        try:
            os.remove(target_abs_path); self.app.set_status(f"PDF '{filename}' verwijderd.", duration_ms=5000)
            pdf_data['exists'] = False
            if pdf_data.get('treeview_iid') and self.pdfs_tree.exists(pdf_data['treeview_iid']):
                 values = list(self.pdfs_tree.item(pdf_data['treeview_iid'], 'values')); values[2] = "NEE"
                 self.pdfs_tree.item(pdf_data['treeview_iid'], values=tuple(values), tags=('pdf_row', 'missing'))
            self._pdfs_reset_right_pane()
        except FileNotFoundError:
             messagebox.showwarning("Verwijder Waarschuwing", "Bestand was al weg.", parent=self.app.root)
             pdf_data['exists'] = False; self._pdfs_reset_right_pane();
        except Exception as e: messagebox.showerror("Fout bij Verwijderen", f"Kon niet verwijderen:\n{e}", parent=self.app.root)

def create_media_manager_tab(parent_frame, app_instance):
    return MediaManagerTab(parent_frame, app_instance)

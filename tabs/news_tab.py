import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, colorchooser, simpledialog
import datetime
import os
import shutil
import re
import html
import uuid

# Ideally, these should be provided by your environment.
# We import them to keep compatibility with your existing structure.
import config
import utils

# --- Constants for Styling ---
PAD_X = 10
PAD_Y = 5
BUTTON_WIDTH = 4

class Tooltip:
    """
    A unified Tooltip class for providing hover information on widgets.
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window:
            return

        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        if event is not None:
            x = event.x_root + 12
            y = event.y_root + 12

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        # Improved styling for the tooltip
        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            justify='left',
            background="#ffffe0",
            foreground="#000000",
            relief='solid',
            borderwidth=1,
            font=("Segoe UI", "8", "normal"),
            padx=3, pady=1
        )
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class NewsTab:
    """
    Main tab for managing News articles: Creating, Editing, Listing, and Deleting.
    Includes a Rich Text Editor.
    """
    SAFE_HREF_SCHEMES = {"http", "https", "mailto", "tel"}
    HREF_SCHEME_RE = re.compile(r'^([a-z][a-z0-9+.-]*):', re.I)
    UNSAFE_HREF_RE = re.compile(r'[\s<>"\']')

    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance
        self.news_data = []
        self.currently_editing_id = None
        self._saved_form_snapshot = None
        self._news_loaded = False

        # Mapping specific tag names (like alink_1) to their URL destinations
        self.anchor_tag_map = {}
        self._alink_counter = 1

        # Icons map
        self.icons = {
            "bold": "𝗕", "color": "🎨", "link": "🔗", "email": "✉️",
            "tel": "📞", "doc": "📄", "upload": "📤", "save": "💾",
            "clear": "🧹", "delete": "🗑️", "refresh": "🔄",
            "edit": "✏️"
        }

        self._create_widgets()
        self._configure_initial_text_tags()
        self._news_load_and_populate_treeview()
        self._update_toolbar_state()
        self._saved_form_snapshot = self._form_snapshot()
        utils.cleanup_pending_assets(self)

    def _form_snapshot(self):
        return tuple(entry.get() for entry in (self.news_entry_date, self.news_entry_title, self.news_entry_category,
                                               self.news_entry_image, self.news_entry_summary)) + (self._get_text_content_as_html(),)

    def has_unsaved_changes(self):
        return self._saved_form_snapshot is not None and self._form_snapshot() != self._saved_form_snapshot

    def _create_widgets(self):
        """Builds the main UI structure."""
        self.parent.grid_rowconfigure(0, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        main_frame = ttk.Frame(self.parent, padding=PAD_X)
        main_frame.grid(row=0, column=0, sticky='nsew')
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Vertical Split: Form (Top) vs List (Bottom)
        paned_window = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned_window.grid(row=0, column=0, sticky='nsew')

        form_pane = self._create_form_pane(paned_window)
        paned_window.add(form_pane, weight=3)

        list_pane = self._create_list_pane(paned_window)
        paned_window.add(list_pane, weight=2)

    def _create_form_pane(self, parent):
        """Creates the top section: Metadata fields and the Text Editor."""
        form_frame = ttk.Frame(parent, padding=(0, 0, 0, 10))
        form_frame.grid_columnconfigure(0, weight=1)
        form_frame.grid_rowconfigure(1, weight=1)

        # 1. Metadata Inputs
        meta_frame = self._create_meta_frame(form_frame)
        meta_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))

        # 2. Rich Text Editor
        editor_frame = self._create_editor_frame(form_frame)
        editor_frame.grid(row=1, column=0, sticky='nsew')

        # 3. Form Action Buttons (Save/Clear)
        action_frame = self._create_action_buttons_frame(form_frame)
        action_frame.grid(row=2, column=0, sticky='e', pady=(10, 0))

        return form_frame

    def _create_meta_frame(self, parent):
        """Creates inputs for Title, Date, Category, etc."""
        meta = ttk.Labelframe(parent, text=" Artikel Details ", padding=PAD_X)
        meta.grid_columnconfigure(1, weight=1)
        meta.grid_columnconfigure(3, weight=1)

        # Hidden ID field
        self.news_entry_id = ttk.Entry(meta)

        # Row 0: Date and Category (swapped positions for better flow)
        ttk.Label(meta, text="Datum (YYYY-MM-DD):*").grid(column=0, row=0, sticky=tk.W, padx=5, pady=PAD_Y)
        self.news_entry_date = ttk.Entry(meta)
        self.news_entry_date.grid(column=1, row=0, sticky='ew', padx=5, pady=PAD_Y)
        self.news_entry_date.insert(0, datetime.date.today().isoformat())

        ttk.Label(meta, text="Categorie:").grid(column=2, row=0, sticky=tk.W, padx=(20, 5), pady=PAD_Y)
        self.news_entry_category = ttk.Entry(meta)
        self.news_entry_category.grid(column=3, row=0, sticky='ew', padx=5, pady=PAD_Y)
        self.news_entry_category.insert(0, config.NEWS_DEFAULT_CATEGORY)

        # Row 1: Title
        ttk.Label(meta, text="Titel:*").grid(column=0, row=1, sticky=tk.W, padx=5, pady=PAD_Y)
        self.news_entry_title = ttk.Entry(meta)
        self.news_entry_title.grid(column=1, row=1, columnspan=3, sticky='ew', padx=5, pady=PAD_Y)

        # Row 2: Image Upload
        ttk.Label(meta, text="Afbeelding:").grid(column=0, row=2, sticky=tk.W, padx=5, pady=PAD_Y)
        img_wrap = ttk.Frame(meta)
        img_wrap.grid(column=1, row=2, columnspan=3, sticky='ew', padx=5, pady=PAD_Y)
        img_wrap.grid_columnconfigure(0, weight=1)

        self.news_entry_image = ttk.Entry(img_wrap)
        self.news_entry_image.grid(column=0, row=0, sticky='ew', padx=(0, 6))

        upload_btn = ttk.Button(img_wrap, text=self.icons["upload"], command=self._news_browse_image, width=BUTTON_WIDTH)
        upload_btn.grid(column=1, row=0, sticky='e')
        Tooltip(upload_btn, "Upload Afbeelding")

        # Row 3: Summary
        ttk.Label(meta, text="Korte Samenvatting:").grid(column=0, row=3, sticky=tk.W, padx=5, pady=PAD_Y)
        self.news_entry_summary = ttk.Entry(meta)
        self.news_entry_summary.grid(column=1, row=3, columnspan=3, sticky='ew', padx=5, pady=PAD_Y)

        return meta

    def _create_editor_frame(self, parent):
        """Creates the Rich Text Editor with Toolbar."""
        editor_box = ttk.Labelframe(parent, text=" Inhoud ", padding=PAD_X)
        editor_box.grid_rowconfigure(1, weight=1)
        editor_box.grid_columnconfigure(0, weight=1)

        # Toolbar
        toolbar = self._create_editor_toolbar(editor_box)
        toolbar.grid(row=0, column=0, sticky='ew', pady=(0, 8))

        # Text Area
        base_px = 16.8
        self.news_text_full_content = scrolledtext.ScrolledText(
            editor_box,
            width=92, height=13,
            wrap=tk.WORD,
            relief=tk.SUNKEN,
            borderwidth=1,
            font=(self.app.default_font_family, int(round(base_px))),
            undo=True
        )
        self.news_text_full_content.grid(row=1, column=0, sticky='nsew')

        # Bindings for toolbar state updates
        self.news_text_full_content.bind("<<Selection>>", self._update_toolbar_state)
        self.news_text_full_content.bind("<KeyRelease>", self._update_toolbar_state)
        self.news_text_full_content.bind("<ButtonRelease-1>", self._update_toolbar_state)
        self.news_text_full_content.bind("<Button-3>", self._show_context_menu)

        return editor_box

    def _create_editor_toolbar(self, parent):
        """Creates the toolbar buttons grouped logically."""
        toolbar = ttk.Frame(parent)

        # Group 1: Text Style
        self.news_button_bold = ttk.Button(toolbar, text=self.icons["bold"], command=self._news_toggle_bold, width=BUTTON_WIDTH)
        self.news_button_bold.pack(side=tk.LEFT, padx=(0, 2))
        Tooltip(self.news_button_bold, "Vetgedrukt (Ctrl+B)")

        self.news_button_color = ttk.Button(toolbar, text=self.icons["color"], command=self._news_apply_color, width=BUTTON_WIDTH)
        self.news_button_color.pack(side=tk.LEFT, padx=(0, 2))
        Tooltip(self.news_button_color, "Tekstkleur")

        self.font_size_var = tk.StringVar(value="16.8")
        font_sizes = [str(v) for v in (10, 11, 12, 13, 14, 15, 16, 16.8, 18, 20, 24, 28, 32)]
        self.font_size_combo = ttk.Combobox(toolbar, textvariable=self.font_size_var, width=5, state="readonly", values=font_sizes)
        self.font_size_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.font_size_combo.bind("<<ComboboxSelected>>", self._news_apply_font_size)
        Tooltip(self.font_size_combo, "Lettergrootte")

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=(5, 5), fill='y')

        # Group 2: Links
        self.link_btn = ttk.Button(toolbar, text=self.icons["link"], width=BUTTON_WIDTH, command=self._make_link)
        self.link_btn.pack(side=tk.LEFT, padx=(0, 2))
        Tooltip(self.link_btn, "Weblink Invoegen")

        self.email_btn = ttk.Button(toolbar, text=self.icons["email"], width=BUTTON_WIDTH, command=self._make_email)
        self.email_btn.pack(side=tk.LEFT, padx=(0, 2))
        Tooltip(self.email_btn, "E-mail Link")

        self.tel_btn = ttk.Button(toolbar, text=self.icons["tel"], width=BUTTON_WIDTH, command=self._make_tel)
        self.tel_btn.pack(side=tk.LEFT, padx=(0, 2))
        Tooltip(self.tel_btn, "Telefoon Link")

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=(5, 5), fill='y')

        # Group 3: Media/Files
        self.doc_btn = ttk.Button(toolbar, text=self.icons["doc"], width=BUTTON_WIDTH, command=self._make_document_link)
        self.doc_btn.pack(side=tk.LEFT, padx=(0, 2))
        Tooltip(self.doc_btn, "Document Koppelen")

        return toolbar

    def _create_action_buttons_frame(self, parent):
        """Creates the Save and Clear buttons."""
        actions = ttk.Frame(parent)

        self.news_button_save_update = ttk.Button(actions, text=f"{self.icons['save']} Opslaan", command=self._news_save_or_update_article)
        self.news_button_save_update.pack(side=tk.LEFT, padx=5)
        Tooltip(self.news_button_save_update, "Artikel Opslaan of Bijwerken")

        self.news_button_clear = ttk.Button(actions, text=f"{self.icons['clear']} Nieuw / Wissen", command=self._news_clear_form)
        self.news_button_clear.pack(side=tk.LEFT, padx=5)
        Tooltip(self.news_button_clear, "Wis formulier en start nieuw artikel")

        return actions

    def _create_list_pane(self, parent):
        """Creates the Treeview listing existing articles."""
        list_frame = ttk.Labelframe(parent, text=" Bestaande Artikelen ", padding=PAD_X)
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        cols = ('id', 'date', 'title')
        self.news_tree = ttk.Treeview(list_frame, columns=cols, show='headings', selectmode='browse')

        # Setup columns
        self.news_tree.heading('id', text='ID', anchor=tk.W)
        self.news_tree.column('id', width=0, minwidth=0, stretch=tk.NO) # Hide ID usually, or keep minimal
        self.news_tree.heading('date', text='Datum', anchor=tk.CENTER)
        self.news_tree.column('date', width=120, minwidth=90, anchor=tk.CENTER, stretch=tk.NO)
        self.news_tree.heading('title', text='Titel', anchor=tk.W)
        self.news_tree.column('title', width=520, minwidth=260, anchor=tk.W)

        # Style for striped rows
        self.news_tree.tag_configure('odd', background='#f9f9f9')
        self.news_tree.tag_configure('even', background='#ffffff')

        # Scrollbar
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.news_tree.yview)
        self.news_tree.configure(yscrollcommand=vsb.set)

        self.news_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')

        self.news_tree.bind("<<TreeviewSelect>>", self._news_on_selection_change)

        # Bottom controls for list
        btn_frame = ttk.Frame(list_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=(10,0), sticky=tk.W)

        self.news_button_delete = ttk.Button(btn_frame, text=self.icons["delete"], command=self._news_delete_selected, state=tk.DISABLED, width=BUTTON_WIDTH)
        self.news_button_delete.pack(side=tk.LEFT, padx=(0, 8))
        Tooltip(self.news_button_delete, "Geselecteerd artikel verwijderen")

        refresh_button = ttk.Button(btn_frame, text=self.icons["refresh"], command=self._news_load_and_populate_treeview, width=BUTTON_WIDTH)
        refresh_button.pack(side=tk.LEFT)
        Tooltip(refresh_button, "Lijst vernieuwen")

        return list_frame

    # --- Text Editor Logic & formatting ---

    def _configure_initial_text_tags(self):
        """Sets up default tags for the rich text editor."""
        try:
            base_px = 16.8
            bold_font = (self.app.default_font_family, int(round(base_px)), 'bold')
            self.news_text_full_content.tag_configure("bold", font=bold_font)
            # Standard hyperlink look
            self.news_text_full_content.tag_configure("alink", foreground="blue", underline=True)
        except Exception as e:
            print(f"Error configuring text tags: {e}")

    def _update_toolbar_state(self, event=None):
        """Updates button states (like pressed/unpressed) based on cursor position."""
        widget = self.news_text_full_content
        try:
            # Determine which tags are active at cursor
            if widget.tag_ranges(tk.SEL):
                current_tags = set(widget.tag_names(tk.SEL_FIRST))
            else:
                current_tags = set(widget.tag_names(tk.INSERT))

            # Check for bold tags (simple or sized)
            is_bold = "bold" in current_tags or any(t.startswith("bold_size-") for t in current_tags)

            if is_bold:
                self.news_button_bold.state(['pressed'])
            else:
                self.news_button_bold.state(['!pressed'])
        except tk.TclError:
            self.news_button_bold.state(['!pressed'])

    def _news_toggle_bold(self):
        """Toggles bold on the selected text."""
        widget = self.news_text_full_content
        if not widget.tag_ranges(tk.SEL):
            self.app.set_status("Selecteer eerst tekst om vet te maken.", duration_ms=3000)
            return

        try:
            start, end = widget.tag_ranges(tk.SEL)
            current_tags = widget.tag_names(start)
        except (tk.TclError, ValueError):
            return

        is_currently_bold = "bold" in current_tags or any(t.startswith("bold_size-") for t in current_tags)

        # Find if there is a specific size tag applied
        font_tag = next((t for t in current_tags if t.startswith("size-") or t.startswith("bold_size-")), None)

        # Clean existing bold/font tags
        widget.tag_remove("bold", start, end)
        if font_tag:
            widget.tag_remove(font_tag, start, end)

        if is_currently_bold:
            # Revert to normal weight (preserve size if exists)
            if font_tag:
                size_str = font_tag.split('-', 1)[1].replace('_', '.')
                size_val = float(size_str)
                new_tag_name = f"size-{size_str.replace('.', '_')}"
                font_tuple = (self.app.default_font_family, int(round(size_val)))
                widget.tag_configure(new_tag_name, font=font_tuple)
                widget.tag_add(new_tag_name, start, end)
            # If no size tag, we just removed "bold", so we are done (default font applies)
        else:
            # Apply bold (preserve size if exists)
            if font_tag:
                size_str = font_tag.split('-', 1)[1].replace('_', '.')
                size_val = float(size_str)
                new_tag_name = f"bold_size-{size_str.replace('.', '_')}"
                font_tuple = (self.app.default_font_family, int(round(size_val)), 'bold')
                widget.tag_configure(new_tag_name, font=font_tuple)
                widget.tag_add(new_tag_name, start, end)
            else:
                widget.tag_add("bold", start, end)

        self._update_toolbar_state()

    def _news_apply_color(self):
        if not self.news_text_full_content.tag_ranges(tk.SEL):
            self.app.set_status("Selecteer eerst tekst om een kleur te geven.", duration_ms=3000)
            return

        color_code = colorchooser.askcolor(title="Kies een kleur")[1]
        if color_code:
            tag_name = f"color-{color_code.lower()}"
            self.news_text_full_content.tag_configure(tag_name, foreground=color_code)
            self._apply_exclusive_tag(tag_name, "color-")

    def _news_apply_font_size(self, event=None):
        widget = self.news_text_full_content
        if not widget.tag_ranges(tk.SEL):
            self.app.set_status("Selecteer eerst tekst.", duration_ms=3000)
            return

        try:
            start, end = widget.tag_ranges(tk.SEL)
            current_tags = widget.tag_names(start)
        except (tk.TclError, ValueError):
            return

        size_str = self.font_size_var.get().strip()
        try:
            size_val = float(size_str)
        except ValueError:
            return

        is_currently_bold = "bold" in current_tags or any(t.startswith("bold_size-") for t in current_tags)

        # Remove old size/bold tags
        old_font_tag = next((t for t in current_tags if t.startswith("size-") or t.startswith("bold_size-")), None)
        if old_font_tag:
            widget.tag_remove(old_font_tag, start, end)
        widget.tag_remove("bold", start, end)

        # Apply new tag
        if is_currently_bold:
            new_tag_name = f"bold_size-{size_str.replace('.', '_')}"
            font_tuple = (self.app.default_font_family, int(round(size_val)), 'bold')
        else:
            new_tag_name = f"size-{size_str.replace('.', '_')}"
            font_tuple = (self.app.default_font_family, int(round(size_val)))

        widget.tag_configure(new_tag_name, font=font_tuple)
        widget.tag_add(new_tag_name, start, end)
        self._update_toolbar_state()

    def _apply_exclusive_tag(self, new_tag, tag_prefix):
        """Applies a tag, removing any other existing tags that start with the prefix."""
        widget = self.news_text_full_content
        try:
            sel_start, sel_end = widget.tag_ranges(tk.SEL)
            for tag in widget.tag_names():
                if tag.startswith(tag_prefix):
                    widget.tag_remove(tag, sel_start, sel_end)
            widget.tag_add(new_tag, sel_start, sel_end)
            self._update_toolbar_state()
        except tk.TclError:
            pass

    # --- Link & Media Logic ---

    def _ensure_selection(self):
        if not self.news_text_full_content.tag_ranges(tk.SEL):
            self.app.set_status("Selecteer eerst tekst.", duration_ms=3000)
            return False
        return True

    def _apply_anchor_to_selection(self, href):
        if not self._ensure_selection(): return

        tag_name = f"alink_{self._alink_counter}"
        self._alink_counter += 1
        self.anchor_tag_map[tag_name] = href

        start, end = self.news_text_full_content.tag_ranges(tk.SEL)
        self.news_text_full_content.tag_add("alink", start, end)
        self.news_text_full_content.tag_add(tag_name, start, end)

    def _normalize_safe_href(self, href, default_to_https=False):
        href = (href or "").strip()
        if not href or self.UNSAFE_HREF_RE.search(href):
            return ""

        scheme_match = self.HREF_SCHEME_RE.match(href)
        if scheme_match:
            scheme = scheme_match.group(1).lower()
            return href if scheme in self.SAFE_HREF_SCHEMES else ""

        if href.startswith("//"):
            return ""
        if href.startswith(("/", "#", "./", "../")):
            return href
        if default_to_https:
            return f"https://{href}"
        return href

    def _make_link(self):
        if not self._ensure_selection(): return
        default = self.news_text_full_content.get(*self.news_text_full_content.tag_ranges(tk.SEL)).strip()
        default = default if default and "://" not in default else "https://"

        url = simpledialog.askstring("Link invoeren", "Voer de URL in:", initialvalue=default, parent=self.parent.winfo_toplevel())
        if not url: return

        safe_url = self._normalize_safe_href(url, default_to_https=True)
        if not safe_url:
            messagebox.showerror("Ongeldige link", "Gebruik een veilige http(s), mailto, tel of relatieve link.")
            return
        self._apply_anchor_to_selection(safe_url)

    def _make_email(self):
        if not self._ensure_selection(): return
        default = self.news_text_full_content.get(*self.news_text_full_content.tag_ranges(tk.SEL)).strip()
        email = simpledialog.askstring("E-mail", "Voer het e-mail adres in:", initialvalue=default, parent=self.parent.winfo_toplevel())
        if email:
            href = self._normalize_safe_href(f"mailto:{email}", default_to_https=False)
            if href:
                self._apply_anchor_to_selection(href)
            else:
                messagebox.showerror("Ongeldig e-mailadres", "Gebruik een e-mailadres zonder spaties of HTML-tekens.")

    def _make_tel(self):
        if not self._ensure_selection(): return
        default = self.news_text_full_content.get(*self.news_text_full_content.tag_ranges(tk.SEL)).strip()
        tel = simpledialog.askstring("Telefoonnummer", "Voer het nummer in:", initialvalue=default, parent=self.parent.winfo_toplevel())
        if tel:
            digits = re.sub(r'[^\d+]', '', tel)
            self._apply_anchor_to_selection(f"tel:{digits}")

    def _make_document_link(self):
        if not self._ensure_selection(): return

        source_path = filedialog.askopenfilename(
            title="Selecteer document",
            filetypes=[("Alle documenten", "*.*"), ("PDF", "*.pdf"), ("Word", "*.doc *.docx"), ("Excel", "*.xls *.xlsx"), ("Tekst", "*.txt")]
        )
        if not source_path: return

        filename = os.path.basename(source_path)
        # Handle destination directory safely
        docs_dir = getattr(config, "NEWS_DOCS_DEST_DIR_ABSOLUTE", os.path.join(getattr(config, "APP_BASE_DIR", os.getcwd()), "docs", "nieuws"))

        try:
            os.makedirs(docs_dir, exist_ok=True)
            dest_path = os.path.join(docs_dir, filename)
            dest_path = utils.copy_new_asset(source_path, dest_path, owner=self)
            filename = os.path.basename(dest_path)

            href = f"/docs/nieuws/{filename}"
            self._apply_anchor_to_selection(href)
            self.app.set_status(f"Document '{filename}' gekoppeld.", duration_ms=4000)
        except Exception as e:
            messagebox.showerror("Upload Fout", f"Kon document niet kopiëren:\n{e}")

    # --- Context Menu & Tag Removal ---

    def _get_range_at_index(self, index):
        w = self.news_text_full_content
        if w.tag_ranges(tk.SEL):
            return w.tag_ranges(tk.SEL)
        return w.index(f"{index} wordstart"), w.index(f"{index} wordend")

    def _remove_generic_tag_at(self, tag, index):
        w = self.news_text_full_content
        try:
            s, e = self._get_range_at_index(index)
            w.tag_remove(tag, s, e)
            if tag.startswith("alink_"):
                w.tag_remove("alink", s, e)
                if not w.tag_ranges(tag):
                    self.anchor_tag_map.pop(tag, None)
        except (tk.TclError, ValueError):
            pass

    def _show_context_menu(self, event):
        w = self.news_text_full_content
        idx = w.index(f"@{event.x},{event.y}")
        tags = w.tag_names(idx)

        menu = tk.Menu(w, tearoff=0)

        # Identify tags at cursor
        alink_tag = next((t for t in tags if t.startswith("alink_")), None)
        size_tag = next((t for t in tags if t.startswith("size-") or t.startswith("bold_size-")), None)
        color_tag = next((t for t in tags if t.startswith("color-")), None)
        is_bold = "bold" in tags or any(t.startswith("bold_size-") for t in tags)

        if alink_tag:
            menu.add_command(label="❌ Verwijder Link", command=lambda t=alink_tag, i=idx: self._remove_generic_tag_at(t, i))
        if is_bold:
            menu.add_command(label="❌ Verwijder Vet", command=lambda i=idx: self._remove_bold_at(i))
        if color_tag:
            menu.add_command(label="❌ Verwijder Kleur", command=lambda t=color_tag, i=idx: self._remove_generic_tag_at(t, i))
        if size_tag:
            menu.add_command(label="❌ Reset Grootte", command=lambda i=idx: self._remove_size_at(i))

        if menu.index("end") is not None:
            menu.tk_popup(event.x_root, event.y_root)

    def _remove_bold_at(self, index):
        """Helper to remove bold but keep size if present."""
        w = self.news_text_full_content
        try:
            s, e = self._get_range_at_index(index)
            tags = w.tag_names(s)
            font_tag = next((t for t in tags if t.startswith("bold_size-")), None)
            w.tag_remove("bold", s, e)

            if font_tag:
                w.tag_remove(font_tag, s, e)
                size_str = font_tag.split('-', 1)[1]
                size_val = float(size_str.replace('_', '.'))
                new_tag_name = f"size-{size_str}"
                font_tuple = (self.app.default_font_family, int(round(size_val)))
                w.tag_configure(new_tag_name, font=font_tuple)
                w.tag_add(new_tag_name, s, e)
            self._update_toolbar_state()
        except (tk.TclError, ValueError):
            pass

    def _remove_size_at(self, index):
        """Helper to remove size but keep bold if present."""
        w = self.news_text_full_content
        try:
            s, e = self._get_range_at_index(index)
            tags = w.tag_names(s)
            font_tag = next((t for t in tags if t.startswith("size-") or t.startswith("bold_size-")), None)

            if not font_tag: return

            is_bold = font_tag.startswith("bold_size-")
            w.tag_remove(font_tag, s, e)

            if is_bold:
                w.tag_add("bold", s, e)
            self._update_toolbar_state()
        except (tk.TclError, ValueError):
            pass

    # --- HTML Conversion Logic ---

    def _get_text_content_as_html(self):
        """
        Converts the Text widget content and its tags into HTML.
        """
        widget = self.news_text_full_content
        content_dump = widget.dump("1.0", "end-1c", all=True)
        html_parts = []
        bold_count = 0
        size_stack = []
        color_stack = []
        link_stack = []

        def _remove_last(stack, value):
            for i in range(len(stack) - 1, -1, -1):
                if stack[i] == value:
                    stack.pop(i)
                    break

        for key, value, index in content_dump:
            if key == "tagon":
                if value == "bold":
                    bold_count += 1
                elif value.startswith("bold_size-"):
                    bold_count += 1
                    size_val = value.split('-', 1)[1].replace('_', '.')
                    size_stack.append(size_val)
                elif value.startswith("size-"):
                    size_val = value.split('-', 1)[1].replace('_', '.')
                    size_stack.append(size_val)
                elif value.startswith("color-"):
                    color_val = value.split('-', 1)[1]
                    color_stack.append(color_val)
                elif value.startswith("alink_"):
                    link_stack.append(value)
            elif key == "tagoff":
                if value == "bold":
                    bold_count = max(0, bold_count - 1)
                elif value.startswith("bold_size-"):
                    bold_count = max(0, bold_count - 1)
                    size_val = value.split('-', 1)[1].replace('_', '.')
                    _remove_last(size_stack, size_val)
                elif value.startswith("size-"):
                    size_val = value.split('-', 1)[1].replace('_', '.')
                    _remove_last(size_stack, size_val)
                elif value.startswith("color-"):
                    color_val = value.split('-', 1)[1]
                    _remove_last(color_stack, color_val)
                elif value.startswith("alink_"):
                    _remove_last(link_stack, value)
            elif key == "text":
                text = html.escape(value).replace('\n', '<br>')
                if not text:
                    continue

                size_val = size_stack[-1] if size_stack else None
                color_val = color_stack[-1] if color_stack else None
                link_tag = link_stack[-1] if link_stack else None
                is_bold = bold_count > 0

                open_tags = []
                close_tags = []

                if link_tag:
                    href = self._normalize_safe_href(self.anchor_tag_map.get(link_tag, ""), default_to_https=False)
                    if href:
                        open_tags.append(f'<a href="{html.escape(href, quote=True)}">')
                        close_tags.insert(0, "</a>")

                styles = []
                if size_val:
                    styles.append(f"font-size: {size_val}px;")
                if color_val:
                    styles.append(f"color: {color_val};")
                if styles:
                    open_tags.append(f'<span style="{" ".join(styles)}">')
                    close_tags.insert(0, "</span>")

                if is_bold:
                    open_tags.append("<strong>")
                    close_tags.insert(0, "</strong>")

                html_parts.append("".join(open_tags) + text + "".join(close_tags))

        full_html = "".join(html_parts)
        # Clean up empty tags that might result from tag logic overlap
        full_html = re.sub(r'<strong></strong>|<span style="[^"]*"></span>|<a></a>', '', full_html, flags=re.IGNORECASE)
        return full_html

    def _insert_html_into_text_widget(self, html_content):
        """
        Parses basic HTML and inserts it into the Text widget with appropriate tags.
        """
        self.anchor_tag_map.clear()
        self._alink_counter = 1
        widget = self.news_text_full_content
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)

        if not html_content:
            widget.edit_reset()
            return

        content_with_nl = re.sub(r'<br\s*/?>', '\n', html_content, flags=re.IGNORECASE)
        pattern = re.compile(r"(<[^>]+>)|([^<]+)")

        active_tags = []
        span_stack = [] # Tracks nested spans
        anchor_stack = []

        for match in pattern.finditer(content_with_nl):
            tag, text = match.groups()

            if text:
                widget.insert(tk.END, html.unescape(text), tuple(active_tags))
            elif tag:
                tag_lower = tag.lower()

                # Bold
                if tag_lower in ('<strong>', '<b>'):
                    active_tags.append('bold')
                elif tag_lower in ('</strong>', '</b>'):
                    if 'bold' in active_tags: active_tags.remove('bold')

                # Links
                elif tag_lower.startswith('<a'):
                    href_match = re.search(r'href="([^"]+)"', tag, re.I)
                    href = self._normalize_safe_href(html.unescape(href_match.group(1) if href_match else ""), default_to_https=False)

                    if href:
                        tname = f"alink_{self._alink_counter}"
                        self._alink_counter += 1
                        self.anchor_tag_map[tname] = href

                        active_tags.extend(["alink", tname])
                        anchor_stack.append(tname)
                    else:
                        anchor_stack.append(None)
                elif tag_lower == '</a>':
                    if anchor_stack:
                        tname = anchor_stack.pop()
                        if tname and tname in active_tags: active_tags.remove(tname)
                    if "alink" in active_tags: active_tags.remove("alink")

                # Spans (Color/Size)
                elif tag_lower.startswith('<span'):
                    style_match = re.search(r'style="([^"]+)"', tag, re.I)
                    tags_added_for_this_span = []

                    if style_match:
                        style_str = style_match.group(1)
                        color_match = re.search(r'color:\s*([^;]+)', style_str, re.I)
                        size_match = re.search(r'font-size:\s*([0-9.]+)\s*px', style_str, re.I)

                        if color_match:
                            color_val = color_match.group(1).strip()
                            color_tag = f"color-{color_val.lower()}"
                            # Ensure the tag exists
                            widget.tag_configure(color_tag, foreground=color_val)
                            active_tags.append(color_tag)
                            tags_added_for_this_span.append(color_tag)

                        if size_match:
                            size_val_str = size_match.group(1)
                            try:
                                size_float = float(size_val_str)
                                is_bold_active = 'bold' in active_tags

                                if is_bold_active:
                                    size_tag_name = f"bold_size-{size_val_str.replace('.', '_')}"
                                    font_tuple = (self.app.default_font_family, int(round(size_float)), 'bold')
                                else:
                                    size_tag_name = f"size-{size_val_str.replace('.', '_')}"
                                    font_tuple = (self.app.default_font_family, int(round(size_float)))

                                widget.tag_configure(size_tag_name, font=font_tuple)
                                active_tags.append(size_tag_name)
                                tags_added_for_this_span.append(size_tag_name)
                            except ValueError: pass

                    span_stack.append(tags_added_for_this_span)
                elif tag_lower == '</span>':
                    if span_stack:
                        for t in span_stack.pop():
                            if t in active_tags: active_tags.remove(t)

        widget.edit_reset()

    # --- Data Management ---

    def _news_load_and_populate_treeview(self):
        if not utils.confirm_discard_changes(self):
            return
        self.app.set_status("Nieuwsberichten laden...")
        try:
            loaded_data, error_msg = utils.news_load_existing_data(config.NEWS_JSON_FILE_PATH)
            if error_msg:
                self._news_loaded = False
                self.app.set_status(f"Fout bij laden: {error_msg}", is_error=True)
                messagebox.showerror("Nieuws Laad Fout", f"Kon nieuws data niet laden:\n{error_msg}")
            else:
                self._news_loaded = True
                self.news_data = loaded_data or [] # Ensure list
                self.app.set_status(f"{len(self.news_data)} nieuwsberichten geladen.")
        except Exception as e:
            self._news_loaded = False
            self.app.set_status("Kritieke fout bij laden data.", is_error=True)
            print(f"Critical load error: {e}")

        self._news_populate_treeview()
        self.news_button_save_update.config(state=tk.NORMAL if self._news_loaded else tk.DISABLED)
        if not self._news_loaded:
            self.news_button_delete.config(state=tk.DISABLED)
        if self._news_loaded and self.currently_editing_id:
            if any(article.get('id') == self.currently_editing_id for article in self.news_data):
                self._news_load_selected_into_form(self.currently_editing_id, force=True)
            else:
                self._news_clear_form(force=True)
        elif self._news_loaded:
            self._news_clear_form(force=True)
        return self._news_loaded

    def _news_populate_treeview(self):
        # Clear existing
        for item in self.news_tree.get_children():
            self.news_tree.delete(item)

        if not self.news_data:
            return

        for index, article in enumerate(self.news_data):
            tag = 'even' if index % 2 == 0 else 'odd'
            self.news_tree.insert(
                '',
                tk.END,
                iid=article.get('id'),
                values=(article.get('id'), article.get('date'), article.get('title')),
                tags=(tag,)
            )

        self._news_on_selection_change()

    def _news_on_selection_change(self, event=None):
        if not self._news_loaded:
            self.news_button_delete.config(state=tk.DISABLED)
            return
        selected = self.news_tree.selection()
        if selected:
            self.news_button_delete.config(state=tk.NORMAL)
            self._news_load_selected_into_form(selected[0])
        else:
            self.news_button_delete.config(state=tk.DISABLED)
            # Only clear form if we are not in the middle of creating a NEW one (optional,
            # but usually clicking away from a list implies we are done with the selection)
            # For simplicity, we don't auto-clear here to avoid losing work if user accidentally clicks list.
            pass

    def _news_load_selected_into_form(self, selected_iid, force=False):
        if not force and selected_iid == self.currently_editing_id:
            return
        if not force and not utils.confirm_discard_changes(self):
            if self.currently_editing_id and self.news_tree.exists(self.currently_editing_id):
                self.news_tree.selection_set(self.currently_editing_id)
            else:
                self.news_tree.selection_remove(self.news_tree.selection())
            return
        article = next((a for a in self.news_data if a.get('id') == selected_iid), None)
        if not article: return

        self.news_entry_id.config(state=tk.NORMAL)
        self.news_entry_id.delete(0, tk.END)
        self.news_entry_id.insert(0, article.get('id', ''))
        self.news_entry_id.config(state=tk.DISABLED)

        self.news_entry_date.delete(0, tk.END)
        self.news_entry_date.insert(0, article.get('date', ''))

        self.news_entry_title.delete(0, tk.END)
        self.news_entry_title.insert(0, article.get('title', ''))

        self.news_entry_category.delete(0, tk.END)
        self.news_entry_category.insert(0, article.get('category', ''))

        self.news_entry_image.delete(0, tk.END)
        self.news_entry_image.insert(0, article.get('image', ''))

        self.news_entry_summary.delete(0, tk.END)
        self.news_entry_summary.insert(0, article.get('summary', ''))

        self._insert_html_into_text_widget(article.get('full_content', ''))

        self.news_button_save_update.config(text=f"{self.icons['save']} Update Artikel")
        self.currently_editing_id = selected_iid
        self._update_toolbar_state()
        self._saved_form_snapshot = self._form_snapshot()
        utils.cleanup_pending_assets(self)

    def _news_clear_form(self, force=False):
        if not force and not utils.confirm_discard_changes(self):
            return
        self.news_entry_date.delete(0, tk.END)
        self.news_entry_date.insert(0, datetime.date.today().isoformat())

        self.news_entry_title.delete(0, tk.END)

        self.news_entry_category.delete(0, tk.END)
        self.news_entry_category.insert(0, config.NEWS_DEFAULT_CATEGORY)

        self.news_entry_image.delete(0, tk.END)
        self.news_entry_image.insert(0, config.NEWS_DEFAULT_IMAGE)

        self.news_entry_summary.delete(0, tk.END)

        self.news_text_full_content.delete('1.0', tk.END)

        self.news_button_save_update.config(text=f"{self.icons['save']} Voeg Artikel Toe")
        self.currently_editing_id = None

        if self.news_tree.selection():
            self.news_tree.selection_remove(self.news_tree.selection())

        self.news_entry_title.focus()
        self._update_toolbar_state()
        self._saved_form_snapshot = self._form_snapshot()
        utils.cleanup_pending_assets(self)

    def _news_delete_selected(self):
        if not self._news_loaded:
            return
        selected_items = self.news_tree.selection()
        if not selected_items: return

        selected_iid = selected_items[0]
        # Get title for friendlier message
        item_title = self.news_tree.item(selected_iid)['values'][2]

        if messagebox.askyesno("Verwijderen", f"Weet je zeker dat je '{item_title}' wilt verwijderen?", icon='warning'):
            candidate = [a for a in self.news_data if a.get('id') != selected_iid]

            error = utils.news_save_data(config.NEWS_JSON_FILE_PATH, candidate)
            if error:
                messagebox.showerror("Fout", f"Kon niet opslaan na verwijderen:\n{error}")
                return

            self.news_data = candidate
            self._news_clear_form(force=True)
            self._news_populate_treeview()

    def _news_browse_image(self):
        source_path = filedialog.askopenfilename(title="Selecteer afbeelding", filetypes=[("Images", "*.jpg *.jpeg *.png *.gif")])
        if not source_path: return

        filename = os.path.basename(source_path)
        dest_path = os.path.join(config.NEWS_IMAGE_DEST_DIR_ABSOLUTE, filename)

        try:
            os.makedirs(config.NEWS_IMAGE_DEST_DIR_ABSOLUTE, exist_ok=True)
            dest_path = utils.copy_new_asset(source_path, dest_path, owner=self)
            filename = os.path.basename(dest_path)
            self.news_entry_image.delete(0, tk.END)
            self.news_entry_image.insert(0, filename)
            self.app.set_status(f"Afbeelding '{filename}' geüpload.", duration_ms=4000)
        except Exception as e:
            messagebox.showerror("Upload Fout", f"Kon afbeelding niet kopiëren:\n{e}")

    def _generate_random_id(self):
        existing = {a.get('id') for a in self.news_data}
        while True:
            rid = uuid.uuid4().hex[:12]
            if rid not in existing:
                return rid

    def _news_save_or_update_article(self):
        if not self._news_loaded:
            messagebox.showerror("Opslagfout", "Laad eerst geldige nieuwsdata voordat je opslaat.")
            return
        # 1. Validation
        title = self.news_entry_title.get().strip()
        date_str = self.news_entry_date.get().strip()

        if not title:
            messagebox.showwarning("Invoer Fout", "De titel mag niet leeg zijn.")
            self.news_entry_title.focus()
            return

        if not date_str:
            messagebox.showwarning("Invoer Fout", "De datum mag niet leeg zijn.")
            self.news_entry_date.focus()
            return

        try:
            # Basic format check YYYY-MM-DD
            datetime.datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            messagebox.showwarning("Datum Fout", "Gebruik het formaat YYYY-MM-DD.")
            return

        # 2. ID Generation
        if self.currently_editing_id:
            article_id = self.currently_editing_id
        else:
            article_id = self._generate_random_id()

        # 3. Construct Data Object
        article_data = {
            "id": article_id,
            "date": date_str,
            "title": title,
            "category": self.news_entry_category.get().strip(),
            "image": self.news_entry_image.get().strip(),
            "summary": self.news_entry_summary.get().strip(),
            "full_content": self._get_text_content_as_html()
        }

        # 4. Update List
        if self.currently_editing_id:
            if not any(article.get('id') == self.currently_editing_id for article in self.news_data):
                messagebox.showerror("Artikel ontbreekt", "Het oorspronkelijke artikel bestaat niet meer. Herlaad de nieuwsdata.")
                return
            # Replace existing
            candidate = [article_data if a.get('id') == self.currently_editing_id else a for a in self.news_data]
        else:
            # Add new to top
            candidate = [article_data] + self.news_data

        # 5. Save to File
        error = utils.news_save_data(config.NEWS_JSON_FILE_PATH, candidate)
        if error:
            messagebox.showerror("Opslagfout", f"Kon nieuws niet opslaan:\n{error}")
        else:
            self.news_data = candidate
            self.currently_editing_id = article_id
            self._saved_form_snapshot = self._form_snapshot()
            utils.cleanup_pending_assets(self)
            self.app.set_status("Nieuws succesvol opgeslagen.", duration_ms=4000)
            self._news_load_and_populate_treeview()
            # If it was a new item, we might want to clear, or stay on it.
            # Usually staying on it is better for minor edits immediately after save.
            self.currently_editing_id = article_id
            self.news_button_save_update.config(text=f"{self.icons['save']} Update Artikel")


def create_news_tab(parent_frame, app_instance):
    return NewsTab(parent_frame, app_instance)

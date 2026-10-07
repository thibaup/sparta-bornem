import tkinter as tk
from tkinter import ttk, messagebox, Listbox, END, MULTIPLE
from tkinter.scrolledtext import ScrolledText
import datetime
import calendar
import os
import copy
import config
import utils

# --- Helper Functions ---

def center_window(window, parent=None):
    """Centers a toplevel window relative to the parent or screen."""
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()

    if parent:
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
    else:
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

    window.geometry(f'{width}x{height}+{x}+{y}')

# --- Dialog Classes ---

class MonthManagerDialog(tk.Toplevel):
    def __init__(self, parent, months_list, month_names):
        super().__init__(parent)
        self.title("Beheer Maanden")
        self.transient(parent)
        self.grab_set()

        self.result = None
        self.month_names = month_names
        self.year_var = tk.IntVar(value=datetime.date.today().year)
        self.vars = {} # (year, month_int) -> BooleanVar

        # Structure data: Year -> Set of selected months (ints)
        self.selected_by_year = {}
        for y, m in months_list:
            self.selected_by_year.setdefault(y, set()).add(m)

        self._create_ui()
        self._build_checks(self.year_var.get())
        center_window(self, parent)

    def _create_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # -- Header (Year Selection) --
        head = ttk.Frame(main_frame)
        head.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(head, text="Jaar:").pack(side=tk.LEFT)

        btn_prev = ttk.Button(head, text="◀", width=3, command=lambda: self._shift_year(-1))
        btn_prev.pack(side=tk.LEFT, padx=(10, 2))

        self.year_spin = ttk.Spinbox(head, from_=1970, to=2100, width=6,
                                     textvariable=self.year_var, command=self._switch_year)
        self.year_spin.bind('<Return>', lambda e: self._switch_year())
        self.year_spin.pack(side=tk.LEFT, padx=2)

        btn_next = ttk.Button(head, text="▶", width=3, command=lambda: self._shift_year(1))
        btn_next.pack(side=tk.LEFT, padx=2)

        ttk.Separator(main_frame).pack(fill=tk.X, pady=10)

        # -- Grid for Months --
        self.grid_frame = ttk.Frame(main_frame)
        self.grid_frame.pack(fill=tk.BOTH, expand=True)
        for i in range(3):
            self.grid_frame.grid_columnconfigure(i, weight=1)

        # -- Quick Actions --
        actions = ttk.Labelframe(main_frame, text="Snelle Selectie", padding=10)
        actions.pack(fill=tk.X, pady=(15, 0))

        ttk.Button(actions, text="Alles Wissen (Jaar)", command=self._clear_current_year).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(actions, text="Q1", width=4, command=lambda: self._set_quarter(1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(actions, text="Q2", width=4, command=lambda: self._set_quarter(2)).pack(side=tk.LEFT, padx=2)
        ttk.Button(actions, text="Q3", width=4, command=lambda: self._set_quarter(3)).pack(side=tk.LEFT, padx=2)
        ttk.Button(actions, text="Q4", width=4, command=lambda: self._set_quarter(4)).pack(side=tk.LEFT, padx=2)

        ttk.Separator(main_frame).pack(fill=tk.X, pady=15)

        # -- Footer Buttons --
        bottom = ttk.Frame(main_frame)
        bottom.pack(fill=tk.X)
        ttk.Button(bottom, text="Opslaan", command=self._ok, default="active").pack(side=tk.RIGHT)
        ttk.Button(bottom, text="Annuleren", command=self._cancel).pack(side=tk.RIGHT, padx=(0, 10))

    def _persist_current_year(self):
        y = self._displayed_year
        selected = set()
        for i in range(1, 13):
            var = self.vars.get((y, i))
            if var and var.get():
                selected.add(i)
        self.selected_by_year[y] = selected

    def _shift_year(self, delta):
        self._persist_current_year()
        self.year_var.set(self._displayed_year + delta)
        self._build_checks(self.year_var.get())

    def _switch_year(self):
        try:
            year = self.year_var.get()
            if not 1970 <= year <= 2100:
                raise ValueError()
        except (tk.TclError, ValueError):
            self.year_var.set(self._displayed_year)
            return
        self._persist_current_year()
        self._build_checks(year)

    def _build_checks(self, year):
        self._displayed_year = year
        # Clear existing checkboxes
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self.vars.clear()

        selected = self.selected_by_year.get(year, set())

        for i, name in enumerate(self.month_names, start=1):
            var = tk.BooleanVar(value=i in selected)
            self.vars[(year, i)] = var

            # Create a nice container for the checkbox
            f = ttk.Frame(self.grid_frame)
            r = (i - 1) // 3
            c = (i - 1) % 3
            f.grid(row=r, column=c, sticky="nsew", padx=5, pady=5)

            cb = ttk.Checkbutton(f, text=f"{name}", variable=var)
            cb.pack(anchor="w", fill=tk.X)

    def _clear_current_year(self):
        y = self._displayed_year
        for i in range(1, 13):
            if (y, i) in self.vars:
                self.vars[(y, i)].set(False)

    def _set_quarter(self, q):
        start_month = (q - 1) * 3 + 1
        end_month = start_month + 2
        y = self._displayed_year
        for i in range(1, 13):
            if (y, i) in self.vars:
                self.vars[(y, i)].set(start_month <= i <= end_month)

    def _ok(self):
        self._persist_current_year()
        result = []
        for y, months in self.selected_by_year.items():
            for m in sorted(months):
                result.append((y, m))
        self.result = sorted(result)
        self.destroy()

    def _cancel(self):
        self.destroy()


class CalendarEventDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_event_dict=None, callback=None):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.callback = callback
        self.result = None
        self.initial_data = initial_event_dict or {}

        # Safely get defaults from config or fallback
        colors = getattr(config, 'CALENDAR_EVENT_COLORS', ["#3a7afe", "#e11d48", "#16a34a", "#ca8a04", "#7c3aed", "black"])
        default_color = colors[0] if colors else "#000000"
        default_date = datetime.date.today().isoformat()

        self.layout_frame = ttk.Frame(self, padding=20)
        self.layout_frame.pack(expand=True, fill=tk.BOTH)

        # -- Form Fields --
        r = 0
        self._add_label("Datum (JJJJ-MM-DD):*", r)
        self.entry_date = ttk.Entry(self.layout_frame, width=25)
        self.entry_date.grid(row=r, column=1, sticky=tk.W, pady=5)
        self.entry_date.insert(0, self.initial_data.get('date') or default_date)

        r += 1
        self._add_label("Titel:*", r)
        self.entry_name = ttk.Entry(self.layout_frame, width=40)
        self.entry_name.grid(row=r, column=1, sticky="ew", pady=5)
        self.entry_name.insert(0, self.initial_data.get('name') or self.initial_data.get('title') or '')

        r += 1
        self._add_label("Kleur:*", r)
        self.color_var = tk.StringVar(value=self.initial_data.get('color') or default_color)
        self.combo_color = ttk.Combobox(self.layout_frame, textvariable=self.color_var, values=colors, state="readonly", width=23)
        self.combo_color.grid(row=r, column=1, sticky=tk.W, pady=5)

        r += 1
        self._add_label("URL:", r)
        self.entry_url = ttk.Entry(self.layout_frame, width=40)
        self.entry_url.grid(row=r, column=1, sticky="ew", pady=5)
        self.entry_url.insert(0, self.initial_data.get('data_url') or self.initial_data.get('url') or '')

        r += 1
        self._add_label("Locatie:", r)
        self.entry_location = ttk.Entry(self.layout_frame, width=40)
        self.entry_location.grid(row=r, column=1, sticky="ew", pady=5)
        self.entry_location.insert(0, self.initial_data.get('data_location') or '')

        r += 1
        self._add_label("Categorie:", r)
        self.entry_category = ttk.Entry(self.layout_frame, width=40)
        self.entry_category.grid(row=r, column=1, sticky="ew", pady=5)
        self.entry_category.insert(0, self.initial_data.get('data_category') or '')

        r += 1
        self._add_label("Extra Info:", r, align=tk.N)
        self.text_info = ScrolledText(self.layout_frame, width=38, height=5, wrap=tk.WORD, borderwidth=1, relief=tk.SOLID)
        self.text_info.grid(row=r, column=1, sticky="ew", pady=5)
        val_info = self.initial_data.get('data_info') or ''
        self.text_info.insert("1.0", val_info)

        # -- Buttons --
        r += 1
        btn_frame = ttk.Frame(self.layout_frame)
        btn_frame.grid(row=r, column=0, columnspan=2, sticky="e", pady=(20, 0))

        ttk.Button(btn_frame, text="OK", command=self.on_ok, default="active").pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="Annuleren", command=self.on_cancel).pack(side=tk.RIGHT, padx=(0, 10))

        self.layout_frame.columnconfigure(1, weight=1)

        # Bindings
        self.grab_set()
        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", self.on_cancel)
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

        center_window(self, parent)
        self.entry_date.focus_set()
        self.wait_window(self)

    def _add_label(self, text, row, align=tk.W):
        ttk.Label(self.layout_frame, text=text).grid(row=row, column=0, sticky=align, padx=(0, 10), pady=5)

    def on_ok(self, event=None):
        date_str = self.entry_date.get().strip()
        name_val = self.entry_name.get().strip()
        color_val = self.color_var.get().strip()

        # Validation
        if not date_str:
            messagebox.showwarning("Invoer Vereist", "Datum is verplicht.", parent=self)
            return
        try:
            # Normalize date
            normalized_date_str = datetime.datetime.strptime(date_str, "%Y-%m-%d").date().isoformat()
        except ValueError:
            messagebox.showwarning("Ongeldig Formaat", "Datum moet JJJJ-MM-DD zijn.", parent=self)
            return

        if not name_val:
            messagebox.showwarning("Invoer Vereist", "Titel is verplicht.", parent=self)
            return

        colors = getattr(config, 'CALENDAR_EVENT_COLORS', [])
        if colors and color_val not in colors:
            messagebox.showwarning("Ongeldige Kleur", "Kies een kleur uit de lijst.", parent=self)
            return

        # Gather data
        data = {
            'date': normalized_date_str,
            'name': name_val,
            'color': color_val,
            'title': name_val, # Keep both for compatibility
            'data_url': self.entry_url.get().strip() or None,
            'data_location': self.entry_location.get().strip() or None,
            'data_category': self.entry_category.get().strip() or None,
            'data_info': self.text_info.get("1.0", tk.END).strip() or None
        }

        # Filter None values
        self.result = {k: v for k, v in data.items() if v is not None}

        if self.callback:
            self.callback(self.result)
        self.destroy()

    def on_cancel(self, event=None):
        self.destroy()


class CalendarTab:
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance

        # Default data structure
        self.full_calendar_json_data = {
            "pageTitle": "Kalender",
            "mainHeading": "Wedstrijden Kalender",
            "legend": {"title": "Legende", "items": []},
            "displayedMonths": [],
            "events": []
        }

        self.calendar_file_loaded = False

        # Safely load month names from config or use defaults
        default_months = ["Januari", "Februari", "Maart", "April", "Mei", "Juni",
                          "Juli", "Augustus", "September", "Oktober", "November", "December"]
        self.month_names_nl = [
            getattr(config, 'MONTH_MAP_NL_FULL', {}).get(i, default_months[i-1])
            for i in range(1, 13)
        ]

        t = datetime.date.today()
        self.current_year = t.year
        self.current_month = t.month

        self.view_month_var = tk.StringVar(value=self.month_names_nl[self.current_month - 1])
        self.view_year_var = tk.StringVar(value=str(self.current_year))

        self._init_styles()
        self._create_widgets()

    def _init_styles(self):
        style = ttk.Style()
        try:
            # Try to pick a better theme if available
            available = style.theme_names()
            if "clam" in available:
                style.theme_use("clam")
        except:
            pass

        # Define custom styles
        style.configure("Cal.Toolbar.TFrame", padding=10, background="#f0f0f0")
        style.configure("Cal.Section.TFrame", background="#ffffff")

        # Header style
        style.configure("Cal.DayHeader.TLabel", font=("Segoe UI", 10, "bold"), anchor="center",
                        background="#e1e8f0", padding=5)

        # Buttons
        style.configure("Cal.Nav.TButton", padding=(5, 3))

        # Labelframes
        style.configure("Cal.Side.TLabelframe", padding=10, background="#ffffff")
        style.configure("Cal.Side.TLabelframe.Label", font=("Segoe UI", 10, "bold"), background="#ffffff")

    def _create_widgets(self):
        # Configure parent grid
        self.parent.grid_rowconfigure(2, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        # --- Toolbar ---
        toolbar = ttk.Frame(self.parent, style="Cal.Toolbar.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew")

        # Left: Load Button
        self.calendar_refresh_button = ttk.Button(toolbar, text="📂 Herladen (JSON)",
                                                command=self._calendar_load_from_json, style="Cal.Nav.TButton")
        self.calendar_refresh_button.pack(side=tk.LEFT, padx=(0, 15))

        # Center: Navigation
        nav = ttk.Frame(toolbar)
        nav.pack(side=tk.LEFT)

        self.prev_btn = ttk.Button(nav, text="◀", width=4, command=self._goto_prev_month, state=tk.DISABLED)
        self.prev_btn.pack(side=tk.LEFT, padx=2)

        self.month_combo = ttk.Combobox(nav, textvariable=self.view_month_var, width=14, state="disabled", font=("Segoe UI", 10))
        self.month_combo.pack(side=tk.LEFT, padx=2)
        self.month_combo.bind("<<ComboboxSelected>>", self._on_view_month_year_changed)

        self.year_combo = ttk.Combobox(nav, textvariable=self.view_year_var, width=8, state="disabled", font=("Segoe UI", 10))
        self.year_combo.pack(side=tk.LEFT, padx=2)
        self.year_combo.bind("<<ComboboxSelected>>", self._on_view_month_year_changed)

        self.next_btn = ttk.Button(nav, text="▶", width=4, command=self._goto_next_month, state=tk.DISABLED)
        self.next_btn.pack(side=tk.LEFT, padx=2)

        self.today_btn = ttk.Button(nav, text="Vandaag", command=self._goto_today, state=tk.DISABLED)
        self.today_btn.pack(side=tk.LEFT, padx=(15, 0))

        # Right: Manage
        self.manage_months_btn = ttk.Button(toolbar, text="⚙ Beheer Maanden", command=self._open_month_manager, state=tk.DISABLED)
        self.manage_months_btn.pack(side=tk.RIGHT)

        ttk.Separator(self.parent).grid(row=1, column=0, sticky="ew")

        # --- Main Body ---
        body = ttk.Frame(self.parent, padding=10)
        body.grid(row=2, column=0, sticky="nsew")

        body.grid_columnconfigure(0, weight=4) # Calendar gets more space
        body.grid_columnconfigure(1, weight=1) # Sidebar
        body.grid_rowconfigure(1, weight=1)

        # -- Calendar Header (Days) --
        header = ttk.Frame(body)
        header.grid(row=0, column=0, sticky='ew')
        days = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
        for c, dn in enumerate(days):
            lbl = ttk.Label(header, text=dn, style="Cal.DayHeader.TLabel")
            lbl.grid(row=0, column=c, sticky="ew", padx=1, pady=(0, 5))
            header.grid_columnconfigure(c, weight=1)

        # -- Calendar Grid --
        grid_wrap = ttk.Frame(body, borderwidth=1, relief="solid")
        grid_wrap.grid(row=1, column=0, sticky='nsew')
        grid_wrap.grid_rowconfigure(0, weight=1)
        grid_wrap.grid_columnconfigure(0, weight=1)

        # Inner frame to hold cells
        self.calendar_grid_outer = tk.Frame(grid_wrap, bg="#cfd8dc")
        self.calendar_grid_outer.grid(row=0, column=0, sticky="nsew")

        self.calendar_grid = tk.Frame(self.calendar_grid_outer, bg="#ffffff")
        self.calendar_grid.pack(expand=True, fill=tk.BOTH, padx=1, pady=1)

        # Grid config
        for r in range(6): self.calendar_grid.grid_rowconfigure(r, weight=1)
        for c in range(7): self.calendar_grid.grid_columnconfigure(c, weight=1)

        # --- Sidebar (Legend + List) ---
        self.side = ttk.Labelframe(body, text="Info & Filters", style="Cal.Side.TLabelframe")
        self.side.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(15, 0))
        self.side.grid_rowconfigure(1, weight=1)
        self.side.grid_columnconfigure(0, weight=1)

        # Legend
        self.legend_frame = ttk.Frame(self.side)
        self.legend_frame.grid(row=0, column=0, sticky="new")

        ttk.Separator(self.side).grid(row=1, column=0, sticky="ew", pady=10)

        # Displayed Months List
        lbl_months = ttk.Label(self.side, text="Zichtbare Maanden:", font=("", 9, "bold"))
        lbl_months.grid(row=2, column=0, sticky="w", pady=(0, 5))

        self.displayed_list = Listbox(self.side, selectmode=MULTIPLE, height=10,
                                      relief="flat", bg="#f9fafb", activestyle="none")
        self.displayed_list.grid(row=3, column=0, sticky="nsew")
        self.displayed_list.config(state=tk.DISABLED)

        # --- Footer ---
        bottom = ttk.Frame(self.parent, padding=10)
        bottom.grid(row=3, column=0, sticky="ew")

        self.calendar_save_button = ttk.Button(bottom, text="💾 Opslaan naar JSON",
                                             command=self._calendar_save_to_json, state=tk.DISABLED)
        self.calendar_save_button.pack(side=tk.RIGHT)

        self._render_calendar_grid_empty()

    def _update_controls_enabled(self, enabled):
        st = tk.NORMAL if enabled else tk.DISABLED
        widgets = [self.prev_btn, self.next_btn, self.today_btn,
                   self.month_combo, self.year_combo,
                   self.calendar_save_button, self.manage_months_btn]
        for w in widgets:
            w.config(state=st)

    def _render_calendar_grid_empty(self):
        for w in self.calendar_grid.winfo_children():
            w.destroy()
        # Just draw empty cells
        for r in range(6):
            for c in range(7):
                cell = tk.Frame(self.calendar_grid, bg="#ffffff", highlightbackground="#ececec", highlightthickness=1)
                cell.grid(row=r, column=c, sticky='nsew')

    def _events_by_date_with_indices(self):
        grouped = {}
        evs = self.full_calendar_json_data.get("events", [])
        for idx, ev in enumerate(evs):
            if not isinstance(ev, dict): continue
            ds = ev.get('date')
            if ds:
                grouped.setdefault(ds, []).append((idx, ev))
        return grouped

    def _get_contrast_fg(self, bg_color):
        """
        Robustly determines if black or white text should be used on top of bg_color.
        Uses Tkinter's internal winfo_rgb to handle all color formats (Hex, Names, System colors).
        """
        try:
            # winfo_rgb returns 16-bit values (0-65535)
            # We rely on self.parent to access the window system
            rgb = self.parent.winfo_rgb(bg_color)
            r, g, b = [x >> 8 for x in rgb] # Convert to 0-255

            # Standard luminance calculation
            # Y = 0.299*R + 0.587*G + 0.114*B
            y = 0.299 * r + 0.587 * g + 0.114 * b

            # Threshold: If luminance is high (light), use black text.
            # If luminance is low (dark), use white text.
            return "black" if y > 128 else "white"
        except:
            # Fallback if color is invalid (e.g. empty string)
            return "black"

    def _badge(self, parent, text, color, index):
        # Calculate readable text color
        fg = self._get_contrast_fg(color)

        # Add a slight 3D effect or border to badge
        frame = tk.Frame(parent, bg=color, pady=1)
        frame.pack(fill=tk.X, padx=2, pady=1)

        lbl = tk.Label(frame, text=text, anchor="w", bg=color, fg=fg,
                       font=("Segoe UI", 8), cursor="hand2")
        lbl.pack(fill=tk.X, padx=4)

        lbl.bind("<Button-1>", lambda e, i=index: self._calendar_edit_by_index(i))
        lbl.bind("<Button-3>", lambda e, i=index: self._popup_event_menu(e, i))

    def _popup_event_menu(self, event, index):
        m = tk.Menu(self.app.root, tearoff=0)
        m.add_command(label="✏ Bewerken", command=lambda: self._calendar_edit_by_index(index))
        m.add_command(label="🗑 Verwijderen", command=lambda: self._calendar_delete_by_index(index))
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def _render_calendar_month(self, year, month):
        # 1. Clean grid
        for w in self.calendar_grid.winfo_children():
            w.destroy()

        # 2. Setup
        first_weekday = datetime.date(year, month, 1).weekday() # 0=Mon
        days_in_month = calendar.monthrange(year, month)[1]
        grouped_events = self._events_by_date_with_indices()
        today = datetime.date.today()

        # 3. Draw Days
        for day in range(1, days_in_month + 1):
            slot = first_weekday + day - 1
            r, c = divmod(slot, 7)

            # Styling
            is_weekend = (c >= 5)
            is_today = (today.year == year and today.month == month and today.day == day)

            bg_color = "#f9fcfd" if is_weekend else "#ffffff"

            # Container Frame for the day cell
            cell_frame = tk.Frame(self.calendar_grid, bg="#cfd8dc", padx=1, pady=1) # Outer border simulation
            cell_frame.grid(row=r, column=c, sticky='nsew')

            # Inner Content Frame
            if is_today:
                # Highlight today
                content = tk.Frame(cell_frame, bg=bg_color, highlightbackground="#3a7afe", highlightthickness=2)
            else:
                content = tk.Frame(cell_frame, bg=bg_color, highlightthickness=0)

            content.pack(fill=tk.BOTH, expand=True)

            # Header inside cell (Day number + Add Button)
            top_row = tk.Frame(content, bg=bg_color)
            top_row.pack(fill=tk.X, padx=2, pady=2)

            day_lbl_color = "#3a7afe" if is_today else "#333333"
            day_font = ("Segoe UI", 11, "bold") if is_today else ("Segoe UI", 10)

            tk.Label(top_row, text=str(day), bg=bg_color, fg=day_lbl_color, font=day_font).pack(side=tk.LEFT)

            # Add Button (Symbol only to save space)
            add_btn = tk.Label(top_row, text="+", bg="#e0e0e0", fg="#555", width=2, cursor="hand2")
            add_btn.pack(side=tk.RIGHT)
            # Bind click
            current_date_obj = datetime.date(year, month, day)
            add_btn.bind("<Button-1>", lambda e, d=current_date_obj: self._add_event_for_date(d))

            # Events Area
            events_area = tk.Frame(content, bg=bg_color)
            events_area.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

            # Allow double click on empty space to add
            content.bind("<Double-Button-1>", lambda e, d=current_date_obj: self._add_event_for_date(d))
            events_area.bind("<Double-Button-1>", lambda e, d=current_date_obj: self._add_event_for_date(d))

            # Add Badges
            date_str = current_date_obj.isoformat()
            if date_str in grouped_events:
                for idx, ev in grouped_events[date_str]:
                    name = ev.get('name', 'Event')
                    color = ev.get('color', '#888')
                    self._badge(events_area, name, color, idx)

        self._refresh_legend()
        self._refresh_displayed_months_list()
        self._refresh_month_year_selectors()

    def _refresh_month_year_selectors(self):
        dms = sorted({tuple(x) for x in self.full_calendar_json_data.get("displayedMonths", [])})

        if not dms:
            # Fallback if no months are configured
            self.year_combo['values'] = [str(self.current_year)]
            self.month_combo['values'] = self.month_names_nl
        else:
            years = sorted({str(y) for y, _ in dms}, key=lambda s: int(s))
            self.year_combo['values'] = years

            # Filter months for current selected year
            months_for_year = sorted({m for y, m in dms if y == self.current_year})

            # If current year has no months (because we switched year), pick first available
            if not months_for_year and dms:
                # Find nearest year or just pick first
                pass

            self.month_combo['values'] = [self.month_names_nl[m - 1] for m in months_for_year]

        # Sync variables
        self.view_year_var.set(str(self.current_year))
        try:
            self.view_month_var.set(self.month_names_nl[self.current_month - 1])
        except IndexError:
            pass

    def _refresh_legend(self):
        for w in self.legend_frame.winfo_children(): w.destroy()

        # Count event colors
        color_counts = {}
        for ev in self.full_calendar_json_data.get("events", []):
            col = ev.get("color")
            if col:
                color_counts[col] = color_counts.get(col, 0) + 1

        if not color_counts:
            ttk.Label(self.legend_frame, text="Geen events gevonden", foreground="#888").pack(anchor="w", padx=5)
            return

        ttk.Label(self.legend_frame, text="Kleurgebruik", font=("", 9, "bold")).pack(anchor="w", pady=(0, 6), padx=5)

        for col, cnt in sorted(color_counts.items(), key=lambda x: (-x[1], x[0])):
            row = ttk.Frame(self.legend_frame)
            row.pack(fill=tk.X, pady=2, padx=5)

            # Determine contrast for the legend text/swatch if needed
            # Here we just show the swatch and black text for the count

            # Color swatch
            lbl_swatch = tk.Label(row, bg=col, width=2, relief="solid", borderwidth=1)
            lbl_swatch.pack(side=tk.LEFT, padx=(0, 8))

            # Text
            tk.Label(row, text=f"{cnt} events", anchor="w").pack(side=tk.LEFT)

    def _refresh_displayed_months_list(self):
        self.displayed_list.config(state=tk.NORMAL)
        self.displayed_list.delete(0, END)
        dms = sorted(self.full_calendar_json_data.get("displayedMonths", []))
        for y, m in dms:
            name = self.month_names_nl[m - 1] if 1 <= m <= 12 else "?"
            self.displayed_list.insert(END, f"{name} {y}")
        self.displayed_list.config(state=tk.DISABLED)

    def _sorted_displayed_months(self):
        return sorted({tuple(x) for x in self.full_calendar_json_data.get("displayedMonths", [])})

    # --- Navigation ---

    def _goto_prev_month(self):
        dms = self._sorted_displayed_months()
        if not dms: return
        try:
            idx = dms.index((self.current_year, self.current_month))
            prev_idx = idx - 1 if idx > 0 else len(dms) - 1
            self.current_year, self.current_month = dms[prev_idx]
            self._render_calendar_month(self.current_year, self.current_month)
        except ValueError:
            # Current view not in list, jump to first
            self.current_year, self.current_month = dms[0]
            self._render_calendar_month(self.current_year, self.current_month)

    def _goto_next_month(self):
        dms = self._sorted_displayed_months()
        if not dms: return
        try:
            idx = dms.index((self.current_year, self.current_month))
            next_idx = idx + 1 if idx < len(dms) - 1 else 0
            self.current_year, self.current_month = dms[next_idx]
            self._render_calendar_month(self.current_year, self.current_month)
        except ValueError:
            self.current_year, self.current_month = dms[0]
            self._render_calendar_month(self.current_year, self.current_month)

    def _goto_today(self):
        t = datetime.date.today()
        # Check if today is in the allowed list, otherwise just show it anyway (or nearest)
        # For this logic, we will force show it, but it might not be in the navigation list
        self.current_year, self.current_month = t.year, t.month
        self._render_calendar_month(self.current_year, self.current_month)

    def _on_view_month_year_changed(self, event=None):
        try:
            new_y = int(self.view_year_var.get())
            new_m_name = self.view_month_var.get()
            if new_m_name in self.month_names_nl:
                new_m = self.month_names_nl.index(new_m_name) + 1
                self.current_year = new_y
                self.current_month = new_m
                self._render_calendar_month(new_y, new_m)
        except ValueError:
            pass

    # --- Logic: Load/Save/Manage ---

    def _open_month_manager(self):
        current = [tuple(x) for x in self.full_calendar_json_data.get("displayedMonths", [])]
        dlg = MonthManagerDialog(self.app.root, current, self.month_names_nl)
        self.app.root.wait_window(dlg)

        if dlg.result is not None:
            # Sync
            new_set = set(dlg.result)
            self.full_calendar_json_data["displayedMonths"] = [list(t) for t in sorted(new_set)]
            self._refresh_displayed_months_list()

            # If current view deleted, jump to valid
            if (self.current_year, self.current_month) not in new_set and new_set:
                y, m = sorted(list(new_set))[0]
                self.current_year, self.current_month = y, m

            self._render_calendar_month(self.current_year, self.current_month)
            self.app.set_status("Maandselectie bijgewerkt.", duration_ms=3000)

    def _calendar_load_from_json(self):
        if not utils.confirm_discard_changes(self):
            return
        json_path = getattr(config, 'KALENDER_JSON_FILE_PATH', 'kalender.json')

        if not os.path.exists(json_path):
            self.calendar_file_loaded = False
            self._update_controls_enabled(False)
            messagebox.showerror("Bestand Niet Gevonden", f"Bestand niet gevonden:\n{json_path}", parent=self.app.root)
            return False

        self.app.set_status(f"Laden uit {os.path.basename(json_path)}...")
        self.app.root.update_idletasks()

        loaded_data, error_msg = utils.kalender_load_json_data(json_path)

        if error_msg:
            self.calendar_file_loaded = False
            self._update_controls_enabled(False)
            messagebox.showerror("Fout", f"Fout bij laden:\n{error_msg}", parent=self.app.root)
            return False

        if not loaded_data:
            loaded_data = {}

        # Merge with defaults to prevent crashes on missing keys
        default_structure = {
            "displayedMonths": [],
            "events": [],
            "legend": {"items": []}
        }
        for k, v in default_structure.items():
            if k not in loaded_data:
                loaded_data[k] = v

        self.full_calendar_json_data = loaded_data
        self.calendar_file_loaded = True

        # Initial View Logic
        dms = self._sorted_displayed_months()
        if dms:
            # Check if today is relevant, else first available
            t = datetime.date.today()
            if (t.year, t.month) in dms:
                 self.current_year, self.current_month = t.year, t.month
            else:
                 self.current_year, self.current_month = dms[0]
        else:
            t = datetime.date.today()
            self.current_year, self.current_month = t.year, t.month

        self._update_controls_enabled(True)
        self._render_calendar_month(self.current_year, self.current_month)
        self.app.set_status(f"Kalender geladen ({len(self.full_calendar_json_data.get('events', []))} events).", duration_ms=5000)
        utils.remember_editor_state(self, self.full_calendar_json_data)

    def has_unsaved_changes(self):
        return utils.editor_state_changed(self, self.full_calendar_json_data)

    def _add_event_for_date(self, date_obj):
        if not self.calendar_file_loaded:
            messagebox.showinfo("Info", "Laad eerst een kalenderbestand.", parent=self.app.root)
            return

        CalendarEventDialog(self.app.root, "Event Toevoegen", {'date': date_obj.isoformat()},
                            lambda d: self._process_event_action('add', d))

    def _calendar_edit_by_index(self, index):
        evs = self.full_calendar_json_data.get("events", [])
        if 0 <= index < len(evs):
            initial = copy.deepcopy(evs[index])
            CalendarEventDialog(self.app.root, "Event Bewerken", initial,
                                lambda d: self._process_event_action('edit', d, index))

    def _calendar_delete_by_index(self, index):
        evs = self.full_calendar_json_data.get("events", [])
        if 0 <= index < len(evs):
            if messagebox.askyesno("Bevestigen", "Dit event verwijderen?", parent=self.app.root):
                del evs[index]
                self._render_calendar_month(self.current_year, self.current_month)
                self.app.set_status("Event verwijderd.", duration_ms=3000)

    def _process_event_action(self, action, data, index=None):
        if not data: return

        if action == 'add':
            self.full_calendar_json_data.setdefault("events", []).append(data)
            self.app.set_status("Event toegevoegd.", duration_ms=3000)
        elif action == 'edit' and index is not None:
            self.full_calendar_json_data["events"][index] = data
            self.app.set_status("Event bijgewerkt.", duration_ms=3000)

        self._render_calendar_month(self.current_year, self.current_month)

    def _calendar_save_to_json(self):
        path = getattr(config, 'KALENDER_JSON_FILE_PATH', 'kalender.json')

        # Ensure data consistency
        data = self.full_calendar_json_data

        self.app.set_status(f"Opslaan naar {os.path.basename(path)}...")
        err = utils.kalender_save_json_data(path, data)

        if not err:
            utils.remember_editor_state(self, self.full_calendar_json_data)
            self.app.set_status("Kalender succesvol opgeslagen.", duration_ms=5000)
        else:
            messagebox.showerror("Opslag Fout", f"Kon bestand niet opslaan:\n{err}", parent=self.app.root)
            self.app.set_status("Fout bij opslaan.", is_error=True)

def create_calendar_tab(parent_frame, app_instance):
    return CalendarTab(parent_frame, app_instance)

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import os
import config
import utils
import copy

class EditTimeDialog(tk.Toplevel):
    def __init__(self, parent, title, category_name, initial_times_list, callback):
        super().__init__(parent)
        self.transient(parent)
        self.title(f"{title} - {category_name}")
        self.category_name = category_name
        # Ensure we have a deep copy to avoid modifying original data accidentally
        self.initial_data = [dict(item) for item in initial_times_list]
        self.callback = callback
        self.result = None
        self.time_entries = [] # List of dicts holding widgets for a row

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(main_frame, text=f"Tijden voor: {category_name}", style="Bold.TLabel").pack(pady=(0, 10), anchor='w')

        # --- Scrollable Area Setup ---
        # Frame to hold canvas and scrollbar
        scroll_container = ttk.Frame(main_frame)
        scroll_container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(scroll_container, borderwidth=0, highlightthickness=0)
        self.vsb = ttk.Scrollbar(scroll_container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.scrollable_frame = ttk.Frame(self.canvas) # Frame to put widgets in

        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw") # Add frame to canvas

        self.scrollable_frame.bind("<Configure>", self._on_frame_configure) # Update scrollregion when frame size changes
        self.canvas.bind('<Configure>', self._on_canvas_configure) # Adjust window width on canvas resize
        self.canvas.bind('<Enter>', self._bind_mousewheel)
        self.canvas.bind('<Leave>', self._unbind_mousewheel)
        # --- End Scrollable Area Setup ---

        # Headers
        header_frame = ttk.Frame(self.scrollable_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(header_frame, text="Dag", width=15, anchor='w').pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="Tijd", width=25, anchor='w').pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="Nota (optioneel)", width=30, anchor='w').pack(side=tk.LEFT, padx=2)

        self._populate_times()

        # --- Bottom Buttons ---
        button_frame = ttk.Frame(main_frame) # Buttons outside scrollable area
        button_frame.pack(fill=tk.X, pady=(10,0), side=tk.BOTTOM)

        add_button = ttk.Button(button_frame, text="Dag/Tijd Toevoegen", command=self._add_time_entry)
        add_button.pack(side=tk.LEFT, padx=5)

        ok_button = ttk.Button(button_frame, text="OK", command=self.on_ok)
        ok_button.pack(side=tk.RIGHT, padx=(5, 0))
        cancel_button = ttk.Button(button_frame, text="Annuleren", command=self.on_cancel)
        cancel_button.pack(side=tk.RIGHT)
        # --- End Bottom Buttons ---

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.bind("<Escape>", self.on_cancel)
        # Update geometry requests and scroll region after initial population
        self.update_idletasks()
        self._on_frame_configure(None) # Set initial scrollregion
        self.wait_window()

    def _on_canvas_configure(self, event):
        # Adjust the width of the frame inside the canvas to match the canvas width
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_frame_configure(self, event):
        # Update the scroll region to encompass the frame
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _bind_mousewheel(self, event):
        # Bind mouse wheel scrolling only when the cursor is over the canvas
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        # Linux bindings
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)


    def _unbind_mousewheel(self, event):
        # Unbind mouse wheel scrolling when the cursor leaves the canvas
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
         # Determine scroll direction (platform-dependent)
        if event.num == 5 or event.delta < 0:
            delta = 1 # Scroll down
        elif event.num == 4 or event.delta > 0:
            delta = -1 # Scroll up
        else:
            delta = 0

        if delta != 0:
            self.canvas.yview_scroll(delta, "units")

    def _populate_times(self):
        # Destroy existing widgets in scrollable frame if any (e.g., if re-populating)
        for widget in self.scrollable_frame.winfo_children():
            # Keep the header frame
            if isinstance(widget, ttk.Frame) and any(isinstance(child, ttk.Label) and child.cget("text") in ["Dag", "Tijd", "Nota (optioneel)"] for child in widget.winfo_children()):
                continue
            widget.destroy()
        self.time_entries = [] # Clear the list tracking widgets

        # Add entries based on initial_data
        for time_data in self.initial_data:
            # Make sure day and time exist before adding
            if time_data.get('day') and time_data.get('time'):
                 self._add_time_entry(time_data['day'], time_data['time'], time_data.get('note', ''))
            # else: print warning?

        # Ensure scroll region is updated after adding all initial items
        self.scrollable_frame.update_idletasks()
        self._on_frame_configure(None)


    def _add_time_entry(self, day="", time="", note=""):
        # Add a new row for Day, Time, Note entries
        entry_frame = ttk.Frame(self.scrollable_frame) # Don't need padding here if added to parent
        entry_frame.pack(fill=tk.X, pady=1, padx=2) # Use small padding for visual separation

        day_entry = ttk.Entry(entry_frame, width=15)
        day_entry.insert(0, day)
        day_entry.pack(side=tk.LEFT, padx=(0, 2)) # Pad right

        time_entry = ttk.Entry(entry_frame, width=25)
        time_entry.insert(0, time)
        time_entry.pack(side=tk.LEFT, padx=2)

        note_entry = ttk.Entry(entry_frame, width=30)
        note_entry.insert(0, note if note else "") # Handle None note
        note_entry.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True) # Let note expand

        remove_button = ttk.Button(entry_frame, text="X", width=3, style="Small.TButton",
                                   command=lambda f=entry_frame: self._remove_time_entry(f))
        remove_button.pack(side=tk.RIGHT, padx=(2, 0)) # Pad left

        # Store references to the widgets for this entry
        self.time_entries.append({'frame': entry_frame, 'day': day_entry, 'time': time_entry, 'note': note_entry})

        # Update scroll region incrementally might be less efficient but ensures it works
        self.scrollable_frame.update_idletasks()
        self._on_frame_configure(None)


    def _remove_time_entry(self, frame_to_remove):
        # Remove the frame and its widgets from the UI
        frame_to_remove.destroy()
        # Remove the corresponding dictionary from our tracking list
        self.time_entries = [entry for entry in self.time_entries if entry['frame'].winfo_exists()]
        # Update scroll region after removing
        self.scrollable_frame.update_idletasks()
        self._on_frame_configure(None)


    def on_ok(self):
        self.result = []
        for entry_widgets in self.time_entries:
            # Double-check if the frame widget still exists before accessing children
            if entry_widgets['frame'].winfo_exists():
                day = entry_widgets['day'].get().strip()
                time = entry_widgets['time'].get().strip()
                note = entry_widgets['note'].get().strip()
                # Only include entries that have at least a day and time specified
                if day and time:
                    self.result.append({'day': day, 'time': time, 'note': note or None}) # Store empty note as None
        if self.callback:
            self.callback(self.category_name, self.result)
        self.destroy()

    def on_cancel(self):
        self.destroy() # No callback needed for cancel


class TrainerDialog(tk.Toplevel):
    def __init__(self, parent, title, categories, initial_data=None, callback=None):
        super().__init__(parent); self.transient(parent); self.title(title); self.callback = callback
        self.initial_data = initial_data or {}
        # Ensure "<Nieuwe Categorie...>" is always last
        self.categories = sorted([c for c in categories if c != "<Nieuwe Categorie...>"]) + ["<Nieuwe Categorie...>"]
        self.result = None

        frame = ttk.Frame(self, padding="15"); frame.pack(expand=True, fill=tk.BOTH)
        row_index = 0

        ttk.Label(frame, text="Categorie:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(frame, textvariable=self.category_var, values=self.categories, state="readonly", width=38)
        self.category_combo.grid(row=row_index, column=1, sticky="ew", padx=5, pady=2)
        # Set initial value carefully
        initial_cat = self.initial_data.get('category')
        if initial_cat and initial_cat in self.categories:
             self.category_var.set(initial_cat)
        elif len(self.categories) > 1: # Avoid setting if only "<Nieuwe...>" exists
             self.category_var.set(self.categories[0]) # Default to first real category
        else:
             self.category_var.set("<Nieuwe Categorie...>") # Default to new if no others exist

        self.category_combo.bind("<<ComboboxSelected>>", self._toggle_new_category)
        row_index += 1

        # Placeholder for the new category entry, placed correctly
        self.new_category_label = ttk.Label(frame, text="Nieuwe Categorie Naam:")
        self.new_category_entry = ttk.Entry(frame, width=40)
        # Grid these later in _toggle_new_category based on selection
        self.new_category_label.grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=2)
        self.new_category_entry.grid(row=row_index, column=1, sticky="ew", padx=5, pady=2)
        row_index += 1

        ttk.Label(frame, text="Naam:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.name_entry = ttk.Entry(frame, width=40)
        self.name_entry.grid(row=row_index, column=1, sticky="ew", padx=5, pady=2)
        self.name_entry.insert(0, self.initial_data.get('name', ''))
        row_index += 1

        ttk.Label(frame, text="E-mail (optioneel):").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.email_entry = ttk.Entry(frame, width=40)
        self.email_entry.grid(row=row_index, column=1, sticky="ew", padx=5, pady=2)
        self.email_entry.insert(0, self.initial_data.get('email', '') or '') # Ensure empty string if None
        row_index += 1

        ttk.Label(frame, text="Tel (optioneel):").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.phone_entry = ttk.Entry(frame, width=40)
        self.phone_entry.grid(row=row_index, column=1, sticky="ew", padx=5, pady=2)
        self.phone_entry.insert(0, self.initial_data.get('phone', '') or '') # Ensure empty string if None
        row_index += 1

        frame.columnconfigure(1, weight=1)
        button_frame = ttk.Frame(frame); button_frame.grid(row=row_index, column=0, columnspan=2, pady=(15, 0), sticky=tk.E)
        ok_button = ttk.Button(button_frame, text="OK", command=self.on_ok); ok_button.pack(side=tk.RIGHT, padx=(5, 0))
        cancel_button = ttk.Button(button_frame, text="Annuleren", command=self.on_cancel); cancel_button.pack(side=tk.RIGHT)

        self._toggle_new_category() # Initial visibility check
        self.grab_set(); self.protocol("WM_DELETE_WINDOW", self.on_cancel); self.bind("<Return>", self.on_ok); self.bind("<Escape>", self.on_cancel)
        self.name_entry.focus_set(); self.wait_window(self)

    def _toggle_new_category(self, event=None):
        # Show/hide the 'New Category Name' entry and label
        if self.category_var.get() == "<Nieuwe Categorie...>":
            self.new_category_label.grid() # Show label
            self.new_category_entry.grid() # Show entry
            self.new_category_entry.config(state=tk.NORMAL)
        else:
            self.new_category_label.grid_remove() # Hide label
            self.new_category_entry.grid_remove() # Hide entry
            self.new_category_entry.delete(0, tk.END)
            self.new_category_entry.config(state=tk.DISABLED)


    def on_ok(self, event=None):
        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        phone = self.phone_entry.get().strip()
        category_selection = self.category_var.get()

        if not name:
            messagebox.showwarning("Invoer Vereist", "Naam mag niet leeg zijn.", parent=self)
            self.name_entry.focus_set(); return

        if category_selection == "<Nieuwe Categorie...>":
            category = self.new_category_entry.get().strip()
            if not category:
                messagebox.showwarning("Invoer Vereist", "Voer een naam in voor de nieuwe categorie.", parent=self)
                self.new_category_entry.focus_set(); return
        elif not category_selection:
             messagebox.showwarning("Invoer Vereist", "Selecteer een categorie.", parent=self)
             self.category_combo.focus_set(); return
        else:
            category = category_selection

        self.result = {'name': name, 'email': email or None, 'phone': phone or None, 'category': category}

        if self.callback:
            # Pass original details back if they exist (for finding the item to modify/delete)
            original_category = self.initial_data.get('category')
            original_index = self.initial_data.get('original_index')
            tree_iid = self.initial_data.get('iid') # Pass iid for easier Treeview update
            self.callback(self.result, original_category, original_index, tree_iid)
        self.destroy()

    def on_cancel(self, event=None):
        self.destroy()


class TrainersTab:
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance
        # Use deepcopy to prevent accidental modification of initial empty dict
        self.trainers_data = copy.deepcopy({'times': {}, 'contacts': {}, 'trainers': {}})
        self.trainers_file_loaded = False
        # Style for small buttons like the remove 'X'
        s = ttk.Style()
        s.configure("Small.TButton", padding=1)
        self._create_widgets()
        self._trainers_load() # Load data on initialization

    def _create_widgets(self):
        self.parent.grid_rowconfigure(0, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        # Main Paned Window
        pw_main = ttk.PanedWindow(self.parent, orient=tk.VERTICAL)
        pw_main.grid(row=0, column=0, sticky='nsew')

        # Top Frame for Controls
        controls_frame = ttk.Frame(pw_main)
        self.load_button = ttk.Button(controls_frame, text="Herlaad Trainers/Tijden Data", command=self._trainers_load)
        self.load_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.save_button = ttk.Button(controls_frame, text="Alle Wijzigingen Opslaan", command=self._trainers_save, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5, pady=5)
        pw_main.add(controls_frame, weight=0)

        # Paned Window for Content Areas
        pw_content = ttk.PanedWindow(pw_main, orient=tk.HORIZONTAL)

        # --- Left Pane: Times and Contacts ---
        left_pane = ttk.Frame(pw_content, padding=5)
        left_pane.grid_rowconfigure(1, weight=1) # Times Treeview expands
        left_pane.grid_columnconfigure(0, weight=1)

        # Contacts Frame
        contacts_frame = ttk.Labelframe(left_pane, text=" Contactpersonen ", padding=10)
        contacts_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        contacts_frame.columnconfigure(1, weight=1)

        # Vertrouwenspersoon
        ttk.Label(contacts_frame, text="Vertrouwenspersoon:", style="Bold.TLabel").grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 5))
        ttk.Label(contacts_frame, text="Naam:").grid(row=1, column=0, sticky='w', padx=5); self.v_name = ttk.Entry(contacts_frame, width=30, state='readonly'); self.v_name.grid(row=1, column=1, sticky='ew', padx=5)
        ttk.Label(contacts_frame, text="Email:").grid(row=2, column=0, sticky='w', padx=5); self.v_email = ttk.Entry(contacts_frame, width=30, state='readonly'); self.v_email.grid(row=2, column=1, sticky='ew', padx=5)
        ttk.Label(contacts_frame, text="Tel:").grid(row=3, column=0, sticky='w', padx=5); self.v_phone = ttk.Entry(contacts_frame, width=30, state='readonly'); self.v_phone.grid(row=3, column=1, sticky='ew', padx=5)
        ttk.Label(contacts_frame, text="Img Src:").grid(row=4, column=0, sticky='w', padx=5); self.v_img = ttk.Entry(contacts_frame, width=30, state='readonly'); self.v_img.grid(row=4, column=1, sticky='ew', padx=5)

        ttk.Separator(contacts_frame, orient=tk.HORIZONTAL).grid(row=5, column=0, columnspan=3, sticky='ew', pady=10)

        # Jeugdcoördinator
        ttk.Label(contacts_frame, text="Jeugdcoördinator:", style="Bold.TLabel").grid(row=6, column=0, columnspan=3, sticky='w', pady=(0, 5))
        ttk.Label(contacts_frame, text="Naam:").grid(row=7, column=0, sticky='w', padx=5); self.j_name = ttk.Entry(contacts_frame, width=30, state='readonly'); self.j_name.grid(row=7, column=1, sticky='ew', padx=5)
        ttk.Label(contacts_frame, text="Email:").grid(row=8, column=0, sticky='w', padx=5); self.j_email = ttk.Entry(contacts_frame, width=30, state='readonly'); self.j_email.grid(row=8, column=1, sticky='ew', padx=5)
        ttk.Label(contacts_frame, text="Tel:").grid(row=9, column=0, sticky='w', padx=5); self.j_phone = ttk.Entry(contacts_frame, width=30, state='readonly'); self.j_phone.grid(row=9, column=1, sticky='ew', padx=5)
        ttk.Label(contacts_frame, text="Img Src:").grid(row=10, column=0, sticky='w', padx=5); self.j_img = ttk.Entry(contacts_frame, width=30, state='readonly'); self.j_img.grid(row=10, column=1, sticky='ew', padx=5)

        # Times Frame
        times_frame = ttk.Labelframe(left_pane, text=" Trainingstijden ", padding=10)
        times_frame.grid(row=1, column=0, sticky='nsew')
        times_frame.grid_rowconfigure(0, weight=1)
        times_frame.grid_columnconfigure(0, weight=1)

        times_cols = ('category', 'times_display')
        self.times_tree = ttk.Treeview(times_frame, columns=times_cols, show='headings', selectmode='browse')
        self.times_tree.heading('category', text='Categorie', command=lambda: self._sort_times_tree('category'))
        self.times_tree.column('category', width=150, anchor=tk.W)
        self.times_tree.heading('times_display', text='Dagen & Tijden', command=lambda: self._sort_times_tree('times_display'))
        self.times_tree.column('times_display', width=300, anchor=tk.W) # Increased width

        times_vsb = ttk.Scrollbar(times_frame, orient="vertical", command=self.times_tree.yview)
        self.times_tree.configure(yscrollcommand=times_vsb.set)
        self.times_tree.grid(row=0, column=0, sticky='nsew')
        times_vsb.grid(row=0, column=1, sticky='ns')
        self._times_sort_column = 'category'
        self._times_sort_reverse = False

        times_button_frame = ttk.Frame(times_frame)
        times_button_frame.grid(row=1, column=0, columnspan=2, sticky='w', pady=(5,0))
        self.edit_times_button = ttk.Button(times_button_frame, text="Bewerk Tijden Geselecteerde Categorie...", command=self._edit_selected_times, state=tk.DISABLED)
        self.edit_times_button.pack(side=tk.LEFT)
        self.times_tree.bind("<<TreeviewSelect>>", lambda e: self.edit_times_button.config(state=tk.NORMAL if self.times_tree.selection() else tk.DISABLED))
        self.times_tree.bind("<Double-1>", lambda e: self._edit_selected_times() if self.edit_times_button['state'] == tk.NORMAL else None)


        pw_content.add(left_pane, weight=1)

        # --- Right Pane: Trainers ---
        right_pane = ttk.Frame(pw_content, padding=5)
        right_pane.grid_rowconfigure(0, weight=1) # Treeview expands
        right_pane.grid_columnconfigure(0, weight=1)

        trainers_frame = ttk.Labelframe(right_pane, text=" Trainers Lijst ", padding=10)
        trainers_frame.grid(row=0, column=0, sticky='nsew')
        trainers_frame.grid_rowconfigure(0, weight=1)
        trainers_frame.grid_columnconfigure(0, weight=1)

        trainer_cols = ('category', 'name', 'email', 'phone')
        self.trainers_tree = ttk.Treeview(trainers_frame, columns=trainer_cols, show='headings', selectmode='browse')
        self.trainers_tree.heading('category', text='Categorie', command=lambda: self._sort_trainers_tree('category')); self.trainers_tree.column('category', width=180, anchor=tk.W) # Wider category
        self.trainers_tree.heading('name', text='Naam', command=lambda: self._sort_trainers_tree('name')); self.trainers_tree.column('name', width=200, anchor=tk.W)
        self.trainers_tree.heading('email', text='E-mail', command=lambda: self._sort_trainers_tree('email')); self.trainers_tree.column('email', width=180, anchor=tk.W)
        self.trainers_tree.heading('phone', text='Telefoon', command=lambda: self._sort_trainers_tree('phone')); self.trainers_tree.column('phone', width=120, anchor=tk.W) # Wider phone
        self._trainers_sort_column = 'category'
        self._trainers_sort_reverse = False

        trainers_vsb = ttk.Scrollbar(trainers_frame, orient="vertical", command=self.trainers_tree.yview)
        trainers_hsb = ttk.Scrollbar(trainers_frame, orient="horizontal", command=self.trainers_tree.xview)
        self.trainers_tree.configure(yscrollcommand=trainers_vsb.set, xscrollcommand=trainers_hsb.set)
        self.trainers_tree.grid(row=0, column=0, sticky='nsew'); trainers_vsb.grid(row=0, column=1, sticky='ns'); trainers_hsb.grid(row=1, column=0, sticky='ew')

        trainer_buttons = ttk.Frame(trainers_frame)
        trainer_buttons.grid(row=2, column=0, columnspan=2, sticky='w', pady=(5,0))
        self.add_trainer_button = ttk.Button(trainer_buttons, text="Trainer Toevoegen...", command=self._add_trainer_dialog, state=tk.DISABLED)
        self.add_trainer_button.pack(side=tk.LEFT, padx=(0,5))
        self.edit_trainer_button = ttk.Button(trainer_buttons, text="Trainer Bewerken...", command=self._edit_trainer_dialog, state=tk.DISABLED)
        self.edit_trainer_button.pack(side=tk.LEFT, padx=5)
        self.delete_trainer_button = ttk.Button(trainer_buttons, text="Trainer Verwijderen", command=self._delete_trainer, state=tk.DISABLED)
        self.delete_trainer_button.pack(side=tk.LEFT, padx=5)

        self.trainers_tree.bind("<<TreeviewSelect>>", self._on_trainer_select)
        self.trainers_tree.bind("<Double-1>", self._on_trainer_double_click)

        pw_content.add(right_pane, weight=2)
        pw_main.add(pw_content, weight=1)

    def _trainers_load(self):
        if not os.path.exists(config.TRAINERS_HTML_FILE_PATH):
            messagebox.showerror("Bestand Niet Gevonden", f"Trainers bestand niet gevonden:\n{config.TRAINERS_HTML_FILE_PATH}", parent=self.app.root)
            self.app.set_status("Fout: Trainers HTML niet gevonden.", is_error=True)
            self._set_ui_state(loaded=False); return

        self.app.set_status("Laden trainers/tijden data..."); self.app.root.update_idletasks()
        parsed_data, error_msg = utils.trainers_parse_html(config.TRAINERS_HTML_FILE_PATH)

        if error_msg:
            # Reset data on error
            self.trainers_data = copy.deepcopy({'times': {}, 'contacts': {}, 'trainers': {}})
            self.trainers_file_loaded = False
            self.app.set_status(f"Fout bij laden trainers: {error_msg}", is_error=True)
            messagebox.showerror("Laad Fout", f"Kon trainers data niet parsen:\n{error_msg}", parent=self.app.root)
        else:
            self.trainers_data = parsed_data if parsed_data else copy.deepcopy({'times': {}, 'contacts': {}, 'trainers': {}})
            self.trainers_file_loaded = True
            self._populate_ui() # Populate with parsed or default data
            self.app.set_status("Trainers/tijden data succesvol geladen.", duration_ms=5000)

        self._set_ui_state(loaded=self.trainers_file_loaded)

    def _set_ui_state(self, loaded):
        state = tk.NORMAL if loaded else tk.DISABLED
        contact_entry_state = tk.NORMAL if loaded else 'readonly' # Make contacts editable when loaded

        # Buttons
        self.save_button.config(state=state)
        self.add_trainer_button.config(state=state)
        # Selection-dependent buttons default to disabled
        self.edit_trainer_button.config(state=tk.DISABLED)
        self.delete_trainer_button.config(state=tk.DISABLED)
        self.edit_times_button.config(state=tk.DISABLED)

        # Contact Entries
        for entry in [self.v_name, self.v_email, self.v_phone, self.v_img, self.j_name, self.j_email, self.j_phone, self.j_img]:
             entry.config(state=contact_entry_state)

        if not loaded:
            self._clear_ui()
        else:
             # Ensure contacts are populated even if parsing returned empty sections
             self._populate_contacts()


    def _clear_ui(self):
         # Clear Contact Fields
        for entry in [self.v_name, self.v_email, self.v_phone, self.v_img, self.j_name, self.j_email, self.j_phone, self.j_img]:
            current_state = entry.cget('state')
            if current_state != 'readonly': entry.config(state=tk.NORMAL)
            entry.delete(0, tk.END)
            entry.config(state=current_state) # Restore original state if needed (though we set it in _set_ui_state)
        # Clear Treeviews
        for item in self.times_tree.get_children(): self.times_tree.delete(item)
        for item in self.trainers_tree.get_children(): self.trainers_tree.delete(item)

    def _populate_ui(self):
        self._clear_ui() # Clear first
        self._populate_contacts()
        self._populate_times_treeview()
        self._populate_trainers_treeview()
        # Reset sort indicators
        self._update_times_sort_indicator()
        self._update_trainers_sort_indicator()
        # Deselect items and disable buttons dependent on selection
        self.times_tree.selection_remove(self.times_tree.selection())
        self.trainers_tree.selection_remove(self.trainers_tree.selection())
        self._on_trainer_select()
        self.edit_times_button.config(state=tk.DISABLED)


    def _populate_contacts(self):
         # Get data, providing empty dicts as defaults
         contacts = self.trainers_data.get('contacts', {})
         v_data = contacts.get('vertrouwenspersoon', {})
         j_data = contacts.get('jeugdcoordinator', {})

         # Update contact fields - ensure they are editable first
         for entry, value in [(self.v_name, v_data.get('name', '')),
                              (self.v_email, v_data.get('email', '')),
                              (self.v_phone, v_data.get('phone', '')),
                              (self.v_img, v_data.get('img', '')),
                              (self.j_name, j_data.get('name', '')),
                              (self.j_email, j_data.get('email', '')),
                              (self.j_phone, j_data.get('phone', '')),
                              (self.j_img, j_data.get('img', ''))]:
             entry.config(state=tk.NORMAL)
             entry.delete(0, tk.END)
             entry.insert(0, value or '') # Insert empty string if value is None

    def _sort_times_tree(self, col):
        items = [(self.times_tree.set(iid, col), iid) for iid in self.times_tree.get_children('')]

        # Determine if the column should be sorted case-insensitively
        numeric_sort = False # Add logic here if a column is numeric
        reverse = (col == self._times_sort_column and not self._times_sort_reverse)
        self._times_sort_reverse = reverse

        if numeric_sort:
            items.sort(key=lambda x: float(x[0]) if x[0] else 0, reverse=reverse)
        else:
            items.sort(key=lambda x: str(x[0]).lower(), reverse=reverse)

        for index, (val, iid) in enumerate(items):
            self.times_tree.move(iid, '', index)

        self._times_sort_column = col
        self._update_times_sort_indicator()


    def _update_times_sort_indicator(self):
         arrow = ' ↓' if self._times_sort_reverse else ' ↑'
         cols = {'category': 'Categorie', 'times_display': 'Dagen & Tijden'}
         for c, base_text in cols.items():
             text = base_text + (arrow if c == self._times_sort_column else '')
             self.times_tree.heading(c, text=text)


    def _populate_times_treeview(self):
        # Clear existing items
        for item in self.times_tree.get_children():
            self.times_tree.delete(item)
        # Repopulate from self.trainers_data['times'] using current sort
        times_dict = self.trainers_data.get('times', {})
        # Create list of tuples for sorting: (sort_value, category, display_string)
        items_to_sort = []
        for category, times_list in times_dict.items():
            display_texts = []
            for item in sorted(times_list, key=lambda x: x.get('day', '')): # Sort times by day within category
                text = f"{item.get('day', '?')}: {item.get('time', '?')}"
                if item.get('note'): text += f" ({item['note']})"
                display_texts.append(text)
            display_str = " | ".join(display_texts)
            sort_val = category if self._times_sort_column == 'category' else display_str
            items_to_sort.append((sort_val, category, display_str))

        # Sort the list
        items_to_sort.sort(key=lambda x: str(x[0]).lower(), reverse=self._times_sort_reverse)

        # Insert sorted items
        for _, category, display_str in items_to_sort:
             self.times_tree.insert('', tk.END, iid=category, values=(category, display_str))

        self._update_times_sort_indicator() # Update headers after populating


    def _edit_selected_times(self):
        selected = self.times_tree.selection()
        if not selected: return
        category = selected[0] # iid is the category name
        # Get a deep copy of the current times for the dialog
        current_times = copy.deepcopy(self.trainers_data.get('times', {}).get(category, []))
        EditTimeDialog(self.app.root, "Trainingstijden Bewerken", category, current_times, self._update_times_data)

    def _update_times_data(self, category, new_times_list):
        if new_times_list is not None: # Check if dialog was cancelled
             # Update the main data dictionary
             self.trainers_data.setdefault('times', {})[category] = new_times_list
             # Repopulate the times treeview to reflect the change and maintain sort order
             self._populate_times_treeview()
             self.app.set_status(f"Tijden voor '{category}' bijgewerkt (niet opgeslagen).", duration_ms=4000)
             # Reselect the item if it still exists
             if self.times_tree.exists(category):
                  self.times_tree.selection_set(category)


    def _on_trainer_select(self, event=None):
         is_selected = bool(self.trainers_tree.selection())
         state = tk.NORMAL if is_selected else tk.DISABLED
         self.edit_trainer_button.config(state=state)
         self.delete_trainer_button.config(state=state)

    def _on_trainer_double_click(self, event=None):
         if self.edit_trainer_button['state'] == tk.NORMAL:
              self._edit_trainer_dialog()

    def _get_trainer_categories(self):
         # Get categories currently present in the trainer data
         return sorted(list(self.trainers_data.get('trainers', {}).keys()))

    def _add_trainer_dialog(self):
         categories = self._get_trainer_categories()
         # Pass callback without original index/category/iid for adding
         TrainerDialog(self.app.root, "Trainer Toevoegen", categories, callback=lambda d, oc, oi, tid: self._process_trainer_edit(d, None, None, None))

    def _edit_trainer_dialog(self):
         selected = self.trainers_tree.selection()
         if not selected: return
         iid = selected[0]
         values = self.trainers_tree.item(iid, 'values')
         tags = self.trainers_tree.item(iid, 'tags')

         if not tags or len(tags) < 2:
              messagebox.showerror("Fout", "Interne fout: Kan trainer data niet lezen.", parent=self.app.root)
              return

         category = tags[0]
         try:
             original_index = int(tags[1])
         except (ValueError, IndexError):
             messagebox.showerror("Fout", "Interne fout: Ongeldige trainer index.", parent=self.app.root)
             return

         initial_data = {
             'category': category,
             'name': values[1],
             'email': values[2] or None,
             'phone': values[3] or None,
             'original_index': original_index, # Pass original index for finding later
             'iid': iid # Pass treeview iid for potential update later
         }
         categories = self._get_trainer_categories()
         TrainerDialog(self.app.root, "Trainer Bewerken", categories, initial_data, self._process_trainer_edit)


    def _process_trainer_edit(self, new_data, original_category, original_index, tree_iid):
         # tree_iid is the iid from the Treeview for the item being edited, if applicable
         if new_data is None: return # Dialog cancelled

         new_category = new_data['category']
         trainer_entry = {'name': new_data['name'], 'email': new_data.get('email'), 'phone': new_data.get('phone')}

         # Remove from old location if it was an edit (original_category and original_index are valid)
         was_edit = original_category is not None and original_index is not None
         if was_edit:
             if original_category in self.trainers_data.get('trainers', {}) and \
                len(self.trainers_data['trainers'][original_category]) > original_index:
                 # Make sure we are deleting the correct one if list order changed (unlikely here but safer)
                 # This check is basic; could compare names if needed.
                 del self.trainers_data['trainers'][original_category][original_index]
                 # If category becomes empty after deletion, remove the category key
                 if not self.trainers_data['trainers'][original_category]:
                     del self.trainers_data['trainers'][original_category]
             else:
                 print(f"Warning: Could not find trainer at original index {original_index} in category '{original_category}' to remove during edit.")


         # Add/update in the new/correct category
         trainers_dict = self.trainers_data.setdefault('trainers', {})
         category_list = trainers_dict.setdefault(new_category, [])
         category_list.append(trainer_entry) # Add the new/edited trainer entry

         # Repopulate the entire trainer treeview to reflect potentially new categories and order
         self._populate_trainers_treeview()
         self.app.set_status("Trainer lijst bijgewerkt (niet opgeslagen).", duration_ms=4000)

         # Try to re-select the newly added/edited item
         # Finding the exact new item is tricky after repopulation.
         # A simple approach is to find the first item matching the new data.
         new_iid_to_select = None
         for item_iid in self.trainers_tree.get_children():
             values = self.trainers_tree.item(item_iid, 'values')
             if values[0] == new_category and values[1] == new_data['name']:
                 new_iid_to_select = item_iid
                 break
         if new_iid_to_select:
             self.trainers_tree.selection_set(new_iid_to_select)
             self.trainers_tree.focus(new_iid_to_select)
             self.trainers_tree.see(new_iid_to_select)


    def _delete_trainer(self):
         selected = self.trainers_tree.selection()
         if not selected: return
         iid = selected[0]
         values = self.trainers_tree.item(iid, 'values')
         tags = self.trainers_tree.item(iid, 'tags')

         if not tags or len(tags) < 2:
              messagebox.showerror("Fout", "Interne fout: Kan trainer data niet lezen.", parent=self.app.root)
              return

         category = tags[0]
         try:
            original_index = int(tags[1])
         except (ValueError, IndexError):
             messagebox.showerror("Fout", "Interne fout: Ongeldige trainer index.", parent=self.app.root)
             return

         name = values[1]

         if messagebox.askyesno("Verwijderen Bevestigen", f"Trainer '{name}' uit categorie '{category}' verwijderen?", icon='warning', parent=self.app.root):
              try:
                  trainers_in_category = self.trainers_data.get('trainers', {}).get(category)
                  if trainers_in_category and len(trainers_in_category) > original_index:
                      del trainers_in_category[original_index]
                      # If category becomes empty, remove it
                      if not trainers_in_category:
                          del self.trainers_data['trainers'][category]
                      self._populate_trainers_treeview() # Repopulate tree
                      self.app.set_status(f"Trainer '{name}' verwijderd (niet opgeslagen).", duration_ms=4000)
                  else:
                       # This case might happen if data is inconsistent
                       messagebox.showerror("Fout", f"Trainer niet gevonden in interne data (Cat: {category}, Idx: {original_index}). Probeer opnieuw te laden.", parent=self.app.root)
                       # Force reload might be good here
                       # self._trainers_load()
              except Exception as e:
                   messagebox.showerror("Fout", f"Fout bij verwijderen: {e}", parent=self.app.root)


    def _sort_trainers_tree(self, col):
        # Map column display name to data key
        key_map = {'category': 0, 'name': 1, 'email': 2, 'phone': 3}
        if col not in key_map: return
        col_index = key_map[col]

        items = [(self.trainers_tree.set(iid, col) or '', iid) for iid in self.trainers_tree.get_children('')]

        reverse = (col == self._trainers_sort_column and not self._trainers_sort_reverse)
        self._trainers_sort_reverse = reverse

        # Simple case-insensitive sort for all columns for now
        items.sort(key=lambda x: str(x[0]).lower(), reverse=reverse)

        for index, (val, iid) in enumerate(items):
            self.trainers_tree.move(iid, '', index)

        self._trainers_sort_column = col
        self._update_trainers_sort_indicator()

    def _update_trainers_sort_indicator(self):
         arrow = ' ↓' if self._trainers_sort_reverse else ' ↑'
         headings = {'category':'Categorie', 'name':'Naam', 'email':'E-mail', 'phone':'Telefoon'}
         for c, base_text in headings.items():
             text = base_text + (arrow if c == self._trainers_sort_column else '')
             self.trainers_tree.heading(c, text=text)


    def _populate_trainers_treeview(self):
        # Clear existing trainer items
        for item in self.trainers_tree.get_children():
            self.trainers_tree.delete(item)

        # Prepare data for sorting: list of (sort_key, category, index, trainer_data, iid_placeholder)
        items_to_sort = []
        trainer_iid_counter = 0
        trainers_dict = self.trainers_data.get('trainers', {})
        key_map = {'category': 0, 'name': 1, 'email': 2, 'phone': 3}
        sort_col_index = key_map.get(self._trainers_sort_column, 0) # Default sort by category

        for category, trainers_list in trainers_dict.items():
            for index, trainer in enumerate(trainers_list):
                iid = f"trainer_{trainer_iid_counter}"
                values = (category, trainer['name'], trainer.get('email', ''), trainer.get('phone', ''))
                sort_val = values[sort_col_index]
                items_to_sort.append((sort_val, category, index, trainer, iid))
                trainer_iid_counter += 1

        # Sort the prepared list
        items_to_sort.sort(key=lambda x: str(x[0]).lower(), reverse=self._trainers_sort_reverse)

        # Repopulate the treeview from the sorted list
        for _, category, original_index_in_sort, trainer, iid in items_to_sort:
             # Find the current index in the *actual data* for the tag, as original_index_in_sort is just for sorting prep
             current_index = -1
             if category in self.trainers_data.get('trainers', {}):
                  try:
                     # Find index based on object identity or name match as fallback
                     current_index = self.trainers_data['trainers'][category].index(trainer)
                  except ValueError:
                     # Fallback: find by name if object identity changed (e.g., due to deepcopy)
                     for idx, t in enumerate(self.trainers_data['trainers'][category]):
                         if t['name'] == trainer['name']: # Basic match
                             current_index = idx
                             break
             # Use current_index if found, otherwise tag might be less reliable
             tag_index = str(current_index) if current_index != -1 else '?'

             values = (category, trainer['name'], trainer.get('email', ''), trainer.get('phone', ''))
             self.trainers_tree.insert('', tk.END, iid=iid, values=values, tags=(category, tag_index))

        # Reset selection and button states
        self._on_trainer_select()
        self._update_trainers_sort_indicator()


    def _get_current_data_from_ui(self):
         # Called just before saving - ensure data reflects UI state
         # Start with the internal data which should be up-to-date from dialogs
         current_data = copy.deepcopy(self.trainers_data)

         # Update contacts directly from the Entry widgets
         # Ensure contacts dict exists
         current_data.setdefault('contacts', {})
         current_data['contacts']['vertrouwenspersoon'] = {
             'name': self.v_name.get().strip(),
             'email': self.v_email.get().strip(),
             'phone': self.v_phone.get().strip(),
             'img': self.v_img.get().strip()
         }
         current_data['contacts']['jeugdcoordinator'] = {
             'name': self.j_name.get().strip(),
             'email': self.j_email.get().strip(),
             'phone': self.j_phone.get().strip(),
             'img': self.j_img.get().strip()
         }
         # Trainer and Times data should have been updated in self.trainers_data via their respective dialog callbacks
         return current_data


    def _trainers_save(self):
        if not self.trainers_file_loaded:
            messagebox.showwarning("Eerst Laden", "Laad data voor opslaan.", parent=self.app.root)
            self.app.set_status("Opslaan mislukt: Data niet geladen.", is_error=True); return

        data_to_save = self._get_current_data_from_ui()
        filename_short = os.path.basename(config.TRAINERS_HTML_FILE_PATH)

        # Validate contact fields (simple check if needed)
        # e.g., if not data_to_save.get('contacts',{}).get('vertrouwenspersoon',{}).get('name'): etc...

        self.app.set_status(f"Opslaan trainers/tijden naar {filename_short}..."); self.app.root.update_idletasks()
        success, error_msg = utils.trainers_save_html(config.TRAINERS_HTML_FILE_PATH, data_to_save)

        if success:
            self.app.set_status(f"Trainers/tijden succesvol opgeslagen naar {filename_short}.", duration_ms=5000)
            # Update internal data to match saved state AFTER successful save
            self.trainers_data = copy.deepcopy(data_to_save)
            # Optionally, repopulate UI to ensure consistency, though not strictly necessary if save worked
            # self._populate_ui()
        else:
            self.app.set_status(f"Fout bij opslaan trainers/tijden: {error_msg}. Controleer console.", is_error=True)
            messagebox.showerror("Opslag Fout", f"Kon wijzigingen niet opslaan:\n{config.TRAINERS_HTML_FILE_PATH}\nFout: {error_msg}\nControleer console.", parent=self.app.root)


def create_trainers_tab(parent_frame, app_instance):
    # Add the small button style definition here or in the main app class
    s = ttk.Style()
    s.configure("Small.TButton", padding=1)
    return TrainersTab(parent_frame, app_instance)
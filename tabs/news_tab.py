import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import datetime
import os
import shutil
import config
import utils

class NewsTab:
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance
        self.news_data = []
        self._create_widgets()
        self._news_load_and_populate_treeview()

    def _create_widgets(self):
        self.parent.grid_rowconfigure(0, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)
        pw = ttk.PanedWindow(self.parent, orient=tk.VERTICAL); pw.grid(row=0, column=0, sticky='nsew')

        form_frame = ttk.Labelframe(pw, text=" Nieuw Artikel Toevoegen ", padding="10"); form_frame.columnconfigure(1, weight=1)
        row_index = 0
        ttk.Label(form_frame, text="Uniek ID:*").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=2); self.news_entry_id = ttk.Entry(form_frame, width=50); self.news_entry_id.grid(column=1, row=row_index, sticky=(tk.W, tk.E), padx=5, pady=2); ttk.Label(form_frame, text="bv. 'nieuwe-trainer-jan'", style="Desc.TLabel").grid(column=2, row=row_index, sticky=tk.W, padx=5); row_index += 1
        ttk.Label(form_frame, text="Kleine letters, cijfers, koppeltekens (-). Moet uniek zijn.", style="Desc.TLabel").grid(column=1, row=row_index, columnspan=2, sticky=tk.W, padx=5, pady=(0, 5)); row_index += 1
        ttk.Label(form_frame, text="Datum:*").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=2); self.news_entry_date = ttk.Entry(form_frame, width=20); self.news_entry_date.grid(column=1, row=row_index, sticky=tk.W, padx=5, pady=2); self.news_entry_date.insert(0, datetime.date.today().isoformat()); ttk.Label(form_frame, text="Formaat: JJJJ-MM-DD", style="Desc.TLabel").grid(column=2, row=row_index, sticky=tk.W, padx=5); row_index += 1
        ttk.Label(form_frame, text="Titel:*").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=2); self.news_entry_title = ttk.Entry(form_frame, width=50); self.news_entry_title.grid(column=1, row=row_index, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2); row_index += 1
        ttk.Label(form_frame, text="Categorie:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=2); self.news_entry_category = ttk.Entry(form_frame, width=30); self.news_entry_category.grid(column=1, row=row_index, sticky=tk.W, padx=5, pady=2); self.news_entry_category.insert(0, config.NEWS_DEFAULT_CATEGORY); ttk.Label(form_frame, text="bv. 'Mededelingen'", style="Desc.TLabel").grid(column=2, row=row_index, sticky=tk.W, padx=5); row_index += 1
        ttk.Label(form_frame, text="Afbeelding:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=2); image_frame = ttk.Frame(form_frame); image_frame.grid(column=1, row=row_index, columnspan=2, sticky=(tk.W, tk.E)); image_frame.columnconfigure(0, weight=1); self.news_entry_image = ttk.Entry(image_frame, width=45); self.news_entry_image.grid(column=0, row=0, sticky=(tk.W, tk.E), padx=(0, 5)); self.news_entry_image.insert(0, config.NEWS_DEFAULT_IMAGE); self.news_button_browse_image = ttk.Button(image_frame, text="Upload Afbeelding", command=self._news_browse_image, width=18); self.news_button_browse_image.grid(column=1, row=0, sticky=tk.W); row_index += 1
        ttk.Label(form_frame, text="Samenvatting:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=2); self.news_entry_summary = ttk.Entry(form_frame, width=50); self.news_entry_summary.grid(column=1, row=row_index, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2); row_index += 1
        ttk.Label(form_frame, text="Volledige Tekst:").grid(column=0, row=row_index, sticky=(tk.W, tk.N), padx=5, pady=2); self.news_text_full_content = scrolledtext.ScrolledText(form_frame, width=60, height=8, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1, font=(self.app.default_font_family, self.app.default_font_size)); self.news_text_full_content.grid(column=1, row=row_index, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=2); form_frame.grid_rowconfigure(row_index, weight=1); row_index += 1
        news_button_frame = ttk.Frame(form_frame); news_button_frame.grid(column=0, row=row_index, columnspan=3, pady=10, sticky=tk.E); self.news_button_add = ttk.Button(news_button_frame, text="Voeg Artikel Toe", command=self._news_add_article); self.news_button_add.pack(side=tk.LEFT, padx=5); self.news_button_clear = ttk.Button(news_button_frame, text="Wis Formulier", command=self._news_clear_form); self.news_button_clear.pack(side=tk.LEFT, padx=5)
        pw.add(form_frame, weight=0)

        list_frame = ttk.Labelframe(pw, text=" Bestaande Artikelen ", padding="10"); list_frame.grid_rowconfigure(0, weight=1); list_frame.grid_columnconfigure(0, weight=1)
        news_columns = ('id', 'date', 'title'); self.news_tree = ttk.Treeview(list_frame, columns=news_columns, show='headings', selectmode='browse')
        self.news_tree.heading('id', text='ID', anchor=tk.W); self.news_tree.column('id', width=180, minwidth=120, anchor=tk.W, stretch=tk.NO)
        self.news_tree.heading('date', text='Datum', anchor=tk.W); self.news_tree.column('date', width=100, minwidth=90, anchor=tk.CENTER, stretch=tk.NO)
        self.news_tree.heading('title', text='Titel', anchor=tk.W); self.news_tree.column('title', width=400, minwidth=200, anchor=tk.W)
        news_vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.news_tree.yview); self.news_tree.configure(yscrollcommand=news_vsb.set)
        self.news_tree.grid(row=0, column=0, sticky='nsew'); news_vsb.grid(row=0, column=1, sticky='ns')
        self.news_tree.bind("<<TreeviewSelect>>", self._news_on_selection_change)
        list_button_frame = ttk.Frame(list_frame); list_button_frame.grid(row=1, column=0, columnspan=2, pady=(10,0), sticky=tk.W)
        self.news_button_delete = ttk.Button(list_button_frame, text="Verwijder Geselecteerd Artikel", command=self._news_delete_selected, state=tk.DISABLED); self.news_button_delete.pack(side=tk.LEFT, padx=(0, 5))
        self.news_button_refresh = ttk.Button(list_button_frame, text="Vernieuw Lijst", command=self._news_load_and_populate_treeview); self.news_button_refresh.pack(side=tk.LEFT, padx=5)
        pw.add(list_frame, weight=1)

    def _news_load_and_populate_treeview(self):
        self.app.set_status("Nieuwsberichten laden..."); self.app.root.update_idletasks()
        loaded_data, error_msg = utils.news_load_existing_data(config.NEWS_JSON_FILE_PATH)
        if error_msg:
            self.news_data = []
            self.app.set_status(f"Fout bij laden nieuws: {error_msg}", is_error=True)
            messagebox.showerror("Nieuws Laad Fout", f"Kon nieuws data niet laden:\n{error_msg}", parent=self.app.root)
        else:
            self.news_data = loaded_data
            item_count = len(self.news_data)
            self.app.set_status(f"{item_count} nieuwsberichten geladen.", duration_ms=3000 if item_count > 0 else 5000)
        self._news_populate_treeview()

    def _news_populate_treeview(self):
        for item in self.news_tree.get_children(): self.news_tree.delete(item)
        for article in self.news_data:
            try:
                article_id = article.get('id', 'ONTBREKEND_ID'); date = article.get('date', '')
                title = article.get('title', 'Geen Titel')
                self.news_tree.insert('', tk.END, iid=article_id, values=(article_id, date, title))
            except Exception as e:
                print(f"[NIEUWS GUI FOUT] Kon nieuws rij niet invoegen: {article}\nFout: {e}")
        self._news_on_selection_change()

    def _news_on_selection_change(self, event=None):
        self.news_button_delete.config(state=tk.NORMAL if self.news_tree.selection() else tk.DISABLED)

    def _news_delete_selected(self):
        selected_items = self.news_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selectie Vereist", "Selecteer a.u.b. een artikel uit de lijst om te verwijderen.", parent=self.app.root)
            return
        selected_iid = selected_items[0]
        article_to_delete = None; article_index = -1
        for i, article in enumerate(self.news_data):
            if article.get('id') == selected_iid:
                article_to_delete = article; article_index = i; break
        if not article_to_delete:
            messagebox.showerror("Fout", f"Kon geselecteerd artikel niet vinden (ID: {selected_iid}). Vernieuwen?", parent=self.app.root)
            self.app.set_status("Fout bij vinden te verwijderen artikel.", is_error=True); return

        title = article_to_delete.get('title', 'Zonder titel'); date = article_to_delete.get('date', 'Geen Datum')
        if messagebox.askyesno("Verwijderen Bevestigen", f"Dit artikel permanent verwijderen?\n\nID: {selected_iid}\nDatum: {date}\nTitel: {title}", icon='warning', parent=self.app.root):
            self.app.set_status(f"Verwijderen artikel '{title}'..."); self.app.root.update_idletasks()
            del self.news_data[article_index]
            save_error = utils.news_save_data(config.NEWS_JSON_FILE_PATH, self.news_data)
            if save_error:
                self.app.set_status(f"Fout bij opslaan na verwijderen: {save_error}", is_error=True)
                messagebox.showerror("Opslag Fout", f"Kon niet opslaan na verwijderen:\n{save_error}", parent=self.app.root)
                self._news_load_and_populate_treeview()
            else:
                self._news_populate_treeview()
                self.app.set_status(f"Artikel '{title}' succesvol verwijderd.", duration_ms=5000)
        else:
            self.app.set_status("Verwijdering geannuleerd.", duration_ms=3000)

    def _news_reset_entry_states(self):
        try:
            self.news_entry_id.state(["!invalid"]); self.news_entry_date.state(["!invalid"]); self.news_entry_title.state(["!invalid"])
        except tk.TclError: pass

    def _news_browse_image(self):
        filetypes = (("Afbeeldingsbestanden", "*.jpg *.jpeg *.png *.gif *.webp *.bmp"), ("Alle bestanden", "*.*"))
        initial_dir = os.path.dirname(config.NEWS_IMAGE_DEST_DIR_ABSOLUTE)
        source_path = filedialog.askopenfilename(title="Selecteer afbeelding", filetypes=filetypes, initialdir=initial_dir)
        if not source_path:
            self.app.set_status("Afbeelding selectie geannuleerd.", duration_ms=3000); return

        filename = os.path.basename(source_path)
        dest_path = os.path.join(config.NEWS_IMAGE_DEST_DIR_ABSOLUTE, filename)
        try: os.makedirs(config.NEWS_IMAGE_DEST_DIR_ABSOLUTE, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Map Fout", f"Kon map niet aanmaken:\n{config.NEWS_IMAGE_DEST_DIR_ABSOLUTE}\nFout: {e}", parent=self.app.root)
            self.app.set_status(f"Fout bij aanmaken map {config.NEWS_IMAGE_DEST_DIR_RELATIVE}", is_error=True); return

        if os.path.exists(dest_path):
            if not messagebox.askyesno("Bestand bestaat al", f"'{filename}' bestaat al in '{config.NEWS_IMAGE_DEST_DIR_RELATIVE}'.\nOverschrijven?", parent=self.app.root):
                self.app.set_status("Upload geannuleerd (overschrijven geweigerd).", duration_ms=4000); return
        try:
            shutil.copy2(source_path, dest_path)
            self.news_entry_image.delete(0, tk.END); self.news_entry_image.insert(0, filename)
            self.app.set_status(f"Afbeelding '{filename}' succesvol geüpload.", duration_ms=5000)
        except Exception as e:
            messagebox.showerror("Upload Fout", f"Kon afbeelding niet kopiëren:\n{dest_path}\nFout: {e}", parent=self.app.root)
            self.app.set_status(f"Fout bij uploaden afbeelding: {e}", is_error=True)

    def _news_clear_form(self):
        self._news_reset_entry_states(); self.news_entry_id.delete(0, tk.END)
        self.news_entry_date.delete(0, tk.END); self.news_entry_date.insert(0, datetime.date.today().isoformat())
        self.news_entry_title.delete(0, tk.END); self.news_entry_category.delete(0, tk.END)
        self.news_entry_category.insert(0, config.NEWS_DEFAULT_CATEGORY); self.news_entry_image.delete(0, tk.END)
        self.news_entry_image.insert(0, config.NEWS_DEFAULT_IMAGE); self.news_entry_summary.delete(0, tk.END)
        self.news_text_full_content.delete('1.0', tk.END); self.app.set_status("Nieuws formulier gewist.", duration_ms=3000)
        self.news_entry_id.focus()

    def _news_add_article(self):
        self.app.set_status("Verwerken nieuwsartikel..."); self.app.root.update_idletasks(); self._news_reset_entry_states()
        article_id = self.news_entry_id.get().strip().lower(); article_date_str = self.news_entry_date.get().strip()
        article_title = self.news_entry_title.get().strip(); article_category = self.news_entry_category.get().strip() or config.NEWS_DEFAULT_CATEGORY
        article_image = self.news_entry_image.get().strip() or config.NEWS_DEFAULT_IMAGE; article_summary = self.news_entry_summary.get().strip()
        article_full_content_raw = self.news_text_full_content.get('1.0', tk.END).strip()
        errors = []; focus_widget = None
        if not article_id: errors.append("Nieuws ID is verplicht."); focus_widget = self.news_entry_id;
        elif not utils.news_is_valid_id(article_id): errors.append("Ongeldig Nieuws ID format (a-z, 0-9, -)."); focus_widget = self.news_entry_id;
        if not article_date_str: errors.append("Nieuws Datum is verplicht."); focus_widget = self.news_entry_date if not focus_widget else focus_widget
        else:
            try: datetime.datetime.strptime(article_date_str, '%Y-%m-%d')
            except ValueError: errors.append("Ongeldig Datum formaat (JJJJ-MM-DD)."); focus_widget = self.news_entry_date if not focus_widget else focus_widget
        if not article_title: errors.append("Nieuws Titel is verplicht."); focus_widget = self.news_entry_title if not focus_widget else focus_widget
        if errors:
            error_message = "Fout: " + errors[0]; self.app.set_status(error_message, is_error=True)
            if focus_widget:
                 try: focus_widget.state(["invalid"])
                 except: pass
                 focus_widget.focus()
            messagebox.showwarning("Validatie Fout", "\n".join(errors), parent=self.app.root); return
        if any(item.get('id') == article_id for item in self.news_data):
            error_message = f"Fout: Nieuws Artikel ID '{article_id}' bestaat al."; self.app.set_status(error_message, is_error=True)
            try: self.news_entry_id.state(["invalid"])
            except: pass
            self.news_entry_id.focus(); messagebox.showerror("Validatie Fout", error_message, parent=self.app.root); return

        processed_content_linked = utils.news_auto_link_text(article_full_content_raw)
        processed_content_html = processed_content_linked.replace('\r\n', '<br>\n').replace('\n', '<br>\n'); final_summary = article_summary or article_title
        new_article = {"id": article_id, "date": article_date_str, "title": article_title, "category": article_category, "image": article_image, "summary": final_summary, "full_content": processed_content_html}
        self.news_data.insert(0, new_article); save_error = utils.news_save_data(config.NEWS_JSON_FILE_PATH, self.news_data)
        if save_error:
            self.app.set_status(f"Fout bij opslaan JSON: {save_error}", is_error=True)
            messagebox.showerror("Opslagfout", f"Kon nieuws niet opslaan:\n{save_error}", parent=self.app.root)
        else:
            self.app.set_status(f"Nieuwsartikel '{article_title}' succesvol toegevoegd.", duration_ms=5000)
            self._news_populate_treeview(); self._news_clear_form()

def create_news_tab(parent_frame, app_instance):
    return NewsTab(parent_frame, app_instance)
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import config
import utils

try:
    from bs4 import Tag, NavigableString
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

class TextEditorTab:
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance
        self.text_editor_found_texts = []
        self.text_editor_selected_iid = None
        self._text_editor_scan_running = False
        self._create_widgets()
        self._text_editor_scan_files()

    def _create_widgets(self):
        self.parent.grid_rowconfigure(1, weight=1)
        self.parent.grid_rowconfigure(2, weight=0)
        self.parent.grid_columnconfigure(0, weight=1)

        if not BS4_AVAILABLE:
            error_label = ttk.Label(self.parent, text="Fout: BeautifulSoup4 bibliotheek ontbreekt/onvolledig.\nKan Tekst Editor niet laden.", style="Error.TLabel", justify=tk.CENTER)
            error_label.grid(row=0, column=0, pady=50, padx=20, sticky='nsew'); return

        top_frame = ttk.Frame(self.parent); top_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        tree_frame = ttk.Frame(self.parent); tree_frame.grid(row=1, column=0, sticky='nsew', pady=5)
        edit_frame = ttk.Frame(self.parent); edit_frame.grid(row=2, column=0, sticky='ew', pady=(10, 0))

        self.text_editor_refresh_button = ttk.Button(top_frame, text="Scan Bestanden voor Tekst", command=self._text_editor_scan_files)
        self.text_editor_refresh_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.text_editor_search_var = tk.StringVar()
        self.text_editor_search_entry = ttk.Entry(top_frame, textvariable=self.text_editor_search_var, width=40, state=tk.DISABLED); self.text_editor_search_entry.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)
        self.text_editor_search_entry.bind("<KeyRelease>", self._text_editor_filter_treeview_event)
        ttk.Label(top_frame, text="<- Zoek Gevonden Tekst", style="Desc.TLabel").pack(side=tk.LEFT, padx=(0,5), pady=5)

        tree_columns = ('file', 'text')
        self.text_editor_tree = ttk.Treeview(tree_frame, columns=tree_columns, show='headings', selectmode='browse')
        self.text_editor_tree.heading('file', text='Bestandspad'); self.text_editor_tree.column('file', width=300, minwidth=200, anchor=tk.W)
        self.text_editor_tree.heading('text', text='Gevonden Tekst Snippet'); self.text_editor_tree.column('text', width=600, minwidth=300, anchor=tk.W)
        tree_vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.text_editor_tree.yview); tree_hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.text_editor_tree.xview)
        self.text_editor_tree.configure(yscrollcommand=tree_vsb.set, xscrollcommand=tree_hsb.set)
        tree_frame.grid_rowconfigure(0, weight=1); tree_frame.grid_columnconfigure(0, weight=1)
        self.text_editor_tree.grid(row=0, column=0, sticky='nsew'); tree_vsb.grid(row=0, column=1, sticky='ns'); tree_hsb.grid(row=1, column=0, sticky='ew')
        self.text_editor_tree.bind("<<TreeviewSelect>>", self._text_editor_on_select)

        edit_frame.grid_columnconfigure(0, weight=1)
        ttk.Label(edit_frame, text="Bewerk Geselecteerde Tekst:", style="Bold.TLabel").grid(row=0, column=0, sticky=tk.W, padx=5, pady=(0,2))
        self.text_editor_edit_area = scrolledtext.ScrolledText(edit_frame, width=80, height=6, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1, state=tk.DISABLED, font=(self.app.default_font_family, self.app.default_font_size));
        self.text_editor_edit_area.grid(row=1, column=0, sticky='ew', padx=5, pady=(0,5))

        edit_button_frame = ttk.Frame(edit_frame); edit_button_frame.grid(row=2, column=0, sticky='ew', padx=5, pady=(0,5))

        self.text_editor_save_button = ttk.Button(edit_button_frame, text="Sla Deze Wijziging Op", command=self._text_editor_save_change, state=tk.DISABLED);
        self.text_editor_save_button.pack(side=tk.LEFT, padx=(0, 5))

        self.text_editor_cancel_button = ttk.Button(edit_button_frame, text="Annuleer Bewerking", command=self._text_editor_cancel_edit, state=tk.DISABLED);
        self.text_editor_cancel_button.pack(side=tk.LEFT, padx=5)

        self.text_editor_delete_button = ttk.Button(edit_button_frame, text="Verwijder Geselecteerde Tekst (Incl. Tag)", command=self._text_editor_delete_selected, state=tk.DISABLED)
        self.text_editor_delete_button.pack(side=tk.LEFT, padx=5)

    def _text_editor_scan_files(self):
        if not BS4_AVAILABLE: return
        if self._text_editor_scan_running: return
        self._text_editor_scan_running = True
        self.text_editor_refresh_button.config(state=tk.DISABLED, text="Scannen...")
        self.app.set_status("Scannen HTML bestanden voor tekst..."); self.app.root.update_idletasks()

        self.text_editor_found_texts = []; self.text_editor_selected_iid = None
        self._text_editor_clear_treeview(); self._text_editor_reset_edit_area(); self.text_editor_search_var.set("")
        self.text_editor_search_entry.config(state=tk.DISABLED)

        html_files, file_count = utils.general_html_find_files(config.HTML_SCAN_TARGET_PATHS_ABSOLUTE)
        processed_files = 0; total_texts_found = 0
        for i, file_path in enumerate(html_files):
            self.app.set_status(f"Scannen bestand {i+1}/{file_count} voor tekst: {os.path.basename(file_path)}..."); self.app.root.update_idletasks()
            texts_in_file = utils.text_editor_parse_file(file_path, self.app.text_editor_parsed_soups, self.text_editor_found_texts)
            if texts_in_file > 0: processed_files += 1; total_texts_found += texts_in_file

        self._text_editor_populate_treeview(self.text_editor_found_texts)
        self.text_editor_search_entry.config(state=tk.NORMAL if self.text_editor_found_texts else tk.DISABLED)
        self.text_editor_refresh_button.config(state=tk.NORMAL, text="Scan Bestanden voor Tekst"); self._text_editor_scan_running = False
        status_msg = f"Tekst scan voltooid. {total_texts_found} snippets gevonden in {processed_files} bestanden." if total_texts_found > 0 else f"Tekst scan voltooid. Geen bewerkbare snippets gevonden in {processed_files} bestanden."
        self.app.set_status(status_msg, duration_ms=8000)

    def _text_editor_clear_treeview(self):
        if not hasattr(self, 'text_editor_tree'): return
        self.text_editor_tree.unbind("<<TreeviewSelect>>");
        for item in self.text_editor_tree.get_children(): self.text_editor_tree.delete(item)

    def _text_editor_populate_treeview(self, data_list):
        self._text_editor_clear_treeview()
        for item_data in data_list:
             try: display_path = os.path.relpath(item_data['file_path'], config.APP_BASE_DIR)
             except ValueError: display_path = item_data['file_path']
             values = (display_path, item_data['display_text'])
             try: self.text_editor_tree.insert('', tk.END, iid=item_data['iid'], values=values, tags=('text_row',))
             except Exception as e: pass
        if data_list: self.text_editor_tree.bind("<<TreeviewSelect>>", self._text_editor_on_select)

    def _text_editor_filter_treeview_event(self, event=None):
        search_term = self.text_editor_search_var.get().lower().strip()
        filtered_data = [item for item in self.text_editor_found_texts if search_term in item['original_text'].lower()] if search_term else self.text_editor_found_texts
        self._text_editor_populate_treeview(filtered_data); self._text_editor_reset_edit_area()

    def _text_editor_reset_edit_area(self):
        self.text_editor_selected_iid = None
        self.text_editor_edit_area.config(state=tk.NORMAL); self.text_editor_edit_area.delete('1.0', tk.END)
        self.text_editor_edit_area.config(state=tk.DISABLED); self.text_editor_save_button.config(state=tk.DISABLED)
        self.text_editor_cancel_button.config(state=tk.DISABLED); self.text_editor_delete_button.config(state=tk.DISABLED)

    def _text_editor_on_select(self, event=None):
        selected_items = self.text_editor_tree.selection()
        if not selected_items: self._text_editor_reset_edit_area(); return
        selected_iid_str = selected_items[0]
        try:
            selected_iid = int(selected_iid_str); data_item = self.text_editor_found_texts[selected_iid]
            self.text_editor_selected_iid = selected_iid
            self.text_editor_edit_area.config(state=tk.NORMAL); self.text_editor_save_button.config(state=tk.NORMAL)
            self.text_editor_cancel_button.config(state=tk.NORMAL)
            delete_state = tk.NORMAL if data_item['dom_reference'] else tk.DISABLED
            self.text_editor_delete_button.config(state=delete_state)
            self.text_editor_edit_area.delete('1.0', tk.END); self.text_editor_edit_area.insert('1.0', data_item['original_text'])
        except (ValueError, IndexError, KeyError) as e:
            messagebox.showerror("Fout", "Kon data voor geselecteerde tekst niet ophalen.", parent=self.app.root)
            self._text_editor_reset_edit_area()

    def _text_editor_delete_selected(self):
        if self.text_editor_selected_iid is None:
            messagebox.showwarning("Geen Selectie", "Selecteer eerst een tekst snippet in de lijst.", parent=self.app.root); return
        try:
            data_item = self.text_editor_found_texts[self.text_editor_selected_iid]; file_path = data_item['file_path']
            text_node_reference = data_item['dom_reference']; modified_soup = self.app.text_editor_parsed_soups[file_path]
            original_text_snippet = data_item['display_text']
            if text_node_reference is None:
                 messagebox.showerror("Verwijder Fout", "Originele tekst locatie verloren. Scan bestanden opnieuw.", parent=self.app.root)
                 self.app.set_status("Verwijderen mislukt: Node referentie verloren.", is_error=True); return
            parent_tag = text_node_reference.parent
            if parent_tag is None or not isinstance(parent_tag, Tag):
                 messagebox.showerror("Verwijder Fout", "Kan niet verwijderen: Geselecteerde tekst heeft geen geldige parent tag (bv. direct in root?). Scan bestanden opnieuw.", parent=self.app.root)
                 self.app.set_status("Verwijderen mislukt: Parent tag niet gevonden/ongeldig.", is_error=True); return
            if parent_tag.name.lower() in ['html', 'body', 'head']:
                messagebox.showerror("Verwijder Fout", f"Kan kritieke tag niet verwijderen: <{parent_tag.name}>.", parent=self.app.root)
                self.app.set_status(f"Verwijderen mislukt: Poging tot verwijderen kritieke <{parent_tag.name}> tag.", is_error=True); return
            confirm_msg = f"Permanent VERWIJDEREN de gehele <{parent_tag.name}> tag die deze tekst bevat?\n\nTekst Snippet:\n'{original_text_snippet}'\n\nTe Verwijderen Tag:\n<{parent_tag.name}> ... </{parent_tag.name}>\n\nBestand: {os.path.basename(file_path)}\n\nWAARSCHUWING: Dit verwijdert de tag EN alles erin.\nDeze actie kan NIET eenvoudig ongedaan gemaakt worden."
            if not messagebox.askyesno("Bevestig Tag Verwijdering", confirm_msg, icon='warning', parent=self.app.root):
                self.app.set_status("Verwijderen geannuleerd.", duration_ms=3000); return
            try: parent_tag.extract()
            except Exception as extract_err:
                 messagebox.showerror("Verwijder Fout", f"Kon parent tag <{parent_tag.name}> niet intern verwijderen.\nFout: {extract_err}", parent=self.app.root)
                 self.app.set_status("Verwijderen mislukt: Interne tag verwijder fout.", is_error=True); return
            try:
                with open(file_path, 'w', encoding='utf-8') as f: f.write(modified_soup.prettify(formatter="html5"))
                self.app.set_status(f"Tag <{parent_tag.name}> verwijderd en opgeslagen in {os.path.basename(file_path)}. Opnieuw scannen sterk aanbevolen.", duration_ms=8000)
                self._text_editor_reset_edit_area()
                try: self.text_editor_tree.delete(self.text_editor_selected_iid)
                except tk.TclError: pass
                except Exception: pass
                if messagebox.askyesno("Opnieuw Scannen Aanbevolen", "Tag succesvol verwijderd.\n\nDe tekstlijst is nu onnauwkeurig door structurele wijzigingen.\n\nBestanden opnieuw scannen om de lijst bij te werken?", parent=self.app.root):
                    self._text_editor_scan_files()
            except Exception as save_err:
                import traceback; messagebox.showerror("Opslag Fout", f"Kon bestand niet schrijven na verwijderen tag:\n{file_path}\nFout: {save_err}", parent=self.app.root)
                self.app.set_status(f"Verwijderen mislukt: Fout bij schrijven bestand {os.path.basename(file_path)}.", is_error=True); traceback.print_exc()
        except (IndexError, KeyError) as e:
            messagebox.showerror("Verwijder Fout", "Kon data niet ophalen om te verwijderen.", parent=self.app.root); self._text_editor_reset_edit_area()
        except Exception as e:
            import traceback; messagebox.showerror("Verwijder Fout", f"Onverwachte fout bij verwijderen tag:\n{e}", parent=self.app.root); traceback.print_exc(); self._text_editor_reset_edit_area()

    def _text_editor_cancel_edit(self):
        self._text_editor_reset_edit_area()
        if self.text_editor_tree.selection(): self.text_editor_tree.selection_remove(self.text_editor_tree.selection()[0])
        self.app.set_status("Bewerking geannuleerd.", duration_ms=3000)

    def _text_editor_save_change(self):
        if self.text_editor_selected_iid is None: messagebox.showwarning("Geen Selectie", "Geen tekst snippet geselecteerd.", parent=self.app.root); return
        try:
            data_item = self.text_editor_found_texts[self.text_editor_selected_iid]; file_path = data_item['file_path']
            text_node_reference = data_item['dom_reference']; edited_text = self.text_editor_edit_area.get('1.0', tk.END)[:-1]
            if text_node_reference is None or not text_node_reference.parent:
                 messagebox.showerror("Opslag Fout", "Originele tekst locatie verloren. Scan bestanden opnieuw.", parent=self.app.root)
                 self.app.set_status("Opslaan mislukt: Node verloren.", is_error=True); self._text_editor_reset_edit_area(); return
            try: text_node_reference.replace_with(NavigableString(edited_text))
            except Exception as replace_err:
                 messagebox.showerror("Opslag Fout", f"Kon tekst niet intern vervangen.\nFout: {replace_err}", parent=self.app.root)
                 self.app.set_status("Opslaan mislukt: Intern wijzigen.", is_error=True); return
            modified_soup = self.app.text_editor_parsed_soups[file_path]
            try:
                with open(file_path, 'w', encoding='utf-8') as f: f.write(modified_soup.prettify(formatter="html5"))
                data_item['original_text'] = edited_text
                new_display_text = (edited_text[:100] + '...') if len(edited_text) > 100 else edited_text
                new_display_text = new_display_text.replace('\n', ' ').replace('\r', '')
                data_item['display_text'] = new_display_text;
                try: display_path = os.path.relpath(file_path, config.APP_BASE_DIR)
                except ValueError: display_path = file_path
                self.text_editor_tree.item(self.text_editor_selected_iid, values=(display_path, new_display_text))
                self._text_editor_reset_edit_area(); self.app.set_status(f"Wijziging opgeslagen naar {os.path.basename(file_path)}.", duration_ms=5000)
            except Exception as save_err:
                import traceback; messagebox.showerror("Opslag Fout", f"Kon bestand niet schrijven:\n{file_path}\nFout: {save_err}", parent=self.app.root)
                self.app.set_status(f"Opslaan mislukt: Fout bij schrijven bestand {os.path.basename(file_path)}.", is_error=True); traceback.print_exc()
        except (IndexError, KeyError) as e:
            messagebox.showerror("Opslag Fout", "Kon data niet ophalen om op te slaan.", parent=self.app.root); self._text_editor_reset_edit_area()
        except Exception as e:
            import traceback; messagebox.showerror("Opslag Fout", f"Onverwachte fout tijdens opslaan:\n{e}", parent=self.app.root); traceback.print_exc(); self._text_editor_reset_edit_area()

def create_text_editor_tab(parent_frame, app_instance):
    return TextEditorTab(parent_frame, app_instance)
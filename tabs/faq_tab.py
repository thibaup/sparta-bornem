"""Manage the questions shown on the members FAQ page."""

import json
import os
import tempfile
import tkinter as tk
from tkinter import messagebox, ttk

import config


def _validated_entries(entries):
    if not isinstance(entries, list):
        raise ValueError("Het FAQ-bestand moet een lijst met vragen bevatten.")

    cleaned = []
    seen_questions = set()
    for number, item in enumerate(entries, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Vraag {number} heeft geen geldig formaat.")
        question = item.get("question")
        answer = item.get("answer")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"Vraag {number} heeft geen vraagtekst.")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError(f"Vraag {number} heeft geen antwoord.")
        question = question.strip()
        answer = answer.strip()
        if question.casefold() in seen_questions:
            raise ValueError(f"De vraag '{question}' komt meer dan één keer voor.")
        seen_questions.add(question.casefold())
        cleaned.append({"question": question, "answer": answer})
    return cleaned


def load_faq_entries(path):
    with open(path, "r", encoding="utf-8-sig") as file:
        return _validated_entries(json.load(file))


def save_faq_entries(path, entries):
    """Replace the JSON only after a complete, valid file has been written."""
    cleaned = _validated_entries(entries)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", suffix=".tmp",
            prefix="faq-", dir=os.path.dirname(os.path.abspath(path)), delete=False
        ) as file:
            temporary_path = file.name
            json.dump(cleaned, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary_path, path)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)


class FaqDialog(tk.Toplevel):
    def __init__(self, parent, title, initial=None, on_save=None):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.resizable(True, True)
        self.minsize(500, 300)
        self.result = None
        self.on_save = on_save

        content = ttk.Frame(self, padding=18)
        content.pack(fill=tk.BOTH, expand=True)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(3, weight=1)

        ttk.Label(content, text="Vraag *").grid(row=0, column=0, sticky="w")
        self.question = ttk.Entry(content)
        self.question.grid(row=1, column=0, sticky="ew", pady=(4, 14))
        self.question.insert(0, (initial or {}).get("question", ""))

        ttk.Label(content, text="Antwoord *").grid(row=2, column=0, sticky="w")
        answer_frame = ttk.Frame(content)
        answer_frame.grid(row=3, column=0, sticky="nsew", pady=(4, 14))
        answer_frame.columnconfigure(0, weight=1)
        answer_frame.rowconfigure(0, weight=1)
        self.answer = tk.Text(answer_frame, height=9, wrap=tk.WORD, undo=True)
        self.answer.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(answer_frame, orient="vertical", command=self.answer.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.answer.configure(yscrollcommand=scroll.set)
        self.answer.insert("1.0", (initial or {}).get("answer", ""))

        buttons = ttk.Frame(content)
        buttons.grid(row=4, column=0, sticky="e")
        ttk.Button(buttons, text="Annuleren", command=self.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(buttons, text="Opslaan", command=self._save).pack(side=tk.RIGHT)

        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Control-Return>", self._save)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.grab_set()
        self.question.focus_set()
        self.wait_window()

    def _save(self, _event=None):
        question = self.question.get().strip()
        answer = self.answer.get("1.0", "end-1c").strip()
        if not question or not answer:
            messagebox.showwarning(
                "Invoer vereist", "Vul zowel de vraag als het antwoord in.", parent=self
            )
            (self.question if not question else self.answer).focus_set()
            return
        candidate = {"question": question, "answer": answer}
        if self.on_save and self.on_save(candidate) is False:
            return
        self.result = candidate
        self.destroy()


class FaqTab:
    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance
        self.entries = []
        self.loaded = False
        self._create_widgets()
        self.reload_data()

    def _create_widgets(self):
        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(1, weight=3)
        self.parent.rowconfigure(2, weight=2)

        heading = ttk.Frame(self.parent)
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        heading.columnconfigure(0, weight=1)
        ttk.Label(heading, text="Veelgestelde vragen", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            heading, text="Wijzigingen worden meteen in het FAQ-bestand opgeslagen.",
            style="Desc.TLabel"
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Button(heading, text="Herladen", command=self.reload_data).grid(row=0, column=1, rowspan=2, padx=(10, 0))

        tree_frame = ttk.Frame(self.parent)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(tree_frame, columns=("number", "question"), show="headings", selectmode="browse")
        self.tree.heading("number", text="#")
        self.tree.heading("question", text="Vraag")
        self.tree.column("number", width=45, minwidth=45, stretch=False, anchor="center")
        self.tree.column("question", width=650, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_selection)
        self.tree.bind("<Double-1>", lambda _event: self._edit())

        preview_frame = ttk.LabelFrame(self.parent, text="Antwoord", padding=8)
        preview_frame.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        self.preview = tk.Text(preview_frame, wrap=tk.WORD, state=tk.DISABLED, height=6)
        self.preview.grid(row=0, column=0, sticky="nsew")
        preview_scroll = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview.yview)
        preview_scroll.grid(row=0, column=1, sticky="ns")
        self.preview.configure(yscrollcommand=preview_scroll.set)

        actions = ttk.Frame(self.parent)
        actions.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        self.add_button = ttk.Button(actions, text="Vraag toevoegen...", command=self._add)
        self.add_button.pack(side=tk.LEFT, padx=(0, 8))
        self.edit_button = ttk.Button(actions, text="Bewerken...", command=self._edit)
        self.edit_button.pack(side=tk.LEFT, padx=(0, 8))
        self.delete_button = ttk.Button(actions, text="Verwijderen", command=self._delete)
        self.delete_button.pack(side=tk.LEFT, padx=(0, 18))
        self.up_button = ttk.Button(actions, text="Omhoog", command=lambda: self._move(-1))
        self.up_button.pack(side=tk.LEFT, padx=(0, 8))
        self.down_button = ttk.Button(actions, text="Omlaag", command=lambda: self._move(1))
        self.down_button.pack(side=tk.LEFT)
        self._update_buttons()

    def reload_data(self):
        try:
            entries = load_faq_entries(config.FAQ_JSON_FILE_PATH)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            self.loaded = False
            self._refresh()
            self.app.set_status(f"FAQ laden mislukt: {error}", is_error=True)
            messagebox.showerror("FAQ laden mislukt", str(error), parent=self.app.root)
            return False

        self.entries = entries
        self.loaded = True
        self._refresh()
        self.app.set_status(f"{len(entries)} FAQ-vragen geladen.", duration_ms=4000)

    def _selected_index(self):
        selection = self.tree.selection()
        return int(selection[0]) if selection else None

    def _refresh(self, select=None):
        self.tree.delete(*self.tree.get_children())
        for index, entry in enumerate(self.entries):
            self.tree.insert("", tk.END, iid=str(index), values=(index + 1, entry["question"]))
        if select is not None and 0 <= select < len(self.entries):
            iid = str(select)
            self.tree.selection_set(iid)
            self.tree.focus(iid)
            self.tree.see(iid)
        self._on_selection()

    def _on_selection(self, _event=None):
        index = self._selected_index()
        answer = self.entries[index]["answer"] if index is not None and index < len(self.entries) else ""
        self.preview.configure(state=tk.NORMAL)
        self.preview.delete("1.0", tk.END)
        self.preview.insert("1.0", answer)
        self.preview.configure(state=tk.DISABLED)
        self._update_buttons()

    def _update_buttons(self):
        if not hasattr(self, "add_button"):
            return
        index = self._selected_index()
        self.add_button.configure(state=tk.NORMAL if self.loaded else tk.DISABLED)
        selected_state = tk.NORMAL if self.loaded and index is not None else tk.DISABLED
        self.edit_button.configure(state=selected_state)
        self.delete_button.configure(state=selected_state)
        self.up_button.configure(state=tk.NORMAL if self.loaded and index is not None and index > 0 else tk.DISABLED)
        self.down_button.configure(state=tk.NORMAL if self.loaded and index is not None and index < len(self.entries) - 1 else tk.DISABLED)

    def _commit(self, entries, select, status):
        try:
            save_faq_entries(config.FAQ_JSON_FILE_PATH, entries)
        except (OSError, ValueError) as error:
            self.app.set_status(f"FAQ opslaan mislukt: {error}", is_error=True)
            messagebox.showerror("FAQ opslaan mislukt", str(error), parent=self.app.root)
            return False
        self.entries = entries
        self._refresh(select)
        self.app.set_status(status, duration_ms=5000)
        return True

    def _add(self):
        if not self.loaded:
            return
        FaqDialog(self.app.root, "FAQ-vraag toevoegen", on_save=lambda result:
                  self._commit(self.entries + [result], len(self.entries), "FAQ-vraag toegevoegd en opgeslagen."))

    def _edit(self):
        index = self._selected_index()
        if not self.loaded or index is None:
            return
        def save(result):
            new_entries = list(self.entries)
            new_entries[index] = result
            return self._commit(new_entries, index, "FAQ-vraag bijgewerkt en opgeslagen.")
        FaqDialog(self.app.root, "FAQ-vraag bewerken", self.entries[index], on_save=save)

    def _delete(self):
        index = self._selected_index()
        if not self.loaded or index is None:
            return
        question = self.entries[index]["question"]
        if not messagebox.askyesno(
            "Vraag verwijderen", f"Wil je deze vraag verwijderen?\n\n{question}",
            icon="warning", parent=self.app.root
        ):
            return
        new_entries = self.entries[:index] + self.entries[index + 1:]
        self._commit(new_entries, min(index, len(new_entries) - 1), "FAQ-vraag verwijderd en opgeslagen.")

    def _move(self, direction):
        index = self._selected_index()
        if not self.loaded or index is None or not 0 <= index + direction < len(self.entries):
            return
        new_entries = list(self.entries)
        new_entries[index], new_entries[index + direction] = new_entries[index + direction], new_entries[index]
        self._commit(new_entries, index + direction, "Volgorde van FAQ-vragen opgeslagen.")


def create_faq_tab(parent_frame, app_instance):
    return FaqTab(parent_frame, app_instance)

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import scrolledtext
from tkinter import filedialog # Added for file dialog
import json
import re
import datetime
import os
import sys
import shutil # Added for file copying

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_RELATIVE_PATH = os.path.join('html', 'nieuws', 'nieuws-data.json')
JSON_FILE_PATH = os.path.join(SCRIPT_DIR, JSON_RELATIVE_PATH)

# Define the destination directory for images (relative to the script)
IMAGE_DEST_DIR_RELATIVE = os.path.join('images', 'nieuws')
IMAGE_DEST_DIR_ABSOLUTE = os.path.join(SCRIPT_DIR, IMAGE_DEST_DIR_RELATIVE)


DEFAULT_CATEGORY = "Algemeen"
DEFAULT_IMAGE = "nieuws-beeld.png" # Fallback/initial default

# --- Helper Functions (load_existing_data, save_data, auto_link_text, is_valid_id - same as before) ---
def load_existing_data(filepath):
    if not os.path.exists(filepath):
        print(f"Info: '{filepath}' not found. Starting with an empty list.")
        return [], None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                print(f"Info: '{filepath}' is empty. Starting with an empty list.")
                return [], None
            data = json.loads(content)
            if not isinstance(data, list):
                msg = f"Warning: Data in '{filepath}' is not a list. Please fix or delete the file."
                print(msg)
                return None, msg
            return data, None
    except json.JSONDecodeError as e:
        msg = f"Error: Could not decode JSON from '{filepath}'. Please check the file format.\n{e}"
        print(msg)
        return None, msg
    except Exception as e:
        msg = f"Error loading data from '{filepath}': {e}"
        print(msg)
        return None, msg

def save_data(filepath, data):
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Successfully updated '{filepath}'")
        return None
    except Exception as e:
        msg = f"Error saving data to '{filepath}': {e}"
        print(msg)
        return msg

def auto_link_text(text):
    if not text: return ''
    email_regex = r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b'
    text = re.sub(email_regex, r'<a href="mailto:\1">\1</a>', text)
    url_regex = r'((?:https?://|www\.)[^\s<>"]+)'
    def replace_url(match):
        url = match.group(1)
        href = url
        if href.startswith('www.'): href = 'https://' + href
        if match.string[match.start()-1:match.start()] == '"' or match.string[match.start()-1:match.start()] == '>': return url
        return f'<a href="{href}" target="_blank" rel="noopener noreferrer">{url}</a>'
    text = re.sub(url_regex, replace_url, text)
    return text

def is_valid_id(article_id):
    return bool(re.match(r'^[a-z0-9-]+$', article_id))


# --- GUI Application Class ---

class NewsArticleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Nieuwsartikel JSON Generator + Upload")
        self.root.geometry("800x750") # Increased width slightly for browse button

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Style
        style = ttk.Style()
        try:
             # Try using a theme that generally looks better if available
             themes = style.theme_names()
             if "clam" in themes: style.theme_use('clam')
             elif "vista" in themes: style.theme_use('vista') # Good fallback on Windows
             elif "aqua" in themes: style.theme_use('aqua') # Good fallback on macOS
        except tk.TclError:
             print("Could not set preferred theme.") # Fallback to default

        desc_font = ('Segoe UI', 8) if sys.platform == "win32" else ('TkDefaultFont', 8)
        style.configure("Desc.TLabel", foreground="grey", font=desc_font)

        # --- Main Frame ---
        frame = ttk.Frame(root, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        frame.columnconfigure(1, weight=1) # Entry column
        frame.columnconfigure(2, weight=0) # Example/Button column
        frame.rowconfigure(12, weight=1) # Full Content text area row

        row_index = 0

        # --- Input Fields with Descriptions ---

        # ID
        ttk.Label(frame, text="Uniek ID:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=5)
        self.entry_id = ttk.Entry(frame, width=50)
        self.entry_id.grid(column=1, row=row_index, sticky=(tk.W, tk.E), padx=5, pady=2)
        ttk.Label(frame, text="bv. 'nieuwe-trainer-jan'", style="Desc.TLabel").grid(column=2, row=row_index, sticky=tk.W, padx=5)
        row_index += 1
        ttk.Label(frame, text="Kleine letters, cijfers, koppeltekens (-). Moet uniek zijn.", style="Desc.TLabel").grid(column=1, row=row_index, columnspan=2, sticky=tk.W, padx=5, pady=(0, 5))
        row_index += 1

        # Date
        ttk.Label(frame, text="Datum:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=5)
        self.entry_date = ttk.Entry(frame, width=20)
        self.entry_date.grid(column=1, row=row_index, sticky=tk.W, padx=5, pady=2)
        self.entry_date.insert(0, datetime.date.today().isoformat())
        ttk.Label(frame, text="Formaat: YYYY-MM-DD", style="Desc.TLabel").grid(column=2, row=row_index, sticky=tk.W, padx=5)
        row_index += 1

        # Title
        ttk.Label(frame, text="Titel:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=5)
        self.entry_title = ttk.Entry(frame, width=50)
        self.entry_title.grid(column=1, row=row_index, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2)
        row_index += 1
        ttk.Label(frame, text="De hoofdtitel van het nieuwsbericht (verplicht).", style="Desc.TLabel").grid(column=1, row=row_index, columnspan=2, sticky=tk.W, padx=5, pady=(0, 5))
        row_index += 1

        # Category
        ttk.Label(frame, text="Categorie:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=5)
        self.entry_category = ttk.Entry(frame, width=30)
        self.entry_category.grid(column=1, row=row_index, sticky=tk.W, padx=5, pady=2)
        self.entry_category.insert(0, DEFAULT_CATEGORY)
        ttk.Label(frame, text="bv. 'Mededelingen', 'Wedstrijden'", style="Desc.TLabel").grid(column=2, row=row_index, sticky=tk.W, padx=5)
        row_index += 1

        # Image --- MODIFIED ---
        ttk.Label(frame, text="Afbeelding:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=5)
        # Frame to hold entry and button side-by-side
        image_frame = ttk.Frame(frame)
        image_frame.grid(column=1, row=row_index, columnspan=2, sticky=(tk.W, tk.E))
        image_frame.columnconfigure(0, weight=1) # Make entry expand

        self.entry_image = ttk.Entry(image_frame, width=45) # Slightly reduced width
        self.entry_image.grid(column=0, row=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.entry_image.insert(0, DEFAULT_IMAGE)

        self.button_browse_image = ttk.Button(image_frame, text="Browse...", command=self.browse_image, width=10)
        self.button_browse_image.grid(column=1, row=0, sticky=tk.W)
        row_index += 1
        ttk.Label(frame, text="Klik 'Browse...' om te uploaden naar /images/nieuws/.", style="Desc.TLabel").grid(column=1, row=row_index, columnspan=2, sticky=tk.W, padx=5, pady=(0, 5))
        row_index += 1
        # --- End Image Modification ---

        # Summary
        ttk.Label(frame, text="Samenvatting:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=5)
        self.entry_summary = ttk.Entry(frame, width=50)
        self.entry_summary.grid(column=1, row=row_index, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2)
        row_index += 1
        ttk.Label(frame, text="Korte tekst voor nieuwslijst (optioneel, anders titel gebruikt).", style="Desc.TLabel").grid(column=1, row=row_index, columnspan=2, sticky=tk.W, padx=5, pady=(0, 5))
        row_index += 1

        # Full Content
        ttk.Label(frame, text="Volledige Tekst:").grid(column=0, row=row_index, sticky=(tk.W, tk.N), padx=5, pady=5)
        self.text_full_content = scrolledtext.ScrolledText(frame, width=60, height=15, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1)
        self.text_full_content.grid(column=1, row=row_index, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=2)
        frame.rowconfigure(row_index, weight=1)
        row_index += 1
        ttk.Label(frame, text="URLs/emails worden links. Nieuwe regels worden <br>. Basis HTML (<b>, <i>) toegestaan.", style="Desc.TLabel").grid(column=1, row=row_index, columnspan=2, sticky=tk.W, padx=5, pady=(0, 5))
        row_index += 1

        # --- Buttons Frame ---
        button_frame = ttk.Frame(frame)
        button_frame.grid(column=0, row=row_index, columnspan=3, pady=10, sticky=tk.E)

        self.button_add = ttk.Button(button_frame, text="Voeg Artikel Toe & Sla Op", command=self.add_article)
        self.button_add.pack(side=tk.LEFT, padx=5)

        self.button_clear = ttk.Button(button_frame, text="Wis Formulier", command=self.clear_form)
        self.button_clear.pack(side=tk.LEFT, padx=5)
        row_index += 1

        # --- Status Bar ---
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=5)
        self.status_label.grid(column=0, row=row_index, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.set_status("Klaar. Vul de velden in.")

    # --- Methods ---

    def set_status(self, message, is_error=False):
        self.status_var.set(message)
        self.status_label.config(foreground="red" if is_error else "black")
        # Reset potentially highlighted backgrounds (basic attempt)
        try:
            err_style = ttk.Style()
            err_style.map("TEntry", fieldbackground=[("active", "#FFCCCC"), ("!disabled", "#FFCCCC")])

            norm_style = ttk.Style()
            norm_style.map("TEntry", fieldbackground=[("active", "white"), ("!disabled", "white")])

            self.entry_id.state(["!invalid"])
            self.entry_date.state(["!invalid"])
            self.entry_title.state(["!invalid"])
        except tk.TclError:
             # Less reliable direct background setting if styles fail
             for entry in [self.entry_id, self.entry_date, self.entry_title]:
                 try: entry.config(background="white")
                 except tk.TclError: pass


    def browse_image(self):
        """Opens file dialog, copies selected image, updates entry field."""
        filetypes = (
            ("Image files", "*.jpg *.jpeg *.png *.gif *.webp *.bmp"),
            ("All files", "*.*")
        )
        source_path = filedialog.askopenfilename(
            title="Selecteer afbeelding",
            filetypes=filetypes
        )

        if not source_path: # User cancelled
            return

        filename = os.path.basename(source_path)
        dest_path = os.path.join(IMAGE_DEST_DIR_ABSOLUTE, filename)

        # Create destination directory if it doesn't exist
        try:
            os.makedirs(IMAGE_DEST_DIR_ABSOLUTE, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Directory Fout", f"Kon map niet aanmaken:\n{IMAGE_DEST_DIR_ABSOLUTE}\n\nFout: {e}")
            self.set_status(f"Fout bij aanmaken map {IMAGE_DEST_DIR_RELATIVE}", is_error=True)
            return

        # Check for overwrite
        if os.path.exists(dest_path):
            if not messagebox.askyesno("Bestand bestaat al",
                                       f"Het bestand '{filename}' bestaat al in '{IMAGE_DEST_DIR_RELATIVE}'.\n\nWilt u het overschrijven?"):
                self.set_status("Afbeelding upload geannuleerd (overschrijven geweigerd).")
                return # User chose not to overwrite

        # Copy the file
        try:
            shutil.copy2(source_path, dest_path) # copy2 preserves metadata
            print(f"Copied '{source_path}' to '{dest_path}'")
            # Update the entry field with the filename ONLY
            self.entry_image.delete(0, tk.END)
            self.entry_image.insert(0, filename)
            self.set_status(f"Afbeelding '{filename}' succesvol geüpload.")

        except Exception as e:
            messagebox.showerror("Upload Fout", f"Kon afbeelding niet kopiëren naar:\n{dest_path}\n\nFout: {e}")
            self.set_status(f"Fout bij uploaden afbeelding: {e}", is_error=True)


    def clear_form(self):
        self.entry_id.delete(0, tk.END)
        self.entry_date.delete(0, tk.END)
        self.entry_date.insert(0, datetime.date.today().isoformat())
        self.entry_title.delete(0, tk.END)
        self.entry_category.delete(0, tk.END)
        self.entry_category.insert(0, DEFAULT_CATEGORY)
        self.entry_image.delete(0, tk.END)
        self.entry_image.insert(0, DEFAULT_IMAGE) # Reset to default placeholder
        self.entry_summary.delete(0, tk.END)
        self.text_full_content.delete('1.0', tk.END)
        self.set_status("Formulier gewist.")
        self.entry_id.focus()


    def add_article(self):
        self.set_status("Verwerken...")
        self.root.update_idletasks()

        # --- Get Input (Image entry now gets filename directly) ---
        article_id = self.entry_id.get().strip().lower()
        article_date_str = self.entry_date.get().strip()
        article_title = self.entry_title.get().strip()
        article_category = self.entry_category.get().strip() or DEFAULT_CATEGORY
        # Get image filename from the entry field (populated by browse or default)
        article_image = self.entry_image.get().strip()
        if not article_image: # Should not happen if default is set, but safety check
            article_image = DEFAULT_IMAGE

        article_summary = self.entry_summary.get().strip()
        article_full_content_raw = self.text_full_content.get('1.0', tk.END).strip()

        # --- Validation (Highlighting error fields improved attempt) ---
        validation_error = False
        if not article_id:
            self.set_status("Fout: ID is verplicht.", is_error=True)
            self.entry_id.state(["invalid"]) # Use ttk state for visual feedback
            self.entry_id.focus()
            validation_error = True
        elif not is_valid_id(article_id):
            self.set_status("Fout: Ongeldig ID format (alleen a-z, 0-9, -).", is_error=True)
            self.entry_id.state(["invalid"])
            self.entry_id.focus()
            validation_error = True
        else:
             self.entry_id.state(["!invalid"])


        if not article_date_str:
            if not validation_error: self.entry_date.focus()
            self.set_status("Fout: Datum is verplicht.", is_error=True)
            self.entry_date.state(["invalid"])
            validation_error = True
        else:
            try:
                datetime.datetime.strptime(article_date_str, '%Y-%m-%d')
                self.entry_date.state(["!invalid"])
            except ValueError:
                if not validation_error: self.entry_date.focus()
                self.set_status("Fout: Ongeldig datum formaat (YYYY-MM-DD).", is_error=True)
                self.entry_date.state(["invalid"])
                validation_error = True

        if not article_title:
            if not validation_error: self.entry_title.focus()
            self.set_status("Fout: Titel is verplicht.", is_error=True)
            self.entry_title.state(["invalid"])
            validation_error = True
        else:
             self.entry_title.state(["!invalid"])

        if validation_error:
            return # Stop if basic validation failed

        # --- Load Existing Data & Check Duplicate ID ---
        existing_data, load_error = load_existing_data(JSON_FILE_PATH)
        if load_error:
            self.set_status(f"Fout bij laden JSON: {load_error}", is_error=True)
            messagebox.showerror("Laadfout", f"Kon {JSON_FILE_PATH} niet laden of lezen:\n{load_error}\n\nControleer het bestand of verwijder het om opnieuw te beginnen.")
            return
        if any(item.get('id') == article_id for item in existing_data):
            self.set_status(f"Fout: Artikel ID '{article_id}' bestaat al.", is_error=True)
            self.entry_id.state(["invalid"])
            self.entry_id.focus()
            return
        else:
             self.entry_id.state(["!invalid"]) # Ensure valid state if check passes


        # --- Process Content ---
        processed_content = auto_link_text(article_full_content_raw)
        processed_content_html = processed_content.replace('\r\n', '<br>').replace('\n', '<br>')
        final_summary = article_summary or article_title

        # --- Create New Article Dict ---
        new_article = {
            "id": article_id,
            "date": article_date_str,
            "title": article_title,
            "category": article_category,
            "image": article_image, # Use the filename from the entry field
            "summary": final_summary,
            "full_content": processed_content_html
        }

        # --- Prepend and Save ---
        updated_data = [new_article] + existing_data
        save_error = save_data(JSON_FILE_PATH, updated_data)

        if save_error:
            self.set_status(f"Fout bij opslaan: {save_error}", is_error=True)
            messagebox.showerror("Opslagfout", f"Kon het bestand niet opslaan:\n{save_error}")
        else:
            self.set_status(f"Artikel '{article_title}' succesvol toegevoegd en opgeslagen.")
            # Clear relevant fields after success
            self.entry_id.delete(0, tk.END)
            self.entry_title.delete(0, tk.END)
            self.entry_summary.delete(0, tk.END)
            self.text_full_content.delete('1.0', tk.END)
            self.entry_image.delete(0, tk.END) # Clear image field too
            self.entry_image.insert(0, DEFAULT_IMAGE) # Reset to default
            self.entry_id.focus()


# --- Main Execution ---
if __name__ == "__main__":
    try:
        os.makedirs(IMAGE_DEST_DIR_ABSOLUTE, exist_ok=True)
    except OSError as e:
        print(f"Warning: Could not pre-create image directory {IMAGE_DEST_DIR_ABSOLUTE}: {e}")

    root = tk.Tk()
    app = NewsArticleApp(root)

    try:
        s = ttk.Style()
        s.map('TEntry',
              bordercolor=[('invalid', 'red'), ('!invalid', 'grey')],
             )
    except tk.TclError:
        print("Info: Could not configure ttk styles for validation feedback.")


    root.mainloop()
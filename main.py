import tkinter as tk
from tkinter import messagebox
import os
import sys

# Try importing essential config and app class
try:
    import config
    from app import WebsiteEditorApp
except ImportError as e:
    print(f"\n[FATALE FOUT] Kon essentiële modules niet importeren: {e}")
    try:
        root_err = tk.Tk(); root_err.withdraw()
        messagebox.showerror("Fatale Fout - Import Probleem", f"Kon module niet laden: {e}\nControleer of alle .py bestanden correct aanwezig zijn.", parent=None)
        root_err.destroy()
    except Exception: pass
    sys.exit(1)
except Exception as e:
     print(f"\n[FATALE FOUT] Fout tijdens setup: {e}")
     try:
        root_err = tk.Tk(); root_err.withdraw()
        messagebox.showerror("Fatale Fout - Setup", f"Fout tijdens initialisatie: {e}", parent=None)
        root_err.destroy()
     except Exception: pass
     sys.exit(1)


# Check for optional libraries here (Pillow, lxml) to show warnings early
warnings_found = False
try:
    from PIL import Image, ImageTk
except ImportError:
    print("[WAARSCHUWING] Pillow (PIL) bibliotheek niet gevonden (Beperkte afbeeldingsformaten).")
    warnings_found = True

try:
    import lxml
except ImportError:
    print("[WAARSCHUWING] lxml bibliotheek niet gevonden (Fallback naar tragere html.parser).")
    warnings_found = True


if __name__ == "__main__":
    print("\n--- Starten Website Editor ---")

    # Basic path check (more detailed checks could be added)
    errors_found = False
    required_files = [config.CALENDAR_HTML_FILE_PATH, config.REPORTS_HTML_FILE_PATH, config.TRAINERS_HTML_FILE_PATH]
    required_dirs = [config.RECORDS_BASE_DIR_ABSOLUTE]

    for path in required_files:
        if not os.path.isfile(path):
            print(f"  *** VEREIST BESTAND ONTBREEKT: {path}")
            errors_found = True
    for path in required_dirs:
         if not os.path.isdir(path):
            print(f"  *** VEREISTE MAP ONTBREEKT: {path}")
            errors_found = True

    if errors_found:
         print("\n[FATALE FOUT] Kritieke bestanden/mappen ontbreken. Zie console.")
         try: root_err = tk.Tk(); root_err.withdraw(); messagebox.showerror("Fatale Fout - Installatie", "Vereiste bestanden/mappen ontbreken. Controleer console.", parent=None); root_err.destroy()
         except Exception: pass
         sys.exit(1)

    if warnings_found:
         print("\n[WAARSCHUWING] Optionele bibliotheken ontbreken. Functionaliteit kan beperkt zijn.")
         try: root_warn = tk.Tk(); root_warn.withdraw(); messagebox.showwarning("Waarschuwing - Bibliotheken", "Optionele bibliotheken (Pillow/lxml) ontbreken. Controleer console.", parent=None); root_warn.destroy()
         except Exception: pass

    print("\n--- Initialiseren GUI ---")
    root = None
    try:
        root = tk.Tk()
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        app = WebsiteEditorApp(root)
        print("--- GUI Klaar ---")
        root.mainloop()
        print("\n--- Applicatie Gesloten ---")
    except Exception as e:
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("[FATALE FOUT] Een onverwachte fout is opgetreden tijdens runtime:")
        import traceback; traceback.print_exc()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        try:
            root_fatal = tk.Tk() if root is None else root; root_fatal.withdraw()
            messagebox.showerror("Fatale Runtime Fout", f"Een onverwachte fout is opgetreden:\n{e}\nControleer console.", parent=root_fatal)
            if root_fatal and not root: root_fatal.destroy()
        except Exception as me: pass
        input("\nDruk op Enter om af te sluiten...")
        sys.exit(1)
import sys
import json
import argparse
import tkinter as tk
from tkinter import messagebox


def _show_startup_error(title, message):
    try:
        root_err = tk.Tk()
        root_err.withdraw()
        messagebox.showerror(title, message, parent=None)
        root_err.destroy()
    except Exception:
        pass


def _check_optional_dependencies():
    warnings_found = False
    try:
        from PIL import Image, ImageTk  # noqa: F401
    except ImportError:
        print("[WAARSCHUWING] Pillow (PIL) bibliotheek niet gevonden (beperkte afbeeldingsformaten).")
        warnings_found = True

    try:
        import lxml  # noqa: F401
    except ImportError:
        print("[WAARSCHUWING] lxml bibliotheek niet gevonden (fallback naar tragere html.parser).")
        warnings_found = True

    if warnings_found:
        print("\n[WAARSCHUWING] Optionele bibliotheken ontbreken. Functionaliteit kan beperkt zijn.")


def _load_app_class():
    try:
        import config  # noqa: F401
        from app import WebsiteEditorApp
        return WebsiteEditorApp
    except ImportError as e:
        print(f"\n[FATALE FOUT] Kon essentiële modules niet importeren: {e}")
        _show_startup_error(
            "Fatale Fout - Import Probleem",
            f"Kon module niet laden: {e}\nControleer of alle .py bestanden correct aanwezig zijn.",
        )
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATALE FOUT] Fout tijdens setup: {e}")
        _show_startup_error("Fatale Fout - Setup", f"Fout tijdens initialisatie: {e}")
        sys.exit(1)


def _smoke_test(output_path):
    """Exercise the packaged editor without network calls or a visible window."""
    result = {'ok': False}
    root = None
    try:
        import config
        from app import WebsiteEditorApp, PreviewManager
        from tabs.media_manager_tab import HAS_PILLOW, HAS_PYMUPDF
        import lxml
        import bs4
        WebsiteEditorApp._perform_initial_load = lambda self: None
        WebsiteEditorApp._check_for_app_update = lambda self: None
        PreviewManager._start_server = lambda self: None
        def fail_dialog(title, message, **kwargs):
            raise RuntimeError(f'{title}: {message}')
        messagebox.showerror = fail_dialog
        root = tk.Tk()
        root.withdraw()
        app = WebsiteEditorApp(root)
        root.update_idletasks()
        if len(app.tab_managers) != 13 or app._unsaved_tab_keys():
            raise RuntimeError('Editor tabs did not initialize cleanly.')
        app.toggle_interaction(False)
        app.toggle_interaction(True)
        if not (HAS_PILLOW and HAS_PYMUPDF):
            raise RuntimeError('Image/PDF dependencies are missing from the executable.')
        result.update(ok=True, version=config.APP_VERSION, tabs=12, pillow=HAS_PILLOW,
                      pymupdf=HAS_PYMUPDF, lxml=lxml.__version__, bs4=bs4.__version__,
                      executable_version=app._current_app_version())
        app._closing = True
    except Exception as error:
        import traceback
        result.update(error=str(error), traceback=traceback.format_exc())
    finally:
        if root is not None:
            root.update_idletasks()
            for callback in root.tk.call('after', 'info'):
                root.after_cancel(callback)
            root.destroy()
        with open(output_path, 'w', encoding='utf-8') as output:
            json.dump(result, output, indent=2)
    return 0 if result['ok'] else 1


def main():
    parser = argparse.ArgumentParser(description='Thiberta Website Editor')
    parser.add_argument('--smoke-test-output', metavar='FILE', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.smoke_test_output:
        sys.exit(_smoke_test(args.smoke_test_output))
    print("\n--- Starten Website Editor ---")
    _check_optional_dependencies()
    WebsiteEditorApp = _load_app_class()

    print("\n--- Initialiseren GUI ---")
    root = None
    try:
        root = tk.Tk()
        WebsiteEditorApp(root)
        print("--- GUI Klaar ---")
        root.mainloop()
        print("\n--- Applicatie Gesloten ---")
    except Exception as e:
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("[FATALE FOUT] Een onverwachte fout is opgetreden tijdens runtime:")
        import traceback
        traceback.print_exc()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        try:
            root_fatal = tk.Tk() if root is None or not root.winfo_exists() else root
            root_fatal.withdraw()
            messagebox.showerror(
                "Fatale Runtime Fout",
                f"Een onverwachte fout is opgetreden:\n{e}\nControleer console.",
                parent=None,
            )
            if root_fatal and root is None:
                root_fatal.destroy()
        except Exception as me:
            print(f"Kon fatale foutmelding niet tonen: {me}")
        sys.exit(1)


if __name__ == "__main__":
    main()

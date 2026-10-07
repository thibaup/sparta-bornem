# utils.py

import os
import sys
import re
import json
import pathlib
import tempfile
import stat
import shutil
import copy
import hashlib
import uuid
import weakref
from urllib.parse import urlsplit, unquote
from contextlib import contextmanager
import tkinter as tk
from tkinter import messagebox
from collections import defaultdict
import traceback
import calendar
import html # <--- Ensure this is imported

try:
    from bs4 import BeautifulSoup, Tag, NavigableString, Comment
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    class DummyBs4Type: pass
    BeautifulSoup = DummyBs4Type
    Tag = DummyBs4Type
    NavigableString = DummyBs4Type
    Comment = DummyBs4Type
    print("\n[FATALE FOUT] BeautifulSoup4 bibliotheek niet gevonden.")
    try:
        root_err = tk.Tk(); root_err.withdraw()
        messagebox.showerror("Fatale Fout - Ontbrekende Bibliotheek", "Vereiste bibliotheek 'BeautifulSoup4' niet gevonden.\nInstalleer a.u.b. via:\npip install beautifulsoup4", parent=None)
        root_err.destroy()
    except Exception: pass
    sys.exit(1)


import config


@contextmanager
def atomic_text_writer(filepath):
    """Replace a saved file only after the complete UTF-8 write succeeds."""
    target = os.path.abspath(os.fspath(filepath))
    directory = os.path.dirname(target)
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.' + os.path.basename(target) + '.', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            yield output
            output.flush()
            os.fsync(output.fileno())
        if os.path.exists(target):
            os.chmod(temporary, stat.S_IMODE(os.stat(target).st_mode))
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.chmod(temporary, stat.S_IWRITE | stat.S_IREAD)
            os.remove(temporary)


def atomic_write_text(filepath, content):
    with atomic_text_writer(filepath) as output:
        output.write(content)


def atomic_write_bytes(filepath, content):
    target = os.path.abspath(os.fspath(filepath))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.' + os.path.basename(target) + '.', suffix='.tmp', dir=os.path.dirname(target))
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def atomic_copy_file(source, destination):
    """Keep the old asset intact if copying its replacement fails."""
    source = os.path.abspath(os.fspath(source))
    destination = os.path.abspath(os.fspath(destination))
    if os.path.exists(destination) and os.path.samefile(source, destination):
        return
    directory = os.path.dirname(destination)
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.' + os.path.basename(destination) + '.', suffix='.tmp', dir=directory)
    os.close(descriptor)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.chmod(temporary, stat.S_IWRITE | stat.S_IREAD)
            os.remove(temporary)


def copy_new_asset(source, destination, owner=None):
    """Import an asset without overwriting a file used by existing content."""
    destination = os.path.abspath(destination)
    if os.path.exists(destination) and os.path.samefile(source, destination):
        return destination
    stem, extension = os.path.splitext(destination)
    counter = 1
    while os.path.exists(destination):
        destination = f'{stem}_{counter}{extension}'
        counter += 1
    atomic_copy_file(source, destination)
    if owner is not None:
        register_pending_asset(owner, destination)
    return destination


def _asset_app(owner):
    return getattr(owner, 'app', None) or getattr(owner, 'app_instance', None) or owner


def _file_fingerprint(path):
    with open(path, 'rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    info = os.stat(path)
    return (info.st_dev, info.st_ino, digest)


def register_pending_asset(owner, path):
    """Only register a new import; pre-existing files must never enter this ledger."""
    app = _asset_app(owner)
    base, path = os.path.realpath(config.APP_BASE_DIR), os.path.realpath(path)
    if os.path.commonpath([os.path.normcase(base), os.path.normcase(path)]) != os.path.normcase(base):
        return
    if not hasattr(app, '_pending_assets'):
        app._pending_assets = {}
        app._pending_asset_owners = {}
    app._pending_assets[path] = _file_fingerprint(path)
    try:
        app._pending_asset_owners[id(owner)] = weakref.ref(owner)
    except TypeError:
        app._pending_asset_owners[id(owner)] = lambda: owner


def _asset_text(value):
    if isinstance(value, dict):
        return '\n'.join(_asset_text(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return '\n'.join(_asset_text(item) for item in value)
    return unquote(html.unescape(str(value or ''))).replace('\\', '/').casefold()


def cleanup_pending_assets(owner, include_drafts=True):
    """Remove unchanged session imports only when neither disk nor drafts reference them."""
    app = _asset_app(owner)
    pending = getattr(app, '_pending_assets', {})
    if not pending:
        return []
    base = os.path.realpath(config.APP_BASE_DIR)
    disk_text, errors = [], []
    for folder, directories, filenames in os.walk(base):
        directories[:] = [name for name in directories if name not in
                          {'.git', '.editor-recovery', 'build', 'dist', '__pycache__', '.venv', 'venv', 'env'}
                          and not os.path.islink(os.path.join(folder, name))]
        for name in filenames:
            if os.path.splitext(name)[1].lower() not in {'.html', '.json', '.css', '.js'}:
                continue
            try:
                with open(os.path.join(folder, name), encoding='utf-8-sig') as source:
                    disk_text.append(_asset_text(source.read()))
            except (OSError, UnicodeError) as error:
                errors.append(f'{name}: {error}')
    # An incomplete reference scan cannot establish that any import is unused.
    if errors:
        return errors
    persisted = '\n'.join(disk_text)
    drafts = []
    if include_drafts:
        fields = ('news_data', 'trainers_data', 'full_bestuur_data', 'full_jury_data',
                  'sponsor_data', 'reports_data', 'downloads', 'data', 'current_soup',
                  'current_main_photo_details', 'current_thumbnails_list')
        owners = [reference() for reference in getattr(app, '_pending_asset_owners', {}).values()]
        owners.extend(getattr(app, 'tab_managers', {}).values())
        for editor in list(owners):
            if editor is None:
                continue
            owners.extend(getattr(editor, name, None) for name in ('bestuur', 'jury'))
        for editor in owners:
            if editor is None:
                continue
            try:
                if isinstance(editor, tk.Toplevel) and not editor.winfo_exists():
                    continue
                drafts.extend(_asset_text(getattr(editor, field)) for field in fields if hasattr(editor, field))
                if hasattr(editor, '_form_snapshot'):
                    drafts.append(_asset_text(editor._form_snapshot()))
            except (tk.TclError, AttributeError):
                return ['De actieve concepten konden niet volledig gecontroleerd worden.']
    active = '\n'.join(drafts)
    for path, fingerprint in list(pending.items()):
        try:
            resolved = os.path.realpath(path)
            if os.path.commonpath([os.path.normcase(base), os.path.normcase(resolved)]) != os.path.normcase(base):
                continue
            relative = pathlib.Path(os.path.relpath(path, base)).as_posix().casefold()
            tokens = [relative]
            if relative.startswith('images/nieuws/'):
                tokens.append(os.path.basename(path).casefold())
            if any(token in persisted for token in tokens):
                pending.pop(path, None)  # A successful metadata save transfers ownership to the site.
            elif not any(token in active for token in tokens):
                if os.path.isfile(path) and not os.path.islink(path) and _file_fingerprint(path) == fingerprint:
                    os.unlink(path)
                pending.pop(path, None)  # Externally modified/replaced assets are preserved.
        except OSError as error:
            errors.append(f'{path}: {error}')
    if not pending:
        getattr(app, '_pending_asset_owners', {}).clear()
    return errors


class EditorTransactionError(OSError):
    pass


def _validate_transaction_directory(directory, base):
    root = os.path.realpath(os.path.join(base, '.editor-recovery'))
    directory = os.path.realpath(directory)
    if (os.path.commonpath([os.path.normcase(base), os.path.normcase(root)]) != os.path.normcase(base)
            or os.path.dirname(directory) != root or not re.fullmatch(r'[a-f0-9]{32}', os.path.basename(directory))):
        raise EditorTransactionError('Ongeldig pad voor transactieherstel.')
    return directory


def _cleanup_transaction(directory, base):
    # Resolve and verify the exact recursive deletion target before removing recovery files.
    directory = _validate_transaction_directory(directory, base)
    shutil.rmtree(directory)


def _transaction_paths(directory, entry, base):
    target = os.path.realpath(os.path.join(base, entry['target']))
    if os.path.commonpath([os.path.normcase(base), os.path.normcase(target)]) != os.path.normcase(base):
        raise EditorTransactionError('Herstelpad ligt buiten de website.')
    backup = os.path.abspath(os.path.join(directory, entry['backup']))
    if os.path.dirname(backup) != directory:
        raise EditorTransactionError('Ongeldig reservekopiepad in herstelbestand.')
    return target, backup


def _restore_transaction(directory, journal, base):
    errors = []
    for entry in reversed(journal['entries']):
        try:
            target, backup = _transaction_paths(directory, entry, base)
            current = _file_fingerprint(target)[2] if os.path.isfile(target) else None
            if current == entry['original_hash']:
                continue
            if current not in (None, entry['output_hash']):
                raise EditorTransactionError('Bestand is sinds de transactie extern gewijzigd; automatisch herstel overgeslagen.')
            if entry['existed']:
                original = pathlib.Path(backup).read_bytes()
                if hashlib.sha256(original).hexdigest() != entry['original_hash']:
                    raise EditorTransactionError('Reservekopie is niet geldig.')
                atomic_write_bytes(target, original)
            elif os.path.exists(target):
                os.unlink(target)
        except (OSError, ValueError, KeyError) as error:
            errors.append(f"{entry.get('target', '?')}: {error}")
    return errors


def recover_editor_transactions(base_dir=None):
    """Restore interrupted batches before the editor reads potentially mixed versions."""
    base = os.path.realpath(base_dir or config.APP_BASE_DIR)
    root = os.path.join(base, '.editor-recovery')
    if not os.path.isdir(root):
        return
    for name in os.listdir(root):
        if not re.fullmatch(r'[a-f0-9]{32}', name):
            continue
        directory = os.path.abspath(os.path.join(root, name))
        directory = _validate_transaction_directory(directory, base)
        journal_path = os.path.join(directory, 'journal.json')
        if not os.path.isfile(journal_path):
            continue
        with open(journal_path, encoding='utf-8') as source:
            journal = json.load(source)
        errors = [] if journal.get('state') == 'committed' else _restore_transaction(directory, journal, base)
        if errors:
            raise EditorTransactionError('Automatisch herstel mislukt. Reservekopieën en herstelbestand: ' +
                                         directory + '\n' + '\n'.join(errors))
        _cleanup_transaction(directory, base)


def atomic_write_many(outputs, base_dir=None):
    """Commit a batch, compensating on failure and retaining recovery evidence if needed."""
    if not outputs:
        return
    base = os.path.realpath(base_dir or config.APP_BASE_DIR)
    recovery_root = os.path.join(base, '.editor-recovery')
    directory = os.path.join(recovery_root, uuid.uuid4().hex)
    directory = _validate_transaction_directory(directory, base)
    os.makedirs(directory)
    journal = {'version': 1, 'state': 'prepared', 'entries': []}
    journal_path = os.path.join(directory, 'journal.json')
    begun = False
    try:
        for index, (filename, content) in enumerate(outputs.items()):
            target = os.path.realpath(filename)
            if os.path.commonpath([os.path.normcase(base), os.path.normcase(target)]) != os.path.normcase(base):
                raise EditorTransactionError('Opslagpad ligt buiten de website.')
            existed = os.path.isfile(target)
            original = pathlib.Path(target).read_bytes() if existed else b''
            backup_name, staged_name = f'{index}.backup', f'{index}.staged'
            atomic_write_bytes(os.path.join(directory, backup_name), original)
            atomic_write_bytes(os.path.join(directory, staged_name), content)
            journal['entries'].append({'target': os.path.relpath(target, base), 'backup': backup_name,
                                       'staged': staged_name, 'existed': existed,
                                       'original_hash': hashlib.sha256(original).hexdigest() if existed else None,
                                       'output_hash': hashlib.sha256(content).hexdigest()})
        atomic_write_text(journal_path, json.dumps(journal, indent=2))
        begun = True
        for entry in journal['entries']:
            target, _ = _transaction_paths(directory, entry, base)
            current = _file_fingerprint(target)[2] if os.path.isfile(target) else None
            if current != entry['original_hash']:
                raise EditorTransactionError('Een doelbestand is tijdens het opslaan gewijzigd.')
            os.replace(os.path.join(directory, entry['staged']), target)
        journal['state'] = 'committed'
        atomic_write_text(journal_path, json.dumps(journal, indent=2))
    except Exception as error:
        failures = _restore_transaction(directory, journal, base) if begun else []
        if failures:
            raise EditorTransactionError(f'Opslaan en herstel mislukt. Reservekopieën: {directory}\n' +
                                         '\n'.join(failures)) from error
        _cleanup_transaction(directory, base)
        raise
    else:
        # All files are committed; leftover recovery files are safe to clean next startup.
        try:
            _cleanup_transaction(directory, base)
        except OSError:
            pass


def resolve_site_path(web_path, source_file=None):
    parsed = urlsplit(str(web_path).replace('\\', '/'))
    if parsed.scheme or parsed.netloc:
        raise ValueError('Dit is geen lokaal websitepad.')
    path = unquote(parsed.path)
    base = os.path.realpath(config.APP_BASE_DIR)
    origin = base if path.startswith('/') or source_file is None else os.path.dirname(os.path.abspath(source_file))
    candidate = os.path.realpath(os.path.join(origin, path.lstrip('/')))
    if os.path.commonpath([os.path.normcase(base), os.path.normcase(candidate)]) != os.path.normcase(base):
        raise ValueError('Het pad ligt buiten de website.')
    return candidate


def remember_editor_state(editor, state, key='_saved_editor_state'):
    setattr(editor, key, copy.deepcopy(state))
    cleanup_pending_assets(editor)


def editor_state_changed(editor, state, key='_saved_editor_state'):
    return hasattr(editor, key) and getattr(editor, key) != state


def confirm_discard_changes(editor, has_changes=None):
    app = getattr(editor, 'app', None)
    if getattr(app, '_discarding_changes', False):
        return True
    if not (editor.has_unsaved_changes() if has_changes is None else has_changes):
        return True
    return messagebox.askyesno("Niet opgeslagen", "Er zijn wijzigingen die nog niet opgeslagen zijn.\nDoorgaan zonder opslaan?",
                              icon='warning', parent=getattr(app, 'root', None))

def news_load_existing_data(filepath):
    """Loads news data from a JSON file."""
    if not os.path.exists(filepath):
        return [], None # Return empty list if file doesn't exist
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return [], None # Return empty list if file is empty
            data = json.loads(content)
            if not isinstance(data, list):
                msg = f"Data in '{filepath}' is geen lijst."
                return None, msg
            ids = set()
            for item in data:
                if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id'] or item['id'] in ids:
                    raise ValueError('Nieuwsitems moeten objecten met unieke, niet-lege ids zijn.')
                ids.add(item['id'])
                for key in ('date', 'title', 'category', 'image', 'summary', 'full_content'):
                    if key in item and item[key] is not None and not isinstance(item[key], str):
                        raise ValueError(f'Nieuwsveld {key} moet tekst bevatten.')
            # Sort by date descending
            data.sort(key=lambda x: x.get('date', '0000-00-00'), reverse=True)
            return data, None
    except json.JSONDecodeError as e:
        msg = f"Kon JSON niet decoderen uit '{filepath}': {e}"
        return None, msg
    except Exception as e:
        msg = f"Fout bij laden nieuws data uit '{filepath}': {e}"
        traceback.print_exc()
        return None, msg

def news_save_data(filepath, data):
    """Saves news data to a JSON file, sorted by date."""
    try:
        # Ensure data is sorted before saving
        data = sorted(data, key=lambda x: x.get('date', '0000-00-00'), reverse=True)
        with atomic_text_writer(filepath) as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return None # Success
    except Exception as e:
        msg = f"Opslaan nieuws data naar '{filepath}': {e}"
        traceback.print_exc()
        return msg

def images_gallery_default_data():
    return {
        "pageTitle": "Images - Atletiekclub Sparta Bornem",
        "heading": "Images",
        "folders": []
    }

def images_gallery_load_json_data(json_filepath):
    """Loads the Images page JSON, creating a valid empty structure when missing."""
    default_data = images_gallery_default_data()
    if not os.path.exists(json_filepath):
        return default_data, None

    try:
        with open(json_filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read().strip()
        if not content:
            return default_data, None

        data = json.loads(content)
        if not isinstance(data, dict):
            return default_data, "Images JSON moet een object zijn."

        data.setdefault("pageTitle", default_data["pageTitle"])
        data.setdefault("heading", default_data["heading"])
        folders = data.setdefault("folders", [])
        if not isinstance(folders, list):
            raise ValueError('Images folders moet een lijst zijn.')
        ids = set()
        for folder in folders:
            if not isinstance(folder, dict):
                raise ValueError('Elke Images map moet een object zijn.')
            folder.setdefault("id", config.sanitize_for_path(folder.get("title", "folder")) or "folder")
            folder.setdefault("title", "Naamloze map")
            identity = folder['id']
            if not isinstance(identity, str) or not identity or identity in ('.', '..') or any(char in identity for char in '/\\:') or identity in ids:
                raise ValueError('Images mapids moeten unieke, geldige mapnamen zijn.')
            ids.add(identity)
            if not isinstance(folder['title'], str) or not isinstance(folder.setdefault('images', []), list):
                raise ValueError('Ongeldige Images mapgegevens.')
            for image in folder['images']:
                if not isinstance(image, dict) or not isinstance(image.get('src'), str) or not image['src']:
                    raise ValueError('Elke afbeelding moet een geldig src-pad bevatten.')
                if any(key in image and not isinstance(image[key], str) for key in ('alt', 'filename')):
                    raise ValueError('Afbeeldingnamen en alt-teksten moeten tekst bevatten.')
        return data, None
    except json.JSONDecodeError as e:
        return default_data, f"Foutieve JSON in {json_filepath}: {e}"
    except Exception as e:
        traceback.print_exc()
        return default_data, f"Kon Images JSON niet laden: {e}"

def images_gallery_save_json_data(json_filepath, data_dict):
    """Saves the Images page JSON."""
    try:
        data_to_save = copy.deepcopy(data_dict) if isinstance(data_dict, dict) else images_gallery_default_data()
        data_to_save.setdefault("pageTitle", "Images - Atletiekclub Sparta Bornem")
        data_to_save.setdefault("heading", "Images")
        data_to_save.setdefault("folders", [])
        with atomic_text_writer(json_filepath) as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        return None
    except Exception as e:
        traceback.print_exc()
        return f"Kon Images JSON niet opslaan: {e}"

def news_auto_link_text(text):
    """Automatically converts URLs and email addresses in text to HTML links."""
    if not text: return ''
    # Regex for finding email addresses
    email_regex = r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b'
    # Regex for finding URLs (http, https, www), avoiding those already in href/src
    url_regex = r'(?<!href=["\'])(?<!src=["\'])\b((?:https?://|www\.)[^\s<>"]+?\.[^\s<>"]+)'

    def replace_email(match):
        """Replacement function for email matches."""
        return f'<a href="mailto:{match.group(1)}">{match.group(1)}</a>'

    def replace_url(match):
        """Replacement function for URL matches."""
        url = match.group(1)
        href = url
        # Prepend https:// if URL starts with www.
        if href.startswith('www.'):
            href = 'https://' + href
        return f'<a href="{href}" target="_blank" rel="noopener noreferrer">{url}</a>'

    # Apply replacements
    text_with_links = re.sub(email_regex, replace_email, text)
    text_with_links = re.sub(url_regex, replace_url, text_with_links)
    return text_with_links

def news_is_valid_id(article_id):
    """Checks if a news article ID is valid (lowercase, numbers, hyphens)."""
    return bool(re.match(r'^[a-z0-9-]+$', article_id))


def records_discover_files(base_dir):
    record_structure = {}
    if not os.path.isdir(base_dir):
        return {}
    try:
        header_path = os.path.abspath(os.path.join(base_dir, '..', '..', '_header.html'))
        header_order = _header_read_order(header_path)
        fs_categories = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
        for category in header_order["categories"]:
            if category in fs_categories:
                category_path = os.path.join(base_dir, category)
                record_structure[category] = {}
                files = [f for f in os.listdir(category_path) if f.lower().endswith('.html')]
                ordered_types = [t for t in header_order["types"].get(category, []) if f"{t}.html" in files]
                for t in ordered_types:
                    record_structure[category][t] = os.path.join(category_path, f"{t}.html")
                for f in files:
                    t = os.path.splitext(f)[0]
                    if t not in record_structure[category]:
                        record_structure[category][t] = os.path.join(category_path, f)
        for category in fs_categories:
            if category not in record_structure:
                category_path = os.path.join(base_dir, category)
                record_structure[category] = {}
                files = [f for f in os.listdir(category_path) if f.lower().endswith('.html')]
                for f in files:
                    t = os.path.splitext(f)[0]
                    record_structure[category][t] = os.path.join(category_path, f)
    except OSError as e:
        print(f"[UTILS][RECORDS] Fout bij toegang tot basis map {base_dir}: {e}")
        return {}
    return record_structure

def _header_find_clubrecords_li(soup):
    nav = soup.find('nav', class_='main-nav')
    if not nav:
        return None
    for li in nav.find_all('li', class_='menu-item-has-children', recursive=True):
        a = li.find('a', recursive=False)
        if a and (a.get_text(strip=True) or "").strip().lower() == "clubrecords":
            return li
    return None

def _header_read_order(header_path):
    result = {"categories": [], "types": {}}
    try:
        with open(header_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'lxml' if 'lxml' in sys.modules else 'html.parser')
        cr_li = _header_find_clubrecords_li(soup)
        if not cr_li:
            return result
        submenu = cr_li.find('ul', class_='submenu')
        if not submenu:
            return result
        for cat_li in submenu.find_all('li', class_='menu-item-has-children', recursive=False):
            cat_a = cat_li.find('a', recursive=False)
            if not cat_a:
                continue
            cat_name = cat_a.get_text(strip=True)
            if not cat_name:
                continue
            result["categories"].append(cat_name)
            result["types"][cat_name] = []
            inner = cat_li.find('ul', class_='submenu')
            if inner:
                for t_li in inner.find_all('li', recursive=False):
                    t_a = t_li.find('a')
                    if t_a:
                        t_name = t_a.get_text(strip=True)
                        if t_name:
                            result["types"][cat_name].append(t_name)
    except Exception:
        pass
    return result

def _header_write_from_order(header_path, base_dir, order_map):
    with open(header_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'lxml' if 'lxml' in sys.modules else 'html.parser')
    cr_li = _header_find_clubrecords_li(soup)
    if not cr_li:
        return False
    submenu = cr_li.find('ul', class_='submenu')
    if not submenu:
        submenu = soup.new_tag('ul', **{'class': 'submenu'})
        cr_li.append(submenu)
    submenu.clear()
    for category in order_map.keys():
        cat_li = soup.new_tag('li', **{'class': 'menu-item-has-children'})
        cat_a = soup.new_tag('a')
        cat_a.string = category
        cat_li.append(cat_a)
        inner = soup.new_tag('ul', **{'class': 'submenu'})
        types = order_map.get(category, [])
        for t in types:
            t_li = soup.new_tag('li')
            t_a = soup.new_tag('a', href=f"/html/clubrecords/{category}/{t}.html")
            t_a.string = t
            t_li.append(t_a)
            inner.append(t_li)
        cat_li.append(inner)
        submenu.append(cat_li)
    with atomic_text_writer(header_path) as f:
        f.write(soup.prettify(formatter="html5"))
    return True

def records_header_set_order(base_dir, partial_order):
    header_path = os.path.abspath(os.path.join(base_dir, '..', '..', '_header.html'))
    current = _header_read_order(header_path)
    cats = current["categories"] if current["categories"] else []
    if not cats:
        fs_cats = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
        cats = fs_cats
    merged = {}
    for c in cats:
        exist = current["types"].get(c, [])
        want = partial_order.get(c)
        if want is None:
            merged[c] = exist
        else:
            seen = set()
            lst = []
            for t in want:
                if t not in seen:
                    lst.append(t); seen.add(t)
            for t in exist:
                if t not in seen:
                    lst.append(t); seen.add(t)
            merged[c] = lst
    _header_write_from_order(header_path, base_dir, merged)

def records_header_append_type(base_dir, category, type_name):
    header_path = os.path.abspath(os.path.join(base_dir, '..', '..', '_header.html'))
    current = _header_read_order(header_path)
    if category not in current["categories"]:
        current["categories"].append(category)
        current["types"][category] = []
    if type_name not in current["types"].get(category, []):
        current["types"][category].append(type_name)
    order = {c: current["types"].get(c, []) for c in current["categories"]}
    _header_write_from_order(header_path, base_dir, order)

def records_header_remove_type(base_dir, category, type_name):
    header_path = os.path.abspath(os.path.join(base_dir, '..', '..', '_header.html'))
    current = _header_read_order(header_path)
    if category in current["types"]:
        current["types"][category] = [t for t in current["types"][category] if t != type_name]
    order = {c: current["types"].get(c, []) for c in (current["categories"] or list(current["types"].keys()))}
    _header_write_from_order(header_path, base_dir, order)


_RECORD_BREAK_RE = re.compile(r'<br\s*/?>|&(?:amp;)*lt;br\s*/?&(?:amp;)*gt;', re.IGNORECASE)


def records_text_lines(value):
    """Decode legacy break delimiters without interpreting other text as HTML."""
    parts = _RECORD_BREAK_RE.split(str(value or ""))
    return [re.sub(r'\s+', ' ', part).strip() for part in parts]


def _records_cell_lines(cell, decode_legacy_breaks=True):
    # Only BR elements delimit slots. Inline formatting and source indentation do not.
    parts = [""]
    for node in cell.descendants:
        if isinstance(node, Tag) and node.name == 'br':
            parts.append("")
        elif isinstance(node, NavigableString) and not isinstance(node, Comment):
            text_parts = _RECORD_BREAK_RE.split(str(node)) if decode_legacy_breaks else [str(node)]
            parts[-1] += text_parts[0]
            parts.extend(text_parts[1:])
    parts = [re.sub(r'\s+', ' ', part).strip() for part in parts]
    # Old saves padded scalar fields with empty breaks. Keep interior empty slots.
    while len(parts) > 1 and not parts[-1]:
        parts.pop()
    return parts


def records_is_relay(discipline):
    return bool(re.search(r'\d\s*[x×]\s*\d|estaf|afloss|relay', discipline, re.IGNORECASE))


def _records_from_cell_lines(columns):
    discipline = columns[0][0]
    names = columns[1]

    def value_at(column, index):
        # A single value is shared by tied records in old tables.
        return column[0] if len(column) == 1 else (column[index] if index < len(column) else "")

    def make_record(member_names, index):
        return {
            "discipline": discipline,
            "names": member_names,
            "performance": value_at(columns[2], index),
            "place": value_at(columns[3], index),
            "date": value_at(columns[4], index),
        }

    if records_is_relay(discipline):
        # Legacy tables may contain several teams separated by padded metadata slots.
        starts = [0] + [i for i in range(1, max(map(len, columns[2:])))
                        if any(i < len(col) and col[i] for col in columns[2:])]
        records = []
        for offset, start in enumerate(starts):
            end = starts[offset + 1] if offset + 1 < len(starts) else len(names)
            records.append(make_record([name for name in names[start:end] if name], start))
        return records

    return [make_record([value_at(names, i)] if value_at(names, i) else [], i)
            for i in range(max(map(len, columns[1:])))]


def records_parse_html(html_path):
    if not BS4_AVAILABLE:
        return None

    all_records = []
    general_messages = []
    contact_prefix = ""
    contact_email = ""

    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'lxml' if 'lxml' in sys.modules else 'html.parser')

        table = soup.find('table', class_='records-table')
        tbody = table.find('tbody') if table else soup.find('tbody')

        if tbody:
            for row in tbody.find_all('tr', recursive=False):
                cells = row.find_all('td', recursive=False)
                if len(cells) != 5:
                    continue

                is_current_format = table is not None and table.get('data-records-format') == '2'
                columns = [_records_cell_lines(td, decode_legacy_breaks=not is_current_format) for td in cells]
                if is_current_format:
                    all_records.append({
                        "discipline": columns[0][0],
                        "names": [name for name in columns[1] if name],
                        "performance": columns[2][0],
                        "place": columns[3][0],
                        "date": columns[4][0],
                    })
                else:
                    all_records.extend(_records_from_cell_lines(columns))

        main_container = soup.find('main', class_='container')
        if main_container:
            for p_tag in main_container.find_all('p', class_='record-notice'):
                link_tag = p_tag.find('a', href=lambda href: href and 'mailto:' in href)
                if link_tag:
                    contact_email = link_tag.get_text(strip=True)
                    # Extract text that is a direct child of p_tag, but not in the a_tag
                    prefix_text = ' '.join(s.strip() for s in p_tag.find_all(string=True, recursive=False) if s.strip())
                    contact_prefix = prefix_text.strip()
                else:
                    general_messages.append(p_tag.get_text(strip=True))

        return {
            "records": all_records,
            "general_messages": general_messages,
            "prefix": contact_prefix,
            "email": contact_email
        }

    except Exception as e:
        print(f"[UTILS][RECORDS] Fout bij parsen {html_path}: {e}")
        traceback.print_exc()
        return None

def records_save_html(html_path, records_data, contact_prefix, contact_email, general_messages, record_type_title=""):
    if not BS4_AVAILABLE:
        return False, "BeautifulSoup niet beschikbaar voor opslaan."

    try:
        soup = None
        if os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'lxml' if 'lxml' in sys.modules else 'html.parser')

        if soup is None:
            template = "<!DOCTYPE html><html lang=\"nl-NL\"><head><meta charset=\"UTF-8\"><title></title><link rel=\"stylesheet\" href=\"/css/style.css\"></head><body><main class=\"container\"></main></body></html>"
            soup = BeautifulSoup(template, 'html.parser')

        if soup.head is None:
            head_tag = soup.new_tag("head")
            if soup.html:
                soup.html.insert(0, head_tag)
            else:
                soup.insert(0, head_tag)
        if soup.body is None:
            body_tag = soup.new_tag("body")
            if soup.html:
                soup.html.append(body_tag)
            else:
                soup.append(body_tag)

        main_container = soup.find("main", class_="container")
        if not main_container:
            main_container = soup.new_tag("main", attrs={'class': 'container'})
            soup.body.append(main_container)

        final_title = record_type_title or "Clubrecords"

        h1_tag = main_container.find('h1')
        if not h1_tag:
            h1_tag = soup.new_tag('h1', style="color: #1774b4;")
            main_container.insert(0, h1_tag)
        h1_tag.string = final_title

        title_tag = soup.head.find('title')
        if not title_tag:
            title_tag = soup.new_tag('title')
            soup.head.append(title_tag)
        title_tag.string = f"Clubrecords {final_title} - Sparta Bornem"

        table_div = main_container.find('div', class_='table-responsive')
        if not table_div:
            table_div = soup.new_tag('div', attrs={'class': 'table-responsive'})
            h1_tag.insert_after(table_div)

        table = table_div.find('table', class_='records-table')
        if table is None:
            table = main_container.find('table', class_='records-table')
            if table is not None:
                table_div.append(table.extract())
        if not table:
            table = soup.new_tag('table', attrs={'class': 'records-table'})
            table_div.append(table)
            thead = soup.new_tag('thead')
            tr_head = soup.new_tag('tr')
            for th_text in ["Discipline", "Naam", "Prestatie", "Plaats", "Datum"]:
                th = soup.new_tag('th'); th.string = th_text; tr_head.append(th)
            thead.append(tr_head)
            table.append(thead)

        table['data-records-format'] = '2'
        tbody = table.find('tbody')
        if not tbody:
            tbody = soup.new_tag('tbody')
            table.append(tbody)
        tbody.clear()

        for record in records_data or []:
            if not isinstance(record, dict):
                raise ValueError("Records moeten afzonderlijke records met een namenlijst zijn.")
            names = record.get('names', [])
            if isinstance(names, str):
                names = records_text_lines(names)
            new_tr = soup.new_tag('tr')
            values = [[record.get('discipline', '')], list(names) or [''],
                      [record.get('performance', '')], [record.get('place', '')], [record.get('date', '')]]
            for cell_values in values:
                new_td = soup.new_tag('td')
                for index, value in enumerate(cell_values):
                    if index:
                        new_td.append(soup.new_tag('br'))
                    new_td.append(NavigableString(str(value if value is not None else "")))
                new_tr.append(new_td)
            tbody.append(new_tr)

        for old_notice in main_container.find_all('p', class_='record-notice'):
            old_notice.decompose()

        insert_after_element = table_div or h1_tag

        for msg_text in general_messages:
            if msg_text.strip():
                p_tag = soup.new_tag('p', **{'class': 'record-notice', 'style': 'font-style: italic;'})
                p_tag.string = msg_text.strip()
                insert_after_element.insert_after(p_tag)
                insert_after_element = p_tag

        if contact_prefix.strip() and contact_email.strip():
            p_tag = soup.new_tag('p', **{'class': 'record-notice'})
            p_tag.append(NavigableString(contact_prefix.strip() + " "))
            mail_link = soup.new_tag('a', href=f"mailto:{contact_email.strip()}")
            mail_link.string = contact_email.strip()
            p_tag.append(mail_link)
            insert_after_element.insert_after(p_tag)

        with atomic_text_writer(html_path) as f:
            f.write(soup.prettify(formatter="html5"))
        return True, None

    except Exception as e:
        error_msg = f"Algemene fout bij opslaan records naar {html_path}: {e}"
        traceback.print_exc()
        return False, error_msg


def kalender_load_json_data(json_filepath):
    """Loads calendar event data from a JSON file."""
    if not os.path.exists(json_filepath):
        print(f"[UTILS][KALENDER_JSON] Fout: JSON-bestand niet gevonden: {json_filepath}")
        return None, f"JSON-bestand niet gevonden: {json_filepath}"
    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                print(f"[UTILS][KALENDER_JSON] Waarschuwing: JSON-bestand is leeg: {json_filepath}")
                # Return a default structure for the GUI if the file is empty
                default_structure = {
                    "pageTitle": "Kalender - Atletiekclub Sparta Bornem",
                    "mainHeading": "Wedstrijden Kalender",
                    "legend": {"title": "Legende", "items": []},
                    "events": []
                }
                return default_structure, None
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError('Kalender JSON moet een object zijn.')
            data.setdefault("events", [])
            data.setdefault("legend", {"title": "Legende", "items": []})
            data.setdefault("displayedMonths", [])
            if not isinstance(data['events'], list) or not all(isinstance(event, dict) for event in data['events']):
                raise ValueError('Kalender events moet een lijst met objecten zijn.')
            import datetime
            for event in data['events']:
                datetime.date.fromisoformat(event.get('date', ''))
                if any(event.get(key) is not None and not isinstance(event[key], str) for key in ('name', 'color', 'title', 'data_location', 'data_category')):
                    raise ValueError('Kalenderevent velden moeten tekst bevatten.')
            if not isinstance(data['legend'], dict) or not isinstance(data['legend'].get('items', []), list):
                raise ValueError('Ongeldige kalenderlegende.')
            if not isinstance(data['displayedMonths'], list):
                raise ValueError('displayedMonths moet een lijst zijn.')
            for month in data['displayedMonths']:
                if not isinstance(month, list) or len(month) != 2 or any(type(value) is not int for value in month):
                    raise ValueError('Elke zichtbare maand moet [jaar, maand] bevatten.')
                datetime.date(month[0], month[1], 1)
            return data, None
    except json.JSONDecodeError as e:
        msg = f"Kon JSON niet decoderen uit '{json_filepath}': {e}"
        print(f"[UTILS][KALENDER_JSON] {msg}")
        traceback.print_exc()
        return None, msg
    except Exception as e:
        msg = f"Algemene fout bij laden kalender JSON data uit '{json_filepath}': {e}"
        print(f"[UTILS][KALENDER_JSON] {msg}")
        traceback.print_exc()
        return None, msg

def kalender_save_json_data(json_filepath, data_dict):
    """Saves calendar event data to a JSON file."""
    try:
        # Ensure the 'events' key exists and is a list, and sort events by date before saving
        data_dict = copy.deepcopy(data_dict)
        events_list = data_dict.get("events", [])
        if isinstance(events_list, list):
            events_list.sort(key=lambda x: x.get("date", "9999-99-99")) # Sort by date
            data_dict["events"] = events_list # Put sorted list back
        else:
            data_dict["events"] = [] # Ensure it's a list if it wasn't

        with atomic_text_writer(json_filepath) as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False)
        print(f"[UTILS][KALENDER_JSON] Data succesvol opgeslagen naar: {json_filepath}")
        return None # Success
    except Exception as e:
        msg = f"Fout bij opslaan kalender JSON data naar '{json_filepath}': {e}"
        print(f"[UTILS][KALENDER_JSON] {msg}")
        traceback.print_exc()
        return msg


def reports_parse_html(html_path):
    """Parses the reports HTML file to extract links grouped by year, newest-first within each year."""
    if not BS4_AVAILABLE: return None, "BeautifulSoup niet beschikbaar"
    import re, html, datetime, pathlib, traceback
    reports_data = {}

    def _extract_date(s):
        if not s: return None
        s = s.lower()
        months = {
            'januari':1,'jan':1,'februari':2,'feb':2,'maart':3,'mrt':3,
            'april':4,'apr':4,'mei':5,'may':5,'juni':6,'jun':6,'juli':7,'jul':7,
            'augustus':8,'aug':8,'september':9,'sep':9,'sept':9,
            'oktober':10,'okt':10,'october':10,'oct':10,
            'november':11,'nov':11,'december':12,'dec':12
        }
        m = re.search(r'(\d{4})[._/\-](\d{1,2})[._/\-](\d{1,2})', s)
        if m:
            y, mo, d = map(int, m.groups())
            try: return datetime.date(y, mo, d)
            except: pass
        m = re.search(r'(\d{1,2})[._/\-](\d{1,2})[._/\-](\d{4})', s)
        if m:
            d, mo, y = map(int, m.groups())
            try: return datetime.date(y, mo, d)
            except: pass
        m = re.search(r'(\d{1,2})\s+([a-zäëïöüé]+)\s+(\d{4})', s)
        if m:
            d, mon, y = int(m.group(1)), m.group(2), int(m.group(3))
            mo = months.get(mon, 0)
            if mo:
                try: return datetime.date(y, mo, d)
                except: pass
        m = re.search(r'\b(20\d{2})(\d{2})(\d{2})\b', s)
        if m:
            y, mo, d = map(int, m.groups())
            try: return datetime.date(y, mo, d)
            except: pass
        return None

    def _item_date(year, text, filename):
        y = int(year) if str(year).isdigit() else datetime.date.today().year
        return _extract_date(text) or _extract_date(filename) or datetime.date(y, 1, 1)

    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            try:
                soup = BeautifulSoup(f, 'lxml')
            except Exception:
                f.seek(0)
                soup = BeautifulSoup(f, 'html.parser')

        reports_section = soup.find('div', id='reports-section')
        if not reports_section:
            return None, "Kon '<div id=\"reports-section\">' niet vinden."

        current_year = None
        for element in reports_section.children:
            if not isinstance(element, Tag):
                continue
            if element.name == 'h2':
                year_match = re.search(r'(\d{4})', element.get_text())
                current_year = year_match.group(1) if year_match else None
                if current_year:
                    reports_data.setdefault(current_year, [])
            elif element.name == 'ul' and 'report-list' in element.get('class', []) and current_year:
                for li in element.find_all('li', recursive=False):
                    a_tag = li.find('a', recursive=False)
                    if a_tag and a_tag.get('href'):
                        report_text = html.unescape(a_tag.get_text(strip=True)) or ''
                        report_path = html.unescape(a_tag.get('href')) or ''
                        report_filename = pathlib.PurePosixPath(report_path).name if report_path else ''
                        if report_text and report_path and report_filename:
                            reports_data[current_year].append({
                                'text': report_text,
                                'filename': report_filename,
                                'path': report_path
                            })

        for y, items in reports_data.items():
            items.sort(key=lambda it: _item_date(y, it.get('text',''), it.get('filename','')), reverse=True)

        return dict(sorted(reports_data.items(), key=lambda item: int(item[0]), reverse=True)), None
    except FileNotFoundError:
        return None, f"Bestand niet gevonden: {html_path}"
    except Exception as e:
        traceback.print_exc()
        return None, f"Fout bij parsen verslagen {html_path}: {e}"


def reports_save_html(html_path, reports_data):
    """Saves the reports data back into the HTML file structure, newest-first within each year."""
    if not BS4_AVAILABLE: return False, "BeautifulSoup niet beschikbaar"
    import re, datetime, traceback
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            try:
                soup = BeautifulSoup(f, 'lxml')
            except Exception:
                f.seek(0)
                soup = BeautifulSoup(f, 'html.parser')

        def _extract_date(s):
            if not s: return None
            s = s.lower()
            months = {
                'januari':1,'jan':1,'februari':2,'feb':2,'maart':3,'mrt':3,
                'april':4,'apr':4,'mei':5,'may':5,'juni':6,'jun':6,'juli':7,'jul':7,
                'augustus':8,'aug':8,'september':9,'sep':9,'sept':9,
                'oktober':10,'okt':10,'october':10,'oct':10,
                'november':11,'nov':11,'december':12,'dec':12
            }
            m = re.search(r'(\d{4})[._/\-](\d{1,2})[._/\-](\d{1,2})', s)
            if m:
                y, mo, d = map(int, m.groups())
                try: return datetime.date(y, mo, d)
                except: pass
            m = re.search(r'(\d{1,2})[._/\-](\d{1,2})[._/\-](\d{4})', s)
            if m:
                d, mo, y = map(int, m.groups())
                try: return datetime.date(y, mo, d)
                except: pass
            m = re.search(r'(\d{1,2})\s+([a-zäëïöüé]+)\s+(\d{4})', s)
            if m:
                d, mon, y = int(m.group(1)), m.group(2), int(m.group(3))
                mo = months.get(mon, 0)
                if mo:
                    try: return datetime.date(y, mo, d)
                    except: pass
            m = re.search(r'\b(20\d{2})(\d{2})(\d{2})\b', s)
            if m:
                y, mo, d = map(int, m.groups())
                try: return datetime.date(y, mo, d)
                except: pass
            return None

        def _item_date(year, text, filename):
            y = int(year) if str(year).isdigit() else datetime.date.today().year
            return _extract_date(text) or _extract_date(filename) or datetime.date(y, 1, 1)

        reports_section = soup.find('div', id='reports-section')
        if not reports_section:
            return False, "Kan '<div id=\"reports-section\">' niet vinden."

        reports_section.clear()
        reports_section.append("\n")

        for year in sorted(reports_data.keys(), key=int, reverse=True):
            year_reports = list(reports_data.get(year, []))
            if not year_reports:
                continue

            year_reports.sort(key=lambda x: _item_date(year, x.get('text',''), x.get('filename','')), reverse=True)

            h2_tag = soup.new_tag('h2')
            h2_tag.string = f"Verslagen {year}"
            reports_section.append(h2_tag)
            reports_section.append("\n")

            ul_tag = soup.new_tag('ul', attrs={'class': 'report-list'})
            ul_tag.append("\n  ")
            reports_section.append(ul_tag)
            reports_section.append("\n")

            for report in year_reports:
                li_tag = soup.new_tag('li')
                a_tag = soup.new_tag('a', href=report['path'], target='_blank')
                a_tag.string = report['text']
                li_tag.append(a_tag)
                ul_tag.append(li_tag)
                ul_tag.append("\n  ")

            if ul_tag.contents and isinstance(ul_tag.contents[-1], NavigableString) and not ul_tag.contents[-1].strip():
                ul_tag.contents.pop()
            ul_tag.append("\n")

        with atomic_text_writer(html_path) as f:
            f.write(soup.prettify(formatter="html5"))
        return True, None
    except FileNotFoundError:
        return False, f"Bestand niet gevonden voor opslaan: {html_path}"
    except Exception as e:
        traceback.print_exc()
        return False, f"Fout bij opslaan verslagen naar {html_path}: {e}"


def downloads_parse_html(html_path):
    if not BS4_AVAILABLE: return None, "BeautifulSoup niet beschikbaar"
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            try: soup = BeautifulSoup(f, 'lxml')
            except Exception: f.seek(0); soup = BeautifulSoup(f, 'html.parser')

        ul = soup.find('ul', id='downloads-list')
        if not ul:
            return None, "Kon downloads lijst met id 'downloads-list' niet vinden."

        items = []
        for li in ul.find_all('li', recursive=False):
            a = li.find('a', recursive=False)
            if a and a.get('href'):
                text_raw = a.get_text(strip=True)
                path_raw = a.get('href')
                text = html.unescape(text_raw) if text_raw else ''
                path = html.unescape(path_raw) if path_raw else ''
                filename = pathlib.PurePosixPath(path).name if path else ''
                if text and path and filename:
                    items.append({'text': text, 'filename': filename, 'path': path})

        return items, None
    except FileNotFoundError:
        return None, f"Bestand niet gevonden: {html_path}"
    except Exception as e:
        traceback.print_exc()
        return None, f"Fout bij parsen downloads {html_path}: {e}"

def downloads_save_html(html_path, downloads_data):
    if not BS4_AVAILABLE: return False, "BeautifulSoup niet beschikbaar"
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            try: soup = BeautifulSoup(f, 'lxml')
            except Exception: f.seek(0); soup = BeautifulSoup(f, 'html.parser')

        ul = soup.find('ul', id='downloads-list')
        if not ul:
            main = soup.find('main')
            if not main:
                main = soup.new_tag('main', attrs={'class': 'main-content container'})
                soup.body.append(main)
            ul = soup.new_tag('ul', id='downloads-list')
            main.append(ul)

        ul.clear()
        ul.append("\n")
        for item in downloads_data:
            li = soup.new_tag('li', attrs={'class': 'download-link'})
            a = soup.new_tag('a', href=item['path'], target='_blank', rel='noopener noreferrer')
            a.string = item['text']
            li.append(a)
            ul.append(li)
            ul.append("\n")

        with atomic_text_writer(html_path) as f:
            f.write(soup.prettify(formatter="html5"))
        return True, None
    except FileNotFoundError:
        return False, f"Bestand niet gevonden voor opslaan: {html_path}"
    except Exception as e:
        traceback.print_exc()
        return False, f"Fout bij opslaan downloads naar {html_path}: {e}"



def _validate_people_data(data, fields):
    if not isinstance(data, dict):
        raise ValueError('Persoonsgegevens moeten een JSON-object zijn.')
    for field in fields:
        entries = data.get(field, [])
        if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
            raise ValueError(f'{field} moet een lijst met objecten zijn.')
        identity_key = {'trainingTimes': 'category', 'contacts': 'role', 'trainerGroups': 'groupName'}.get(field)
        seen = set()
        for entry in entries:
            if identity_key:
                identity = entry.get(identity_key)
                if not isinstance(identity, str) or not identity.strip() or identity in seen:
                    raise ValueError(f'{field} bevat een ontbrekende of dubbele {identity_key}.')
                seen.add(identity)
            for key in ('name', 'role', 'email', 'phone', 'image', 'imageSrc', 'imageAlt', 'description', 'address'):
                if key in entry and entry[key] is not None and not isinstance(entry[key], str):
                    raise ValueError(f'{field}.{key} moet tekst bevatten.')
            child_field = {'trainingTimes': 'schedule', 'trainerGroups': 'trainers'}.get(field)
            if child_field:
                children = entry.get(child_field, [])
                if not isinstance(children, list) or not all(isinstance(child, dict) for child in children):
                    raise ValueError(f'{field}.{child_field} moet een lijst met objecten zijn.')
                required = ('day', 'time') if child_field == 'schedule' else ('name',)
                for child in children:
                    if any(not isinstance(child.get(key), str) for key in required):
                        raise ValueError(f'Ongeldige invoer in {field}.{child_field}.')
            if field == 'trainerGroups':
                if not isinstance(entry.get('mainPhoto', {}), dict) or not isinstance(entry.get('thumbnails', []), list):
                    raise ValueError('Ongeldige afbeeldingen in trainergroep.')
                if not all(isinstance(image, dict) and isinstance(image.get('src'), str) for image in entry.get('thumbnails', [])):
                    raise ValueError('Ongeldige miniaturen in trainergroep.')
    for key in ('times_category_order', 'trainer_category_order'):
        if key in data and (not isinstance(data[key], list) or not all(isinstance(value, str) for value in data[key])):
            raise ValueError(f'{key} moet een lijst met categorieën zijn.')


def trainers_load_json_data(json_filepath):
    if not os.path.exists(json_filepath):
        print(f"[UTILS][TRAINERS_JSON] Fout: JSON-bestand niet gevonden: {json_filepath}")
        return None, f"JSON-bestand niet gevonden: {json_filepath}"
    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                print(f"[UTILS][TRAINERS_JSON] Waarschuwing: JSON-bestand is leeg: {json_filepath}")
                return {}, None
            data = json.loads(content)
            _validate_people_data(data, ('trainingTimes', 'contacts', 'trainerGroups'))
            return data, None
    except json.JSONDecodeError as e:
        msg = f"Kon JSON niet decoderen uit '{json_filepath}': {e}"
        print(f"[UTILS][TRAINERS_JSON] {msg}")
        traceback.print_exc()
        return None, msg
    except Exception as e:
        msg = f"Algemene fout bij laden trainers JSON data uit '{json_filepath}': {e}"
        print(f"[UTILS][TRAINERS_JSON] {msg}")
        traceback.print_exc()
        return None, msg

def strip_html(html_string):
    if not BS4_AVAILABLE:
        print("[UTILS][WARN] BeautifulSoup niet beschikbaar, kan HTML niet strippen. Originele string wordt geretourneerd.")
        return html_string if html_string else ""
    if not html_string:
        return ""
    try:
        soup = BeautifulSoup(str(html_string), "html.parser")
        return soup.get_text()
    except Exception as e:
        print(f"[UTILS][ERROR] Fout bij strippen van HTML: {e}")
        return str(html_string)

def trainers_save_json_data(json_filepath, data_dict):
    try:
        with atomic_text_writer(json_filepath) as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False)
        print(f"[UTILS][TRAINERS_JSON] Data succesvol opgeslagen naar: {json_filepath}")
        return None
    except Exception as e:
        msg = f"Fout bij opslaan trainers JSON data naar '{json_filepath}': {e}"
        print(f"[UTILS][TRAINERS_JSON] {msg}")
        traceback.print_exc()
        return msg

def get_abs_path(rel_path):
    return resolve_site_path(rel_path)

def sponsors_parse_html(html_path):
    """Parses a sponsor HTML file to extract sponsor data."""
    if not BS4_AVAILABLE: return None, "BeautifulSoup niet beschikbaar"
    sponsors_list = []
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            try: soup = BeautifulSoup(f, 'lxml')
            except Exception: f.seek(0); soup = BeautifulSoup(f, 'html.parser')

        grid = soup.find('div', class_='sponsor-grid')
        if not grid:
            print(f"[UTILS][SPONSOR] Geen <div class=\"sponsor-grid\"> gevonden in {html_path}")
            return [], None

        for item in grid.find_all('div', class_='sponsor-item', recursive=False):
            img_tag = item.find('img')
            if not img_tag: continue

            # *** MODIFIED for unescape ***
            img_src_raw = img_tag.get('src', '').strip()
            img_alt_raw = img_tag.get('alt', '').strip()
            link_href_raw = None

            link_tag = img_tag.find_parent('a')
            if link_tag and link_tag.get('href'):
                 href_raw = link_tag['href'].strip()
                 if href_raw and href_raw != '#' and not href_raw.lower().startswith('javascript:'):
                      link_href_raw = href_raw

            # Unescape data
            img_src = html.unescape(img_src_raw) if img_src_raw else ''
            img_alt = html.unescape(img_alt_raw) if img_alt_raw else ''
            link_href = html.unescape(link_href_raw) if link_href_raw else None

            if img_src: # Check unescaped src
                sponsors_list.append({
                    'img_src': img_src,
                    'alt': img_alt,
                    'link_href': link_href,
                    '_source_html': str(item)
                })

        return sponsors_list, None
    except FileNotFoundError:
        return None, f"Bestand niet gevonden: {html_path}"
    except Exception as e:
        msg = f"Fout bij parsen sponsor HTML ({type(e).__name__}): {e}"
        traceback.print_exc()
        return None, msg

def sponsors_render_html(html_path, sponsors_list):
    if not BS4_AVAILABLE:
        raise ValueError('BeautifulSoup niet beschikbaar')
    with open(html_path, 'r', encoding='utf-8') as f:
         try: soup = BeautifulSoup(f, 'lxml')
         except Exception: f.seek(0); soup = BeautifulSoup(f, 'html.parser')

    grid = soup.find('div', class_='sponsor-grid')
    if not grid:
        msg = f"Kan <div class=\"sponsor-grid\"> niet vinden in {html_path}."
        raise ValueError(msg)

    original_items = grid.find_all('div', class_='sponsor-item', recursive=False)
    anchor = Comment('editor sponsor insertion')
    if original_items:
        original_items[0].insert_before(anchor)
    else:
        grid.append(anchor)
    for original in original_items:
        original.extract()

    for sponsor in sponsors_list:
        if not sponsor.get('img_src'):
            continue
        source = sponsor.get('_source_html')
        item_div = BeautifulSoup(source, 'html.parser').find('div', class_='sponsor-item') if source else None
        if item_div is None:
            item_div = soup.new_tag('div', attrs={'class': 'sponsor-item'})
            item_div.append(soup.new_tag('img'))
        img_tag = item_div.find('img')
        img_tag['src'] = sponsor['img_src']
        img_tag['alt'] = sponsor.get('alt', 'Sponsor Logo')
        link = img_tag.find_parent('a')
        href = sponsor.get('link_href')
        if href:
            if link is None:
                link = soup.new_tag('a', target='_blank', rel='noopener noreferrer')
                (img_tag.find_parent('picture') or img_tag).wrap(link)
            link['href'] = href
        elif link is not None:
            link.attrs.pop('href', None)
        anchor.insert_before(item_div)
    anchor.extract()

    return soup.prettify(formatter="html5").encode('utf-8')


def sponsors_save_html(html_path, sponsors_list):
    try:
        atomic_write_bytes(html_path, sponsors_render_html(html_path, sponsors_list))
        return True, None
    except (OSError, ValueError) as error:
        return False, f'Kon sponsorbestand niet opslaan: {error}'

def jury_load_json_data(json_filepath):
    if not os.path.exists(json_filepath):
        return None, f"JSON-bestand niet gevonden: {json_filepath}"
    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                default_structure = {
                    "pageTitle": "Juryleden - Atletiekclub Sparta Bornem",
                    "mainHeading": "Juryleden",
                    "juryMembers": []
                }
                return default_structure, None
            data = json.loads(content)
            _validate_people_data(data, ('juryMembers',))
            return data, None
    except json.JSONDecodeError as e:
        msg = f"Kon JSON niet decoderen uit '{json_filepath}': {e}"
        traceback.print_exc()
        return None, msg
    except Exception as e:
        msg = f"Algemene fout bij laden jury JSON data uit '{json_filepath}': {e}"
        traceback.print_exc()
        return None, msg

def jury_save_json_data(json_filepath, data_dict):
    try:
        target_dir = os.path.dirname(json_filepath)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        with atomic_text_writer(json_filepath) as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False)
        return None
    except Exception as e:
        msg = f"Fout bij opslaan jury JSON data naar '{json_filepath}': {e}"
        traceback.print_exc()
        return msg

def bestuur_load_json_data(json_filepath):
    """Loads board members (bestuur) data from a JSON file."""
    if not os.path.exists(json_filepath):
        print(f"[UTILS][BESTUUR_JSON] Fout: JSON-bestand niet gevonden: {json_filepath}")
        # Return a default structure or None, and an error message
        # The GUI tab will need to handle the case where data is None or empty.
        return None, f"JSON-bestand niet gevonden: {json_filepath}"
    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                print(f"[UTILS][BESTUUR_JSON] Waarschuwing: JSON-bestand is leeg: {json_filepath}")
                # Return a default structure for the GUI to initialize with if the file is empty
                default_structure = {
                    "pageTitle": "Bestuur - Atletiekclub Sparta Bornem", # Default values
                    "mainHeading": "Bestuur",
                    "boardMembers": []
                }
                return default_structure, None # Or just {}, None if GUI handles full default
            data = json.loads(content)
            _validate_people_data(data, ('boardMembers',))
            return data, None
    except json.JSONDecodeError as e:
        msg = f"Kon JSON niet decoderen uit '{json_filepath}': {e}"
        print(f"[UTILS][BESTUUR_JSON] {msg}")
        traceback.print_exc()
        return None, msg
    except Exception as e:
        msg = f"Algemene fout bij laden bestuur JSON data uit '{json_filepath}': {e}"
        print(f"[UTILS][BESTUUR_JSON] {msg}")
        traceback.print_exc()
        return None, msg

def bestuur_save_json_data(json_filepath, data_dict):
    """Saves board members (bestuur) data to a JSON file."""
    try:
        # Ensure the directory exists
        target_dir = os.path.dirname(json_filepath)
        if target_dir: # Check if dirname returned something (it might be empty if saving to current dir)
            os.makedirs(target_dir, exist_ok=True)

        with atomic_text_writer(json_filepath) as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False) # indent for readability
        print(f"[UTILS][BESTUUR_JSON] Data succesvol opgeslagen naar: {json_filepath}")
        return None # Indicates success (no error message)
    except Exception as e:
        msg = f"Fout bij opslaan bestuur JSON data naar '{json_filepath}': {e}"
        print(f"[UTILS][BESTUUR_JSON] {msg}")
        traceback.print_exc()
        return msg # Return the error message


def ages_parse_html(html_path):
    if not BS4_AVAILABLE: return None, None, "BeautifulSoup niet beschikbaar"
    import html as _html
    age_categories = []
    top_text = ""
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            try:
                soup = BeautifulSoup(f, 'lxml')
            except Exception:
                f.seek(0)
                soup = BeautifulSoup(f, 'html.parser')

        age_table = soup.find('table', class_='age-table')
        if age_table:
            para_before = age_table.find_previous_sibling('p')
            if para_before:
                raw_text = para_before.get_text(" ", strip=True)
                top_text = _html.unescape(raw_text)

        tbody = age_table.find('tbody') if age_table else None
        if not tbody:
            return [], top_text, None

        for row in tbody.find_all('tr', recursive=False):
            cells = row.find_all('td', recursive=False)
            if len(cells) == 2:
                category_raw = cells[0].get_text(strip=True)
                years_raw = cells[1].get_text(strip=True)
                category = _html.unescape(category_raw)
                years = _html.unescape(years_raw)
                if category and years:
                    age_categories.append({'category': category, 'years': years})

        return age_categories, top_text, None

    except FileNotFoundError:
        return None, None, f"Bestand niet gevonden: {html_path}"
    except Exception as e:
        msg = f"Fout bij parsen leeftijden HTML ({type(e).__name__}): {e}"
        traceback.print_exc()
        return None, None, msg



def ages_save_html(html_path, age_categories_list, top_text):
    if not BS4_AVAILABLE: return False, "BeautifulSoup niet beschikbaar"
    import re
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            try:
                soup = BeautifulSoup(f, 'lxml')
            except Exception:
                f.seek(0)
                soup = BeautifulSoup(f, 'html.parser')

        age_table = soup.find('table', class_='age-table')
        para_updated = False
        if age_table:
            para_before = age_table.find_previous_sibling('p')
            if para_before:
                if html.unescape(para_before.get_text(" ", strip=True)) != top_text:
                    existing_strong = para_before.find('strong')
                    strong_text = existing_strong.get_text(strip=True) if existing_strong else None
                    para_before.clear()

                    chosen_strong = None
                    if strong_text and strong_text in top_text:
                        chosen_strong = strong_text
                    else:
                        m = re.search(r'\b(20\d{2}\s*-\s*20\d{2})\b', top_text)
                        if m:
                            chosen_strong = m.group(1)

                    if chosen_strong and chosen_strong in top_text:
                        pre, _, post = top_text.partition(chosen_strong)
                        if pre:
                            para_before.append(NavigableString(pre))
                        s = soup.new_tag('strong')
                        s.string = chosen_strong
                        para_before.append(s)
                        if post:
                            para_before.append(NavigableString(post))
                    else:
                        para_before.append(NavigableString(top_text))

                para_updated = True

        if not para_updated:
            return False, f"Kon paragraaf boven de tabel niet vinden of bijwerken in {html_path}."

        tbody = age_table.find('tbody') if age_table else None
        if not tbody:
            return False, f"Kan <tbody> niet vinden in class 'age-table' in {html_path}."

        tbody.clear()
        tbody.append("\n                ")

        for item in age_categories_list:
            category = item.get('category')
            years = item.get('years')
            if not category or not years:
                continue
            tr = soup.new_tag('tr')
            tr.append("\n                    ")
            td_cat = soup.new_tag('td')
            td_cat.string = category
            tr.append(td_cat)
            tr.append("\n                    ")
            td_years = soup.new_tag('td')
            td_years.string = years
            tr.append(td_years)
            tr.append("\n                ")
            tbody.append(tr)
            tbody.append("\n                ")

        if tbody.contents and isinstance(tbody.contents[-1], NavigableString) and not tbody.contents[-1].strip():
            tbody.contents.pop()
        tbody.append("\n            ")

        with atomic_text_writer(html_path) as f:
            f.write(str(soup))
        return True, None

    except FileNotFoundError:
        return False, f"Bestand niet gevonden: {html_path}"
    except Exception as e:
        msg = f"Fout bij opslaan leeftijden HTML ({type(e).__name__}): {e}"
        traceback.print_exc()
        return False, msg



def general_html_find_files(targets_abs):
    html_files = set()

    excluded_folders = [
        '/clubrecords/',
        '/nieuws/',
        '/downloads/',
    ]

    excluded_files = {
        '(Nieuwe) leden/leeftijden.html',
        'wedstrijden/kalender.html',
        'info/sponsors.html',
        'info/bestuur.html',
        'info/juryleden.html',
        'info/trainers.html',
        'info/grotesponsors.html',
        'info/hoofdsponsors.html',
    }

    for target_path in targets_abs:
        if not os.path.exists(target_path):
            continue

        if os.path.isfile(target_path):
            if target_path.lower().endswith(('.html', '.htm')):
                # Normalize path for consistent checking
                normalized_path = target_path.replace('\\', '/')

                # Apply exclusion checks
                is_excluded = False
                if any(folder in normalized_path for folder in excluded_folders):
                    is_excluded = True
                if not is_excluded and any(normalized_path.endswith(ef) for ef in excluded_files):
                    is_excluded = True

                if not is_excluded:
                    html_files.add(target_path)

        elif os.path.isdir(target_path):
            for root, _, files in os.walk(target_path):
                for filename in files:
                    if filename.lower().endswith(('.html', '.htm')):
                        full_path = os.path.join(root, filename)

                        # Normalize path for consistent checking
                        normalized_path = full_path.replace('\\', '/')

                        is_excluded = False
                        if any(folder in normalized_path for folder in excluded_folders):
                            is_excluded = True
                        if not is_excluded and any(normalized_path.endswith(ef) for ef in excluded_files):
                            is_excluded = True

                        if not is_excluded:
                            html_files.add(full_path)

    return sorted(list(html_files)), len(html_files)

def _is_excluded_or_processed(element, processed_element_ids, excluded_tags):
    if id(element) in processed_element_ids: return True
    current = element
    while current:
        if id(current) in processed_element_ids: return True
        if isinstance(current, Tag) and current.name in excluded_tags: return True
        current = getattr(current, 'parent', None)
        if isinstance(current, BeautifulSoup): break
    return False

def text_editor_parse_file(file_path, parsed_soups_dict, found_items_list):

    items_in_file = 0
    initial_items_count = len(found_items_list)
    processed_element_ids = set()
    excluded_tags = set(config.TEXT_EDITOR_EXCLUDED_TAGS)

    try:
        # Use cached soup if available, otherwise parse the file
        if file_path in parsed_soups_dict:
            soup = parsed_soups_dict[file_path]
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            try:
                soup = BeautifulSoup(content, 'lxml')
            except Exception:
                try:
                    soup = BeautifulSoup(content, 'html.parser')
                except Exception as parse_err:
                    print(f"[UTILS][TEXT/LINK/BOLD] Kon {file_path} niet parsen: {parse_err}")
                    return 0
            parsed_soups_dict[file_path] = soup

        if soup is None: # If a previous parse attempt failed
            return 0

        for strong_tag in soup.find_all('strong'):
            if _is_excluded_or_processed(strong_tag, processed_element_ids, excluded_tags):
                continue

            # .get_text() automatically unescapes HTML entities and gets all text from children.
            original_text = strong_tag.get_text(strip=True)
            if not original_text:
                continue

            display_text_snippet = original_text.replace('\n', ' ')
            display_text = f"[Vet] {display_text_snippet[:90]}..." if len(display_text_snippet) > 90 else f"[Vet] {display_text_snippet}"

            iid = initial_items_count + items_in_file
            found_items_list.append({
                'file_path': file_path,
                'dom_reference': strong_tag,
                'type': 'bold',
                'original_text': original_text, # This is clean, unescaped text
                'original_href': None,
                'display_text': display_text,
                'iid': iid
            })
            items_in_file += 1
            # Mark this tag and all its children as processed to avoid re-processing them later.
            processed_element_ids.add(id(strong_tag))
            for descendant in strong_tag.descendants:
                processed_element_ids.add(id(descendant))

        # --- Pass 2: Find all <a> tags with an href attribute ---
        for link_tag in soup.find_all('a', href=True):
            if _is_excluded_or_processed(link_tag, processed_element_ids, excluded_tags):
                continue

            href_raw = link_tag.get('href', '')
            if not href_raw or href_raw.strip().lower().startswith('javascript:'):
                continue

            # Get clean, unescaped text content from the link.
            original_text = link_tag.get_text(strip=True)
            # Manually unescape the href attribute value.
            original_href = html.unescape(href_raw.strip())

            display_text_part = original_text if original_text else "[Link Zonder Tekst]"
            display_text_part = (display_text_part[:60] + '...') if len(display_text_part) > 60 else display_text_part
            display_href_part = f" ({original_href[:40]}{'...' if len(original_href) > 40 else ''})"
            display_text = f"{display_text_part}{display_href_part}".replace('\n', ' ').replace('\r', '')

            iid = initial_items_count + items_in_file
            found_items_list.append({
                'file_path': file_path,
                'dom_reference': link_tag,
                'type': 'link',
                'original_text': original_text,   # Clean, unescaped text
                'original_href': original_href,   # Clean, unescaped href
                'display_text': display_text,
                'iid': iid
            })
            items_in_file += 1
            # Mark this tag and its children as processed.
            processed_element_ids.add(id(link_tag))
            for descendant in link_tag.descendants:
                processed_element_ids.add(id(descendant))

        # --- Pass 3: Find remaining, unprocessed plain text nodes (NavigableString) ---
        for text_node in soup.find_all(string=True):
            # Skip comments, already processed nodes, or nodes inside excluded tags.
            if isinstance(text_node, Comment) or _is_excluded_or_processed(text_node, processed_element_ids, excluded_tags):
                continue

            # Get the raw text, which may contain HTML entities.
            raw_node_text = str(text_node)
            if not raw_node_text.strip():
                continue

            # Unescape the raw text to get a clean version for editing.
            original_text = html.unescape(raw_node_text)
            stripped_text = original_text.strip()

            # Final check to ensure there's actual content after unescaping.
            if not stripped_text:
                continue

            display_text = (stripped_text[:100] + '...') if len(stripped_text) > 100 else stripped_text
            display_text = display_text.replace('\n', ' ').replace('\r', '')

            iid = initial_items_count + items_in_file
            found_items_list.append({
                'file_path': file_path,
                'dom_reference': text_node,
                'type': 'text',
                'original_text': original_text, # The full, unescaped text, preserving whitespace
                'original_href': None,
                'display_text': display_text,
                'iid': iid
            })
            items_in_file += 1
            # Mark this text node as processed.
            processed_element_ids.add(id(text_node))

        return items_in_file

    except FileNotFoundError:
        print(f"[UTILS][TEXT/LINK/BOLD] Bestand niet gevonden: {file_path}")
        return 0
    except Exception as e:
        print(f"[UTILS][TEXT/LINK/BOLD] Fout bij verwerken {file_path}: {e}")
        traceback.print_exc()
        return 0

def images_parse_file(file_path, parsed_soups_dict, found_images_list):
    if not BS4_AVAILABLE: return 0
    images_in_file = 0; total_images_so_far = len(found_images_list)
    try:
        with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
        try: soup = BeautifulSoup(content, 'lxml')
        except Exception:
            try: soup = BeautifulSoup(content, 'html.parser')
            except Exception as parse_err: print(f"[UTILS][IMG] Kon {file_path} niet parsen: {parse_err}"); return 0
        parsed_soups_dict[file_path] = soup

        for img_tag in soup.find_all('img', src=True):
            src_raw = img_tag['src'].strip()
            src_attr = html.unescape(src_raw) if src_raw else ''

            if not src_attr or src_attr.startswith(('data:', 'http:', 'https:')): continue
            iid = total_images_so_far + images_in_file
            img_abs_path = "Error Resolving Path"; exists = False
            try:
                img_abs_path = resolve_site_path(src_attr, source_file=file_path)
                exists = os.path.isfile(img_abs_path)
            except Exception as path_err: print(f"[UTILS][IMG] Fout bij oplossen pad '{src_attr}' in {file_path}: {path_err}")

            found_images_list.append({'html_file': file_path, 'src': src_attr, 'dom_reference': img_tag, 'abs_path': img_abs_path, 'exists': exists, 'iid': iid})
            images_in_file += 1
        return images_in_file
    except FileNotFoundError: return 0
    except Exception as e: print(f"[UTILS][IMG] Fout bij verwerken {file_path}: {e}"); traceback.print_exc(); return 0

def pdfs_parse_file(base_dir):
    found_pdfs_list = []
    scan_path = os.path.join(base_dir, 'docs')

    if not os.path.isdir(scan_path):
        print(f"[UTILS][PDF] Scan directory not found: {scan_path}")
        return found_pdfs_list

    for root, _, files in os.walk(scan_path):
        for filename in files:
            if filename.lower().endswith('.pdf'):
                abs_path = os.path.normpath(os.path.join(root, filename))
                found_pdfs_list.append({
                    'abs_path': abs_path,
                    'exists': True,
                    'iid': abs_path
                })
    return found_pdfs_list

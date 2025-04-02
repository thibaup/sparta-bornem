import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import scrolledtext
from tkinter import filedialog
import tkinter.simpledialog # Added for commit message

import os
import sys
import re
import datetime
import json
import shutil
import pathlib # For safer path manipulation, especially relative paths
import subprocess # <-- IMPORT SUBPROCESS
from collections import defaultdict # For image usage count

# --- Library Checks ---
try:
    # Test essential components used
    from bs4 import BeautifulSoup, Tag, NavigableString, Comment
    print("[INFO] BeautifulSoup4 library found.")
except ImportError:
    print("\n[FATAL ERROR] BeautifulSoup4 library not found (needed for most functions).")
    print("Please install it using: pip install beautifulsoup4")
    # Show error immediately and exit if BS4 is missing
    try:
        root_err = tk.Tk(); root_err.withdraw()
        messagebox.showerror("Fatal Error - Missing Library", "Required library 'BeautifulSoup4' not found.\nCannot start application.\nPlease install using:\npip install beautifulsoup4", parent=None)
        root_err.destroy()
    except Exception: pass
    sys.exit(1)
    # Keep linters happy if exit doesn't happen immediately
    BeautifulSoup = None; Tag = None; NavigableString = None; Comment = None


try:
    from PIL import Image, ImageTk
    print("[INFO] Pillow (PIL) library found (Recommended for image previews).")
    HAS_PILLOW = True
except ImportError:
    print("\n[WARNING] Pillow (PIL) library not found.")
    print("Image previews will be limited to GIF/PGM/PPM formats.")
    print("Install using: pip install Pillow")
    HAS_PILLOW = False
    Image = None; ImageTk = None

# --- Determine Application Base Directory ---
if getattr(sys, 'frozen', False):
    APP_BASE_DIR = os.path.dirname(sys.executable)
    print(f"[INFO] Running from frozen executable. Base directory: {APP_BASE_DIR}")
elif __file__:
    APP_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    print(f"[INFO] Running from Python script. Base directory: {APP_BASE_DIR}")
else:
    APP_BASE_DIR = os.getcwd()
    print(f"[WARNING] Could not determine script path reliably. Using current working directory: {APP_BASE_DIR}")

# --- Configuration (Using APP_BASE_DIR for data) ---
try:
    print(f"\n[CONFIG] Using Application Base Directory for paths: {APP_BASE_DIR}")

    # News Config
    NEWS_JSON_RELATIVE_PATH = os.path.join('html', 'nieuws', 'nieuws-data.json')
    NEWS_JSON_FILE_PATH = os.path.join(APP_BASE_DIR, NEWS_JSON_RELATIVE_PATH)
    NEWS_IMAGE_DEST_DIR_RELATIVE = os.path.join('images', 'nieuws')
    NEWS_IMAGE_DEST_DIR_ABSOLUTE = os.path.join(APP_BASE_DIR, NEWS_IMAGE_DEST_DIR_RELATIVE)
    NEWS_DEFAULT_CATEGORY = "Algemeen"
    NEWS_DEFAULT_IMAGE = "nieuws-beeld.png"
    print(f"[CONFIG] News JSON path: {NEWS_JSON_FILE_PATH}")
    print(f"[CONFIG] News Image Dest path: {NEWS_IMAGE_DEST_DIR_ABSOLUTE}")

    # Records Config
    RECORDS_BASE_DIR_RELATIVE = os.path.join('html', 'clubrecords')
    RECORDS_BASE_DIR_ABSOLUTE = os.path.join(APP_BASE_DIR, RECORDS_BASE_DIR_RELATIVE)
    print(f"[CONFIG] Records Base path: {RECORDS_BASE_DIR_ABSOLUTE}")

    # Calendar Config
    CALENDAR_HTML_RELATIVE_PATH = os.path.join('html', 'wedstrijden', 'kalender.html')
    CALENDAR_HTML_FILE_PATH = os.path.join(APP_BASE_DIR, CALENDAR_HTML_RELATIVE_PATH)
    CALENDAR_EVENT_COLORS = ["green", "blue", "red", "black"]
    DUTCH_MONTH_MAP = {
        'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
        'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12
    }
    print(f"[CONFIG] Calendar HTML path: {CALENDAR_HTML_FILE_PATH}")

    # Reports Config
    REPORTS_HTML_RELATIVE_PATH = os.path.join('html', 'downloads', 'bestuursverslagen.html')
    REPORTS_HTML_FILE_PATH = os.path.join(APP_BASE_DIR, REPORTS_HTML_RELATIVE_PATH)
    REPORTS_DOCS_HREF_DIR_RELATIVE = '/docs/bestuursvergadering' # Keep as URL path
    REPORTS_DOCS_DEST_DIR_ABSOLUTE = os.path.join(APP_BASE_DIR, 'docs', 'bestuursvergadering') # Filesystem path
    print(f"[CONFIG] Reports HTML path: {REPORTS_HTML_FILE_PATH}")
    print(f"[CONFIG] Reports Docs Dest path (absolute): {REPORTS_DOCS_DEST_DIR_ABSOLUTE}")
    print(f"[CONFIG] Reports Docs Href path (relative): {REPORTS_DOCS_HREF_DIR_RELATIVE}")

    # --- HTML File Discovery Config (Used by Text & Image Tabs) ---
    HTML_SCAN_TARGET_PATHS_RELATIVE = [
        'index.html',
        # Add folders containing HTML files you want scanned for text/images
        os.path.join('html'),
        # Add specific files if needed
        # os.path.join('another_folder', 'specific_page.html')
    ]
    HTML_SCAN_TARGET_PATHS_ABSOLUTE = [os.path.join(APP_BASE_DIR, p) for p in HTML_SCAN_TARGET_PATHS_RELATIVE]
    print(f"[CONFIG] HTML Scan Target Paths (absolute): {HTML_SCAN_TARGET_PATHS_ABSOLUTE}")

    # --- Text Editor Config ---
    TEXT_EDITOR_EXCLUDED_TAGS = ['script', 'style'] # Tags whose text content should be ignored
    print(f"[CONFIG] Text Editor Excluded Tags: {TEXT_EDITOR_EXCLUDED_TAGS}")

    # --- Image Management Config ---
    IMAGE_PREVIEW_MAX_WIDTH = 300
    IMAGE_PREVIEW_MAX_HEIGHT = 250
    # Common locations where images might be stored or added
    IMAGE_COMMON_DIRS_RELATIVE = [
        'images',
        os.path.join('images', 'nieuws'),
        os.path.join('images', 'pagina'),
        os.path.join('images', 'sponsors'),
        os.path.join('images', 'personen'),
        os.path.join('images', 'sponsers', "grote sponsers"),
        os.path.join('images', 'sponsers', "hoofdsponsers"),
        os.path.join('images', 'sponsers', "sponsers"),
    ]
    IMAGE_COMMON_DIRS_ABSOLUTE = {
        # Use relative path as key for display, absolute as value
        str(pathlib.Path(p).as_posix()): os.path.join(APP_BASE_DIR, p)
        for p in IMAGE_COMMON_DIRS_RELATIVE
    }
    print(f"[CONFIG] Image Common Dirs (Relative->Absolute): {IMAGE_COMMON_DIRS_ABSOLUTE}")

except Exception as e:
    print(f"\n[FATAL ERROR] Failed to configure paths.")
    print(f"APP_BASE_DIR was calculated as: {APP_BASE_DIR if 'APP_BASE_DIR' in locals() else 'Not Set'}")
    print(f"Error details: {e}")
    try:
        root_for_err = tk._default_root if tk._default_root else tk.Tk(); root_for_err.withdraw()
        messagebox.showerror("Fatal Error - Path Config", f"Failed to configure paths:\n{e}")
        if not tk._default_root: root_for_err.destroy()
    except Exception: pass
    input("Press Enter to exit...")
    sys.exit(1)


# --- Helper Functions: News (Keep Existing) ---
def _news_load_existing_data(filepath):
    """Loads existing NEWS JSON data from the file, returns (data_list, error_msg)."""
    if not os.path.exists(filepath):
        print(f"[NEWS INFO] News JSON '{filepath}' not found. Starting empty list.")
        return [], None # Return empty list if file not found
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                print(f"[NEWS INFO] News JSON '{filepath}' is empty. Starting empty list.")
                return [], None # Return empty list if file is empty
            data = json.loads(content)
            if not isinstance(data, list):
                msg = f"Data in '{filepath}' is not a list. Please fix or delete."
                print(f"[NEWS WARNING] {msg}")
                return None, msg # Return None on invalid format
            print(f"[NEWS DEBUG] Loaded {len(data)} news items from {filepath}")
            # Sort data by date descending immediately after loading
            data.sort(key=lambda x: x.get('date', '0000-00-00'), reverse=True)
            return data, None
    except json.JSONDecodeError as e:
        msg = f"Could not decode JSON from '{filepath}': {e}"
        print(f"[NEWS ERROR] {msg}")
        return None, msg # Return None on decode error
    except Exception as e:
        msg = f"Error loading news data from '{filepath}': {e}"
        print(f"[NEWS ERROR] {msg}")
        return None, msg # Return None on other errors

def _news_save_data(filepath, data):
    """Saves the NEWS data list back to the JSON file, returns error_msg or None."""
    try:
        # Ensure data is sorted by date descending before saving
        data.sort(key=lambda x: x.get('date', '0000-00-00'), reverse=True)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[NEWS INFO] Successfully updated '{filepath}'")
        return None
    except Exception as e:
        msg = f"Saving news data to '{filepath}': {e}"
        print(f"[NEWS ERROR] {msg}")
        return msg

def _news_auto_link_text(text):
    """Converts plain text URLs and emails to HTML links for news content."""
    if not text: return ''
    email_regex = r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b'
    url_regex = r'(?<!href=["\'])(?<!src=["\'])\b((?:https?://|www\.)[^\s<>"]+?\.[^\s<>"]+)'
    def replace_email(match): return f'<a href="mailto:{match.group(1)}">{match.group(1)}</a>'
    def replace_url(match):
        url = match.group(1); href = url
        if href.startswith('www.'): href = 'https://' + href
        return f'<a href="{href}" target="_blank" rel="noopener noreferrer">{url}</a>'
    text = re.sub(email_regex, replace_email, text); text = re.sub(url_regex, replace_url, text)
    return text

def _news_is_valid_id(article_id):
    """Checks if NEWS ID format is valid."""
    return bool(re.match(r'^[a-z0-9-]+$', article_id))

# --- Helper Functions: Records (Keep Existing) ---
def _records_discover_files(base_dir):
    """Discovers HTML record files."""
    print(f"[RECORDS DEBUG] Discovering files in: {base_dir}")
    record_structure = {}
    if not os.path.isdir(base_dir): print(f"[RECORDS ERROR] Base directory not found: {base_dir}"); return {}
    try:
        categories = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))])
        print(f"[RECORDS DEBUG] Found categories: {categories}")
        for category in categories:
            category_path = os.path.join(base_dir, category); record_structure[category] = {}
            try:
                files = sorted([f for f in os.listdir(category_path) if f.lower().endswith('.html')])
                print(f"[RECORDS DEBUG] Files in '{category}': {files}")
                for filename in files:
                    base_name = os.path.splitext(filename)[0]
                    record_type_name = ' '.join(word.capitalize() for word in base_name.split('-'))
                    record_structure[category][record_type_name] = os.path.join(category_path, filename)
            except OSError as e: print(f"[RECORDS WARNING] Could not read dir {category_path}: {e}")
    except OSError as e: print(f"[RECORDS ERROR] Accessing base dir {base_dir}: {e}"); return {}
    print("[RECORDS DEBUG] Discovery complete."); return record_structure

def _records_parse_html(html_path):
    """Parses records from HTML."""
    records = []; print(f"[RECORDS DEBUG] Parsing HTML file: {html_path}")
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            try: soup = BeautifulSoup(f, 'lxml'); parser_used = "lxml"
            except Exception: print("[RECORDS WARNING] lxml parser failed, trying html.parser."); f.seek(0); soup = BeautifulSoup(f, 'html.parser'); parser_used = "html.parser"
            print(f"[RECORDS DEBUG] Parsed using {parser_used}.")
        tbody = soup.find('table', class_='records-table'); tbody = tbody.find('tbody') if tbody else None
        if not tbody: print(f"[RECORDS WARNING] No tbody in table.records-table in {html_path}. Trying any tbody."); tbody = soup.find('tbody')
        if not tbody: print(f"[RECORDS ERROR] No <tbody> found at all in {html_path}"); return None
        rows_found, valid_rows = 0, 0
        for row in tbody.find_all('tr', recursive=False):
            rows_found += 1; cells = [td.get_text(strip=True) for td in row.find_all('td', recursive=False)]
            if len(cells) == 5: records.append(cells); valid_rows += 1
            else: print(f"[RECORDS WARNING] Row in {html_path} has {len(cells)} cells (expected 5): {cells}")
        print(f"[RECORDS DEBUG] Found {rows_found} rows, parsed {valid_rows} valid records."); return records
    except FileNotFoundError: print(f"[RECORDS ERROR] File not found: {html_path}"); return None
    except Exception: import traceback; print(f"[RECORDS ERROR] Parsing HTML file {html_path}:"); traceback.print_exc(); return None

def _records_save_html(html_path, records_data):
    """Saves records back to HTML."""
    print(f"[RECORDS DEBUG] Saving {len(records_data)} records to: {html_path}")
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
             try: soup = BeautifulSoup(f, 'lxml')
             except Exception: print("[RECORDS WARNING] lxml parser failed for saving, trying html.parser."); f.seek(0); soup = BeautifulSoup(f, 'html.parser')
        tbody = soup.find('table', class_='records-table'); tbody = tbody.find('tbody') if tbody else None
        if not tbody: print(f"[RECORDS WARNING] No tbody in table.records-table for saving. Trying any tbody."); tbody = soup.find('tbody')
        if not tbody: print(f"[RECORDS ERROR] Cannot find <tbody> in {html_path} to save."); return False
        tbody.clear(); print("[RECORDS DEBUG] Cleared existing tbody content.")
        for record_row in records_data:
            new_tr = soup.new_tag('tr')
            for cell_data in record_row:
                new_td = soup.new_tag('td'); new_td.string = str(cell_data) if cell_data is not None else ""; new_tr.append(new_td)
            tbody.append(new_tr)
        print(f"[RECORDS DEBUG] Added {len(records_data)} new rows to tbody.")
        with open(html_path, 'w', encoding='utf-8') as f: f.write(soup.prettify(formatter="html5"))
        print("[RECORDS DEBUG] File successfully written."); return True
    except FileNotFoundError: print(f"[RECORDS ERROR] File not found for saving: {html_path}"); return False
    except Exception: import traceback; print(f"[RECORDS ERROR] Saving records to {html_path}:"); traceback.print_exc(); return False

# --- Helper Functions: Calendar (Keep Existing) ---
def _calendar_parse_html(html_path):
    """Parses events from kalender.html."""
    events = []; print(f"[CALENDAR DEBUG] Parsing calendar file: {html_path}")
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            try: soup = BeautifulSoup(f, 'lxml'); parser_used = "lxml"
            except Exception: print("[CALENDAR WARNING] lxml parser failed, trying html.parser."); f.seek(0); soup = BeautifulSoup(f, 'html.parser'); parser_used = "html.parser"
            print(f"[CALENDAR DEBUG] Parsed using {parser_used}.")
        month_grids = soup.find_all('section', class_='month-grid')
        if not month_grids: print("[CALENDAR ERROR] No sections with class 'month-grid' found."); return None
        print(f"[CALENDAR DEBUG] Found {len(month_grids)} month grids.")
        for month_section in month_grids:
            month_title_tag = month_section.find('h2', class_='month-title'); 
            if not month_title_tag: 
                continue
            match = re.match(r'(\w+)\s+(\d{4})', month_title_tag.get_text(strip=True), re.IGNORECASE); 
            if not match: 
                continue
            month_name_nl, year_str = match.groups(); month_num = DUTCH_MONTH_MAP.get(month_name_nl.lower()); 
            if not month_num: 
                continue; 
            year = int(year_str)
            print(f"[CALENDAR DEBUG] Processing Month: {month_name_nl} {year} (Month: {month_num})")
            for day_div in month_section.select('.calendar-days .calendar-day:not(.padding-day)'):
                day_num_tag = day_div.find('span', class_='day-number'); 
                if not day_num_tag: 
                    continue
                try: day = int(day_num_tag.get_text(strip=True)); current_date_str = f"{year:04d}-{month_num:02d}-{day:02d}"
                except ValueError: continue
                for event_span in day_div.find_all('span', class_='calendar-event', recursive=False):
                    event_name, event_link, event_color = "", None, "black"; link_tag = event_span.find('a')
                    if link_tag: event_name = link_tag.get_text(strip=True); event_link = link_tag.get('href')
                    else: event_name = event_span.get_text(strip=True)
                    for css_class in event_span.get('class', []):
                        if css_class.startswith('event-') and css_class.split('-')[1] in CALENDAR_EVENT_COLORS: event_color = css_class.split('-')[1]; break
                    if event_name: events.append({'date': current_date_str, 'name': event_name, 'color': event_color, 'link': event_link})
                    else: print(f"[CALENDAR WARNING] Found event span with no name on {current_date_str}")
        events.sort(key=lambda x: x['date']); print(f"[CALENDAR DEBUG] Parsed total {len(events)} events."); return events
    except FileNotFoundError: print(f"[CALENDAR ERROR] Calendar file not found: {html_path}"); return None
    except Exception: import traceback; print(f"[CALENDAR ERROR] Parsing calendar file {html_path}:"); traceback.print_exc(); return None

def _calendar_save_html(html_path, events_data):
    """Saves the list of event dicts back into kalender.html."""
    print(f"[CALENDAR DEBUG] Saving {len(events_data)} events to: {html_path}")
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
             try: soup = BeautifulSoup(f, 'lxml')
             except Exception: print("[CALENDAR WARNING] lxml parser failed for saving, trying html.parser."); f.seek(0); soup = BeautifulSoup(f, 'html.parser')
        events_by_date = defaultdict(list)
        for event in events_data: events_by_date[event['date']].append(event)
        month_grids = soup.find_all('section', class_='month-grid')
        if not month_grids: print("[CALENDAR ERROR] Cannot save: No sections with class 'month-grid' found in HTML."); return False
        for month_section in month_grids:
            month_title_tag = month_section.find('h2', class_='month-title'); 
            if not month_title_tag: 
                continue
            match = re.match(r'(\w+)\s+(\d{4})', month_title_tag.get_text(strip=True), re.IGNORECASE); 
            if not match: 
                continue
            month_name_nl, year_str = match.groups(); month_num = DUTCH_MONTH_MAP.get(month_name_nl.lower()); 
            if not month_num: continue; 
            year = int(year_str)
            for day_div in month_section.select('.calendar-days .calendar-day:not(.padding-day)'):
                for old_event in day_div.find_all('span', class_='calendar-event', recursive=False): old_event.decompose()
                day_num_tag = day_div.find('span', class_='day-number'); 
                if not day_num_tag: continue
                try: day = int(day_num_tag.get_text(strip=True)); current_date_str = f"{year:04d}-{month_num:02d}-{day:02d}"
                except ValueError: continue
                if current_date_str in events_by_date:
                    print(f"[CALENDAR DEBUG] Adding {len(events_by_date[current_date_str])} event(s) for {current_date_str}")
                    for event in events_by_date[current_date_str]:
                        new_event_span = soup.new_tag('span', attrs={'class': f"calendar-event event-{event.get('color', 'black')}"}); new_event_span['title'] = event.get('name', '')
                        if event.get('link'): link_tag = soup.new_tag('a', href=event['link']); link_tag.string = event.get('name', ''); new_event_span.append(link_tag)
                        else: new_event_span.string = event.get('name', '')
                        day_div.append(new_event_span); day_div.append("\n        ")
        with open(html_path, 'w', encoding='utf-8') as f: f.write(soup.prettify(formatter="html5"))
        print("[CALENDAR DEBUG] Calendar file successfully written."); return True
    except FileNotFoundError: print(f"[CALENDAR ERROR] Calendar file not found for saving: {html_path}"); return False
    except Exception: import traceback; print(f"[CALENDAR ERROR] Saving calendar file {html_path}:"); traceback.print_exc(); return False

# --- Helper Functions: Reports (Keep Existing) ---
def _reports_parse_html(html_path):
    """Parses reports grouped by year from the HTML file."""
    reports_data = {}; print(f"[REPORTS DEBUG] Parsing reports file: {html_path}")
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            try: soup = BeautifulSoup(f, 'lxml'); parser_used = "lxml"
            except Exception: print("[REPORTS WARNING] lxml parser failed, trying html.parser."); f.seek(0); soup = BeautifulSoup(f, 'html.parser'); parser_used = "html.parser"
            print(f"[REPORTS DEBUG] Parsed using {parser_used}.")
        reports_section = soup.find('div', id='reports-section')
        if not reports_section: msg = "Could not find '<div id=\"reports-section\">' in HTML. Cannot parse reports."; print(f"[REPORTS ERROR] {msg}"); return None, msg
        current_year = None
        for element in reports_section.children:
             if not isinstance(element, Tag): continue
             if element.name == 'h2':
                 year_match = re.search(r'(\d{4})', element.get_text()); current_year = year_match.group(1) if year_match else None
                 if current_year: reports_data.setdefault(current_year, []); print(f"[REPORTS DEBUG] Found year section: {current_year}")
                 else: print(f"[REPORTS WARNING] Found H2 without a 4-digit year: {element.get_text(strip=True)}")
             elif element.name == 'ul' and 'report-list' in element.get('class', []) and current_year:
                 print(f"[REPORTS DEBUG] Processing report list for year: {current_year}"); items_in_list = 0
                 for li in element.find_all('li', recursive=False):
                     a_tag = li.find('a', recursive=False)
                     if a_tag and a_tag.get('href'):
                         report_text = a_tag.get_text(strip=True); report_path = a_tag.get('href'); report_filename = pathlib.PurePosixPath(report_path).name
                         if report_text and report_path and report_filename: reports_data[current_year].append({'text': report_text, 'filename': report_filename, 'path': report_path}); items_in_list += 1
                         else: print(f"[REPORTS WARNING] Skipping malformed list item in year {current_year}: {li.prettify()}")
                     else: print(f"[REPORTS WARNING] Skipping list item without valid link in year {current_year}: {li.prettify()}")
                 print(f"[REPORTS DEBUG] Found {items_in_list} reports for {current_year}")
        parsed_count = sum(len(v) for v in reports_data.values()); print(f"[REPORTS DEBUG] Parsed total {parsed_count} reports across {len(reports_data)} years.")
        return dict(sorted(reports_data.items(), key=lambda item: int(item[0]), reverse=True)), None
    except FileNotFoundError: msg = f"Reports HTML file not found: {html_path}"; print(f"[REPORTS ERROR] {msg}"); return None, msg
    except Exception as e: import traceback; msg = f"Parsing reports file {html_path}: {e}"; print(f"[REPORTS ERROR] {msg}"); traceback.print_exc(); return None, msg

def _reports_save_html(html_path, reports_data):
    """Saves the reports data structure back into the HTML file, preserving surrounding content."""
    report_count = sum(len(v) for v in reports_data.values()); print(f"[REPORTS DEBUG] Saving {report_count} reports to: {html_path}")
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
             try: soup = BeautifulSoup(f, 'lxml')
             except Exception: print("[REPORTS WARNING] lxml parser failed for saving, trying html.parser."); f.seek(0); soup = BeautifulSoup(f, 'html.parser')
        reports_section = soup.find('div', id='reports-section')
        if not reports_section: msg = "Cannot save: Could not find '<div id=\"reports-section\">' in HTML template."; print(f"[REPORTS ERROR] {msg}"); return False, msg
        reports_section.clear(); print("[REPORTS DEBUG] Cleared existing content inside #reports-section.")
        for year in sorted(reports_data.keys(), key=int, reverse=True):
            year_reports = reports_data[year];
            if not year_reports: print(f"[REPORTS DEBUG] Skipping empty year {year} during save."); continue
            h2_tag = soup.new_tag('h2'); h2_tag.string = f"Verslagen {year}"
            reports_section.append(h2_tag); reports_section.append("\n")
            ul_tag = soup.new_tag('ul', attrs={'class': 'report-list'})
            reports_section.append(ul_tag); reports_section.append("\n")
            for report in year_reports: # Assuming already sorted if needed
                li_tag = soup.new_tag('li'); a_tag = soup.new_tag('a', href=report['path'], target='_blank'); a_tag.string = report['text']
                li_tag.append(a_tag); ul_tag.append(li_tag); ul_tag.append("\n")
            print(f"[REPORTS DEBUG] Added section for year {year} with {len(year_reports)} reports.")
        with open(html_path, 'w', encoding='utf-8') as f: f.write(soup.prettify(formatter="html5"))
        print("[REPORTS DEBUG] Reports HTML file successfully written."); return True, None
    except FileNotFoundError: msg = f"Reports HTML file not found for saving: {html_path}"; print(f"[REPORTS ERROR] {msg}"); return False, msg
    except Exception as e: import traceback; msg = f"Saving reports file {html_path}: {e}"; print(f"[REPORTS ERROR] {msg}"); traceback.print_exc(); return False, msg

# --- Helper Functions: General HTML ---
def _general_html_find_files(targets_abs):
    """Finds all HTML files based on target paths (files or dirs)."""
    html_files = set(); print(f"[HTML SCAN] Scanning targets: {targets_abs}")
    for target_path in targets_abs:
        if not os.path.exists(target_path): print(f"[HTML SCAN WARNING] Target path not found: {target_path}"); continue
        if os.path.isfile(target_path):
            if target_path.lower().endswith(('.html', '.htm')): html_files.add(target_path); print(f"[HTML SCAN] Found file: {target_path}")
        elif os.path.isdir(target_path):
            print(f"[HTML SCAN] Scanning directory: {target_path}")
            for root, _, files in os.walk(target_path):
                for filename in files:
                    if filename.lower().endswith(('.html', '.htm')): full_path = os.path.join(root, filename); html_files.add(full_path); print(f"[HTML SCAN] Found file in dir: {full_path}")
        else: print(f"[HTML SCAN WARNING] Target is neither file nor directory: {target_path}")
    found_count = len(html_files); print(f"[HTML SCAN] Found {found_count} unique HTML files.")
    return sorted(list(html_files)), found_count

# --- Helper Functions: Text Editor (Extended for Adding Text) ---
def _text_editor_parse_file(file_path, parsed_soups_dict, found_texts_list):
    """Parses a single file for text, adds to lists. Returns texts_found_in_file count."""
    texts_in_file = 0; total_texts_so_far = len(found_texts_list)
    try:
        with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
        try: soup = BeautifulSoup(content, 'lxml'); parser_used = 'lxml'
        except Exception:
            try: print(f"[TEXT EDITOR WARNING] lxml failed for {file_path}, trying html.parser."); soup = BeautifulSoup(content, 'html.parser'); parser_used = 'html.parser'
            except Exception as parse_err: print(f"[TEXT EDITOR ERROR] Failed to parse {file_path}: {parse_err}"); return 0 # Skip file on parse error
        print(f"[TEXT EDITOR DEBUG] Parsed {os.path.basename(file_path)} using {parser_used}")
        parsed_soups_dict[file_path] = soup
        for text_node in soup.find_all(string=True):
            parent_tag = text_node.parent
            if parent_tag and parent_tag.name in TEXT_EDITOR_EXCLUDED_TAGS: continue
            if isinstance(text_node, Comment): continue
            original_text = str(text_node).strip()
            if not original_text: continue # Skip empty or whitespace-only strings
            iid = total_texts_so_far + texts_in_file # Calculate unique ID
            display_text = (original_text[:100] + '...') if len(original_text) > 100 else original_text
            display_text = display_text.replace('\n', ' ').replace('\r', '') # Clean for display
            found_texts_list.append({
                'file_path': file_path,
                'original_text': str(text_node), # Store original with original whitespace for editing
                'dom_reference': text_node,      # Direct reference to the BS4 node
                'display_text': display_text,    # Cleaned for treeview
                'iid': iid                       # Unique sequential ID for treeview
            })
            texts_in_file += 1
        if texts_in_file > 0: print(f"[TEXT EDITOR DEBUG] Found {texts_in_file} snippets in {os.path.basename(file_path)}")
        return texts_in_file
    except FileNotFoundError: print(f"[TEXT EDITOR ERROR] File not found during scan: {file_path}"); return 0
    except Exception as e: import traceback; print(f"[TEXT EDITOR ERROR] Error processing file {file_path}: {e}"); traceback.print_exc(); return 0

# --- Helper Functions: Image Management ---
def _images_parse_file(file_path, parsed_soups_dict, found_images_list):
    """Parses a single file for images, adds to lists. Returns images_found_in_file count."""
    images_in_file = 0; total_images_so_far = len(found_images_list)
    try:
        # Reuse soup if already parsed by text editor for efficiency
        if file_path in parsed_soups_dict:
            soup = parsed_soups_dict[file_path]
            print(f"[IMAGE SCAN DEBUG] Reusing parsed soup for {os.path.basename(file_path)}")
        else:
            with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
            try: soup = BeautifulSoup(content, 'lxml'); parser_used = 'lxml'
            except Exception:
                try: print(f"[IMAGE SCAN WARNING] lxml failed for {file_path}, trying html.parser."); soup = BeautifulSoup(content, 'html.parser'); parser_used = 'html.parser'
                except Exception as parse_err: print(f"[IMAGE SCAN ERROR] Failed to parse {file_path} for images: {parse_err}"); return 0
            print(f"[IMAGE SCAN DEBUG] Parsed {os.path.basename(file_path)} for images using {parser_used}")
            parsed_soups_dict[file_path] = soup # Store if parsed here

        # Find all <img> tags with a src attribute
        for img_tag in soup.find_all('img', src=True):
            src_attr = img_tag['src'].strip()
            if not src_attr or src_attr.startswith(('data:', 'http:', 'https:')):
                continue # Skip empty, data URIs, or external URLs

            iid = total_images_so_far + images_in_file # Unique ID

            # Attempt to resolve the src path relative to APP_BASE_DIR
            # This assumes website paths map directly to filesystem structure from APP_BASE_DIR
            try:
                # Normalize posix paths from HTML ('/') to system paths
                relative_src_path = src_attr.lstrip('/') # Remove leading slash for joining
                img_abs_path = os.path.abspath(os.path.join(APP_BASE_DIR, relative_src_path))
                exists = os.path.isfile(img_abs_path)
            except Exception as path_err:
                print(f"[IMAGE SCAN WARNING] Error resolving path '{src_attr}' in {file_path}: {path_err}")
                img_abs_path = "Error Resolving Path"
                exists = False

            found_images_list.append({
                'html_file': file_path,       # HTML file where image is found
                'src': src_attr,              # Original src attribute value
                'dom_reference': img_tag,     # Reference to the <img> tag
                'abs_path': img_abs_path,     # Calculated absolute path
                'exists': exists,             # Whether the file exists at abs_path
                'iid': iid                    # Unique sequential ID
            })
            images_in_file += 1

        # TODO: Optionally add scanning for background-image in style attributes or <style> tags (more complex)

        if images_in_file > 0: print(f"[IMAGE SCAN DEBUG] Found {images_in_file} local image refs in {os.path.basename(file_path)}")
        return images_in_file

    except FileNotFoundError: print(f"[IMAGE SCAN ERROR] File not found during scan: {file_path}"); return 0
    except Exception as e: import traceback; print(f"[IMAGE SCAN ERROR] Error processing file {file_path} for images: {e}"); traceback.print_exc(); return 0


# --- Main Application Class ---
class WebsiteEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Thiberta Software - Website Editor") # Updated Title
        self.root.geometry("1300x950") # Slightly larger default size

        print("[GUI INFO] Initializing main application...")
        # --- Style Configuration (Keep Existing) ---
        style = ttk.Style()
        try:
             themes = style.theme_names(); preferred_themes = ["clam", "vista", "aqua", "default"]
             for theme in preferred_themes:
                 if theme in themes: style.theme_use(theme); break
             print(f"[GUI INFO] Using theme: {style.theme_use()}")
        except tk.TclError: print("[GUI WARNING] Could not set preferred theme.")
        self.default_font_family = "Segoe UI" if sys.platform == "win32" else "TkDefaultFont"; self.default_font_size = 9; self.desc_font_size = 8; self.bold_font_weight = 'bold'
        self.desc_font = (self.default_font_family, self.desc_font_size); self.bold_font = (self.default_font_family, self.default_font_size, self.bold_font_weight)
        style.configure("TLabel", font=(self.default_font_family, self.default_font_size)); style.configure("TButton", font=(self.default_font_family, self.default_font_size))
        style.configure("TEntry", font=(self.default_font_family, self.default_font_size)); style.configure("TCombobox", font=(self.default_font_family, self.default_font_size))
        style.configure("Treeview.Heading", font=self.bold_font); style.configure("Treeview", rowheight=25, font=(self.default_font_family, self.default_font_size))
        style.configure("Desc.TLabel", foreground="grey", font=self.desc_font); style.configure("Error.TLabel", foreground="red", font=(self.default_font_family, self.default_font_size))
        style.configure("Bold.TLabel", font=self.bold_font); style.configure("Warning.TLabel", foreground="orange", font=(self.default_font_family, self.default_font_size))
        try:
             style.map('TEntry', fieldbackground=[('invalid', '#FED8D8'), ('!invalid', 'white')], bordercolor=[('invalid', 'red'), ('!invalid', 'grey')], foreground=[('invalid', 'black'), ('!invalid', 'black')])
        except tk.TclError: print("[GUI WARNING] Could not configure TEntry validation styles.")

        # --- Create Notebook (Tabs) ---
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=10, padx=10, expand=True, fill='both')

        # --- Create Frames for each Tab ---
        self.news_tab_frame = ttk.Frame(self.notebook, padding="0")
        self.records_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.calendar_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.reports_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.text_editor_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.images_tab_frame = ttk.Frame(self.notebook, padding="10") # <-- New Image Tab Frame

        self.news_tab_frame.pack(fill='both', expand=True)
        self.records_tab_frame.pack(fill='both', expand=True)
        self.calendar_tab_frame.pack(fill='both', expand=True)
        self.reports_tab_frame.pack(fill='both', expand=True)
        self.text_editor_tab_frame.pack(fill='both', expand=True)
        self.images_tab_frame.pack(fill='both', expand=True) # <-- Pack New Frame

        # --- Add Tabs to Notebook ---
        self.notebook.add(self.news_tab_frame, text=' Manage News ')
        self.notebook.add(self.records_tab_frame, text=' Edit Records ')
        self.notebook.add(self.calendar_tab_frame, text=' Edit Calendar ')
        self.notebook.add(self.reports_tab_frame, text=' Manage Reports ')
        self.notebook.add(self.images_tab_frame, text=' Manage Images ') # <-- Add New Tab
        self.notebook.add(self.text_editor_tab_frame, text=' Edit Website Text ')

        # --- Shared Bottom Bar (Status + Git) (Keep Existing) ---
        bottom_bar_frame = ttk.Frame(root)
        bottom_bar_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(bottom_bar_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), pady=2)
        self.git_publish_button = ttk.Button(bottom_bar_frame, text="Publish Changes (Git)", command=self._git_publish)
        self.git_publish_button.pack(side=tk.RIGHT, pady=2)
        self.set_status("Application started. Initializing...")

        # --- Initialize Data Structures ---
        self.news_data = []
        self.text_editor_parsed_soups = {} # Share parsed soups between Text & Image tabs
        # Other tabs manage their data internally

        # --- Populate Tabs ---
        self._create_news_tab(self.news_tab_frame)
        self._create_records_tab(self.records_tab_frame)
        self._create_calendar_tab(self.calendar_tab_frame)
        self._create_reports_tab(self.reports_tab_frame)
        self._create_images_tab(self.images_tab_frame) # <-- Create New Image Tab
        self._create_text_editor_tab(self.text_editor_tab_frame)

        # --- <<< AUTOMATIC DATA LOADING >>> ---
        print("\n[INIT] Starting automatic data loading...")
        self.set_status("Loading initial data...")
        self.root.update_idletasks()

        # News
        self._news_load_and_populate_treeview()
        # Records (Discovery happens in _create_records_tab)
        # Calendar
        self._calendar_load()
        # Reports
        self._reports_load()
        # Images (Scan HTML)
        self._images_scan_files()
        # Text Editor (Scan HTML, using shared soup where possible)
        self._text_editor_scan_files()

        initial_load_status = "Initial data load complete. Ready."
        if not hasattr(self, 'news_tree'): initial_load_status = "Error initializing News tab."
        elif not hasattr(self, 'records_tree'): initial_load_status = "Error initializing Records tab (BS4?)."
        elif not hasattr(self, 'calendar_tree'): initial_load_status = "Error initializing Calendar tab (BS4?)."
        elif not hasattr(self, 'reports_tree'): initial_load_status = "Error initializing Reports tab (BS4?)."
        elif not hasattr(self, 'images_tree'): initial_load_status = "Error initializing Images tab (BS4?)."
        elif not hasattr(self, 'text_editor_tree'): initial_load_status = "Error initializing Text Editor tab (BS4?)."

        self.set_status(initial_load_status, duration_ms=5000)
        print("[INIT] Automatic data loading phase finished.")
        # --- <<< END OF AUTOMATIC LOADING >>> ---

        print("[GUI INFO] Main application initialized.")


    def _git_publish(self): # Keep Existing Git Publish
        """Runs git pull, add, commit, push commands, with basic conflict check."""
        print("[GIT PUBLISH] Button clicked.")
        git_dir = os.path.join(APP_BASE_DIR, '.git')
        if not os.path.isdir(git_dir):
            messagebox.showwarning("Git Error", f"Could not find a '.git' directory in:\n{APP_BASE_DIR}\n\nEnsure this application runs from your Git repository root.", parent=self.root)
            self.set_status("Publish failed: Not a Git repository root.", is_error=True); return
        commit_msg = tk.simpledialog.askstring("Commit Message", "Enter a brief description of the changes:", parent=self.root)
        if not commit_msg: self.set_status("Git publish cancelled: No commit message entered.", duration_ms=3000); return
        if not messagebox.askyesno("Confirm Git Publish", f"This will run:\n1. git pull\n2. git add .\n3. git commit -m \"{commit_msg}\"\n4. git push\n\nProceed?", parent=self.root):
            self.set_status("Git publish cancelled by user.", duration_ms=3000); return
        self.git_publish_button.config(state=tk.DISABLED); self.root.update_idletasks()
        def run_git_command(command_list, description):
            self.set_status(f"Running {description}..."); print(f"[GIT PUBLISH] Executing: {' '.join(command_list)} in {APP_BASE_DIR}"); self.root.update_idletasks(); startupinfo = None
            if sys.platform == "win32": startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startupinfo.wShowWindow = subprocess.SW_HIDE
            try:
                result = subprocess.run(command_list, cwd=APP_BASE_DIR, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace', startupinfo=startupinfo)
                print(f"[GIT PUBLISH] Return Code: {result.returncode}"); print(f"[GIT PUBLISH] STDOUT:\n{result.stdout.strip()}" if result.stdout else "[GIT PUBLISH] STDOUT: None"); print(f"[GIT PUBLISH] STDERR:\n{result.stderr.strip()}" if result.stderr else "[GIT PUBLISH] STDERR: None"); return result
            except FileNotFoundError: print("[GIT PUBLISH] Git command not found error."); return None
            except Exception as e: print(f"[GIT PUBLISH] Unexpected Python error running command: {e}"); return False
        final_success, error_details = True, ""
        pull_result = run_git_command(['git', 'pull'], 'git pull')
        if pull_result is None or pull_result is False: error_details = "Command Failed: git pull\n\nError: 'git' not found or Python error."; final_success = False
        elif pull_result.returncode != 0:
            if "Merge conflict" in pull_result.stdout or "Merge conflict" in pull_result.stderr or "Automatic merge failed" in pull_result.stderr: error_details = "Merge Conflict Detected!\n\n'git pull' resulted in merge conflicts.\nResolve conflicts manually outside this app."; final_success = False; print("[GIT PUBLISH] Merge conflict detected. Aborting.")
            else: error_details = f"Command Failed: git pull\n\nError Code: {pull_result.returncode}\n\n{pull_result.stderr or pull_result.stdout}"; final_success = False
        else: print("[GIT PUBLISH] git pull successful or up-to-date."); self.set_status("Pull successful. Proceeding..."); self.root.update_idletasks()
        if final_success:
            add_result = run_git_command(['git', 'add', '.'], 'git add .');
            if add_result is None or add_result is False or add_result.returncode != 0: error_details = f"Command Failed: git add .\n\n{add_result.stderr or add_result.stdout if isinstance(add_result, subprocess.CompletedProcess) else 'Git not found or Python error'}"; final_success = False
        if final_success:
            commit_result = run_git_command(['git', 'commit', '-m', commit_msg], f'git commit -m "{commit_msg}"')
            if commit_result is None or commit_result is False: error_details = "Command Failed: git commit\n\nGit not found or Python error"; final_success = False
            elif commit_result.returncode != 0:
                 if "nothing to commit" in commit_result.stdout or "nothing added to commit" in commit_result.stderr or "no changes added to commit" in commit_result.stdout: print("[GIT PUBLISH] Commit skipped - nothing to commit."); self.set_status("Nothing new to commit. Checking push..."); self.root.update_idletasks()
                 else: error_details = f"Command Failed: git commit\n\nError Code: {commit_result.returncode}\n\n{commit_result.stderr or commit_result.stdout}"; final_success = False
        if final_success:
             push_result = run_git_command(['git', 'push'], 'git push')
             if push_result is None or push_result is False or push_result.returncode != 0:
                  error_details = f"Command Failed: git push\n\nError Code: {push_result.returncode if isinstance(push_result, subprocess.CompletedProcess) else 'N/A'}\n\n{push_result.stderr or push_result.stdout if isinstance(push_result, subprocess.CompletedProcess) else 'Git not found or Python error'}"
                  if isinstance(push_result, subprocess.CompletedProcess) and 'rejected' in push_result.stderr and ('non-fast-forward' in push_result.stderr or 'fetch first' in push_result.stderr): error_details += "\n\nHint: Remote changes exist. Try 'git pull' manually."
                  final_success = False
        self.git_publish_button.config(state=tk.NORMAL)
        if final_success: messagebox.showinfo("Git Publish Successful", "Changes successfully pulled, added, committed, and pushed.", parent=self.root); self.set_status("Git publish completed successfully.", duration_ms=5000)
        else: messagebox.showerror("Git Publish Failed", error_details, parent=self.root); self.set_status("Git publish failed. See error popup.", is_error=True)

    def set_status(self, message, is_error=False, duration_ms=0): # Keep Existing Status Update
        """Sets the status bar message, optionally auto-clearing after a duration."""
        log_level = "[STATUS ERROR]" if is_error else "[STATUS INFO]"; print(f"{log_level} {message}")
        self.status_var.set(message); self.status_label.config(foreground="red" if is_error else "black")
        if hasattr(self, "_status_clear_timer") and self._status_clear_timer: self.root.after_cancel(self._status_clear_timer); self._status_clear_timer = None
        if duration_ms > 0: self._status_clear_timer = self.root.after(duration_ms, self._clear_status)

    def _clear_status(self): # Keep Existing Status Clear
        """Clears the status bar message."""
        self.status_var.set(""); self.status_label.config(foreground="black"); self._status_clear_timer = None


    # --- News Tab Creation & Methods (Keep Existing) ---
    def _create_news_tab(self, parent_frame):
        print("[GUI INFO] Creating News Tab...")
        pw = ttk.PanedWindow(parent_frame, orient=tk.VERTICAL); pw.pack(fill=tk.BOTH, expand=True)
        form_frame = ttk.Labelframe(pw, text=" Add New Article ", padding="10"); form_frame.columnconfigure(1, weight=1)
        row_index = 0
        ttk.Label(form_frame, text="Uniek ID:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=2); self.news_entry_id = ttk.Entry(form_frame, width=50); self.news_entry_id.grid(column=1, row=row_index, sticky=(tk.W, tk.E), padx=5, pady=2); ttk.Label(form_frame, text="bv. 'nieuwe-trainer-jan'", style="Desc.TLabel").grid(column=2, row=row_index, sticky=tk.W, padx=5); row_index += 1
        ttk.Label(form_frame, text="Kleine letters, cijfers, koppeltekens (-). Moet uniek zijn.", style="Desc.TLabel").grid(column=1, row=row_index, columnspan=2, sticky=tk.W, padx=5, pady=(0, 5)); row_index += 1
        ttk.Label(form_frame, text="Datum:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=2); self.news_entry_date = ttk.Entry(form_frame, width=20); self.news_entry_date.grid(column=1, row=row_index, sticky=tk.W, padx=5, pady=2); self.news_entry_date.insert(0, datetime.date.today().isoformat()); ttk.Label(form_frame, text="Formaat: YYYY-MM-DD", style="Desc.TLabel").grid(column=2, row=row_index, sticky=tk.W, padx=5); row_index += 1
        ttk.Label(form_frame, text="Titel:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=2); self.news_entry_title = ttk.Entry(form_frame, width=50); self.news_entry_title.grid(column=1, row=row_index, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2); row_index += 1
        ttk.Label(form_frame, text="Categorie:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=2); self.news_entry_category = ttk.Entry(form_frame, width=30); self.news_entry_category.grid(column=1, row=row_index, sticky=tk.W, padx=5, pady=2); self.news_entry_category.insert(0, NEWS_DEFAULT_CATEGORY); ttk.Label(form_frame, text="bv. 'Mededelingen'", style="Desc.TLabel").grid(column=2, row=row_index, sticky=tk.W, padx=5); row_index += 1
        ttk.Label(form_frame, text="Afbeelding:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=2); image_frame = ttk.Frame(form_frame); image_frame.grid(column=1, row=row_index, columnspan=2, sticky=(tk.W, tk.E)); image_frame.columnconfigure(0, weight=1); self.news_entry_image = ttk.Entry(image_frame, width=45); self.news_entry_image.grid(column=0, row=0, sticky=(tk.W, tk.E), padx=(0, 5)); self.news_entry_image.insert(0, NEWS_DEFAULT_IMAGE); self.news_button_browse_image = ttk.Button(image_frame, text="upload img", command=self._news_browse_image, width=10); self.news_button_browse_image.grid(column=1, row=0, sticky=tk.W); row_index += 1
        ttk.Label(form_frame, text="Samenvatting:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=2); self.news_entry_summary = ttk.Entry(form_frame, width=50); self.news_entry_summary.grid(column=1, row=row_index, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2); row_index += 1
        ttk.Label(form_frame, text="Volledige Tekst:").grid(column=0, row=row_index, sticky=(tk.W, tk.N), padx=5, pady=2); self.news_text_full_content = scrolledtext.ScrolledText(form_frame, width=60, height=8, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1, font=(self.default_font_family, self.default_font_size)); self.news_text_full_content.grid(column=1, row=row_index, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=2); row_index += 1
        news_button_frame = ttk.Frame(form_frame); news_button_frame.grid(column=0, row=row_index, columnspan=3, pady=10, sticky=tk.E); self.news_button_add = ttk.Button(news_button_frame, text="Voeg Artikel Toe", command=self._news_add_article); self.news_button_add.pack(side=tk.LEFT, padx=5); self.news_button_clear = ttk.Button(news_button_frame, text="Wis Formulier", command=self._news_clear_form); self.news_button_clear.pack(side=tk.LEFT, padx=5)
        pw.add(form_frame, weight=0)
        list_frame = ttk.Labelframe(pw, text=" Existing Articles ", padding="10"); list_frame.grid_rowconfigure(0, weight=1); list_frame.grid_columnconfigure(0, weight=1)
        news_columns = ('id', 'date', 'title'); self.news_tree = ttk.Treeview(list_frame, columns=news_columns, show='headings', selectmode='browse')
        self.news_tree.heading('id', text='ID', anchor=tk.W); self.news_tree.column('id', width=180, minwidth=120, anchor=tk.W, stretch=tk.NO)
        self.news_tree.heading('date', text='Date', anchor=tk.W); self.news_tree.column('date', width=100, minwidth=90, anchor=tk.CENTER, stretch=tk.NO)
        self.news_tree.heading('title', text='Title', anchor=tk.W); self.news_tree.column('title', width=400, minwidth=200, anchor=tk.W)
        news_vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.news_tree.yview); self.news_tree.configure(yscrollcommand=news_vsb.set)
        self.news_tree.grid(row=0, column=0, sticky='nsew'); news_vsb.grid(row=0, column=1, sticky='ns')
        self.news_tree.bind("<<TreeviewSelect>>", self._news_on_selection_change)
        list_button_frame = ttk.Frame(list_frame); list_button_frame.grid(row=1, column=0, columnspan=2, pady=(10,0), sticky=tk.W)
        self.news_button_delete = ttk.Button(list_button_frame, text="Delete Selected Article", command=self._news_delete_selected, state=tk.DISABLED); self.news_button_delete.pack(side=tk.LEFT, padx=(0, 5))
        self.news_button_refresh = ttk.Button(list_button_frame, text="Refresh List", command=self._news_load_and_populate_treeview); self.news_button_refresh.pack(side=tk.LEFT, padx=5)
        pw.add(list_frame, weight=1)
    def _news_load_and_populate_treeview(self):
        self.set_status("Loading news articles..."); self.root.update_idletasks(); loaded_data, error_msg = _news_load_existing_data(NEWS_JSON_FILE_PATH)
        if error_msg: self.news_data = []; self.set_status(f"Error loading news: {error_msg}", is_error=True); messagebox.showerror("News Load Error", f"Failed to load news data:\n{error_msg}", parent=self.root)
        else: self.news_data = loaded_data; item_count = len(self.news_data); self.set_status(f"Loaded {item_count} news articles.", duration_ms=3000 if item_count > 0 else 5000)
        self._news_populate_treeview()
    def _news_populate_treeview(self):
        for item in self.news_tree.get_children(): self.news_tree.delete(item)
        for article in self.news_data:
            try: article_id = article.get('id', 'MISSING_ID'); date = article.get('date', ''); title = article.get('title', 'No Title'); self.news_tree.insert('', tk.END, iid=article_id, values=(article_id, date, title))
            except Exception as e: print(f"[NEWS GUI ERROR] Failed inserting news row: {article}\nError: {e}")
        self._news_on_selection_change()
    def _news_on_selection_change(self, event=None):
        self.news_button_delete.config(state=tk.NORMAL if self.news_tree.selection() else tk.DISABLED)
    def _news_delete_selected(self):
        selected_items = self.news_tree.selection();
        if not selected_items: messagebox.showwarning("Selection Required", "Please select an article from the list to delete.", parent=self.root); return
        selected_iid = selected_items[0]; article_to_delete = None; article_index = -1
        for i, article in enumerate(self.news_data):
            if article.get('id') == selected_iid: article_to_delete = article; article_index = i; break
        if not article_to_delete: messagebox.showerror("Error", f"Could not find selected article (ID: {selected_iid}). Refresh?", parent=self.root); self.set_status("Error finding article to delete.", is_error=True); return
        title = article_to_delete.get('title', 'Untitled'); date = article_to_delete.get('date', 'No Date')
        if messagebox.askyesno("Confirm Deletion", f"Permanently delete this article?\n\nID: {selected_iid}\nDate: {date}\nTitle: {title}", icon='warning', parent=self.root):
            print(f"[NEWS INFO] Deleting article: ID='{selected_iid}', Title='{title}'"); self.set_status(f"Deleting article '{title}'..."); self.root.update_idletasks()
            del self.news_data[article_index]; save_error = _news_save_data(NEWS_JSON_FILE_PATH, self.news_data)
            if save_error: self.set_status(f"Error saving after deletion: {save_error}", is_error=True); messagebox.showerror("Save Error", f"Failed to save after deleting:\n{save_error}", parent=self.root); self._news_load_and_populate_treeview()
            else: self._news_populate_treeview(); self.set_status(f"Article '{title}' deleted successfully.", duration_ms=5000)
        else: print("[NEWS INFO] Deletion cancelled."); self.set_status("Deletion cancelled.", duration_ms=3000)
    def _news_reset_entry_states(self):
        try: self.news_entry_id.state(["!invalid"]); self.news_entry_date.state(["!invalid"]); self.news_entry_title.state(["!invalid"])
        except tk.TclError: pass
    def _news_browse_image(self):
        print("[NEWS DEBUG] Browse image clicked."); filetypes = (("Image files", "*.jpg *.jpeg *.png *.gif *.webp *.bmp"), ("All files", "*.*")); initial_dir = os.path.dirname(NEWS_IMAGE_DEST_DIR_ABSOLUTE); source_path = filedialog.askopenfilename(title="Selecteer afbeelding", filetypes=filetypes, initialdir=initial_dir)
        if not source_path: self.set_status("Afbeelding selectie geannuleerd.", duration_ms=3000); return
        filename = os.path.basename(source_path); dest_path = os.path.join(NEWS_IMAGE_DEST_DIR_ABSOLUTE, filename); print(f"[NEWS DEBUG] Selected '{source_path}', dest: '{dest_path}'")
        try: os.makedirs(NEWS_IMAGE_DEST_DIR_ABSOLUTE, exist_ok=True)
        except OSError as e: messagebox.showerror("Directory Fout", f"Kon map niet aanmaken:\n{NEWS_IMAGE_DEST_DIR_ABSOLUTE}\nFout: {e}", parent=self.root); self.set_status(f"Fout bij aanmaken map {NEWS_IMAGE_DEST_DIR_RELATIVE}", is_error=True); return
        if os.path.exists(dest_path):
            if not messagebox.askyesno("Bestand bestaat al", f"'{filename}' bestaat al in '{NEWS_IMAGE_DEST_DIR_RELATIVE}'.\nOverschrijven?", parent=self.root): self.set_status("Upload geannuleerd (overschrijven geweigerd).", duration_ms=4000); return
        try: shutil.copy2(source_path, dest_path); print(f"[NEWS INFO] Copied '{source_path}' to '{dest_path}'"); self.news_entry_image.delete(0, tk.END); self.news_entry_image.insert(0, filename); self.set_status(f"Afbeelding '{filename}' succesvol geüpload.", duration_ms=5000)
        except Exception as e: messagebox.showerror("Upload Fout", f"Kon afbeelding niet kopiëren:\n{dest_path}\nFout: {e}", parent=self.root); self.set_status(f"Fout bij uploaden afbeelding: {e}", is_error=True)
    def _news_clear_form(self):
        print("[NEWS DEBUG] Clear form clicked."); self._news_reset_entry_states(); self.news_entry_id.delete(0, tk.END); self.news_entry_date.delete(0, tk.END); self.news_entry_date.insert(0, datetime.date.today().isoformat()); self.news_entry_title.delete(0, tk.END); self.news_entry_category.delete(0, tk.END); self.news_entry_category.insert(0, NEWS_DEFAULT_CATEGORY); self.news_entry_image.delete(0, tk.END); self.news_entry_image.insert(0, NEWS_DEFAULT_IMAGE); self.news_entry_summary.delete(0, tk.END); self.news_text_full_content.delete('1.0', tk.END); self.set_status("Nieuws formulier gewist.", duration_ms=3000); self.news_entry_id.focus()
    def _news_add_article(self):
        print("[NEWS DEBUG] Add article clicked."); self.set_status("Verwerken nieuwsartikel..."); self.root.update_idletasks(); self._news_reset_entry_states()
        article_id = self.news_entry_id.get().strip().lower(); article_date_str = self.news_entry_date.get().strip(); article_title = self.news_entry_title.get().strip(); article_category = self.news_entry_category.get().strip() or NEWS_DEFAULT_CATEGORY; article_image = self.news_entry_image.get().strip() or NEWS_DEFAULT_IMAGE; article_summary = self.news_entry_summary.get().strip(); article_full_content_raw = self.news_text_full_content.get('1.0', tk.END).strip()
        errors = []; focus_widget = None
        if not article_id: 
            errors.append("Nieuws ID is verplicht.")
            try: 
                self.news_entry_id.state(["invalid"])
                focus_widget = self.news_entry_id; 
            except: 
                pass
        elif not _news_is_valid_id(article_id): 
            errors.append("Ongeldig Nieuws ID format (a-z, 0-9, -)."); 
            try: 
                self.news_entry_id.state(["invalid"]); 
                focus_widget = self.news_entry_id; 
            except: 
                pass
        if not article_date_str: errors.append("Nieuws Datum is verplicht.");
        else:
            try: datetime.datetime.strptime(article_date_str, '%Y-%m-%d')
            except ValueError: errors.append("Ongeldig Datum formaat (YYYY-MM-DD)."); 
            try: 
                self.news_entry_date.state(["invalid"]); 
                focus_widget = self.news_entry_date; 
            except: 
                pass
        if not article_title: 
            errors.append("Nieuws Titel is verplicht.")
            try:
                self.news_entry_title.state(["invalid"]); 
                focus_widget = self.news_entry_title; 
            except: 
                pass
        if errors: error_message = "Fout: " + errors[0]; self.set_status(error_message, is_error=True); 
        if focus_widget: 
            focus_widget.focus(); 
            messagebox.showwarning("Validatie Fout", "\n".join(errors), parent=self.root); return
        if any(item.get('id') == article_id for item in self.news_data): 
            error_message = f"Fout: Nieuws Artikel ID '{article_id}' bestaat al."; 
            self.set_status(error_message, is_error=True); 
            try: 
                self.news_entry_id.state(["invalid"]) 
            except: 
                self.news_entry_id.focus()
                messagebox.showerror("Validatie Fout", error_message, parent=self.root); 
                return
            
        processed_content_linked = _news_auto_link_text(article_full_content_raw); processed_content_html = processed_content_linked.replace('\r\n', '<br>\n').replace('\n', '<br>\n'); final_summary = article_summary or article_title
        new_article = {"id": article_id, "date": article_date_str, "title": article_title, "category": article_category, "image": article_image, "summary": final_summary, "full_content": processed_content_html}; print(f"[NEWS DEBUG] Prepared new article: {new_article['id']}")
        self.news_data.insert(0, new_article); save_error = _news_save_data(NEWS_JSON_FILE_PATH, self.news_data)
        if save_error: self.set_status(f"Fout bij opslaan JSON: {save_error}", is_error=True); messagebox.showerror("Opslagfout", f"Kon nieuws niet opslaan:\n{save_error}", parent=self.root)
        else: self.set_status(f"Nieuwsartikel '{article_title}' succesvol toegevoegd.", duration_ms=5000); self._news_populate_treeview(); self._news_clear_form()

    # --- Records Tab Creation & Methods (Keep Existing) ---
    def _create_records_tab(self, parent_frame):
        print("[GUI INFO] Creating Records Tab...")
        top_frame = ttk.Frame(parent_frame); top_frame.pack(fill=tk.X, pady=(0, 5)); middle_frame = ttk.Frame(parent_frame); middle_frame.pack(fill=tk.BOTH, expand=True, pady=5); bottom_frame = ttk.Frame(parent_frame); bottom_frame.pack(fill=tk.X, pady=(5, 0))
        self.records_structure = {}; self.records_current_file_path = None; self.records_current_data = []
        ttk.Label(top_frame, text="Categorie:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky=tk.W); self.records_category_var = tk.StringVar(); self.records_category_combo = ttk.Combobox(top_frame, textvariable=self.records_category_var, state="disabled", width=30); self.records_category_combo.grid(row=0, column=1, padx=(0, 10), pady=5, sticky=tk.W); self.records_category_combo.bind("<<ComboboxSelected>>", self._records_update_type_dropdown)
        ttk.Label(top_frame, text="Record Type:").grid(row=0, column=2, padx=(10, 5), pady=5, sticky=tk.W); self.records_type_var = tk.StringVar(); self.records_type_combo = ttk.Combobox(top_frame, textvariable=self.records_type_var, state="disabled", width=40); self.records_type_combo.grid(row=0, column=3, padx=(0, 10), pady=5, sticky=tk.W)
        self.records_load_button = ttk.Button(top_frame, text="Load Records", command=self._records_load, state=tk.DISABLED); self.records_load_button.grid(row=0, column=4, padx=(10, 0), pady=5)
        columns = ('discipline', 'name', 'performance', 'place', 'date'); self.records_tree = ttk.Treeview(middle_frame, columns=columns, show='headings', selectmode='browse')
        self.records_tree.heading('discipline', text='Discipline'); self.records_tree.column('discipline', width=150, minwidth=100, anchor=tk.W); self.records_tree.heading('name', text='Naam'); self.records_tree.column('name', width=200, minwidth=120, anchor=tk.W); self.records_tree.heading('performance', text='Prestatie'); self.records_tree.column('performance', width=100, minwidth=80, anchor=tk.CENTER); self.records_tree.heading('place', text='Plaats'); self.records_tree.column('place', width=120, minwidth=100, anchor=tk.W); self.records_tree.heading('date', text='Datum'); self.records_tree.column('date', width=100, minwidth=90, anchor=tk.CENTER)
        vsb = ttk.Scrollbar(middle_frame, orient="vertical", command=self.records_tree.yview); hsb = ttk.Scrollbar(middle_frame, orient="horizontal", command=self.records_tree.xview); self.records_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.records_tree.grid(row=0, column=0, sticky='nsew'); vsb.grid(row=0, column=1, sticky='ns'); hsb.grid(row=1, column=0, sticky='ew'); middle_frame.grid_rowconfigure(0, weight=1); middle_frame.grid_columnconfigure(0, weight=1); self.records_tree.bind("<Double-1>", self._records_on_double_click_edit)
        button_area = ttk.Frame(bottom_frame); button_area.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.records_add_button = ttk.Button(button_area, text="Add Record", command=self._records_add_dialog, state=tk.DISABLED); self.records_add_button.pack(side=tk.LEFT, padx=(0,5)); self.records_edit_button = ttk.Button(button_area, text="Edit Selected", command=self._records_edit_dialog, state=tk.DISABLED); self.records_edit_button.pack(side=tk.LEFT, padx=5); self.records_delete_button = ttk.Button(button_area, text="Delete Selected", command=self._records_delete, state=tk.DISABLED); self.records_delete_button.pack(side=tk.LEFT, padx=5); self.records_save_button = ttk.Button(button_area, text="Save Changes to File", command=self._records_save, state=tk.DISABLED); self.records_save_button.pack(side=tk.RIGHT, padx=(5,0))
        self._records_discover_and_populate_categories()
    def _records_discover_and_populate_categories(self):
        print("[RECORDS GUI DEBUG] Discovering categories..."); self.records_structure = _records_discover_files(RECORDS_BASE_DIR_ABSOLUTE); categories = sorted(self.records_structure.keys())
        if not categories: self.set_status("Error: No record category folders found!", is_error=True); messagebox.showerror("Setup Error", f"No category directories found inside:\n{RECORDS_BASE_DIR_ABSOLUTE}", parent=self.root); self.records_category_combo['values'] = []; self.records_category_var.set(""); self.records_type_combo['values'] = []; self.records_type_var.set(""); self.records_category_combo.config(state=tk.DISABLED); self.records_type_combo.config(state=tk.DISABLED); self.records_load_button.config(state=tk.DISABLED); self._records_update_button_states(loaded=False); return
        self.records_category_combo['values'] = categories; self.records_category_var.set(categories[0]); self.records_category_combo.config(state="readonly"); self._records_update_type_dropdown()
        if self.records_type_combo['values']: self.records_load_button.config(state=tk.NORMAL)
        else: self.records_load_button.config(state=tk.DISABLED)
    def _records_update_type_dropdown(self, event=None):
        print("[RECORDS GUI DEBUG] Updating record type dropdown..."); selected_category = self.records_category_var.get(); record_types = sorted(self.records_structure.get(selected_category, {}).keys())
        if record_types: self.records_type_combo['values'] = record_types; self.records_type_var.set(record_types[0]); self.records_type_combo.config(state="readonly"); self.records_load_button.config(state=tk.NORMAL)
        else: self.records_type_combo['values'] = []; self.records_type_var.set(""); self.records_type_combo.config(state=tk.DISABLED); self.records_load_button.config(state=tk.DISABLED); print(f"[RECORDS GUI WARNING] No record types found for '{selected_category}'.")
        self._records_clear_treeview(); self._records_update_button_states(loaded=False); self.records_current_file_path = None; self.records_current_data = []; self.set_status("Select category/type and click Load Records.", duration_ms=4000)
    def _records_update_button_states(self, loaded=False):
        state = tk.NORMAL if loaded else tk.DISABLED; print(f"[RECORDS GUI DEBUG] Updating action button states: {'NORMAL' if loaded else 'DISABLED'}")
        try: self.records_add_button.config(state=state); self.records_edit_button.config(state=tk.DISABLED); self.records_delete_button.config(state=tk.DISABLED); self.records_save_button.config(state=state);
        except tk.TclError as e: print(f"[RECORDS GUI WARNING] Could not update button states: {e}")
        if loaded: self.records_tree.bind("<<TreeviewSelect>>", self._records_on_selection_change)
        else: self.records_tree.unbind("<<TreeviewSelect>>")
    def _records_on_selection_change(self, event=None):
        state = tk.NORMAL if self.records_tree.selection() else tk.DISABLED; self.records_edit_button.config(state=state); self.records_delete_button.config(state=state)
    def _records_clear_treeview(self):
        print("[RECORDS GUI DEBUG] Clearing Treeview."); self.records_tree.unbind("<<TreeviewSelect>>");
        for item in self.records_tree.get_children(): self.records_tree.delete(item)
    def _records_populate_treeview(self, data):
        print(f"[RECORDS GUI DEBUG] Populating Treeview with {len(data)} items."); self._records_clear_treeview()
        for i, record_row in enumerate(data):
            try: padded_row = (list(record_row) + [""] * 5)[:5]; self.records_tree.insert('', tk.END, iid=i, values=padded_row)
            except Exception as e: print(f"[RECORDS GUI ERROR] Failed inserting row {i}: {record_row}\nError: {e}")
        self._records_on_selection_change()
        if data: self.records_tree.bind("<<TreeviewSelect>>", self._records_on_selection_change)
    def _records_load(self):
        category = self.records_category_var.get(); record_type = self.records_type_var.get(); print(f"[RECORDS GUI DEBUG] Load clicked. Cat='{category}', Type='{record_type}'");
        if not category or not record_type: messagebox.showwarning("Selection Missing", "Please select category and record type.", parent=self.root); return
        try: self.records_current_file_path = self.records_structure[category][record_type]; print(f"[RECORDS GUI DEBUG] Loading file: {self.records_current_file_path}")
        except KeyError: messagebox.showerror("Error", f"Internal Error: Path not found for {category} - {record_type}.", parent=self.root); self.records_current_file_path = None; self._records_clear_treeview(); self._records_update_button_states(loaded=False); self.set_status(f"Error finding path for {category} / {record_type}", is_error=True); return
        self.set_status(f"Loading records from {os.path.basename(self.records_current_file_path)}..."); self.root.update_idletasks(); self.records_current_data = _records_parse_html(self.records_current_file_path); self._records_clear_treeview()
        if self.records_current_data is not None: self._records_populate_treeview(self.records_current_data); self._records_update_button_states(loaded=True); self.set_status(f"Loaded {len(self.records_current_data)} records from {os.path.basename(self.records_current_file_path)}.", duration_ms=5000)
        else: self.records_current_data = []; self.set_status(f"Error loading records from {os.path.basename(self.records_current_file_path)}. Check console.", is_error=True); messagebox.showerror("Load Error", f"Failed to parse records from:\n{self.records_current_file_path}\nCheck console log.", parent=self.root); self._records_update_button_states(loaded=False); self.records_current_file_path = None
    def _records_on_double_click_edit(self, event):
        print("[RECORDS GUI DEBUG] Double-click detected.");
        if not self.records_current_file_path or not self.records_tree.selection(): return
        if self.records_edit_button['state'] == tk.NORMAL: print("[RECORDS GUI DEBUG] Initiating edit via double-click."); self._records_edit_dialog()
        else: print("[RECORDS GUI DEBUG] Double-click ignored, edit button disabled.")
    def _records_add_dialog(self):
        if not self.records_current_file_path: messagebox.showwarning("Load Required", "Please load a record file before adding.", parent=self.root); return
        print("[RECORDS GUI DEBUG] Add Record dialog."); RecordDialog(self.root, "Add New Record", None, self._records_process_new)
    def _records_edit_dialog(self):
        print("[RECORDS GUI DEBUG] Edit Record action initiated."); selected_items = self.records_tree.selection();
        if not selected_items: messagebox.showwarning("Selection Required", "Please select a record to edit.", parent=self.root); return
        item_id = selected_items[0]; print(f"[RECORDS GUI DEBUG] Editing item iid: {item_id}")
        try: record_index = int(item_id); initial_data = self.records_current_data[record_index]; print(f"[RECORDS GUI DEBUG] Initial data for edit: {initial_data}"); RecordDialog(self.root, "Edit Record", initial_data, lambda data: self._records_process_edited(record_index, data))
        except (IndexError, ValueError) as e: print(f"[RECORDS GUI ERROR] Edit failed. Index '{item_id}' invalid: {e}"); messagebox.showerror("Error", "Could not retrieve selected record data for editing.", parent=self.root)
    def _records_process_new(self, new_data):
        print(f"[RECORDS GUI DEBUG] Processing new record data: {new_data}")
        if new_data and len(new_data) == 5:
            self.records_current_data.append(new_data); new_item_index = len(self.records_current_data) - 1; new_item_iid = str(new_item_index)
            try: self.records_tree.insert('', tk.END, iid=new_item_iid, values=new_data); self.set_status("New record added (unsaved). Click 'Save Changes'.", duration_ms=5000); self.records_tree.selection_set(new_item_iid); self.records_tree.focus(new_item_iid); self.records_tree.see(new_item_iid)
            except Exception as e: print(f"[RECORDS GUI ERROR] Error adding new item {new_item_iid} to treeview: {e}. Repopulating."); self._records_populate_treeview(self.records_current_data)
        elif new_data: print(f"[RECORDS GUI WARNING] Received invalid data from Add dialog: {new_data}")
        else: print("[RECORDS GUI DEBUG] Add dialog cancelled.")
    def _records_process_edited(self, record_index, updated_data):
        print(f"[RECORDS GUI DEBUG] Processing edited data for index {record_index}: {updated_data}")
        if updated_data and len(updated_data) == 5:
            try: self.records_current_data[record_index] = updated_data; item_iid = str(record_index); self.records_tree.item(item_iid, values=updated_data); self.set_status("Record updated (unsaved). Click 'Save Changes'.", duration_ms=5000); self.records_tree.selection_set(item_iid); self.records_tree.focus(item_iid); self.records_tree.see(item_iid)
            except IndexError: print(f"[RECORDS GUI ERROR] Edit process failed: index {record_index} out of bounds."); messagebox.showerror("Error", "Failed to update record (internal index error). Reload.", parent=self.root)
            except Exception as e: print(f"[RECORDS GUI ERROR] Error updating item {item_iid} in treeview: {e}. Repopulating."); self._records_populate_treeview(self.records_current_data)
        elif updated_data: print(f"[RECORDS GUI WARNING] Received invalid data from Edit dialog: {updated_data}")
        else: print("[RECORDS GUI DEBUG] Edit dialog cancelled.")
    def _records_delete(self):
        print("[RECORDS GUI DEBUG] Delete action initiated."); selected_items = self.records_tree.selection();
        if not selected_items: messagebox.showwarning("Selection Required", "Please select a record to delete.", parent=self.root); return
        item_id = selected_items[0];
        try:
            record_index = int(item_id); record_details_list = self.records_current_data[record_index][:3]; record_details = " | ".join(map(str, record_details_list)); print(f"[RECORDS GUI DEBUG] Attempting to delete index {record_index}: {record_details}")
            if messagebox.askyesno("Confirm Deletion", f"Delete this record?\n\n{record_details}", parent=self.root):
                del self.records_current_data[record_index]; print(f"[RECORDS GUI DEBUG] Record deleted from internal data at index {record_index}."); self._records_populate_treeview(self.records_current_data); self.set_status("Record deleted (unsaved). Click 'Save Changes'.", duration_ms=5000)
            else: print("[RECORDS GUI DEBUG] Deletion cancelled by user.")
        except (IndexError, ValueError) as e: print(f"[RECORDS GUI ERROR] Delete failed. Index '{item_id}' invalid: {e}"); messagebox.showerror("Error", "Could not find selected record to delete.", parent=self.root)
    def _records_save(self):
        print("[RECORDS GUI DEBUG] Save clicked.");
        if not self.records_current_file_path: messagebox.showerror("Error", "No record file loaded. Cannot save.", parent=self.root); self.set_status("Save failed: No file loaded.", is_error=True); return
        data_to_save = self.records_current_data; filename_short = os.path.basename(self.records_current_file_path); print(f"[RECORDS GUI DEBUG] Preparing to save {len(data_to_save)} records to {self.records_current_file_path}")
        if not data_to_save:
            if not messagebox.askyesno("Confirm Empty Save", f"Save empty list to:\n{filename_short}?\nThis removes all records.", icon='warning', parent=self.root): self.set_status("Save cancelled (empty list).", duration_ms=4000); return
        self.set_status(f"Saving changes to {filename_short}..."); self.root.update_idletasks(); success = _records_save_html(self.records_current_file_path, data_to_save)
        if success: self.set_status(f"Changes saved to {filename_short}.", duration_ms=5000); print(f"[RECORDS INFO] Save successful: {self.records_current_file_path}")
        else: self.set_status(f"Error saving changes to {filename_short}. Check console.", is_error=True); messagebox.showerror("Save Error", f"Failed to save changes to:\n{self.records_current_file_path}\nCheck console.", parent=self.root)

    # --- Calendar Tab Creation & Methods (Keep Existing) ---
    def _create_calendar_tab(self, parent_frame):
        print("[GUI INFO] Creating Calendar Tab..."); self.calendar_events_data = []; self.calendar_file_loaded = False
        cal_top_frame = ttk.Frame(parent_frame); cal_top_frame.pack(fill=tk.X, pady=(0, 5)); cal_middle_frame = ttk.Frame(parent_frame); cal_middle_frame.pack(fill=tk.BOTH, expand=True, pady=5); cal_bottom_frame = ttk.Frame(parent_frame); cal_bottom_frame.pack(fill=tk.X, pady=(5, 0))
        self.calendar_refresh_button = ttk.Button(cal_top_frame, text="Refresh Calendar Events", command=self._calendar_load); self.calendar_refresh_button.pack(side=tk.LEFT, padx=5, pady=5)
        cal_columns = ('date', 'name', 'color', 'link'); self.calendar_tree = ttk.Treeview(cal_middle_frame, columns=cal_columns, show='headings', selectmode='browse')
        self.calendar_tree.heading('date', text='Date (YYYY-MM-DD)', anchor=tk.W, command=lambda: self._calendar_sort_treeview('date')); self.calendar_tree.column('date', width=130, minwidth=110, anchor=tk.W, stretch=tk.NO)
        self.calendar_tree.heading('name', text='Event Name', anchor=tk.W, command=lambda: self._calendar_sort_treeview('name')); self.calendar_tree.column('name', width=350, minwidth=200, anchor=tk.W)
        self.calendar_tree.heading('color', text='Color', anchor=tk.W, command=lambda: self._calendar_sort_treeview('color')); self.calendar_tree.column('color', width=80, minwidth=60, anchor=tk.W, stretch=tk.NO)
        self.calendar_tree.heading('link', text='Link (Optional)', anchor=tk.W, command=lambda: self._calendar_sort_treeview('link')); self.calendar_tree.column('link', width=250, minwidth=150, anchor=tk.W)
        cal_vsb = ttk.Scrollbar(cal_middle_frame, orient="vertical", command=self.calendar_tree.yview); cal_hsb = ttk.Scrollbar(cal_middle_frame, orient="horizontal", command=self.calendar_tree.xview); self.calendar_tree.configure(yscrollcommand=cal_vsb.set, xscrollcommand=cal_hsb.set)
        self.calendar_tree.grid(row=0, column=0, sticky='nsew'); cal_vsb.grid(row=0, column=1, sticky='ns'); cal_hsb.grid(row=1, column=0, sticky='ew'); cal_middle_frame.grid_rowconfigure(0, weight=1); cal_middle_frame.grid_columnconfigure(0, weight=1)
        self.calendar_tree.bind("<Double-1>", self._calendar_on_double_click_edit); self._calendar_sort_column = 'date'; self._calendar_sort_reverse = False
        cal_button_area = ttk.Frame(cal_bottom_frame); cal_button_area.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.calendar_add_button = ttk.Button(cal_button_area, text="Add Event", command=self._calendar_add_dialog, state=tk.DISABLED); self.calendar_add_button.pack(side=tk.LEFT, padx=(0,5)); self.calendar_edit_button = ttk.Button(cal_button_area, text="Edit Selected", command=self._calendar_edit_dialog, state=tk.DISABLED); self.calendar_edit_button.pack(side=tk.LEFT, padx=5); self.calendar_delete_button = ttk.Button(cal_button_area, text="Delete Selected", command=self._calendar_delete, state=tk.DISABLED); self.calendar_delete_button.pack(side=tk.LEFT, padx=5); self.calendar_save_button = ttk.Button(cal_button_area, text="Save Calendar Changes", command=self._calendar_save, state=tk.DISABLED); self.calendar_save_button.pack(side=tk.RIGHT, padx=(5,0))
    def _calendar_update_button_states(self, loaded=False):
        state = tk.NORMAL if loaded else tk.DISABLED; print(f"[CALENDAR GUI DEBUG] Updating action button states: {'NORMAL' if loaded else 'DISABLED'}")
        try: self.calendar_add_button.config(state=state); self.calendar_edit_button.config(state=tk.DISABLED); self.calendar_delete_button.config(state=tk.DISABLED); self.calendar_save_button.config(state=state);
        except tk.TclError as e: print(f"[CALENDAR GUI WARNING] Could not update calendar button states: {e}")
        if loaded: self.calendar_tree.bind("<<TreeviewSelect>>", self._calendar_on_selection_change)
        else: self.calendar_tree.unbind("<<TreeviewSelect>>")
    def _calendar_on_selection_change(self, event=None):
        state = tk.NORMAL if self.calendar_tree.selection() else tk.DISABLED; self.calendar_edit_button.config(state=state); self.calendar_delete_button.config(state=state)
    def _calendar_clear_treeview(self):
        print("[CALENDAR GUI DEBUG] Clearing Calendar Treeview."); self.calendar_tree.unbind("<<TreeviewSelect>>");
        for item in self.calendar_tree.get_children(): self.calendar_tree.delete(item)
    def _calendar_populate_treeview(self):
        print(f"[CALENDAR GUI DEBUG] Populating Calendar Treeview with {len(self.calendar_events_data)} events."); self._calendar_clear_treeview(); key_map = {'date': 'date', 'name': 'name', 'color': 'color', 'link': 'link'}; sort_key_name = key_map.get(self._calendar_sort_column, 'date')
        def sort_func(event_dict): val = event_dict.get(sort_key_name); return (val.lower() if sort_key_name != 'date' else val) if isinstance(val, str) else "" if val is None else str(val).lower()
        display_data_dicts = sorted(self.calendar_events_data, key=sort_func, reverse=self._calendar_sort_reverse); original_indices = {id(event): index for index, event in enumerate(self.calendar_events_data)}
        for event_dict in display_data_dicts:
            try: original_index = original_indices[id(event_dict)]; item_iid = str(original_index); values = [event_dict['date'], event_dict['name'], event_dict['color'], event_dict.get('link') or ""]; self.calendar_tree.insert('', tk.END, iid=item_iid, values=values, tags=('event_row',))
            except KeyError: print(f"[CALENDAR GUI WARNING] Could not find original index for event: {event_dict}")
            except Exception as e: print(f"[CALENDAR GUI ERROR] Failed inserting row for event: {event_dict}\nError: {e}")
        self._calendar_update_sort_indicator(); self._calendar_on_selection_change()
        if self.calendar_events_data: self.calendar_tree.bind("<<TreeviewSelect>>", self._calendar_on_selection_change)
    def _calendar_sort_treeview(self, col):
        if col == self._calendar_sort_column: self._calendar_sort_reverse = not self._calendar_sort_reverse
        else: self._calendar_sort_column = col; self._calendar_sort_reverse = False
        print(f"[CALENDAR GUI DEBUG] Sorting by '{self._calendar_sort_column}', reverse={self._calendar_sort_reverse}"); self._calendar_populate_treeview()
    def _calendar_update_sort_indicator(self):
         arrow = ' ↓' if self._calendar_sort_reverse else ' ↑'; headings = {'date': "Date (YYYY-MM-DD)", 'name': "Event Name", 'color': "Color", 'link': "Link (Optional)"}
         for c, base_text in headings.items(): self.calendar_tree.heading(c, text=base_text + (arrow if c == self._calendar_sort_column else ""))
    def _calendar_load(self):
        print("[CALENDAR GUI DEBUG] Load/Refresh calendar clicked.");
        if not os.path.exists(CALENDAR_HTML_FILE_PATH): messagebox.showerror("File Not Found", f"Calendar file not found:\n{CALENDAR_HTML_FILE_PATH}", parent=self.root); self.set_status("Error: Calendar HTML file not found.", is_error=True); self._calendar_update_button_states(loaded=False); self.calendar_file_loaded = False; return
        self.set_status("Loading/Refreshing calendar events from HTML..."); self.root.update_idletasks(); loaded_events = _calendar_parse_html(CALENDAR_HTML_FILE_PATH); self._calendar_clear_treeview(); self.calendar_events_data = []
        if loaded_events is not None: self.calendar_events_data = loaded_events; self.calendar_file_loaded = True; self._calendar_sort_column = 'date'; self._calendar_sort_reverse = False; self._calendar_populate_treeview(); self._calendar_update_button_states(loaded=True); self.set_status(f"Loaded {len(self.calendar_events_data)} calendar events.", duration_ms=5000)
        else: self.calendar_file_loaded = False; self._calendar_update_button_states(loaded=False); self.set_status("Error loading calendar events. Check console.", is_error=True); messagebox.showerror("Load Error", f"Failed to parse events from:\n{CALENDAR_HTML_FILE_PATH}\nCheck console log.", parent=self.root)
    def _calendar_on_double_click_edit(self, event):
        print("[CALENDAR GUI DEBUG] Double-click detected.");
        if not self.calendar_file_loaded or not self.calendar_tree.selection(): return
        if self.calendar_edit_button['state'] == tk.NORMAL: print("[CALENDAR GUI DEBUG] Initiating edit via double-click."); self._calendar_edit_dialog()
        else: print("[CALENDAR GUI DEBUG] Double-click ignored, edit button disabled.")
    def _calendar_add_dialog(self):
        if not self.calendar_file_loaded: messagebox.showwarning("Load Required", "Please load calendar data before adding.", parent=self.root); return
        print("[CALENDAR GUI DEBUG] Add Event dialog initiated."); CalendarEventDialog(self.root, "Add Calendar Event", None, self._calendar_process_new)
    def _calendar_edit_dialog(self):
        print("[CALENDAR GUI DEBUG] Edit Event action initiated."); selected_items = self.calendar_tree.selection();
        if not selected_items: messagebox.showwarning("Selection Required", "Please select an event to edit.", parent=self.root); return
        item_iid = selected_items[0];
        try: record_index = int(item_iid); initial_data = self.calendar_events_data[record_index]; print(f"[CALENDAR GUI DEBUG] Initial data for edit (index {record_index}): {initial_data}"); CalendarEventDialog(self.root, "Edit Calendar Event", initial_data, lambda data: self._calendar_process_edited(record_index, data))
        except (IndexError, ValueError) as e: print(f"[CALENDAR GUI ERROR] Edit failed. Cannot find index '{item_iid}': {e}"); messagebox.showerror("Error", "Could not find selected event data for editing.", parent=self.root)
    def _calendar_process_new(self, new_event_dict):
        print(f"[CALENDAR GUI DEBUG] Processing new event data: {new_event_dict}")
        if new_event_dict:
            self.calendar_events_data.append(new_event_dict); new_original_index = len(self.calendar_events_data) - 1; new_item_iid = str(new_original_index); self._calendar_populate_treeview(); self.set_status("New event added (unsaved). Click 'Save Changes'.", duration_ms=5000)
            try: self.calendar_tree.selection_set(new_item_iid); self.calendar_tree.focus(new_item_iid); self.calendar_tree.see(new_item_iid)
            except tk.TclError: print(f"[CALENDAR GUI WARNING] Could not select/focus new item {new_item_iid}.")
        else: print("[CALENDAR GUI DEBUG] Add event dialog cancelled.")
    def _calendar_process_edited(self, record_index, updated_event_dict):
        print(f"[CALENDAR GUI DEBUG] Processing edited event for index {record_index}: {updated_event_dict}")
        if updated_event_dict:
            try:
                self.calendar_events_data[record_index] = updated_event_dict; self._calendar_populate_treeview(); self.set_status("Event updated (unsaved). Click 'Save Changes'.", duration_ms=5000); item_iid = str(record_index)
                try:
                    if self.calendar_tree.exists(item_iid): self.calendar_tree.selection_set(item_iid); self.calendar_tree.focus(item_iid); self.calendar_tree.see(item_iid)
                    else: print(f"[CALENDAR GUI WARNING] Item {item_iid} no longer exists after edit/repop.")
                except tk.TclError: print(f"[CALENDAR GUI WARNING] Could not re-select edited item {item_iid}.")
            except IndexError: print(f"[CALENDAR GUI ERROR] Edit process failed: index {record_index} out of bounds."); messagebox.showerror("Error", "Failed to update event (index error).", parent=self.root)
        else: print("[CALENDAR GUI DEBUG] Edit event dialog cancelled.")
    def _calendar_delete(self):
        print("[CALENDAR GUI DEBUG] Delete event action initiated."); selected_items = self.calendar_tree.selection()
        if not selected_items: messagebox.showwarning("Selection Required", "Please select an event to delete.", parent=self.root); return
        item_iid = selected_items[0]
        try: 
            record_index = int(item_iid); 
            event_details = f"{self.calendar_events_data[record_index]['date']} | {self.calendar_events_data[record_index]['name']}"; 
            print(f"[CALENDAR GUI DEBUG] Attempting to delete event index {record_index}: {event_details}")
            if messagebox.askyesno("Confirm Deletion", f"Delete this event?\n\n{event_details}", parent=self.root):
                del self.calendar_events_data[record_index]; print(f"[CALENDAR INFO] Deleted event from data index {record_index}."); self._calendar_populate_treeview(); self.set_status("Event deleted (unsaved). Click 'Save Changes'.", duration_ms=5000)
            else: print("[CALENDAR GUI DEBUG] Deletion cancelled.")
        except (IndexError, ValueError) as e: print(f"[CALENDAR GUI ERROR] Delete failed. Cannot find index '{item_iid}': {e}"); messagebox.showerror("Error", "Could not find selected event to delete.", parent=self.root)
    def _calendar_save(self):
        print("[CALENDAR GUI DEBUG] Save calendar clicked.")
        if not self.calendar_file_loaded: messagebox.showwarning("Load First", "Please load calendar data before saving.", parent=self.root); self.set_status("Save failed: Calendar data not loaded.", is_error=True); return
        self.calendar_events_data.sort(key=lambda x: x['date']); data_to_save = self.calendar_events_data; filename_short = os.path.basename(CALENDAR_HTML_FILE_PATH); print(f"[CALENDAR GUI DEBUG] Saving {len(data_to_save)} events to {CALENDAR_HTML_FILE_PATH}"); self.set_status(f"Saving calendar changes to {filename_short}..."); self.root.update_idletasks(); success = _calendar_save_html(CALENDAR_HTML_FILE_PATH, data_to_save)
        if success: self.set_status(f"Calendar changes saved to {filename_short}.", duration_ms=5000); print(f"[CALENDAR INFO] Save successful: {CALENDAR_HTML_FILE_PATH}")
        else: self.set_status(f"Error saving calendar changes to {filename_short}. Check console.", is_error=True); messagebox.showerror("Save Error", f"Failed to save changes to:\n{CALENDAR_HTML_FILE_PATH}\nCheck console.", parent=self.root)

    # --- Reports Tab Creation & Methods (Keep Existing) ---
    def _create_reports_tab(self, parent_frame):
        print("[GUI INFO] Creating Reports Tab..."); self.reports_data = {}; self.reports_file_loaded = False; self._reports_sort_column = 'year'; self._reports_sort_reverse = True
        rep_controls_frame = ttk.Frame(parent_frame); rep_controls_frame.pack(fill=tk.X, pady=(0, 10)); rep_tree_frame = ttk.Frame(parent_frame); rep_tree_frame.pack(fill=tk.BOTH, expand=True, pady=5); rep_actions_frame = ttk.Frame(parent_frame); rep_actions_frame.pack(fill=tk.X, pady=(10, 0))
        self.reports_refresh_button = ttk.Button(rep_controls_frame, text="Refresh Reports List", command=self._reports_load); self.reports_refresh_button.grid(row=0, column=0, rowspan=4, padx=5, pady=5, sticky=tk.W+tk.N); ttk.Separator(rep_controls_frame, orient=tk.VERTICAL).grid(row=0, column=1, rowspan=4, sticky="ns", padx=15, pady=5)
        ttk.Label(rep_controls_frame, text="Add New Report Link:", style="Bold.TLabel").grid(row=0, column=2, columnspan=3, sticky=tk.W, padx=5, pady=(5,2)); ttk.Label(rep_controls_frame, text="Year:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2); self.reports_year_var = tk.StringVar(); self.reports_year_combo = ttk.Combobox(rep_controls_frame, textvariable=self.reports_year_var, width=12, state=tk.DISABLED); self.reports_year_combo.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2); self.reports_year_combo.bind("<<ComboboxSelected>>", self._reports_toggle_new_year_entry)
        self.reports_new_year_entry = ttk.Entry(rep_controls_frame, width=8, state=tk.DISABLED); self.reports_new_year_entry.grid(row=1, column=4, sticky=tk.W, padx=5, pady=2); self.reports_new_year_entry.insert(0, "YYYY"); self.reports_new_year_entry.bind("<FocusIn>", lambda e: self.reports_new_year_entry.delete(0, tk.END) if self.reports_new_year_entry.get() == "YYYY" else None); self.reports_new_year_entry.bind("<FocusOut>", lambda e: self.reports_new_year_entry.insert(0, "YYYY") if not self.reports_new_year_entry.get() else None)
        ttk.Label(rep_controls_frame, text="Link Text:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2); self.reports_link_text_entry = ttk.Entry(rep_controls_frame, width=45, state=tk.DISABLED); self.reports_link_text_entry.grid(row=2, column=3, columnspan=3, sticky=tk.W+tk.E, padx=5, pady=2); self.reports_upload_button = ttk.Button(rep_controls_frame, text="Browse Document & Add Link", command=self._reports_browse_and_upload, state=tk.DISABLED); self.reports_upload_button.grid(row=3, column=3, columnspan=3, sticky=tk.W, padx=5, pady=(5,5)); rep_controls_frame.columnconfigure(3, weight=1)
        rep_columns = ('year', 'text', 'filename'); self.reports_tree = ttk.Treeview(rep_tree_frame, columns=rep_columns, show='headings', selectmode='browse')
        self.reports_tree.heading('year', text='Year', anchor=tk.W, command=lambda: self._reports_sort_treeview('year')); self.reports_tree.column('year', width=80, anchor=tk.W, stretch=tk.NO); self.reports_tree.heading('text', text='Link Text', anchor=tk.W, command=lambda: self._reports_sort_treeview('text')); self.reports_tree.column('text', width=400, minwidth=250, anchor=tk.W); self.reports_tree.heading('filename', text='Filename (in docs folder)', anchor=tk.W, command=lambda: self._reports_sort_treeview('filename')); self.reports_tree.column('filename', width=350, minwidth=200, anchor=tk.W)
        rep_vsb = ttk.Scrollbar(rep_tree_frame, orient="vertical", command=self.reports_tree.yview); rep_hsb = ttk.Scrollbar(rep_tree_frame, orient="horizontal", command=self.reports_tree.xview); self.reports_tree.configure(yscrollcommand=rep_vsb.set, xscrollcommand=rep_hsb.set)
        self.reports_tree.grid(row=0, column=0, sticky='nsew'); rep_vsb.grid(row=0, column=1, sticky='ns'); rep_hsb.grid(row=1, column=0, sticky='ew'); rep_tree_frame.grid_rowconfigure(0, weight=1); rep_tree_frame.grid_columnconfigure(0, weight=1)
        rep_button_area = ttk.Frame(rep_actions_frame); rep_button_area.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.reports_delete_button = ttk.Button(rep_button_area, text="Delete Selected Link", command=self._reports_delete, state=tk.DISABLED); self.reports_delete_button.pack(side=tk.LEFT, padx=(0,5)); self.reports_save_button = ttk.Button(rep_button_area, text="Save Changes to HTML", command=self._reports_save, state=tk.DISABLED); self.reports_save_button.pack(side=tk.RIGHT, padx=(5,0))
    def _reports_update_ui_states(self, loaded=False):
        add_form_state = tk.NORMAL if loaded else tk.DISABLED; combo_state = "readonly" if loaded else tk.DISABLED; print(f"[REPORTS GUI DEBUG] Updating UI states: {'LOADED' if loaded else 'NOT LOADED'}")
        try:
            self.reports_save_button.config(state=add_form_state); self.reports_upload_button.config(state=add_form_state); self.reports_delete_button.config(state=tk.DISABLED); self.reports_year_combo.config(state=combo_state); self.reports_link_text_entry.config(state=add_form_state); is_new_year_selected = self.reports_year_var.get() == "<Nieuw Jaar>"
            self.reports_new_year_entry.config(state=tk.NORMAL if loaded and is_new_year_selected else tk.DISABLED)
            if loaded: self._reports_update_year_dropdown(); self.reports_tree.bind("<<TreeviewSelect>>", self._reports_on_selection_change)
            else: self.reports_year_combo['values'] = []; self.reports_year_var.set(""); self.reports_link_text_entry.delete(0, tk.END); self.reports_new_year_entry.delete(0, tk.END); self.reports_new_year_entry.insert(0, "YYYY"); self.reports_tree.unbind("<<TreeviewSelect>>")
        except Exception as e: print(f"[REPORTS GUI ERROR] Unexpected error updating UI states: {e}")
    def _reports_on_selection_change(self, event=None):
        self.reports_delete_button.config(state=tk.NORMAL if self.reports_tree.selection() else tk.DISABLED)
    def _reports_update_year_dropdown(self):
        if not self.reports_file_loaded: self.reports_year_combo['values'] = []; self.reports_year_var.set(""); return
        years = sorted([y for y in self.reports_data.keys() if y.isdigit()], key=int, reverse=True); current_system_year = str(datetime.date.today().year); new_year_option = "<Nieuw Jaar>"; options = [new_year_option]; unique_options = []
        if current_system_year not in years: options.append(current_system_year)
        options.extend(years);
        for opt in options:
            if opt not in unique_options: unique_options.append(opt)
        self.reports_year_combo['values'] = unique_options; current_selection = self.reports_year_var.get()
        if current_selection not in unique_options:
             if current_system_year in unique_options: self.reports_year_var.set(current_system_year)
             elif years: self.reports_year_var.set(years[0])
             else: self.reports_year_var.set(new_year_option)
        self._reports_toggle_new_year_entry()
    def _reports_toggle_new_year_entry(self, event=None):
        is_new_year = self.reports_year_var.get() == "<Nieuw Jaar>"; new_state = tk.NORMAL if self.reports_file_loaded and is_new_year else tk.DISABLED; self.reports_new_year_entry.config(state=new_state)
        if new_state == tk.NORMAL and self.reports_new_year_entry.get() == "YYYY": self.reports_new_year_entry.delete(0, tk.END)
        elif new_state == tk.DISABLED and not self.reports_new_year_entry.get(): self.reports_new_year_entry.insert(0, "YYYY")
    def _reports_clear_treeview(self):
        print("[REPORTS GUI DEBUG] Clearing Reports Treeview."); self.reports_tree.unbind("<<TreeviewSelect>>");
        for item in self.reports_tree.get_children(): self.reports_tree.delete(item)
    def _reports_populate_treeview(self):
        print(f"[REPORTS GUI DEBUG] Populating Reports Treeview with {sum(len(v) for v in self.reports_data.values())} items."); self._reports_clear_treeview(); flat_reports = []
        for year, reports_list in self.reports_data.items():
            for index, report_dict in enumerate(reports_list): flat_reports.append({'year': year, 'text': report_dict['text'], 'filename': report_dict['filename'], 'path': report_dict['path'], 'original_index': index})
        def sort_key_func(item): col_value = item.get(self._reports_sort_column, ""); return int(col_value) if self._reports_sort_column == 'year' and isinstance(col_value, str) and col_value.isdigit() else 0 if self._reports_sort_column == 'year' else col_value.lower() if isinstance(col_value, str) else col_value
        sorted_flat_reports = sorted(flat_reports, key=sort_key_func, reverse=self._reports_sort_reverse)
        for item_data in sorted_flat_reports:
            item_id = f"{item_data['year']}-{item_data['original_index']}"; values = (item_data['year'], item_data['text'], item_data['filename'])
            try: self.reports_tree.insert('', tk.END, iid=item_id, values=values, tags=('report_row',))
            except Exception as e: print(f"[REPORTS GUI ERROR] Failed inserting report row {item_id}: {values}\nError: {e}")
        self._reports_update_sort_indicator(); self._reports_on_selection_change()
        if self.reports_data: self.reports_tree.bind("<<TreeviewSelect>>", self._reports_on_selection_change)
    def _reports_sort_treeview(self, col):
        if col == self._reports_sort_column: self._reports_sort_reverse = not self._reports_sort_reverse
        else: self._reports_sort_column = col; self._reports_sort_reverse = (col == 'year')
        print(f"[REPORTS GUI DEBUG] Sorting Reports by '{self._reports_sort_column}', reverse={self._reports_sort_reverse}"); self._reports_populate_treeview()
    def _reports_update_sort_indicator(self):
         arrow = ' ↓' if self._reports_sort_reverse else ' ↑'; headings = {'year': "Year", 'text': "Link Text", 'filename': "Filename (in docs folder)"}
         for c, base_text in headings.items(): self.reports_tree.heading(c, text=base_text + (arrow if c == self._reports_sort_column else ""))
    def _reports_load(self):
        print("[REPORTS GUI DEBUG] Load/Refresh reports clicked.");
        if not os.path.exists(REPORTS_HTML_FILE_PATH): messagebox.showerror("File Not Found", f"Reports HTML file not found:\n{REPORTS_HTML_FILE_PATH}", parent=self.root); self.set_status("Error: Reports HTML file not found.", is_error=True); self._reports_update_ui_states(loaded=False); self.reports_file_loaded = False; return
        self.set_status("Loading/Refreshing reports from HTML..."); self.root.update_idletasks(); self._reports_clear_treeview(); self.reports_data = {}; self.reports_file_loaded = False; loaded_data, error_msg = _reports_parse_html(REPORTS_HTML_FILE_PATH)
        if error_msg is None: self.reports_data = loaded_data; self.reports_file_loaded = True; self._reports_sort_column = 'year'; self._reports_sort_reverse = True; self._reports_populate_treeview(); self._reports_update_ui_states(loaded=True); report_count = sum(len(v) for v in self.reports_data.values()); self.set_status(f"Loaded {report_count} report links successfully.", duration_ms=5000)
        else: self._reports_update_ui_states(loaded=False); self.set_status(f"Error loading reports: {error_msg}", is_error=True); messagebox.showerror("Load Error", f"Failed to parse reports from HTML:\n{error_msg}", parent=self.root)
    def _reports_browse_and_upload(self):
        print("[REPORTS GUI DEBUG] Browse and Add Report Link clicked.");
        if not self.reports_file_loaded: messagebox.showwarning("Load Required", "Please load reports before adding links.", parent=self.root); self.set_status("Error: Load reports first.", is_error=True); return
        selected_year_str = self.reports_year_var.get(); target_year = None
        if selected_year_str == "<Nieuw Jaar>": new_year_input = self.reports_new_year_entry.get().strip();
        elif selected_year_str and selected_year_str.isdigit(): target_year = selected_year_str
        else: messagebox.showerror("Invalid Input", "Select target year or '<Nieuw Jaar>'.", parent=self.root); self.reports_year_combo.focus(); return
        link_text = self.reports_link_text_entry.get().strip()
        if not link_text: messagebox.showerror("Invalid Input", "Enter link text.", parent=self.root); self.reports_link_text_entry.focus(); return
        filetypes = (("Document Files", "*.pdf *.doc *.docx *.odt *.xls *.xlsx *.ppt *.pptx"), ("All files", "*.*")); initial_dir = REPORTS_DOCS_DEST_DIR_ABSOLUTE if os.path.isdir(REPORTS_DOCS_DEST_DIR_ABSOLUTE) else APP_BASE_DIR; source_path = filedialog.askopenfilename(title="Select Report Document", filetypes=filetypes, initialdir=initial_dir)
        if not source_path: self.set_status("Document selection cancelled.", duration_ms=3000); return
        filename = os.path.basename(source_path);
        try: os.makedirs(REPORTS_DOCS_DEST_DIR_ABSOLUTE, exist_ok=True); print(f"[REPORTS DEBUG] Ensured dest dir exists: {REPORTS_DOCS_DEST_DIR_ABSOLUTE}")
        except OSError as e: messagebox.showerror("Directory Error", f"Could not create destination directory:\n{REPORTS_DOCS_DEST_DIR_ABSOLUTE}\nError: {e}", parent=self.root); self.set_status(f"Error creating dest dir: {e}", is_error=True); return
        dest_path_absolute = os.path.join(REPORTS_DOCS_DEST_DIR_ABSOLUTE, filename); href_path_relative = str(pathlib.PurePosixPath(REPORTS_DOCS_HREF_DIR_RELATIVE) / filename); print(f"[REPORTS DEBUG] Source: '{source_path}', Dest Abs: '{dest_path_absolute}', Href Rel: '{href_path_relative}'")
        if os.path.exists(dest_path_absolute):
            if not messagebox.askyesno("Confirm Overwrite", f"File '{filename}' already exists.\nReplace existing file?", icon='warning', parent=self.root): self.set_status("Upload cancelled (overwrite declined).", duration_ms=4000); return
        try: shutil.copy2(source_path, dest_path_absolute); print(f"[REPORTS INFO] Copied '{filename}' to destination.")
        except Exception as e: messagebox.showerror("Upload Error", f"Could not copy document:\n{dest_path_absolute}\nError: {e}", parent=self.root); self.set_status(f"Error copying document: {e}", is_error=True); return
        new_report_entry = {'text': link_text, 'filename': filename, 'path': href_path_relative}
        if target_year not in self.reports_data: self.reports_data[target_year] = []; print(f"[REPORTS INFO] Created new year entry: {target_year}"); self._reports_update_year_dropdown(); self.reports_year_var.set(target_year)
        existing_filenames = [item['filename'] for item in self.reports_data[target_year]]
        if filename in existing_filenames: print(f"[REPORTS WARNING] Filename '{filename}' already exists in year {target_year}.");
        self.reports_data[target_year].append(new_report_entry); self._reports_populate_treeview(); self.set_status(f"Report link '{link_text}' added for {target_year} (unsaved).", duration_ms=5000); self.reports_link_text_entry.delete(0, tk.END)
    def _reports_delete(self):
        print("[REPORTS GUI DEBUG] Delete report link action initiated."); selected_items = self.reports_tree.selection();
        if not selected_items: messagebox.showwarning("Selection Required", "Select a report link to delete.", parent=self.root); return
        item_id = selected_items[0];
        try:
            year, original_index_str = item_id.split('-', 1); original_index = int(original_index_str);
            if year not in self.reports_data or not isinstance(self.reports_data[year], list) or original_index >= len(self.reports_data[year]): raise ValueError(f"Data for item ID '{item_id}' not found.")
            report_to_delete = self.reports_data[year][original_index]; details = f"Year: {year}\nLink Text: {report_to_delete['text']}\nFilename: {report_to_delete['filename']}"; print(f"[REPORTS GUI DEBUG] Attempting delete: ID='{item_id}', Details='{details}'")
            if messagebox.askyesno("Confirm Link Deletion", f"Remove this link entry?\n\n{details}\n\n(Does NOT delete file '{report_to_delete['filename']}')", icon='warning', parent=self.root):
                del self.reports_data[year][original_index]; print(f"[REPORTS INFO] Deleted link entry index {original_index} for year {year}.")
                if not self.reports_data[year]: del self.reports_data[year]; print(f"[REPORTS INFO] Removed empty year: {year}"); self._reports_update_year_dropdown()
                self._reports_populate_treeview(); self.set_status("Report link removed (unsaved). Click 'Save Changes'.", duration_ms=5000)
            else: print("[REPORTS GUI DEBUG] Link deletion cancelled.")
        except (ValueError, KeyError, IndexError, TypeError) as e: print(f"[REPORTS GUI ERROR] Failed delete for ID '{item_id}': {e}"); messagebox.showerror("Error", f"Could not delete link.\nError: {e}\nTry reloading.", parent=self.root)
    def _reports_save(self):
        print("[REPORTS GUI DEBUG] Save reports clicked.");
        if not self.reports_file_loaded: messagebox.showwarning("Load First", "Load reports data before saving.", parent=self.root); self.set_status("Save failed: Reports data not loaded.", is_error=True); return
        data_to_save = self.reports_data; report_count = sum(len(v) for v in data_to_save.values()); filename_short = os.path.basename(REPORTS_HTML_FILE_PATH); print(f"[REPORTS GUI DEBUG] Saving {report_count} links across {len(data_to_save)} years to {REPORTS_HTML_FILE_PATH}")
        if not data_to_save:
            if not messagebox.askyesno("Confirm Empty Save", f"Reports list is empty.\nSave changes to:\n{filename_short}?\n(Removes #reports-section content)", icon='warning', parent=self.root): self.set_status("Save cancelled (empty list).", duration_ms=4000); return
        self.set_status(f"Saving report links to {filename_short}..."); self.root.update_idletasks(); success, error_msg = _reports_save_html(REPORTS_HTML_FILE_PATH, data_to_save)
        if success: self.set_status(f"Report links saved to {filename_short}.", duration_ms=5000); print(f"[REPORTS INFO] Save successful: {REPORTS_HTML_FILE_PATH}")
        else: self.set_status(f"Error saving report links: {error_msg}. Check console.", is_error=True); messagebox.showerror("Save Error", f"Failed to save changes to:\n{REPORTS_HTML_FILE_PATH}\nError: {error_msg}\nCheck console.", parent=self.root)

    # --- Images Tab Creation & Methods (NEW) ---
    def _create_images_tab(self, parent_frame):
        print("[GUI INFO] Creating Images Tab...")
        self.images_found_list = [] # List of dicts for each <img> reference
        self.images_by_abs_path = {} # Dict mapping abs_path -> { 'usage_count': N, 'src_list': [], 'html_files': [], 'iid_list': [] }
        self.images_selected_abs_path = None
        self._images_scan_running = False
        self._image_preview_widget = None # Keep reference to PhotoImage to prevent garbage collection

        # Main layout: PanedWindow (Left: Tree+Controls, Right: Preview+Actions)
        pw_main = ttk.PanedWindow(parent_frame, orient=tk.HORIZONTAL)
        pw_main.pack(fill=tk.BOTH, expand=True)

        # --- Left Pane: Treeview and Scan/Search ---
        left_frame = ttk.Frame(pw_main, padding=(0, 0, 5, 0)) # Padding on right side
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        img_scan_frame = ttk.Frame(left_frame)
        img_scan_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.images_refresh_button = ttk.Button(img_scan_frame, text="Rescan HTML for Images", command=self._images_scan_files)
        self.images_refresh_button.pack(side=tk.LEFT, padx=(0, 5))
        # Add search later if needed

        img_tree_frame = ttk.Frame(left_frame)
        img_tree_frame.grid(row=1, column=0, sticky="nsew")
        img_tree_frame.grid_rowconfigure(0, weight=1)
        img_tree_frame.grid_columnconfigure(0, weight=1)

        img_columns = ('filename', 'path', 'exists', 'usage')
        self.images_tree = ttk.Treeview(img_tree_frame, columns=img_columns, show='headings', selectmode='browse')
        self.images_tree.heading('filename', text='Filename', anchor=tk.W)
        self.images_tree.column('filename', width=200, minwidth=150, anchor=tk.W)
        self.images_tree.heading('path', text='Relative Path', anchor=tk.W)
        self.images_tree.column('path', width=300, minwidth=200, anchor=tk.W)
        self.images_tree.heading('exists', text='Exists?', anchor=tk.CENTER)
        self.images_tree.column('exists', width=60, minwidth=50, anchor=tk.CENTER, stretch=tk.NO)
        self.images_tree.heading('usage', text='Uses', anchor=tk.CENTER)
        self.images_tree.column('usage', width=50, minwidth=40, anchor=tk.CENTER, stretch=tk.NO)

        img_vsb = ttk.Scrollbar(img_tree_frame, orient="vertical", command=self.images_tree.yview)
        img_hsb = ttk.Scrollbar(img_tree_frame, orient="horizontal", command=self.images_tree.xview)
        self.images_tree.configure(yscrollcommand=img_vsb.set, xscrollcommand=img_hsb.set)
        self.images_tree.grid(row=0, column=0, sticky='nsew')
        img_vsb.grid(row=0, column=1, sticky='ns')
        img_hsb.grid(row=1, column=0, sticky='ew')
        self.images_tree.bind("<<TreeviewSelect>>", self._images_on_select)
        # Define tags for styling missing files
        self.images_tree.tag_configure('missing', foreground='red')

        pw_main.add(left_frame, weight=2) # Give treeview more initial space

        # --- Right Pane: Preview and Actions ---
        right_frame = ttk.Frame(pw_main, padding=(5, 0, 0, 0)) # Padding on left side
        right_frame.grid_rowconfigure(1, weight=1) # Let preview expand slightly
        right_frame.grid_columnconfigure(0, weight=1)

        img_actions_frame = ttk.Labelframe(right_frame, text=" Image Actions ", padding=10)
        img_actions_frame.grid(row=0, column=0, sticky="new")
        img_actions_frame.columnconfigure(0, weight=1) # Allow buttons to space out if needed

        self.images_add_button = ttk.Button(img_actions_frame, text="Add New Image...", command=self._images_add_dialog)
        self.images_add_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.images_change_button = ttk.Button(img_actions_frame, text="Change Selected Image File...", command=self._images_change, state=tk.DISABLED)
        self.images_change_button.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.images_delete_button = ttk.Button(img_actions_frame, text="Delete Selected Image File...", command=self._images_delete, state=tk.DISABLED)
        self.images_delete_button.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        ttk.Label(img_actions_frame, text="", justify=tk.LEFT, style="Warning.TLabel").grid(row=3, column=0, padx=5, pady=(10, 5), sticky="w")

        img_preview_frame = ttk.Labelframe(right_frame, text=" Preview ", padding=10)
        img_preview_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        img_preview_frame.grid_rowconfigure(0, weight=1)
        img_preview_frame.grid_columnconfigure(0, weight=1)

        # Create a fixed-size frame for the preview label to prevent layout shifts
        preview_outer_frame = ttk.Frame(img_preview_frame, width=IMAGE_PREVIEW_MAX_WIDTH+10, height=IMAGE_PREVIEW_MAX_HEIGHT+10) # Add padding
        preview_outer_frame.grid(row=0, column=0, sticky="nsew")
        preview_outer_frame.grid_propagate(False) # Prevent frame from shrinking to label size
        preview_outer_frame.grid_rowconfigure(0, weight=1)
        preview_outer_frame.grid_columnconfigure(0, weight=1)

        self.images_preview_label = ttk.Label(preview_outer_frame, text="Select an image from the list", anchor=tk.CENTER, relief=tk.GROOVE, background="lightgrey")
        self.images_preview_label.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.images_path_label = ttk.Label(img_preview_frame, text="Path: ", wraplength=IMAGE_PREVIEW_MAX_WIDTH+50, justify=tk.LEFT, style="Desc.TLabel")
        self.images_path_label.grid(row=1, column=0, sticky="ew", padx=5, pady=(5, 0))

        pw_main.add(right_frame, weight=1)

    def _images_scan_files(self):
        """Scans HTML files for image tags."""
        if self._images_scan_running: print("[IMAGE SCAN WARNING] Scan already in progress."); return
        self._images_scan_running = True
        self.images_refresh_button.config(state=tk.DISABLED, text="Scanning...")
        self.set_status("Scanning HTML files for images...")
        self.root.update_idletasks()

        self.images_found_list = [] # Reset list of all <img> occurrences
        # self.text_editor_parsed_soups is used to store/reuse parsed files
        self._images_clear_treeview()
        self._images_reset_preview_area()
        # Keep existing buttons disabled until selection

        html_files, file_count = _general_html_find_files(HTML_SCAN_TARGET_PATHS_ABSOLUTE)
        processed_files = 0; total_images_found = 0

        for i, file_path in enumerate(html_files):
            self.set_status(f"Scanning file {i+1}/{file_count} for images: {os.path.basename(file_path)}...")
            self.root.update_idletasks()
            images_in_file = _images_parse_file(file_path, self.text_editor_parsed_soups, self.images_found_list)
            if images_in_file > 0:
                processed_files += 1
                total_images_found += images_in_file

        # Process the found images list to group by unique absolute path
        self._images_process_found_list()
        self._images_populate_treeview()

        self.images_refresh_button.config(state=tk.NORMAL, text="Rescan HTML for Images")
        self._images_scan_running = False
        status_msg = f"Image scan complete. Found {len(self.images_by_abs_path)} unique local image files referenced in {processed_files} HTML files."
        self.set_status(status_msg, duration_ms=8000)

    def _images_process_found_list(self):
        """Groups the raw found_images_list by unique absolute file path."""
        self.images_by_abs_path = {}
        print(f"[IMAGE PROCESS] Grouping {len(self.images_found_list)} image references...")
        for img_ref in self.images_found_list:
            abs_path = img_ref['abs_path']
            if not abs_path or abs_path == "Error Resolving Path":
                continue # Skip images we couldn't resolve

            if abs_path not in self.images_by_abs_path:
                self.images_by_abs_path[abs_path] = {
                    'usage_count': 0,
                    'src_list': set(),       # Set of unique src attributes pointing here
                    'html_files': set(),     # Set of unique HTML files using this image
                    'exists': img_ref['exists'], # Store existence status
                    'treeview_iid': None     # Placeholder for Treeview ID
                }
            entry = self.images_by_abs_path[abs_path]
            entry['usage_count'] += 1
            entry['src_list'].add(img_ref['src'])
            entry['html_files'].add(img_ref['html_file'])
            # Update 'exists' status if found again and now exists (e.g., after adding)
            if not entry['exists'] and img_ref['exists']:
                entry['exists'] = True
        print(f"[IMAGE PROCESS] Found {len(self.images_by_abs_path)} unique image files.")

    def _images_clear_treeview(self):
        print("[IMAGE DEBUG] Clearing image treeview.")
        self.images_tree.unbind("<<TreeviewSelect>>")
        for item in self.images_tree.get_children(): self.images_tree.delete(item)
        self.images_by_abs_path = {k: {**v, 'treeview_iid': None} for k, v in self.images_by_abs_path.items()} # Reset treeview IDs

    def _images_populate_treeview(self):
        """Populates the treeview with unique images found."""
        self._images_clear_treeview()
        print(f"[IMAGE DEBUG] Populating image treeview with {len(self.images_by_abs_path)} unique images.")

        # Sort by absolute path for consistent order
        sorted_abs_paths = sorted(self.images_by_abs_path.keys())

        for abs_path in sorted_abs_paths:
            img_data = self.images_by_abs_path[abs_path]
            try:
                filename = os.path.basename(abs_path)
                try: display_path = os.path.relpath(abs_path, APP_BASE_DIR)
                except ValueError: display_path = abs_path # If on different drive etc.
                display_path = str(pathlib.Path(display_path).as_posix()) # Use posix paths for display consistency
                exists_str = "Yes" if img_data['exists'] else "NO"
                usage_count = img_data['usage_count']
                values = (filename, display_path, exists_str, usage_count)

                # Use abs_path as the iid for direct mapping
                item_iid = abs_path
                tags = ('image_row',)
                if not img_data['exists']:
                    tags += ('missing',) # Add tag for styling missing files

                self.images_tree.insert('', tk.END, iid=item_iid, values=values, tags=tags)
                img_data['treeview_iid'] = item_iid # Store the iid back

            except Exception as e:
                print(f"[IMAGE GUI ERROR] Failed inserting image row for {abs_path}: {e}")

        if self.images_by_abs_path:
            self.images_tree.bind("<<TreeviewSelect>>", self._images_on_select)

    def _images_reset_preview_area(self):
        self.images_selected_abs_path = None
        self.images_preview_label.config(image='', text="Select an image from the list")
        self.images_path_label.config(text="Path: ")
        self._image_preview_widget = None # Clear photoimage reference
        self.images_change_button.config(state=tk.DISABLED)
        self.images_delete_button.config(state=tk.DISABLED)

    def _images_on_select(self, event=None):
        """Handles selection change in the image treeview."""
        selected_items = self.images_tree.selection()
        if not selected_items:
            self._images_reset_preview_area()
            return

        selected_iid = selected_items[0] # iid is the absolute path
        self.images_selected_abs_path = selected_iid

        if selected_iid not in self.images_by_abs_path:
             print(f"[IMAGE ERROR] Selected iid '{selected_iid}' not found in data. Refreshing.")
             messagebox.showerror("Error", "Selected image data not found. List might be outdated. Please rescan.", parent=self.root)
             self._images_reset_preview_area()
             # Optionally trigger a rescan here, or just clear
             return

        img_data = self.images_by_abs_path[selected_iid]
        abs_path = selected_iid # Recall iid is the abs_path
        exists = img_data['exists']
        display_path = self.images_tree.item(selected_iid, 'values')[1] # Get display path from tree

        self.images_path_label.config(text=f"Path: {display_path}")

        # Update preview
        photo = None; preview_text = "Preview N/A"
        if exists:
            try:
                if HAS_PILLOW:
                    with Image.open(abs_path) as img:
                        img.thumbnail((IMAGE_PREVIEW_MAX_WIDTH, IMAGE_PREVIEW_MAX_HEIGHT))
                        photo = ImageTk.PhotoImage(img)
                        preview_text = "" # Clear text if image loaded
                else:
                    # Try basic Tkinter PhotoImage (GIF/PGM/PPM only)
                    try: photo = tk.PhotoImage(file=abs_path); preview_text = ""
                    except tk.TclError: preview_text = "Preview N/A\n(Install Pillow for more formats)"; photo = None
            except FileNotFoundError:
                preview_text = "File Not Found"
                img_data['exists'] = False # Update data if file deleted externally
                self.images_tree.item(selected_iid, values=(os.path.basename(abs_path), display_path, "NO", img_data['usage_count']), tags=('image_row', 'missing'))
            except Exception as e:
                print(f"[IMAGE PREVIEW ERROR] Loading {abs_path}: {e}")
                preview_text = f"Error Loading Preview:\n{e}"
        else:
            preview_text = "Image File Not Found"

        self.images_preview_label.config(image=photo, text=preview_text)
        self._image_preview_widget = photo # Keep reference!

        # Update button states
        action_state = tk.NORMAL if exists else tk.DISABLED
        self.images_change_button.config(state=action_state)
        self.images_delete_button.config(state=action_state)

    def _images_add_dialog(self):
        """Opens a dialog to add a new image."""
        print("[IMAGE DEBUG] Add image dialog.")
        # Use a custom dialog to select file AND destination
        ImageAddDialog(self.root, "Add New Image File", self._images_process_add)

    def _images_process_add(self, source_path, dest_dir_abs, dest_dir_rel):
        """Copies the selected image file to the destination."""
        if not source_path or not dest_dir_abs or not dest_dir_rel:
            print("[IMAGE DEBUG] Add image cancelled or invalid data received."); return

        filename = os.path.basename(source_path)
        dest_path_abs = os.path.join(dest_dir_abs, filename)
        print(f"[IMAGE INFO] Adding image. Source='{source_path}', DestAbs='{dest_path_abs}', DestRel='{dest_dir_rel}'")

        try: os.makedirs(dest_dir_abs, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Directory Error", f"Could not create destination directory:\n{dest_dir_abs}\nError: {e}", parent=self.root)
            self.set_status(f"Error creating directory '{dest_dir_rel}': {e}", is_error=True); return

        if os.path.exists(dest_path_abs):
            if not messagebox.askyesno("Confirm Overwrite", f"File '{filename}' already exists in '{dest_dir_rel}'.\nReplace existing file?", icon='warning', parent=self.root):
                self.set_status("Add image cancelled (overwrite declined).", duration_ms=4000); return
            else: print(f"[IMAGE INFO] Overwriting existing file: {dest_path_abs}")

        try:
            shutil.copy2(source_path, dest_path_abs) # copy2 preserves metadata
            print(f"[IMAGE INFO] Copied '{filename}' to '{dest_dir_rel}'.")
            self.set_status(f"Image '{filename}' added to '{dest_dir_rel}'. Rescan HTML to see usage.", duration_ms=8000)

            # --- Update internal state and Treeview ---
            # Check if this image path is already known
            if dest_path_abs in self.images_by_abs_path:
                img_data = self.images_by_abs_path[dest_path_abs]
                img_data['exists'] = True # Mark as existing
                # Update treeview item if it exists
                if img_data.get('treeview_iid') and self.images_tree.exists(img_data['treeview_iid']):
                    values = self.images_tree.item(img_data['treeview_iid'], 'values')
                    self.images_tree.item(img_data['treeview_iid'], values=(values[0], values[1], "Yes", values[3]), tags=('image_row',))
                    self.images_tree.selection_set(img_data['treeview_iid']) # Select the updated item
            else:
                # Add as a new entry (no usage found yet)
                 new_img_data = {
                    'usage_count': 0, 'src_list': set(), 'html_files': set(),
                    'exists': True, 'treeview_iid': dest_path_abs # Use abs_path as iid
                 }
                 self.images_by_abs_path[dest_path_abs] = new_img_data
                 # Insert into treeview
                 try: display_path = str(pathlib.Path(os.path.relpath(dest_path_abs, APP_BASE_DIR)).as_posix())
                 except ValueError: display_path = dest_path_abs
                 values = (filename, display_path, "Yes", 0)
                 self.images_tree.insert('', tk.END, iid=dest_path_abs, values=values, tags=('image_row',))
                 self.images_tree.selection_set(dest_path_abs) # Select the new item

            # Trigger selection handler to update preview etc.
            self._images_on_select()

        except Exception as e:
            messagebox.showerror("Add Image Error", f"Could not copy image to:\n{dest_path_abs}\nError: {e}", parent=self.root)
            self.set_status(f"Error adding image '{filename}': {e}", is_error=True)


    def _images_change(self):
        """Replaces the selected image file with a new one."""
        if not self.images_selected_abs_path:
            messagebox.showwarning("Selection Required", "Please select an image from the list to change.", parent=self.root); return

        target_abs_path = self.images_selected_abs_path
        if not os.path.isfile(target_abs_path):
             messagebox.showerror("Error", f"Selected image file not found:\n{target_abs_path}\nCannot change it.", parent=self.root)
             self._images_reset_preview_area() # Reset state as file is missing
             # Optionally trigger a rescan or update the tree item state
             return

        filename = os.path.basename(target_abs_path)
        print(f"[IMAGE DEBUG] Change image requested for: {target_abs_path}")

        if not messagebox.askyesno("Confirm Image Change", f"This will REPLACE the existing file:\n'{filename}'\n\nWith a new image you select.\nThe filename will stay the same.\nThis CANNOT be undone easily.\n\nProceed?", icon='warning', parent=self.root):
            self.set_status("Change image cancelled.", duration_ms=3000); return

        filetypes = (("Image files", "*.jpg *.jpeg *.png *.gif *.webp *.bmp"), ("All files", "*.*"))
        new_source_path = filedialog.askopenfilename(title=f"Select NEW Image to Replace '{filename}'", filetypes=filetypes)

        if not new_source_path:
            self.set_status("Change image cancelled (no new file selected).", duration_ms=3000); return

        print(f"[IMAGE INFO] Replacing '{target_abs_path}' with content from '{new_source_path}'")
        self.set_status(f"Replacing '{filename}'...")
        self.root.update_idletasks()

        try:
            shutil.copy2(new_source_path, target_abs_path) # Overwrites target
            print(f"[IMAGE INFO] Successfully replaced '{filename}'.")
            self.set_status(f"Image file '{filename}' replaced successfully.", duration_ms=5000)
            # Force preview refresh for the selected item
            self._images_on_select()
        except Exception as e:
            messagebox.showerror("Change Image Error", f"Could not replace file:\n{target_abs_path}\nError: {e}", parent=self.root)
            self.set_status(f"Error replacing image '{filename}': {e}", is_error=True)


    def _images_delete(self):
        """Deletes the selected image file from disk."""
        if not self.images_selected_abs_path:
            messagebox.showwarning("Selection Required", "Please select an image from the list to delete.", parent=self.root); return

        target_abs_path = self.images_selected_abs_path
        img_data = self.images_by_abs_path.get(target_abs_path)

        if not img_data or not img_data['exists']:
             messagebox.showerror("Error", f"Selected image file not found or already marked missing:\n{target_abs_path}\nCannot delete.", parent=self.root)
             self._images_reset_preview_area()
             return

        filename = os.path.basename(target_abs_path)
        usage_count = img_data['usage_count']
        print(f"[IMAGE DEBUG] Delete image requested for: {target_abs_path} (Used {usage_count} times)")

        warning_msg = f"Permanently DELETE the image file:\n'{filename}'\nfrom your computer?\n\n"
        if usage_count > 0:
            warning_msg += f"WARNING: This image is used {usage_count} time(s) in your HTML files.\nDeleting the file WILL cause broken images on your website.\n\n"
        warning_msg += "This action CANNOT be undone.\nAre you absolutely sure?"

        if not messagebox.askyesno("Confirm Image File Deletion", warning_msg, icon='error', parent=self.root): # Use error icon
            self.set_status("Delete image cancelled.", duration_ms=3000); return

        print(f"[IMAGE INFO] Deleting file: {target_abs_path}")
        self.set_status(f"Deleting '{filename}'...")
        self.root.update_idletasks()

        try:
            os.remove(target_abs_path)
            print(f"[IMAGE INFO] Successfully deleted '{filename}'.")
            self.set_status(f"Image file '{filename}' deleted successfully.", duration_ms=5000)

            # --- Update internal state and Treeview ---
            img_data['exists'] = False
            img_data['usage_count'] = 0 # Reset usage count as file is gone for practical purposes
            # Update treeview item visually
            if img_data.get('treeview_iid') and self.images_tree.exists(img_data['treeview_iid']):
                 values = self.images_tree.item(img_data['treeview_iid'], 'values')
                 self.images_tree.item(img_data['treeview_iid'], values=(values[0], values[1], "NO", 0), tags=('image_row', 'missing'))

            # Clear selection and preview as the file is gone
            self._images_reset_preview_area()

        except FileNotFoundError:
             messagebox.showwarning("Delete Warning", f"File was already gone before deletion:\n{target_abs_path}", parent=self.root)
             img_data['exists'] = False # Ensure state is correct
             if img_data.get('treeview_iid') and self.images_tree.exists(img_data['treeview_iid']):
                  values = self.images_tree.item(img_data['treeview_iid'], 'values')
                  self.images_tree.item(img_data['treeview_iid'], values=(values[0], values[1], "NO", 0), tags=('image_row', 'missing'))
             self._images_reset_preview_area()
        except Exception as e:
            messagebox.showerror("Delete Image Error", f"Could not delete file:\n{target_abs_path}\nError: {e}", parent=self.root)
            self.set_status(f"Error deleting image '{filename}': {e}", is_error=True)


    # --- Text Editor Tab Creation & Methods (Extended) ---
    def _create_text_editor_tab(self, parent_frame):
        # ... (Keep the setup before the edit_button_frame) ...
        print("[GUI INFO] Creating Text Editor Tab...")
        if not NavigableString or not Comment:
            error_label = ttk.Label(parent_frame, text="Error: BeautifulSoup4 library missing/incomplete.\nCannot load Text Editor.", style="Error.TLabel", justify=tk.CENTER)
            error_label.pack(pady=50, padx=20, expand=True); print("[GUI ERROR] Text Editor tab disabled: BS4 NavigableString/Comment missing."); return

        self.text_editor_found_texts = []; # self.text_editor_parsed_soups shared
        self.text_editor_selected_iid = None; self._text_editor_scan_running = False

        top_frame = ttk.Frame(parent_frame); top_frame.pack(fill=tk.X, pady=(0, 10))
        tree_frame = ttk.Frame(parent_frame); tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        edit_frame = ttk.Frame(parent_frame); edit_frame.pack(fill=tk.X, pady=(10, 0))

        self.text_editor_refresh_button = ttk.Button(top_frame, text="Rescan Files for Text", command=self._text_editor_scan_files)
        self.text_editor_refresh_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.text_editor_search_var = tk.StringVar()
        self.text_editor_search_entry = ttk.Entry(top_frame, textvariable=self.text_editor_search_var, width=40, state=tk.DISABLED); self.text_editor_search_entry.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)
        self.text_editor_search_entry.bind("<KeyRelease>", self._text_editor_filter_treeview_event)
        ttk.Label(top_frame, text="<- Search Found Text", style="Desc.TLabel").pack(side=tk.LEFT, padx=(0,5), pady=5)

        tree_columns = ('file', 'text')
        self.text_editor_tree = ttk.Treeview(tree_frame, columns=tree_columns, show='headings', selectmode='browse')
        self.text_editor_tree.heading('file', text='File Path'); self.text_editor_tree.column('file', width=300, minwidth=200, anchor=tk.W)
        self.text_editor_tree.heading('text', text='Found Text Snippet'); self.text_editor_tree.column('text', width=600, minwidth=300, anchor=tk.W)
        tree_vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.text_editor_tree.yview); tree_hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.text_editor_tree.xview)
        self.text_editor_tree.configure(yscrollcommand=tree_vsb.set, xscrollcommand=tree_hsb.set)
        self.text_editor_tree.grid(row=0, column=0, sticky='nsew'); tree_vsb.grid(row=0, column=1, sticky='ns'); tree_hsb.grid(row=1, column=0, sticky='ew')
        tree_frame.grid_rowconfigure(0, weight=1); tree_frame.grid_columnconfigure(0, weight=1)
        self.text_editor_tree.bind("<<TreeviewSelect>>", self._text_editor_on_select)

        ttk.Label(edit_frame, text="Edit Selected Text:", style="Bold.TLabel").pack(anchor=tk.W, padx=5, pady=(0,2))
        self.text_editor_edit_area = scrolledtext.ScrolledText(edit_frame, width=80, height=6, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1, state=tk.DISABLED, font=(self.default_font_family, self.default_font_size)); self.text_editor_edit_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0,5))

        # --- Button Frame ---
        edit_button_frame = ttk.Frame(edit_frame); edit_button_frame.pack(fill=tk.X, padx=5, pady=(0,5))

        self.text_editor_save_button = ttk.Button(edit_button_frame, text="Save This Change", command=self._text_editor_save_change, state=tk.DISABLED);
        self.text_editor_save_button.pack(side=tk.LEFT, padx=(0, 5))

        self.text_editor_cancel_button = ttk.Button(edit_button_frame, text="Cancel Edit", command=self._text_editor_cancel_edit, state=tk.DISABLED);
        self.text_editor_cancel_button.pack(side=tk.LEFT, padx=5)

        self.text_editor_add_element_button = ttk.Button(edit_button_frame, text="Add Element...", command=self._text_editor_add_element_dialog, state=tk.DISABLED)
        self.text_editor_add_element_button.pack(side=tk.LEFT, padx=5)

        # --- NEW Delete Button ---
        self.text_editor_delete_button = ttk.Button(edit_button_frame, text="Delete Selected Text", command=self._text_editor_delete_selected, state=tk.DISABLED)
        self.text_editor_delete_button.pack(side=tk.LEFT, padx=5)
    
    def _text_editor_scan_files(self):
        if self._text_editor_scan_running: print("[TEXT EDITOR WARNING] Scan already in progress."); return
        self._text_editor_scan_running = True
        self.text_editor_refresh_button.config(state=tk.DISABLED, text="Scanning...")
        self.set_status("Scanning HTML files for text...")
        self.root.update_idletasks()

        self.text_editor_found_texts = []; # self.text_editor_parsed_soups used
        self.text_editor_selected_iid = None
        self._text_editor_clear_treeview(); self._text_editor_reset_edit_area(); self.text_editor_search_var.set("")
        self.text_editor_search_entry.config(state=tk.DISABLED)

        html_files, file_count = _general_html_find_files(HTML_SCAN_TARGET_PATHS_ABSOLUTE)
        processed_files = 0; total_texts_found = 0
        for i, file_path in enumerate(html_files):
            self.set_status(f"Scanning file {i+1}/{file_count} for text: {os.path.basename(file_path)}...")
            self.root.update_idletasks()
            texts_in_file = _text_editor_parse_file(file_path, self.text_editor_parsed_soups, self.text_editor_found_texts)
            if texts_in_file > 0: processed_files += 1; total_texts_found += texts_in_file

        self._text_editor_populate_treeview(self.text_editor_found_texts)
        self.text_editor_search_entry.config(state=tk.NORMAL if self.text_editor_found_texts else tk.DISABLED)
        self.text_editor_refresh_button.config(state=tk.NORMAL, text="Rescan Files for Text")
        self._text_editor_scan_running = False
        status_msg = f"Text scan complete. Found {total_texts_found} snippets in {processed_files} files." if total_texts_found > 0 else f"Text scan complete. No editable snippets found in {processed_files} files."
        self.set_status(status_msg, duration_ms=8000)

    def _text_editor_clear_treeview(self):
        print("[TEXT EDITOR DEBUG] Clearing text editor treeview."); self.text_editor_tree.unbind("<<TreeviewSelect>>");
        for item in self.text_editor_tree.get_children(): self.text_editor_tree.delete(item)

    def _text_editor_populate_treeview(self, data_list):
        self._text_editor_clear_treeview(); print(f"[TEXT EDITOR DEBUG] Populating treeview with {len(data_list)} items.")
        for item_data in data_list:
             try: display_path = os.path.relpath(item_data['file_path'], APP_BASE_DIR)
             except ValueError: display_path = item_data['file_path']
             values = (display_path, item_data['display_text'])
             try: self.text_editor_tree.insert('', tk.END, iid=item_data['iid'], values=values, tags=('text_row',))
             except Exception as e: print(f"[TEXT EDITOR GUI ERROR] Failed inserting row {item_data['iid']}: {values}\nError: {e}")
        if data_list: self.text_editor_tree.bind("<<TreeviewSelect>>", self._text_editor_on_select)

    def _text_editor_filter_treeview_event(self, event=None):
        search_term = self.text_editor_search_var.get().lower().strip(); print(f"[TEXT EDITOR DEBUG] Filtering treeview with term: '{search_term}'")
        filtered_data = [item for item in self.text_editor_found_texts if search_term in item['original_text'].lower()] if search_term else self.text_editor_found_texts
        self._text_editor_populate_treeview(filtered_data); self._text_editor_reset_edit_area()

    def _text_editor_reset_edit_area(self):
            self.text_editor_selected_iid = None
            self.text_editor_edit_area.config(state=tk.NORMAL)
            self.text_editor_edit_area.delete('1.0', tk.END)
            self.text_editor_edit_area.config(state=tk.DISABLED)
            self.text_editor_save_button.config(state=tk.DISABLED)
            self.text_editor_cancel_button.config(state=tk.DISABLED)
            self.text_editor_add_element_button.config(state=tk.DISABLED)
            # --- ADDED ---
            self.text_editor_delete_button.config(state=tk.DISABLED) # Disable delete button too
            # --- END ---
        
    def _text_editor_on_select(self, event=None):
        selected_items = self.text_editor_tree.selection()
        if not selected_items:
            self._text_editor_reset_edit_area()
            return
        selected_iid_str = selected_items[0]
        try:
            selected_iid = int(selected_iid_str)
            data_item = self.text_editor_found_texts[selected_iid]
            self.text_editor_selected_iid = selected_iid

            # Enable Edit/Save/Cancel
            self.text_editor_edit_area.config(state=tk.NORMAL)
            self.text_editor_save_button.config(state=tk.NORMAL)
            self.text_editor_cancel_button.config(state=tk.NORMAL)

            # Enable Add Element only if parent tag is valid
            parent_valid = data_item['dom_reference'] and data_item['dom_reference'].parent and isinstance(data_item['dom_reference'].parent, Tag)
            add_state = tk.NORMAL if parent_valid else tk.DISABLED
            self.text_editor_add_element_button.config(state=add_state)

            # --- ADDED ---
            # Enable Delete button if the node reference is valid
            delete_state = tk.NORMAL if data_item['dom_reference'] else tk.DISABLED
            self.text_editor_delete_button.config(state=delete_state)
             # --- END ---

            # Populate edit area
            self.text_editor_edit_area.delete('1.0', tk.END)
            self.text_editor_edit_area.insert('1.0', data_item['original_text'])
            print(f"[TEXT EDITOR DEBUG] Selected item iid {selected_iid}. Displaying text.")

        except (ValueError, IndexError, KeyError) as e:
            print(f"[TEXT EDITOR ERROR] Error retrieving data for iid '{selected_iid_str}': {e}")
            messagebox.showerror("Error", "Could not retrieve data for selected text.", parent=self.root)
            self._text_editor_reset_edit_area()
    
        # --- UPDATED Delete Method ---
    def _text_editor_delete_selected(self):
        """Deletes the PARENT TAG containing the selected text node from the HTML."""
        if self.text_editor_selected_iid is None:
            messagebox.showwarning("No Selection", "Select a text snippet in the list first.", parent=self.root)
            return

        try:
            data_item = self.text_editor_found_texts[self.text_editor_selected_iid]
            file_path = data_item['file_path']
            text_node_reference = data_item['dom_reference']
            modified_soup = self.text_editor_parsed_soups[file_path]
            original_text_snippet = data_item['display_text']

            if text_node_reference is None:
                 messagebox.showerror("Delete Error", "Original text location lost. Re-scan files.", parent=self.root)
                 self.set_status("Delete failed: Node reference lost.", is_error=True); return

            # --- Find the parent tag to delete ---
            parent_tag = text_node_reference.parent
            if parent_tag is None or not isinstance(parent_tag, Tag):
                 messagebox.showerror("Delete Error", "Cannot delete: Selected text doesn't have a valid parent tag (e.g., it might be directly in the root?). Re-scan files.", parent=self.root)
                 self.set_status("Delete failed: Parent tag not found/invalid.", is_error=True); return

            # Prevent deleting critical tags like html or body
            if parent_tag.name.lower() in ['html', 'body', 'head']:
                messagebox.showerror("Delete Error", f"Cannot delete critical tag: <{parent_tag.name}>.", parent=self.root)
                self.set_status(f"Delete failed: Attempted to delete critical <{parent_tag.name}> tag.", is_error=True); return

            print(f"[TEXT EDITOR DEBUG] Deleting parent tag <{parent_tag.name}> containing text for iid {self.text_editor_selected_iid} in {os.path.basename(file_path)}")

            # --- Updated Confirmation Dialog ---
            confirm_msg = f"Permanently DELETE the entire <{parent_tag.name}> tag containing this text?\n\nText Snippet:\n'{original_text_snippet}'\n\nTag to Delete:\n<{parent_tag.name}> ... </{parent_tag.name}>\n\nFile: {os.path.basename(file_path)}\n\nWARNING: This deletes the tag AND everything inside it.\nThis action CANNOT be undone easily."
            if not messagebox.askyesno("Confirm Tag Deletion", confirm_msg, icon='warning', parent=self.root):
                self.set_status("Delete cancelled.", duration_ms=3000)
                return

            # --- Perform Deletion of the PARENT TAG ---
            try:
                # Extract removes the node (the parent tag) and its children from the tree
                parent_tag.extract()
                print(f"[TEXT EDITOR DEBUG] Parent tag <{parent_tag.name}> extracted from BS object.")
            except Exception as extract_err:
                 messagebox.showerror("Delete Error", f"Failed to remove parent tag <{parent_tag.name}> internally.\nError: {extract_err}", parent=self.root)
                 self.set_status("Delete failed: Internal tag removal error.", is_error=True); return

            # --- Save the modified file ---
            try:
                with open(file_path, 'w', encoding='utf-8') as f: f.write(modified_soup.prettify(formatter="html5"))
                print(f"[TEXT EDITOR INFO] Saved modified file after deleting tag: {file_path}")
                self.set_status(f"Tag <{parent_tag.name}> deleted and saved in {os.path.basename(file_path)}. Rescan strongly recommended.", duration_ms=8000)

                # --- Update UI & Recommend Rescan ---
                # Clear edit area immediately
                self._text_editor_reset_edit_area()
                # Attempt to remove from the tree (using the original text's iid)
                try:
                    print(f"[TEXT EDITOR DEBUG] Attempting to remove item {self.text_editor_selected_iid} from treeview after parent deletion.")
                    self.text_editor_tree.delete(self.text_editor_selected_iid)
                    print(f"[TEXT EDITOR DEBUG] Removed item {self.text_editor_selected_iid} from treeview.")
                except tk.TclError as e:
                    print(f"[TEXT EDITOR WARNING] Could not delete item {self.text_editor_selected_iid} from treeview (might be gone already): {e}")
                except Exception as e:
                     print(f"[TEXT EDITOR ERROR] Unexpected error deleting item {self.text_editor_selected_iid} from treeview: {e}")

                # Prompt strongly for rescan as structure changed
                if messagebox.askyesno("Rescan Recommended", "Tag deleted successfully.\n\nThe text list is now inaccurate due to structural changes.\n\nRescan files to update the list?", parent=self.root):
                    self._text_editor_scan_files()
                # If user says no, the list is stale.

            except Exception as save_err:
                import traceback; messagebox.showerror("Save Error", f"Failed to write file after deleting tag:\n{file_path}\nError: {save_err}", parent=self.root)
                self.set_status(f"Delete failed: Error writing file {os.path.basename(file_path)}.", is_error=True); traceback.print_exc();
                print("[TEXT EDITOR WARNING] File save failed after deleting tag. Change might be lost on next scan.")
                # Attempting to undo is very hard here, as we don't know where to re-insert.

        except (IndexError, KeyError) as e:
            print(f"[TEXT EDITOR ERROR] Error retrieving data for iid '{self.text_editor_selected_iid}' during delete: {e}"); messagebox.showerror("Delete Error", "Could not retrieve data to delete.", parent=self.root); self._text_editor_reset_edit_area()
        except Exception as e:
            import traceback; print(f"[TEXT EDITOR ERROR] Unexpected error during delete: {e}"); messagebox.showerror("Delete Error", f"Unexpected error deleting tag:\n{e}", parent=self.root); traceback.print_exc(); self._text_editor_reset_edit_area()

    def _text_editor_cancel_edit(self):
        print("[TEXT EDITOR DEBUG] Cancel edit clicked."); self._text_editor_reset_edit_area()
        if self.text_editor_tree.selection(): self.text_editor_tree.selection_remove(self.text_editor_tree.selection()[0])
        self.set_status("Edit cancelled.", duration_ms=3000)

    def _text_editor_save_change(self):
        if self.text_editor_selected_iid is None: messagebox.showwarning("No Selection", "No text snippet selected.", parent=self.root); return
        try:
            data_item = self.text_editor_found_texts[self.text_editor_selected_iid]; file_path = data_item['file_path']; text_node_reference = data_item['dom_reference']
            edited_text = self.text_editor_edit_area.get('1.0', tk.END)[:-1] # Remove trailing newline
            print(f"[TEXT EDITOR DEBUG] Saving change for iid {self.text_editor_selected_iid} in {file_path}")
            if text_node_reference is None or not text_node_reference.parent: messagebox.showerror("Save Error", "Original text location lost. Re-scan files.", parent=self.root); self.set_status("Save failed: Node lost.", is_error=True); self._text_editor_reset_edit_area(); return
            try: text_node_reference.replace_with(NavigableString(edited_text)); print(f"[TEXT EDITOR DEBUG] Replaced text in BS object for {file_path}") # Ensure it's saved as NavigableString
            except Exception as replace_err: messagebox.showerror("Save Error", f"Failed to replace text internally.\nError: {replace_err}", parent=self.root); self.set_status("Save failed: Modify internal.", is_error=True); return
            modified_soup = self.text_editor_parsed_soups[file_path]
            try:
                with open(file_path, 'w', encoding='utf-8') as f: f.write(modified_soup.prettify(formatter="html5")); print(f"[TEXT EDITOR INFO] Saved modified file: {file_path}")
                data_item['original_text'] = edited_text; new_display_text = (edited_text[:100] + '...') if len(edited_text) > 100 else edited_text; new_display_text = new_display_text.replace('\n', ' ').replace('\r', '')
                data_item['display_text'] = new_display_text;
                try: display_path = os.path.relpath(file_path, APP_BASE_DIR)
                except ValueError: display_path = file_path
                self.text_editor_tree.item(self.text_editor_selected_iid, values=(display_path, new_display_text)); self._text_editor_reset_edit_area(); self.set_status(f"Change saved to {os.path.basename(file_path)}.", duration_ms=5000)
            except Exception as save_err: import traceback; messagebox.showerror("Save Error", f"Failed to write file:\n{file_path}\nError: {save_err}", parent=self.root); self.set_status(f"Save failed: Error writing file {os.path.basename(file_path)}.", is_error=True); traceback.print_exc(); print("[TEXT EDITOR WARNING] File save failed. In-memory object modified but not saved.")
        except (IndexError, KeyError) as e: print(f"[TEXT EDITOR ERROR] Error retrieving data for iid '{self.text_editor_selected_iid}' during save: {e}"); messagebox.showerror("Save Error", "Could not retrieve data to save.", parent=self.root); self._text_editor_reset_edit_area()
        except Exception as e: import traceback; print(f"[TEXT EDITOR ERROR] Unexpected error during save: {e}"); messagebox.showerror("Save Error", f"Unexpected error during save:\n{e}", parent=self.root); traceback.print_exc(); self._text_editor_reset_edit_area()

    def _text_editor_process_add_element(self, element_type, new_text_content, position):
        """Adds the new element tag before or after the selected item's parent tag and saves."""
        if element_type is None: # Dialog cancelled
            print("[TEXT EDITOR DEBUG] Add element cancelled."); return

        if self.text_editor_selected_iid is None: return # Should not happen

        try:
            data_item = self.text_editor_found_texts[self.text_editor_selected_iid]
            file_path = data_item['file_path']
            text_node_reference = data_item['dom_reference']
            modified_soup = self.text_editor_parsed_soups[file_path]

            # --- Find the reference tag for insertion ---
            # We insert relative to the PARENT TAG of the selected text node
            reference_tag = text_node_reference.parent
            if reference_tag is None or not isinstance(reference_tag, Tag):
                 messagebox.showerror("Save Error", "Cannot add element: Parent tag of selected text is missing or invalid.\nRe-scan files.", parent=self.root)
                 self.set_status("Add failed: Parent tag lost.", is_error=True); return

            print(f"[TEXT EDITOR DEBUG] Adding <{element_type}> with text '{new_text_content[:30]}...' {position} tag <{reference_tag.name}> in {os.path.basename(file_path)}")

            # Create the new element
            new_element = modified_soup.new_tag(element_type)
            new_element.string = new_text_content

            # Insert the new element and newlines for readability
            if position == 'before':
                reference_tag.insert_before(NavigableString("\n")) # Newline before the new element
                reference_tag.insert_before(new_element)
                reference_tag.insert_before(NavigableString("\n")) # Newline after the new element
            elif position == 'after':
                reference_tag.insert_after(NavigableString("\n")) # Newline before the new element
                reference_tag.insert_after(new_element)
                reference_tag.insert_after(NavigableString("\n")) # Newline after the new element
            else:
                print(f"[TEXT EDITOR ERROR] Invalid position: {position}"); return

            # Save the modified file
            try:
                with open(file_path, 'w', encoding='utf-8') as f: f.write(modified_soup.prettify(formatter="html5"))
                print(f"[TEXT EDITOR INFO] Saved modified file after adding element: {file_path}")
                self.set_status(f"Element <{element_type}> added and saved to {os.path.basename(file_path)}. Rescan highly recommended.", duration_ms=8000)

                # --- !!! Rescan Recommended !!! ---
                if messagebox.askyesno("Rescan Recommended", f"<{element_type}> element added successfully.\n\nThe text list might be inaccurate now due to structural changes.\n\nRescan files to update the list?", parent=self.root):
                    self._text_editor_scan_files() # Rescan both text and images if needed
                else:
                    self._text_editor_reset_edit_area() # Clear edit area, list is stale

            except Exception as save_err:
                import traceback; messagebox.showerror("Save Error", f"Failed to write file:\n{file_path}\nError: {save_err}", parent=self.root)
                self.set_status(f"Add failed: Error writing file {os.path.basename(file_path)}.", is_error=True); traceback.print_exc();
                print("[TEXT EDITOR WARNING] File save failed after adding element. Attempting to undo in memory.")
                # Attempt simple undo (might fail if structure is complex)
                try: new_element.find_previous_sibling(string="\n").extract()
                except: pass
                try: new_element.find_next_sibling(string="\n").extract()
                except: pass
                try: new_element.extract()
                except: print("[TEXT EDITOR WARNING] In-memory undo failed.")


        except (IndexError, KeyError) as e:
            print(f"[TEXT EDITOR ERROR] Error retrieving data for iid '{self.text_editor_selected_iid}' during add element: {e}"); messagebox.showerror("Add Error", "Could not retrieve data to add element.", parent=self.root); self._text_editor_reset_edit_area()
        except Exception as e:
            import traceback; print(f"[TEXT EDITOR ERROR] Unexpected error during add element: {e}"); messagebox.showerror("Add Error", f"Unexpected error adding element:\n{e}", parent=self.root); traceback.print_exc(); self._text_editor_reset_edit_area()

    def _text_editor_add_element_dialog(self):
        """Opens dialog to add a new HTML element near the selected node."""
        if self.text_editor_selected_iid is None:
            messagebox.showwarning("No Selection", "Select a text snippet in the list first.", parent=self.root)
            return

        try:
             data_item = self.text_editor_found_texts[self.text_editor_selected_iid]
             text_node_reference = data_item['dom_reference']

             # --- Check if the reference node and its parent tag are valid ---
             if text_node_reference is None or not hasattr(text_node_reference, 'parent') or not isinstance(text_node_reference.parent, Tag):
                 messagebox.showerror("Error", "Cannot add element: Original text location or its parent tag is invalid.\nPlease re-scan files.", parent=self.root)
                 return

             font_tuple = (self.default_font_family, self.default_font_size)
             # Call the new dialog
             AddElementDialog(self.root, "Add HTML Element", self._text_editor_process_add_element, default_font=font_tuple)

        except (IndexError, KeyError) as e:
            messagebox.showerror("Error", "Could not retrieve data for selected item.", parent=self.root)
        except Exception as e:
             messagebox.showerror("Error", f"An unexpected error occurred preparing to add element:\n{e}", parent=self.root)

    def _text_editor_process_add_adjacent(self, new_text, position):
        """Adds the new text before or after the selected node and saves."""
        if new_text is None or position is None:
            print("[TEXT EDITOR DEBUG] Add text cancelled."); return

        if self.text_editor_selected_iid is None: return # Should not happen if button enabled

        try:
            data_item = self.text_editor_found_texts[self.text_editor_selected_iid]
            file_path = data_item['file_path']
            text_node_reference = data_item['dom_reference']
            modified_soup = self.text_editor_parsed_soups[file_path]

            if text_node_reference is None or not text_node_reference.parent:
                 messagebox.showerror("Save Error", "Original text location lost. Re-scan files.", parent=self.root)
                 self.set_status("Add failed: Node lost.", is_error=True); return

            # Add newline before/after for better formatting in source
            new_text_with_space = f" {new_text} " # Add space around
            new_navigable_string = NavigableString(new_text_with_space)

            print(f"[TEXT EDITOR DEBUG] Adding text '{new_text}' {position} iid {self.text_editor_selected_iid}")

            if position == 'before':
                text_node_reference.insert_before(new_navigable_string)
                # Optionally add a newline before the original node too if inserting before
                text_node_reference.insert_before(NavigableString("\n"))
            elif position == 'after':
                text_node_reference.insert_after(new_navigable_string)
                 # Optionally add a newline after the new node
                text_node_reference.insert_after(NavigableString("\n"))
            else:
                print(f"[TEXT EDITOR ERROR] Invalid position: {position}"); return

            # Save the modified file
            try:
                with open(file_path, 'w', encoding='utf-8') as f: f.write(modified_soup.prettify(formatter="html5"))
                print(f"[TEXT EDITOR INFO] Saved modified file after adding text: {file_path}")
                self.set_status(f"Text added and saved to {os.path.basename(file_path)}. Rescan recommended.", duration_ms=8000)

                # --- !!! Rescan Recommended !!! ---
                # Modifying the structure makes the existing dom_references potentially unreliable.
                # It's safest to force a rescan after adding text.
                if messagebox.askyesno("Rescan Recommended", "Text block added successfully.\n\nIt's highly recommended to rescan files now to reflect the changes accurately in the editor.\n\nRescan now?", parent=self.root):
                    self._text_editor_scan_files()
                else:
                    self._text_editor_reset_edit_area() # Clear edit area, but list is now potentially stale

            except Exception as save_err:
                import traceback; messagebox.showerror("Save Error", f"Failed to write file:\n{file_path}\nError: {save_err}", parent=self.root)
                self.set_status(f"Add failed: Error writing file {os.path.basename(file_path)}.", is_error=True); traceback.print_exc();
                print("[TEXT EDITOR WARNING] File save failed after adding text.")
                # Attempt to undo the change in memory? Risky.

        except (IndexError, KeyError) as e:
            print(f"[TEXT EDITOR ERROR] Error retrieving data for iid '{self.text_editor_selected_iid}' during add: {e}"); messagebox.showerror("Add Error", "Could not retrieve data to add text.", parent=self.root); self._text_editor_reset_edit_area()
        except Exception as e:
            import traceback; print(f"[TEXT EDITOR ERROR] Unexpected error during add: {e}"); messagebox.showerror("Add Error", f"Unexpected error adding text:\n{e}", parent=self.root); traceback.print_exc(); self._text_editor_reset_edit_area()


# --- Record Add/Edit Dialog Class (Keep Existing) ---
class RecordDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_data=None, callback=None):
        super().__init__(parent); self.transient(parent); self.title(title); self.callback = callback
        self.initial_data = (list(initial_data) + [""] * 5)[:5] if initial_data and isinstance(initial_data, (list, tuple)) else ["", "", "", "", ""]
        self.result = None; print(f"[RECORD DIALOG DEBUG] Init '{title}': {self.initial_data}")
        frame = ttk.Frame(self, padding="15"); frame.pack(expand=True, fill=tk.BOTH)
        labels = ["Discipline:", "Naam:", "Prestatie:", "Plaats:", "Datum (bv. YYYY.MM.DD):"]; self.entries = []
        for i, label_text in enumerate(labels):
            ttk.Label(frame, text=label_text).grid(row=i, column=0, sticky=tk.W, padx=5, pady=5)
            entry = ttk.Entry(frame, width=40); entry.grid(row=i, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
            entry.insert(0, str(self.initial_data[i]) if self.initial_data[i] is not None else "")
            self.entries.append(entry)
        frame.columnconfigure(1, weight=1)
        button_frame = ttk.Frame(frame); button_frame.grid(row=len(labels), column=0, columnspan=2, pady=(15, 0), sticky=tk.E)
        ok_button = ttk.Button(button_frame, text="OK", command=self.on_ok); ok_button.pack(side=tk.RIGHT, padx=(5, 0))
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.on_cancel); cancel_button.pack(side=tk.RIGHT)
        self.grab_set(); self.protocol("WM_DELETE_WINDOW", self.on_cancel); self.bind("<Return>", self.on_ok); self.bind("<Escape>", self.on_cancel)
        self.entries[0].focus_set(); self.wait_window(self); print("[RECORD DIALOG DEBUG] Dialog closed.")
    def on_ok(self, event=None):
        data = [entry.get().strip() for entry in self.entries]; print(f"[RECORD DIALOG DEBUG] OK clicked. Data: {data}")
        if not data[0]: messagebox.showwarning("Input Required", "'Discipline' cannot be empty.", parent=self); self.entries[0].focus_set(); return
        if not data[1]: messagebox.showwarning("Input Required", "'Naam' cannot be empty.", parent=self); self.entries[1].focus_set(); return
        self.result = data
        if self.callback: self.callback(self.result)
        self.destroy()
    def on_cancel(self, event=None): 
        print("[RECORD DIALOG DEBUG] Cancelled.")
        if self.callback: 
            self.callback(None)
        self.destroy()

# --- Calendar Event Add/Edit Dialog Class (Keep Existing) ---
class CalendarEventDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_event_dict=None, callback=None):
        super().__init__(parent); self.transient(parent); self.title(title); self.callback = callback; self.result = None
        self.initial_data = initial_event_dict or {}; default_date = datetime.date.today().isoformat(); default_color = CALENDAR_EVENT_COLORS[0] if CALENDAR_EVENT_COLORS else "black"
        print(f"[CALENDAR DIALOG] Init '{title}': {self.initial_data}")
        frame = ttk.Frame(self, padding="15"); frame.pack(expand=True, fill=tk.BOTH); row_index = 0
        ttk.Label(frame, text="Date (YYYY-MM-DD):*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5); self.entry_date = ttk.Entry(frame, width=20); self.entry_date.grid(row=row_index, column=1, sticky=tk.W, padx=5, pady=2); self.entry_date.insert(0, self.initial_data.get('date', default_date)); row_index += 1
        ttk.Label(frame, text="Event Name:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5); self.entry_name = ttk.Entry(frame, width=45); self.entry_name.grid(row=row_index, column=1, sticky=(tk.W, tk.E), padx=5, pady=2); self.entry_name.insert(0, self.initial_data.get('name', '')); row_index += 1
        ttk.Label(frame, text="Color:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5); self.color_var = tk.StringVar(value=self.initial_data.get('color', default_color)); self.combo_color = ttk.Combobox(frame, textvariable=self.color_var, values=CALENDAR_EVENT_COLORS, state="readonly", width=18); self.combo_color.grid(row=row_index, column=1, sticky=tk.W, padx=5, pady=2)
        if self.initial_data.get('color') in CALENDAR_EVENT_COLORS: 
            self.combo_color.set(self.initial_data['color']) 
        else: 
            self.combo_color.set(default_color)
        row_index += 1
        ttk.Label(frame, text="Link (Optional):").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5); self.entry_link = ttk.Entry(frame, width=45); self.entry_link.grid(row=row_index, column=1, sticky=(tk.W, tk.E), padx=5, pady=2); self.entry_link.insert(0, self.initial_data.get('link') or ''); row_index += 1
        frame.columnconfigure(1, weight=1)
        button_frame = ttk.Frame(frame); button_frame.grid(row=row_index, column=0, columnspan=2, pady=(15, 0), sticky=tk.E)
        ok_button = ttk.Button(button_frame, text="OK", command=self.on_ok); ok_button.pack(side=tk.RIGHT, padx=(5, 0)); cancel_button = ttk.Button(button_frame, text="Cancel", command=self.on_cancel); cancel_button.pack(side=tk.RIGHT)
        self.grab_set(); self.protocol("WM_DELETE_WINDOW", self.on_cancel); self.bind("<Return>", self.on_ok); self.bind("<Escape>", self.on_cancel); self.entry_date.focus_set(); self.wait_window(self); print("[CALENDAR DIALOG DEBUG] Dialog closed.")
    def on_ok(self, event=None):
        print("[CALENDAR DIALOG DEBUG] OK pressed."); date_str = self.entry_date.get().strip(); name = self.entry_name.get().strip(); color = self.color_var.get(); link = self.entry_link.get().strip() or None
        if not date_str: messagebox.showwarning("Input Required", "'Date' cannot be empty.", parent=self); self.entry_date.focus_set(); return
        try: normalized_date_str = datetime.datetime.strptime(date_str, '%Y-%m-%d').date().isoformat()
        except ValueError: messagebox.showwarning("Invalid Format", "'Date' must be YYYY-MM-DD.", parent=self); self.entry_date.focus_set(); return
        if not name: messagebox.showwarning("Input Required", "'Event Name' cannot be empty.", parent=self); self.entry_name.focus_set(); return
        if not color or color not in CALENDAR_EVENT_COLORS: messagebox.showerror("Internal Error", "Invalid color selected.", parent=self); return
        if link and not (link.startswith(('http://', 'https://', '/', '#', 'mailto:'))):
             if not messagebox.askyesno("Link Format Check", f"Unusual link format:\n'{link}'\nIs this correct?", icon='question', parent=self): self.entry_link.focus_set(); return
        self.result = {'date': normalized_date_str, 'name': name, 'color': color, 'link': link}; print(f"[CALENDAR DIALOG DEBUG] Result: {self.result}")
        if self.callback: self.callback(self.result)
        self.destroy()
    def on_cancel(self, event=None): 
        print("[CALENDAR DIALOG DEBUG] Cancelled.")
        if self.callback: 
            self.callback(None)
        self.destroy()

# --- Add Element Dialog Class (NEW) ---
# --- Add Element Dialog Class (MODIFIED for Descriptions) ---
class AddElementDialog(tk.Toplevel):
    # Define the mapping INSIDE the class for clarity
    ELEMENT_MAP = {
        "Subtitle (h3)": "h3",
        "Sub-subtitle (h4)": "h4",
        "Paragraph (p)": "p",
        "List Item (li)": "li",
        "Division (div)": "div",
        "Heading 2 (h2)": "h2", # Added h2
        "Heading 5 (h5)": "h5", # Added h5
        "Heading 6 (h6)": "h6", # Added h6
        # Add more mappings as needed (e.g., "Table Data (td)": "td")
    }

    def __init__(self, parent, title, callback=None, default_font=None):
        super().__init__(parent); self.transient(parent); self.title(title); self.callback = callback; self.result = None
        print(f"[ADD ELEMENT DIALOG] Init '{title}'")
        frame = ttk.Frame(self, padding="15"); frame.pack(expand=True, fill=tk.BOTH)
        row_index = 0

        # --- Element Type ---
        ttk.Label(frame, text="Element Type:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.element_description_var = tk.StringVar() # Use a different var name
        # Get descriptive names (keys) for the dropdown
        element_descriptions = sorted(list(AddElementDialog.ELEMENT_MAP.keys()))
        self.element_type_combo = ttk.Combobox(frame, textvariable=self.element_description_var, values=element_descriptions, state="readonly", width=25) # Wider dropdown
        self.element_type_combo.grid(row=row_index, column=1, columnspan=2, sticky=tk.W, padx=5, pady=2) # Span 2 cols
        if element_descriptions: self.element_type_combo.set(element_descriptions[0]) # Default to first option
        row_index += 1

        # --- Text Content ---
        ttk.Label(frame, text="Text Content:*").grid(row=row_index, column=0, sticky=(tk.W, tk.N), padx=5, pady=5)
        self.text_area = scrolledtext.ScrolledText(frame, width=60, height=6, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1, font=default_font)
        self.text_area.grid(row=row_index, column=1, columnspan=2, sticky="nsew", padx=5, pady=2)
        frame.grid_rowconfigure(row_index, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        row_index += 1

        # --- Position Selection ---
        ttk.Label(frame, text="Position (relative\nto selected item's tag):*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.position_var = tk.StringVar(value='after') # Default to after
        after_radio = ttk.Radiobutton(frame, text="After Selected Item's Tag", variable=self.position_var, value='after')
        after_radio.grid(row=row_index, column=1, sticky=tk.W, padx=5, pady=2)
        before_radio = ttk.Radiobutton(frame, text="Before Selected Item's Tag", variable=self.position_var, value='before')
        before_radio.grid(row=row_index, column=2, sticky=tk.W, padx=5, pady=2)
        row_index += 1


        # --- Buttons ---
        button_frame = ttk.Frame(frame); button_frame.grid(row=row_index, column=0, columnspan=3, pady=(15, 0), sticky=tk.E)
        ok_button = ttk.Button(button_frame, text="Add Element", command=self.on_ok); ok_button.pack(side=tk.RIGHT, padx=(5, 0))
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.on_cancel); cancel_button.pack(side=tk.RIGHT)

        self.grab_set(); self.protocol("WM_DELETE_WINDOW", self.on_cancel); self.bind("<Escape>", self.on_cancel)
        self.element_type_combo.focus_set(); self.wait_window(self); print("[ADD ELEMENT DIALOG DEBUG] Dialog closed.")

    def on_ok(self, event=None):
        selected_description = self.element_description_var.get()
        # Map description back to actual HTML tag
        element_type = AddElementDialog.ELEMENT_MAP.get(selected_description)

        new_text_content = self.text_area.get('1.0', tk.END)[:-1].strip()
        position = self.position_var.get()
        print(f"[ADD ELEMENT DIALOG DEBUG] OK pressed. Desc='{selected_description}', Tag='{element_type}', Pos='{position}', Text='{new_text_content[:50]}...'")

        if not element_type: messagebox.showerror("Error", "Invalid element type selected.", parent=self); return # Should not happen with readonly combo
        if not new_text_content: messagebox.showwarning("Input Required", "Enter the text content for the new element.", parent=self); self.text_area.focus_set(); return
        if not position: messagebox.showerror("Error", "Select a position (Before/After).", parent=self); return

        # Pass the ACTUAL element type ('h3', 'li', etc.) to the callback
        self.result = (element_type, new_text_content, position)
        if self.callback: self.callback(element_type, new_text_content, position)
        self.destroy()

    def on_cancel(self, event=None):
        print("[ADD ELEMENT DIALOG DEBUG] Cancelled.")
        if self.callback: self.callback(None, None, None)
        self.destroy()

class AddTextDialog(tk.Toplevel):
    def __init__(self, parent, title, callback=None, default_font=None):
        super().__init__(parent); self.transient(parent); self.title(title); self.callback = callback; self.result = None
        print(f"[ADD TEXT DIALOG] Init '{title}'")
        frame = ttk.Frame(self, padding="15"); frame.pack(expand=True, fill=tk.BOTH)
        row_index = 0

        # Position Selection
        ttk.Label(frame, text="Position:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.position_var = tk.StringVar(value='after') # Default to after
        after_radio = ttk.Radiobutton(frame, text="After Selected Text", variable=self.position_var, value='after')
        after_radio.grid(row=row_index, column=1, sticky=tk.W, padx=5, pady=2)
        before_radio = ttk.Radiobutton(frame, text="Before Selected Text", variable=self.position_var, value='before')
        before_radio.grid(row=row_index, column=2, sticky=tk.W, padx=5, pady=2)
        row_index += 1

        # Text Input - Use the passed default_font
        ttk.Label(frame, text="New Text:*").grid(row=row_index, column=0, sticky=(tk.W, tk.N), padx=5, pady=5)
        self.text_area = scrolledtext.ScrolledText(frame, width=60, height=8, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1, font=default_font) # Use default_font here
        self.text_area.grid(row=row_index, column=1, columnspan=2, sticky="nsew", padx=5, pady=2)
        frame.grid_rowconfigure(row_index, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        row_index += 1

        # Buttons
        button_frame = ttk.Frame(frame); button_frame.grid(row=row_index, column=0, columnspan=3, pady=(15, 0), sticky=tk.E)
        ok_button = ttk.Button(button_frame, text="Add Text", command=self.on_ok); ok_button.pack(side=tk.RIGHT, padx=(5, 0))
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.on_cancel); cancel_button.pack(side=tk.RIGHT)

        self.grab_set(); self.protocol("WM_DELETE_WINDOW", self.on_cancel); self.bind("<Escape>", self.on_cancel)
        self.text_area.focus_set(); self.wait_window(self); print("[ADD TEXT DIALOG DEBUG] Dialog closed.")

    def on_ok(self, event=None):
        # ... (rest of the method remains the same)
        new_text = self.text_area.get('1.0', tk.END)[:-1].strip() # Remove trailing newline and strip
        position = self.position_var.get()
        print(f"[ADD TEXT DIALOG DEBUG] OK pressed. Position={position}, Text='{new_text[:50]}...'")
        if not new_text: messagebox.showwarning("Input Required", "Please enter the text to add.", parent=self); self.text_area.focus_set(); return
        if not position: messagebox.showerror("Error", "Please select a position (Before/After).", parent=self); return

        self.result = (new_text, position)
        if self.callback: self.callback(new_text, position)
        self.destroy()

    def on_cancel(self, event=None):
        # ... (rest of the method remains the same)
        print("[ADD TEXT DIALOG DEBUG] Cancelled.")
        if self.callback: self.callback(None, None) # Send None values
        self.destroy()

# --- Image Add Dialog Class (NEW) ---
class ImageAddDialog(tk.Toplevel):
    def __init__(self, parent, title, callback=None):
        super().__init__(parent); self.transient(parent); self.title(title); self.callback = callback; self.result = None
        print(f"[IMAGE ADD DIALOG] Init '{title}'")
        frame = ttk.Frame(self, padding="15"); frame.pack(expand=True, fill=tk.BOTH); row_index = 0

        # Source File Selection
        ttk.Label(frame, text="Source Image File:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.source_path_var = tk.StringVar()
        source_entry = ttk.Entry(frame, textvariable=self.source_path_var, width=50, state="readonly")
        source_entry.grid(row=row_index, column=1, sticky="ew", padx=5, pady=2)
        browse_button = ttk.Button(frame, text="Browse...", command=self._browse_source)
        browse_button.grid(row=row_index, column=2, sticky="w", padx=5, pady=2)
        row_index += 1

        # Destination Folder Selection
        ttk.Label(frame, text="Destination Folder:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.dest_rel_path_var = tk.StringVar()
        dest_options = sorted(list(IMAGE_COMMON_DIRS_ABSOLUTE.keys())) + ["<Other...>"] # Add other option
        self.dest_combo = ttk.Combobox(frame, textvariable=self.dest_rel_path_var, values=dest_options, state="readonly", width=48)
        self.dest_combo.grid(row=row_index, column=1, sticky="ew", padx=5, pady=2)
        if dest_options[0] != "<Other...>": self.dest_combo.set(dest_options[0]) # Default to first common dir
        else: self.dest_combo.set("")
        self.dest_combo.bind("<<ComboboxSelected>>", self._toggle_other_dest)
        self.other_dest_button = ttk.Button(frame, text="Browse...", command=self._browse_dest, state=tk.DISABLED)
        self.other_dest_button.grid(row=row_index, column=2, sticky="w", padx=5, pady=2)
        row_index += 1
        ttk.Label(frame, text="Folder relative to website root", style="Desc.TLabel").grid(row=row_index, column=1, sticky="w", padx=5)
        row_index += 1

        frame.columnconfigure(1, weight=1)

        # Buttons
        button_frame = ttk.Frame(frame); button_frame.grid(row=row_index, column=0, columnspan=3, pady=(15, 0), sticky=tk.E)
        ok_button = ttk.Button(button_frame, text="Add Image", command=self.on_ok); ok_button.pack(side=tk.RIGHT, padx=(5, 0))
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.on_cancel); cancel_button.pack(side=tk.RIGHT)

        self.grab_set(); self.protocol("WM_DELETE_WINDOW", self.on_cancel); self.bind("<Escape>", self.on_cancel)
        self.wait_window(self); print("[IMAGE ADD DIALOG DEBUG] Dialog closed.")

    def _browse_source(self):
        filetypes = (("Image files", "*.jpg *.jpeg *.png *.gif *.webp *.bmp"), ("All files", "*.*"))
        source_path = filedialog.askopenfilename(title="Select Source Image", filetypes=filetypes)
        if source_path:
            self.source_path_var.set(source_path)
            print(f"[IMAGE ADD DIALOG] Source selected: {source_path}")

    def _toggle_other_dest(self, event=None):
        if self.dest_rel_path_var.get() == "<Other...>":
            self.other_dest_button.config(state=tk.NORMAL)
        else:
            self.other_dest_button.config(state=tk.DISABLED)

    def _browse_dest(self):
        # Allow selecting a sub-directory within the application base directory
        dest_dir_abs = filedialog.askdirectory(title="Select Destination Folder (within website structure)", initialdir=APP_BASE_DIR)
        if dest_dir_abs:
            # Convert absolute path back to relative for display/storage if possible
            try:
                 dest_rel_path = os.path.relpath(dest_dir_abs, APP_BASE_DIR)
                 dest_rel_path_posix = str(pathlib.Path(dest_rel_path).as_posix())
                 self.dest_rel_path_var.set(dest_rel_path_posix) # Update combobox text
                 print(f"[IMAGE ADD DIALOG] Other destination selected: Rel='{dest_rel_path_posix}', Abs='{dest_dir_abs}'")
            except ValueError:
                 # If path is outside APP_BASE_DIR (e.g., different drive)
                 messagebox.showwarning("Path Warning", "Destination folder is outside the website base directory. Using absolute path.", parent=self)
                 self.dest_rel_path_var.set(dest_dir_abs) # Show absolute path
                 print(f"[IMAGE ADD DIALOG] Other destination selected (absolute): {dest_dir_abs}")


    def on_ok(self, event=None):
        source_path = self.source_path_var.get()
        dest_rel_path = self.dest_rel_path_var.get()
        print(f"[IMAGE ADD DIALOG DEBUG] OK pressed. Source='{source_path}', DestRel='{dest_rel_path}'")

        if not source_path: messagebox.showwarning("Input Required", "Select a source image file.", parent=self); return
        if not dest_rel_path or dest_rel_path == "<Other...>": messagebox.showwarning("Input Required", "Select a destination folder.", parent=self); return

        # Determine absolute destination path
        dest_abs_path = ""
        if dest_rel_path in IMAGE_COMMON_DIRS_ABSOLUTE:
            dest_abs_path = IMAGE_COMMON_DIRS_ABSOLUTE[dest_rel_path]
        elif os.path.isabs(dest_rel_path): # Handle case where user browsed outside base dir
            dest_abs_path = dest_rel_path
        else: # Assume relative path entered via "Other..." browsing
            dest_abs_path = os.path.abspath(os.path.join(APP_BASE_DIR, dest_rel_path))

        if not dest_abs_path:
             messagebox.showerror("Error", "Could not determine absolute destination path.", parent=self); return

        print(f"[IMAGE ADD DIALOG DEBUG] Final Dest Abs='{dest_abs_path}'")

        if self.callback: self.callback(source_path, dest_abs_path, dest_rel_path)
        self.destroy()

    def on_cancel(self, event=None):
        print("[IMAGE ADD DIALOG DEBUG] Cancelled.")
        if self.callback: self.callback(None, None, None)
        self.destroy()


# --- Main Execution ---
if __name__ == "__main__":
    print("\n--- Starting Website Editor ---")
    # --- Pre-flight Checks (Revised) ---
    errors_found, warnings_found = False, False; print("\n[Check 1] Checking Libraries...")
    # BS4 check moved to top level
    if not HAS_PILLOW: print("  - Pillow: --- WARNING - Not Found (Image previews limited) ---"); warnings_found = True
    else: print("  - Pillow: OK")
    try: import lxml; print("  - lxml: OK (Recommended HTML parser)")
    except ImportError: print("  - lxml: --- WARNING - Not Found (html.parser fallback) ---"); warnings_found = True

    print("\n[Check 2] Checking Required Files & Directories...")
    required_paths = {"Records Base Dir": RECORDS_BASE_DIR_ABSOLUTE, "Calendar HTML": CALENDAR_HTML_FILE_PATH, "Reports HTML": REPORTS_HTML_FILE_PATH}
    optional_paths = {"News JSON": NEWS_JSON_FILE_PATH, "News Images Dir": NEWS_IMAGE_DEST_DIR_ABSOLUTE, "Reports Docs Dir": REPORTS_DOCS_DEST_DIR_ABSOLUTE}
    html_scan_targets = HTML_SCAN_TARGET_PATHS_ABSOLUTE
    image_dirs = IMAGE_COMMON_DIRS_ABSOLUTE.values()

    for name, path in required_paths.items():
        if not os.path.exists(path): print(f"  - {name}: *** MISSING *** -> {path}"); errors_found = True
        elif name.endswith("Dir") and not os.path.isdir(path): print(f"  - {name}: *** ERROR (Not Directory) *** -> {path}"); errors_found = True
        elif not name.endswith("Dir") and not os.path.isfile(path): print(f"  - {name}: *** ERROR (Not File) *** -> {path}"); errors_found = True
        else: print(f"  - {name}: OK -> {path}")
    for name, path in optional_paths.items():
        if not os.path.exists(path): print(f"  - {name}: --- Optional - Not Found --- -> {path}"); warnings_found = True
        elif name.endswith("Dir") and not os.path.isdir(path): print(f"  - {name}: *** ERROR (Not Directory) *** -> {path}"); errors_found = True
        elif name.endswith("Dir"): print(f"  - {name}: OK -> {path}") # Check if dir exists for optional dirs
        elif not name.endswith("Dir") and not os.path.isfile(path): print(f"  - {name}: OK (Optional File Not Found) -> {path}") # Optional file is fine if missing
        else: print(f"  - {name}: OK -> {path}")

    print("  - HTML Scan Targets:"); missing_targets = False
    for path in html_scan_targets:
         if not os.path.exists(path): print(f"    - Target Not Found: {path}"); missing_targets = True
    if missing_targets: print("    --- Some HTML scan targets missing. ---"); warnings_found = True
    else: print("    - All configured HTML scan targets exist.")

    print("  - Common Image Directories (Attempting to create if missing):")
    for path in image_dirs:
        try:
            created = False
            if not os.path.exists(path):
                os.makedirs(path); created = True
                print(f"    - Created: {path}"); warnings_found = True # Warn if created
            elif not os.path.isdir(path):
                print(f"    - *** ERROR (Not Directory) *** -> {path}"); errors_found = True
            else:
                print(f"    - OK: {path}")
        except OSError as e:
             print(f"    - *** ERROR Creating Dir *** {path}: {e}"); errors_found = True

    if errors_found:
         print("\n[FATAL ERROR] Critical setup issues found. Cannot continue.")
         try: root_err = tk.Tk(); root_err.withdraw(); messagebox.showerror("Fatal Error - Setup Issue", "Missing required files/dirs or creation error. Check console.", parent=None); root_err.destroy()
         except Exception: pass
         sys.exit(1)
    elif warnings_found:
         print("\n[SETUP WARNING] Optional files/libs missing or dirs created. App will attempt to continue.")
         try: root_warn = tk.Tk(); root_warn.withdraw(); messagebox.showwarning("Setup Warning", "Optional files/libs missing or dirs created. Check console.", parent=None); root_warn.destroy()
         except Exception: pass
    else: print("\n[Check 3] Pre-flight checks passed.")

    print("\n--- Initializing GUI ---")
    root = None
    try:
        root = tk.Tk()
        app = WebsiteEditorApp(root)
        print("--- GUI Ready ---")
        root.mainloop()
        print("\n--- Application Closed ---")
    except Exception as e:
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("[FATAL ERROR] An unexpected error occurred during runtime:")
        import traceback; traceback.print_exc()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        try:
            root_fatal = tk.Tk() if root is None else root; root_fatal.withdraw()
            messagebox.showerror("Fatal Runtime Error", f"An unexpected error occurred:\n{e}\nCheck console.", parent=root_fatal)
            if root_fatal: root_fatal.destroy()
        except Exception as me: print(f"ALSO FAILED TO SHOW TKINTER MESSAGEBOX: {me}")
        input("\nPress Enter to exit...")
        sys.exit(1)
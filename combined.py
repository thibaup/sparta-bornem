# <<< START OF MODIFIED CODE >>>
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import scrolledtext
from tkinter import filedialog
import os
import sys
import re
import datetime
import json
import shutil
import pathlib # For safer path manipulation, especially relative paths
import subprocess # <-- IMPORT SUBPROCESS

try:
    from bs4 import BeautifulSoup, Tag, NavigableString, Comment # Added NavigableString, Comment
except ImportError:
    print("\nERROR: BeautifulSoup4 library not found (needed for Records/Calendar/Reports/Text Editor).")
    print("Please install it using: pip install beautifulsoup4")
    BeautifulSoup = None
    Tag = None
    NavigableString = None
    Comment = None

# --- Determine Application Base Directory ---
# (Using the improved logic from your provided code)
if getattr(sys, 'frozen', False):
    APP_BASE_DIR = os.path.dirname(sys.executable)
    print(f"[INFO] Running from frozen executable. Base directory: {APP_BASE_DIR}")
elif __file__:
    # Handle cases where __file__ might be relative when run differently
    APP_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    print(f"[INFO] Running from Python script. Base directory: {APP_BASE_DIR}")
else:
    # Fallback if __file__ is not available (e.g., interactive session)
    APP_BASE_DIR = os.getcwd()
    print(f"[WARNING] Could not determine script path reliably. Using current working directory: {APP_BASE_DIR}")

# --- Configuration (Using APP_BASE_DIR for data) ---
try:
    print(f"[CONFIG] Application Base Directory (for data): {APP_BASE_DIR}")

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
    REPORTS_DOCS_HREF_DIR_RELATIVE = '/docs/bestuursvergadering'
    REPORTS_DOCS_DEST_DIR_ABSOLUTE = os.path.join(APP_BASE_DIR, 'docs', 'bestuursvergadering')
    print(f"[CONFIG] Reports HTML path: {REPORTS_HTML_FILE_PATH}")
    print(f"[CONFIG] Reports Docs Dest path (absolute): {REPORTS_DOCS_DEST_DIR_ABSOLUTE}")
    print(f"[CONFIG] Reports Docs Href path (relative): {REPORTS_DOCS_HREF_DIR_RELATIVE}")

    # --- Text Editor Config (NEW) ---
    TEXT_EDITOR_TARGET_PATHS_RELATIVE = [
        'index.html',
        os.path.join('html', '(Nieuwe) leden'), # Folder
        os.path.join('html', 'info'),           # Folder
        os.path.join('html', 'extra'),          # Folder
        os.path.join('html', 'wedstrijden', 'wedstrijdinfo.html') # File
    ]
    TEXT_EDITOR_TARGET_PATHS_ABSOLUTE = [os.path.join(APP_BASE_DIR, p) for p in TEXT_EDITOR_TARGET_PATHS_RELATIVE]
    TEXT_EDITOR_EXCLUDED_TAGS = ['script', 'style'] # Tags whose text content should be ignored
    print(f"[CONFIG] Text Editor Target Paths (absolute): {TEXT_EDITOR_TARGET_PATHS_ABSOLUTE}")
    print(f"[CONFIG] Text Editor Excluded Tags: {TEXT_EDITOR_EXCLUDED_TAGS}")

except Exception as e:
    print(f"\n[FATAL ERROR] Failed to configure paths.")
    print(f"APP_BASE_DIR was calculated as: {APP_BASE_DIR if 'APP_BASE_DIR' in locals() else 'Not Set'}")
    print(f"Error details: {e}")
    try:
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("Fatal Error", f"Failed to configure paths:\n{e}")
        root.destroy()
    except Exception: pass
    input("Press Enter to exit...")
    sys.exit(1)


# --- Helper Functions: News ---
# (Keep existing _news_... functions)
def _news_load_existing_data(filepath):
    """Loads existing NEWS JSON data from the file."""
    if not os.path.exists(filepath):
        print(f"[NEWS INFO] News JSON '{filepath}' not found. Starting empty list.")
        return [], None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                print(f"[NEWS INFO] News JSON '{filepath}' is empty. Starting empty list.")
                return [], None
            data = json.loads(content)
            if not isinstance(data, list):
                msg = f"[NEWS WARNING] Data in '{filepath}' is not a list. Please fix or delete."
                print(msg)
                return None, msg
            print(f"[NEWS DEBUG] Loaded {len(data)} news items from {filepath}")
            return data, None
    except json.JSONDecodeError as e:
        msg = f"[NEWS ERROR] Could not decode JSON from '{filepath}': {e}"
        print(msg)
        return None, msg
    except Exception as e:
        msg = f"[NEWS ERROR] Loading news data from '{filepath}': {e}"
        print(msg)
        return None, msg

def _news_save_data(filepath, data):
    """Saves the NEWS data list back to the JSON file."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[NEWS INFO] Successfully updated '{filepath}'")
        return None
    except Exception as e:
        msg = f"[NEWS ERROR] Saving news data to '{filepath}': {e}"
        print(msg)
        return msg

def _news_auto_link_text(text):
    """Converts plain text URLs and emails to HTML links for news content."""
    if not text: return ''
    # Simple email regex
    email_regex = r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b'
    # More robust URL regex (handles various schemes, www., paths, query params, fragments)
    # Need to be careful not to match inside existing HTML tags
    url_regex = r'(?<!href=["\'])(?<!src=["\'])\b((?:https?://|www\.)[^\s<>"]+?\.[^\s<>"]+)'

    def replace_email(match):
        email = match.group(1)
        return f'<a href="mailto:{email}">{email}</a>'

    def replace_url(match):
        url = match.group(1)
        href = url
        if href.startswith('www.'):
            href = 'https://' + href
        # Basic check to avoid relinking inside existing tags (might need refinement)
        # This is simple and might miss complex cases.
        return f'<a href="{href}" target="_blank" rel="noopener noreferrer">{url}</a>'

    # Apply email replacement first
    text = re.sub(email_regex, replace_email, text)
     # Apply URL replacement
    text = re.sub(url_regex, replace_url, text)

    return text

def _news_is_valid_id(article_id):
    """Checks if NEWS ID format is valid."""
    return bool(re.match(r'^[a-z0-9-]+$', article_id))

# --- Helper Functions: Records ---
# (Keep existing _records_... functions)
def _records_discover_files(base_dir):
    """Discovers HTML record files."""
    print(f"[RECORDS DEBUG] Discovering files in: {base_dir}")
    record_structure = {}
    if not os.path.isdir(base_dir):
        print(f"[RECORDS ERROR] Base directory not found: {base_dir}")
        return {}
    try:
        categories = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))])
        print(f"[RECORDS DEBUG] Found categories: {categories}")
        for category in categories:
            category_path = os.path.join(base_dir, category)
            record_structure[category] = {}
            try:
                files = sorted([f for f in os.listdir(category_path) if f.lower().endswith('.html')])
                print(f"[RECORDS DEBUG] Files in '{category}': {files}")
                for filename in files:
                    base_name = os.path.splitext(filename)[0]
                    record_type_name = ' '.join(word.capitalize() for word in base_name.split('-')) # Handle hyphens too
                    full_path = os.path.join(category_path, filename)
                    record_structure[category][record_type_name] = full_path
            except OSError as e:
                 print(f"[RECORDS WARNING] Could not read dir {category_path}: {e}")
    except OSError as e:
        print(f"[RECORDS ERROR] Accessing base dir {base_dir}: {e}")
        return {}
    print(f"[RECORDS DEBUG] Discovery complete.")
    return record_structure

def _records_parse_html(html_path):
    """Parses records from HTML."""
    if not BeautifulSoup:
        print("[RECORDS ERROR] Cannot parse HTML: BeautifulSoup library not loaded.")
        return None
    records = []
    print(f"[RECORDS DEBUG] Parsing HTML file: {html_path}")
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            try:
                soup = BeautifulSoup(f, 'lxml'); parser_used = "lxml"
            except Exception:
                print("[RECORDS WARNING] lxml parser failed, trying html.parser.")
                f.seek(0); soup = BeautifulSoup(f, 'html.parser'); parser_used = "html.parser"
            print(f"[RECORDS DEBUG] Parsed using {parser_used}.")

        tbody = soup.find('table', class_='records-table')
        if tbody: tbody = tbody.find('tbody')
        if not tbody:
            # Try finding any tbody as a fallback
            print(f"[RECORDS WARNING] No tbody in table.records-table in {html_path}. Trying any tbody.")
            tbody = soup.find('tbody')
            if not tbody:
                 print(f"[RECORDS ERROR] No <tbody> found at all in {html_path}")
                 return None

        rows_found, valid_rows = 0, 0
        for row in tbody.find_all('tr', recursive=False):
            rows_found += 1
            cells = [td.get_text(strip=True) for td in row.find_all('td', recursive=False)]
            if len(cells) == 5:
                records.append(cells); valid_rows += 1
            else:
                print(f"[RECORDS WARNING] Row in {html_path} has {len(cells)} cells (expected 5): {cells}")

        print(f"[RECORDS DEBUG] Found {rows_found} rows, parsed {valid_rows} valid records.")
        return records
    except FileNotFoundError:
        print(f"[RECORDS ERROR] File not found: {html_path}")
        return None
    except Exception as e:
        import traceback
        print(f"[RECORDS ERROR] Parsing HTML file {html_path}:"); traceback.print_exc()
        return None

def _records_save_html(html_path, records_data):
    """Saves records back to HTML."""
    if not BeautifulSoup:
        print("[RECORDS ERROR] Cannot save HTML: BeautifulSoup library not loaded.")
        return False
    print(f"[RECORDS DEBUG] Saving {len(records_data)} records to: {html_path}")
    try:
        # It's crucial to read the *entire* file to preserve structure outside the table
        with open(html_path, 'r', encoding='utf-8') as f:
             try: soup = BeautifulSoup(f, 'lxml')
             except Exception:
                 print("[RECORDS WARNING] lxml parser failed for saving, trying html.parser.")
                 f.seek(0); soup = BeautifulSoup(f, 'html.parser')

        tbody = soup.find('table', class_='records-table')
        if tbody: tbody = tbody.find('tbody')
        if not tbody:
             # Try finding any tbody as a fallback
             print(f"[RECORDS WARNING] No tbody in table.records-table for saving. Trying any tbody.")
             tbody = soup.find('tbody')
             if not tbody:
                 print(f"[RECORDS ERROR] Cannot find <tbody> in {html_path} to save.")
                 return False

        # Clear only the *tbody* content
        tbody.clear()
        print("[RECORDS DEBUG] Cleared existing tbody content.")
        for record_row in records_data:
            new_tr = soup.new_tag('tr')
            for cell_data in record_row:
                new_td = soup.new_tag('td')
                # Handle None values explicitly before converting to string
                new_td.string = str(cell_data) if cell_data is not None else ""
                new_tr.append(new_td)
            tbody.append(new_tr)
        print(f"[RECORDS DEBUG] Added {len(records_data)} new rows to tbody.")

        # Write the modified soup (including unchanged parts) back to the file
        with open(html_path, 'w', encoding='utf-8') as f:
            # Use prettify for slightly better formatting, though results vary
            f.write(soup.prettify(formatter="html5"))
            # Alternatively, use str(soup) for more compact output:
            # f.write(str(soup))

        print("[RECORDS DEBUG] File successfully written.")
        return True
    except FileNotFoundError:
        print(f"[RECORDS ERROR] File not found for saving: {html_path}")
        return False
    except Exception as e:
        import traceback
        print(f"[RECORDS ERROR] Saving records to {html_path}:"); traceback.print_exc()
        return False

# --- Helper Functions: Calendar ---
# (Keep existing _calendar_... functions)
def _calendar_parse_html(html_path):
    """Parses events from kalender.html."""
    if not BeautifulSoup:
        print("[CALENDAR ERROR] Cannot parse HTML: BeautifulSoup library not loaded.")
        return None
    events = []
    print(f"[CALENDAR DEBUG] Parsing calendar file: {html_path}")
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            try: soup = BeautifulSoup(f, 'lxml'); parser_used = "lxml"
            except Exception:
                print("[CALENDAR WARNING] lxml parser failed, trying html.parser.")
                f.seek(0); soup = BeautifulSoup(f, 'html.parser'); parser_used = "html.parser"
            print(f"[CALENDAR DEBUG] Parsed using {parser_used}.")

        month_grids = soup.find_all('section', class_='month-grid')
        if not month_grids:
            print("[CALENDAR ERROR] No sections with class 'month-grid' found.")
            return None
        print(f"[CALENDAR DEBUG] Found {len(month_grids)} month grids.")

        for month_section in month_grids:
            month_title_tag = month_section.find('h2', class_='month-title')
            if not month_title_tag:
                print("[CALENDAR WARNING] Skipping month section - no h2.month-title found.")
                continue

            month_title_text = month_title_tag.get_text(strip=True)
            match = re.match(r'(\w+)\s+(\d{4})', month_title_text, re.IGNORECASE)
            if not match:
                print(f"[CALENDAR WARNING] Skipping month: Could not parse month/year from '{month_title_text}'")
                continue

            month_name_nl, year_str = match.groups()
            month_num = DUTCH_MONTH_MAP.get(month_name_nl.lower())
            year = int(year_str)

            if not month_num:
                print(f"[CALENDAR WARNING] Skipping month: Unknown month name '{month_name_nl}'")
                continue
            print(f"[CALENDAR DEBUG] Processing Month: {month_name_nl} {year} (Month: {month_num})")

            # Select only non-padding day divs within the current month section
            day_divs = month_section.select('.calendar-days .calendar-day:not(.padding-day)')
            for day_div in day_divs:
                day_num_tag = day_div.find('span', class_='day-number')
                if not day_num_tag: continue # Should not happen in valid non-padding day

                try:
                    day = int(day_num_tag.get_text(strip=True))
                    current_date_str = f"{year:04d}-{month_num:02d}-{day:02d}"
                except ValueError:
                    print(f"[CALENDAR WARNING] Invalid day number found: '{day_num_tag.get_text(strip=True)}'")
                    continue

                # Find events within this specific day_div
                # recursive=False is important here to only get direct children spans
                day_events = day_div.find_all('span', class_='calendar-event', recursive=False)
                for event_span in day_events:
                    event_name = ""
                    event_link = None
                    event_color = "black" # Default color

                    # Extract link and name
                    link_tag = event_span.find('a')
                    if link_tag:
                        event_name = link_tag.get_text(strip=True)
                        event_link = link_tag.get('href')
                    else:
                        # Get text directly from the span if no link
                        event_name = event_span.get_text(strip=True)

                    # Extract color from class list
                    for css_class in event_span.get('class', []):
                        if css_class.startswith('event-') and css_class.split('-')[1] in CALENDAR_EVENT_COLORS:
                            event_color = css_class.split('-')[1]
                            break # Found the color class

                    if event_name: # Only add if we found a name
                        events.append({
                            'date': current_date_str,
                            'name': event_name,
                            'color': event_color,
                            'link': event_link # Can be None
                        })
                    else:
                         print(f"[CALENDAR WARNING] Found event span with no name on {current_date_str}")

        # Sort events by date after parsing all months
        events.sort(key=lambda x: x['date'])
        print(f"[CALENDAR DEBUG] Parsed total {len(events)} events.")
        return events

    except FileNotFoundError:
        print(f"[CALENDAR ERROR] Calendar file not found: {html_path}")
        return None
    except Exception as e:
        import traceback
        print(f"[CALENDAR ERROR] Parsing calendar file {html_path}:")
        traceback.print_exc()
        return None

def _calendar_save_html(html_path, events_data):
    """Saves the list of event dicts back into kalender.html."""
    if not BeautifulSoup:
        print("[CALENDAR ERROR] Cannot save HTML: BeautifulSoup library not loaded.")
        return False

    print(f"[CALENDAR DEBUG] Saving {len(events_data)} events to: {html_path}")
    try:
        # Read existing content first to preserve structure outside calendar days
        with open(html_path, 'r', encoding='utf-8') as f:
             try: soup = BeautifulSoup(f, 'lxml')
             except Exception:
                 print("[CALENDAR WARNING] lxml parser failed for saving, trying html.parser.")
                 f.seek(0); soup = BeautifulSoup(f, 'html.parser')

        # Create a lookup dictionary for faster searching: {'YYYY-MM-DD': [event1, event2,...]}
        events_by_date = {}
        for event in events_data:
            date_str = event['date']
            if date_str not in events_by_date:
                events_by_date[date_str] = []
            events_by_date[date_str].append(event)

        month_grids = soup.find_all('section', class_='month-grid')
        if not month_grids:
             print("[CALENDAR ERROR] Cannot save: No sections with class 'month-grid' found in HTML.")
             return False

        # Process each month grid found in the template
        for month_section in month_grids:
            month_title_tag = month_section.find('h2', class_='month-title')
            if not month_title_tag: continue # Skip if no title
            month_title_text = month_title_tag.get_text(strip=True)
            match = re.match(r'(\w+)\s+(\d{4})', month_title_text, re.IGNORECASE)
            if not match: continue # Skip if title format is wrong
            month_name_nl, year_str = match.groups()
            month_num = DUTCH_MONTH_MAP.get(month_name_nl.lower())
            if not month_num: continue # Skip if month name unknown
            year = int(year_str)

            # Process each non-padding day div WITHIN this specific month section
            day_divs = month_section.select('.calendar-days .calendar-day:not(.padding-day)')
            for day_div in day_divs:
                # --- CRITICAL: Remove ALL old event spans first ---
                for old_event in day_div.find_all('span', class_='calendar-event', recursive=False):
                    old_event.decompose() # Remove the entire span and its contents

                day_num_tag = day_div.find('span', class_='day-number')
                if not day_num_tag: continue # Should not happen
                try: day = int(day_num_tag.get_text(strip=True))
                except ValueError: continue # Skip if day number is invalid

                current_date_str = f"{year:04d}-{month_num:02d}-{day:02d}"

                # --- Add new events IF they exist for this specific date ---
                if current_date_str in events_by_date:
                    print(f"[CALENDAR DEBUG] Adding {len(events_by_date[current_date_str])} event(s) for {current_date_str}")
                    for event in events_by_date[current_date_str]:
                        # Create new event span
                        new_event_span = soup.new_tag(
                            'span',
                            # Ensure class exists and add color class
                            attrs={'class': f"calendar-event event-{event.get('color', 'black')}"}
                        )
                        # Add title attribute (good for tooltips on hover)
                        new_event_span['title'] = event.get('name', '')

                        # Create link tag *inside* span if link exists
                        if event.get('link'):
                            link_tag = soup.new_tag('a', href=event['link'])
                            link_tag.string = event.get('name', '') # Link text is the event name
                            # Optional: Add target="_blank" etc. if needed for external links
                            # link_tag['target'] = '_blank'
                            # link_tag['rel'] = 'noopener noreferrer'
                            new_event_span.append(link_tag)
                        else:
                            # No link, just add event name text directly to the span
                            new_event_span.string = event.get('name', '')

                        # Append the completed new span to the day div
                        day_div.append(new_event_span)
                        # Add a newline *after* the span for slightly better source formatting (optional)
                        day_div.append("\n        ") # Match indentation

        # --- Write the modified HTML (entire soup) back ---
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(soup.prettify(formatter="html5")) # Use prettify for readable output

        print("[CALENDAR DEBUG] Calendar file successfully written.")
        return True

    except FileNotFoundError:
        print(f"[CALENDAR ERROR] Calendar file not found for saving: {html_path}")
        return False
    except Exception as e:
        import traceback
        print(f"[CALENDAR ERROR] Saving calendar file {html_path}:")
        traceback.print_exc()
        return False

# --- Helper Functions: Reports ---
# (Keep existing _reports_... functions)
def _reports_parse_html(html_path):
    """Parses reports grouped by year from the HTML file."""
    if not BeautifulSoup or not Tag: # Check for Tag too
        print("[REPORTS ERROR] Cannot parse HTML: BeautifulSoup library not loaded properly.")
        return None, "BeautifulSoup library not loaded."
    reports_data = {} # { "2023": [ {text: "", filename: "", path: ""}, ...], "2022": [...] }
    print(f"[REPORTS DEBUG] Parsing reports file: {html_path}")
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            try: soup = BeautifulSoup(f, 'lxml'); parser_used = "lxml"
            except Exception:
                print("[REPORTS WARNING] lxml parser failed, trying html.parser.")
                f.seek(0); soup = BeautifulSoup(f, 'html.parser'); parser_used = "html.parser"
            print(f"[REPORTS DEBUG] Parsed using {parser_used}.")

        # Find the specific container div
        reports_section = soup.find('div', id='reports-section')
        if not reports_section:
            msg = "Could not find '<div id=\"reports-section\">' in HTML. Cannot parse reports."
            print(f"[REPORTS ERROR] {msg}")
            return None, msg

        current_year = None
        # Iterate through direct children to maintain year grouping logic
        for element in reports_section.children:
             # Skip NavigableStrings (like newlines between tags)
             if not isinstance(element, Tag):
                 continue

             # Check for Year Header (H2)
             if element.name == 'h2':
                 year_match = re.search(r'(\d{4})', element.get_text())
                 if year_match:
                     current_year = year_match.group(1)
                     # Initialize year key only if it doesn't exist
                     if current_year not in reports_data:
                         reports_data[current_year] = []
                     print(f"[REPORTS DEBUG] Found year section: {current_year}")
                 else:
                     current_year = None # Reset if header doesn't contain a year
                     print(f"[REPORTS WARNING] Found H2 without a 4-digit year: {element.get_text(strip=True)}")

             # Check for Report List (UL) *associated with the current valid year*
             elif element.name == 'ul' and 'report-list' in element.get('class', []) and current_year:
                 print(f"[REPORTS DEBUG] Processing report list for year: {current_year}")
                 items_in_list = 0
                 # Find list items directly within this UL
                 for li in element.find_all('li', recursive=False):
                     a_tag = li.find('a', recursive=False) # Find link directly in LI
                     if a_tag and a_tag.get('href'):
                         report_text = a_tag.get_text(strip=True)
                         report_path = a_tag.get('href')
                         # Extract filename from path using pathlib for robustness
                         # Use PurePosixPath because URLs/hrefs use forward slashes
                         report_filename = pathlib.PurePosixPath(report_path).name

                         if report_text and report_path and report_filename:
                             reports_data[current_year].append({
                                 'text': report_text,
                                 'filename': report_filename,
                                 'path': report_path
                             })
                             items_in_list += 1
                         else:
                             print(f"[REPORTS WARNING] Skipping malformed list item in year {current_year}: {li.prettify()}")
                     else:
                         print(f"[REPORTS WARNING] Skipping list item without valid link in year {current_year}: {li.prettify()}")
                 print(f"[REPORTS DEBUG] Found {items_in_list} reports for {current_year}")
                 # Decide whether to reset current_year here. If multiple ULs can belong to one H2, don't reset.
                 # If structure is strictly H2 -> UL, resetting might be safer. Let's not reset for now.
                 # current_year = None

        parsed_count = sum(len(v) for v in reports_data.values())
        print(f"[REPORTS DEBUG] Parsed total {parsed_count} reports across {len(reports_data)} years.")
        # Sort years numerically, descending for consistency (though _reports_save_html does it too)
        sorted_reports_data = dict(sorted(reports_data.items(), key=lambda item: int(item[0]), reverse=True))
        return sorted_reports_data, None

    except FileNotFoundError:
        msg = f"Reports HTML file not found: {html_path}"
        print(f"[REPORTS ERROR] {msg}")
        return None, msg
    except Exception as e:
        import traceback
        msg = f"Parsing reports file {html_path}: {e}"
        print(f"[REPORTS ERROR] {msg}"); traceback.print_exc()
        return None, msg

def _reports_save_html(html_path, reports_data):
    """Saves the reports data structure back into the HTML file, preserving surrounding content."""
    if not BeautifulSoup or not Tag:
        print("[REPORTS ERROR] Cannot save HTML: BeautifulSoup library not loaded properly.")
        return False, "BeautifulSoup library not loaded."

    report_count = sum(len(v) for v in reports_data.values())
    print(f"[REPORTS DEBUG] Saving {report_count} reports to: {html_path}")
    try:
        # Read existing content first to preserve overall structure
        with open(html_path, 'r', encoding='utf-8') as f:
             try: soup = BeautifulSoup(f, 'lxml')
             except Exception:
                 print("[REPORTS WARNING] lxml parser failed for saving, trying html.parser.")
                 f.seek(0); soup = BeautifulSoup(f, 'html.parser')

        # Find the specific container div
        reports_section = soup.find('div', id='reports-section')
        if not reports_section:
            msg = "Cannot save: Could not find '<div id=\"reports-section\">' in HTML template."
            print(f"[REPORTS ERROR] {msg}")
            return False, msg

        # --- Clear only the existing content *within* the reports section ---
        reports_section.clear()
        print("[REPORTS DEBUG] Cleared existing content inside #reports-section.")

        # --- Rebuild the content from reports_data ---
        # Sort years numerically, descending for display order
        sorted_years = sorted(reports_data.keys(), key=int, reverse=True)

        for year in sorted_years:
            year_reports = reports_data[year]
            if not year_reports: # Skip years that became empty
                print(f"[REPORTS DEBUG] Skipping empty year {year} during save.")
                continue

            # Create H2 for the year
            h2_tag = soup.new_tag('h2')
            h2_tag.string = f"Verslagen {year}"
            reports_section.append(h2_tag)
            reports_section.append("\n") # Add newline for readability in source

            # Create UL for the reports
            ul_tag = soup.new_tag('ul', attrs={'class': 'report-list'})
            reports_section.append(ul_tag)
            reports_section.append("\n") # Add newline

            # Sort reports within the year (e.g., by text, or keep original order from data)
            # sorted_year_reports = sorted(year_reports, key=lambda x: x['text']) # Optional sort
            sorted_year_reports = year_reports # Keep order as it was manipulated in the GUI

            for report in sorted_year_reports:
                li_tag = soup.new_tag('li')
                # Create the anchor tag with href and target
                a_tag = soup.new_tag('a', href=report['path'], target='_blank')
                # Set the link text
                a_tag.string = report['text']
                # Append the anchor tag to the list item
                li_tag.append(a_tag)
                # Append the list item to the unordered list
                ul_tag.append(li_tag)
                ul_tag.append("\n") # Add newline after each list item

            print(f"[REPORTS DEBUG] Added section for year {year} with {len(year_reports)} reports.")

        # --- Write the entire modified soup back ---
        with open(html_path, 'w', encoding='utf-8') as f:
            # Use prettify for better formatting
            f.write(soup.prettify(formatter="html5"))

        print("[REPORTS DEBUG] Reports HTML file successfully written.")
        return True, None

    except FileNotFoundError:
        msg = f"Reports HTML file not found for saving: {html_path}"
        print(f"[REPORTS ERROR] {msg}")
        return False, msg
    except Exception as e:
        import traceback
        msg = f"Saving reports file {html_path}: {e}"
        print(f"[REPORTS ERROR] {msg}"); traceback.print_exc()
        return False, msg


# --- Main Application Class ---
class WebsiteEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Thiberta Software")
        # Increase initial size to better accommodate the new tab
        self.root.geometry("1200x900") # Increased size

        print("[GUI INFO] Initializing main application...")
        # --- Style ---
        style = ttk.Style()
        try:
             # Try more modern themes first
             themes = style.theme_names()
             preferred_themes = ["clam", "vista", "aqua", "default"]
             for theme in preferred_themes:
                 if theme in themes:
                     style.theme_use(theme)
                     break
             print(f"[GUI INFO] Using theme: {style.theme_use()}")
        except tk.TclError:
             print("[GUI WARNING] Could not set preferred theme.")
        # Define fonts based on platform for better look
        self.default_font_family = "Segoe UI" if sys.platform == "win32" else "TkDefaultFont"
        self.default_font_size = 9
        self.desc_font_size = 8
        self.bold_font_weight = 'bold'

        self.desc_font = (self.default_font_family, self.desc_font_size)
        self.bold_font = (self.default_font_family, self.default_font_size, self.bold_font_weight)

        style.configure("TLabel", font=(self.default_font_family, self.default_font_size))
        style.configure("TButton", font=(self.default_font_family, self.default_font_size))
        style.configure("TEntry", font=(self.default_font_family, self.default_font_size))
        style.configure("TCombobox", font=(self.default_font_family, self.default_font_size))
        style.configure("Treeview.Heading", font=self.bold_font)
        style.configure("Treeview", rowheight=25, font=(self.default_font_family, self.default_font_size)) # Font for tree items
        style.configure("Desc.TLabel", foreground="grey", font=self.desc_font)
        style.configure("Error.TLabel", foreground="red", font=(self.default_font_family, self.default_font_size))
        style.configure("Bold.TLabel", font=self.bold_font) # For section headers

        # Validation styling for Entries
        try:
             # Style for invalid state (e.g., red border)
             style.map('TEntry',
                       fieldbackground=[('invalid', '#FED8D8'), ('!invalid', 'white')], # Light red background
                       bordercolor=[('invalid', 'red'), ('!invalid', 'grey')],
                       foreground=[('invalid', 'black'), ('!invalid', 'black')])
        except tk.TclError:
            print("[GUI WARNING] Could not configure TEntry validation styles (might depend on theme).")


        # --- Create Notebook (Tabs) ---
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=10, padx=10, expand=True, fill='both')

        # --- Create Frames for each Tab ---
        self.news_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.records_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.calendar_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.reports_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.text_editor_tab_frame = ttk.Frame(self.notebook, padding="10") # New Text Editor Frame

        self.news_tab_frame.pack(fill='both', expand=True)
        self.records_tab_frame.pack(fill='both', expand=True)
        self.calendar_tab_frame.pack(fill='both', expand=True)
        self.reports_tab_frame.pack(fill='both', expand=True)
        self.text_editor_tab_frame.pack(fill='both', expand=True) # Pack New Text Editor Frame

        # --- Add Tabs to Notebook ---
        self.notebook.add(self.news_tab_frame, text=' Manage News ')
        self.notebook.add(self.records_tab_frame, text=' Edit Records ')
        self.notebook.add(self.calendar_tab_frame, text=' Edit Calendar ')
        self.notebook.add(self.reports_tab_frame, text=' Manage Reports ')
        self.notebook.add(self.text_editor_tab_frame, text=' Edit Website Text ') # New Text Editor Tab

        # --- Shared Status Bar ---
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=5)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))
        self.set_status("Application started. Select a tab.")

        # --- Populate Tabs ---
        self._create_news_tab(self.news_tab_frame)
        self._create_records_tab(self.records_tab_frame)
        self._create_calendar_tab(self.calendar_tab_frame)
        self._create_reports_tab(self.reports_tab_frame)
        self._create_text_editor_tab(self.text_editor_tab_frame)

        bottom_bar_frame = ttk.Frame(root)
        bottom_bar_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))

        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(bottom_bar_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), pady=2)

        self.git_publish_button = ttk.Button(bottom_bar_frame, text="Publish Changes (Git)", command=self._git_publish)
        self.git_publish_button.pack(side=tk.RIGHT, pady=2) 

        self.set_status("Application started. Select a tab.")

        print("[GUI INFO] Main application initialized.")


    def _git_publish(self):
        """Runs git pull, add, commit, push commands, with basic conflict check."""
        print("[GIT PUBLISH] Button clicked.")
        git_dir = os.path.join(APP_BASE_DIR, '.git')
        if not os.path.isdir(git_dir):
            messagebox.showwarning("Git Error", f"Could not find a '.git' directory in:\n{APP_BASE_DIR}\n\nEnsure this application runs from your Git repository root.", parent=self.root)
            self.set_status("Publish failed: Not a Git repository root.", is_error=True)
            return

        # --- Prompt for Commit Message ---
        commit_msg = tk.simpledialog.askstring("Commit Message", "Enter a brief description of the changes:", parent=self.root)
        if not commit_msg:
            self.set_status("Git publish cancelled: No commit message entered.", duration_ms=3000)
            return # User cancelled or entered empty message

        # --- Confirmation ---
        if not messagebox.askyesno("Confirm Git Publish",
                                   "This will run the following commands:\n\n"
                                   "1. git pull (attempt to get latest changes)\n"
                                   "2. git add .\n"
                                   f"3. git commit -m \"{commit_msg}\"\n"
                                   "4. git push\n\n"
                                   "Proceed?", parent=self.root):
            self.set_status("Git publish cancelled by user.", duration_ms=3000)
            return

        self.git_publish_button.config(state=tk.DISABLED)
        self.root.update_idletasks()

        # --- Helper function to run commands ---
        def run_git_command(command_list, description):
            self.set_status(f"Running {description}...")
            print(f"[GIT PUBLISH] Executing: {' '.join(command_list)} in {APP_BASE_DIR}")
            self.root.update_idletasks()
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            try:
                result = subprocess.run(
                    command_list, cwd=APP_BASE_DIR, capture_output=True, text=True,
                    check=False, encoding='utf-8', errors='replace', startupinfo=startupinfo
                )
                print(f"[GIT PUBLISH] Return Code: {result.returncode}")
                if result.stdout: print(f"[GIT PUBLISH] STDOUT:\n{result.stdout.strip()}")
                if result.stderr: print(f"[GIT PUBLISH] STDERR:\n{result.stderr.strip()}")
                return result # Return the completed process object
            except FileNotFoundError:
                print("[GIT PUBLISH] Git command not found error.")
                return None # Indicate Git not found
            except Exception as e:
                 print(f"[GIT PUBLISH] Unexpected Python error running command: {e}")
                 return False # Indicate other Python error


        # --- Command Sequence ---
        final_success = True
        error_details = ""

        # 1. Git Pull
        pull_result = run_git_command(['git', 'pull'], 'git pull')
        if pull_result is None: # Git not found
            error_details = "Command Failed: git pull\n\nError: 'git' command not found.\nIs Git installed and in your system's PATH?"
            final_success = False
        elif pull_result is False: # Other Python error
            error_details = "Command Failed: git pull\n\nAn unexpected Python error occurred."
            final_success = False
        elif pull_result.returncode != 0:
            # Check for merge conflicts specifically
            if "Merge conflict" in pull_result.stdout or "Merge conflict" in pull_result.stderr or "Automatic merge failed" in pull_result.stderr:
                error_details = ("Merge Conflict Detected!\n\n"
                                 "'git pull' resulted in merge conflicts.\n"
                                 "You need to resolve these conflicts manually outside this application "
                                 "(using standard Git tools or your code editor) before you can commit and push.\n\n"
                                 "Publish process stopped.")
                print("[GIT PUBLISH] Merge conflict detected during pull. Aborting publish.")
            else:
                # Other pull error
                 error_details = f"Command Failed: git pull\n\nError Code: {pull_result.returncode}\n\n{pull_result.stderr or pull_result.stdout}"
            final_success = False
        else:
             print("[GIT PUBLISH] git pull successful or up-to-date.")
             self.set_status("Pull successful. Proceeding...")
             self.root.update_idletasks()


        # 2. Git Add (only if pull succeeded)
        if final_success:
            add_result = run_git_command(['git', 'add', '.'], 'git add .')
            if add_result is None or add_result is False or add_result.returncode != 0:
                 error_details = f"Command Failed: git add .\n\n{add_result.stderr or add_result.stdout if isinstance(add_result, subprocess.CompletedProcess) else 'Git not found or Python error'}"
                 final_success = False

        # 3. Git Commit (only if pull and add succeeded)
        if final_success:
            commit_result = run_git_command(['git', 'commit', '-m', commit_msg], f'git commit -m "{commit_msg}"')
            if commit_result is None or commit_result is False:
                 error_details = "Command Failed: git commit\n\nGit not found or Python error"
                 final_success = False
            elif commit_result.returncode != 0:
                 # Allow "nothing to commit"
                 if "nothing to commit" in commit_result.stdout or "nothing added to commit" in commit_result.stderr or "no changes added to commit" in commit_result.stdout:
                      print("[GIT PUBLISH] Commit skipped - nothing to commit.")
                      self.set_status("Nothing new to commit. Checking push...")
                      self.root.update_idletasks()
                      # Don't set final_success to False, proceed to push
                 else:
                      error_details = f"Command Failed: git commit\n\nError Code: {commit_result.returncode}\n\n{commit_result.stderr or commit_result.stdout}"
                      final_success = False

        # 4. Git Push (only if pull, add, commit succeeded or commit was skipped)
        if final_success:
             push_result = run_git_command(['git', 'push'], 'git push')
             if push_result is None or push_result is False or push_result.returncode != 0:
                  error_details = f"Command Failed: git push\n\nError Code: {push_result.returncode if isinstance(push_result, subprocess.CompletedProcess) else 'N/A'}\n\n{push_result.stderr or push_result.stdout if isinstance(push_result, subprocess.CompletedProcess) else 'Git not found or Python error'}"
                  # Check for specific non-fast-forward error (means pull needed)
                  if isinstance(push_result, subprocess.CompletedProcess) and 'rejected' in push_result.stderr and ('non-fast-forward' in push_result.stderr or 'fetch first' in push_result.stderr):
                      error_details += "\n\nHint: Remote changes exist. Try 'git pull' manually outside the app, resolve conflicts if any, then try publishing again."
                  final_success = False


        # --- Final Feedback ---
        self.git_publish_button.config(state=tk.NORMAL) # Re-enable button

        if final_success:
            messagebox.showinfo("Git Publish Successful", "Changes successfully pulled (if any), added, committed, and pushed.", parent=self.root)
            self.set_status("Git publish completed successfully.", duration_ms=5000)
        else:
            messagebox.showerror("Git Publish Failed", error_details, parent=self.root)
            self.set_status("Git publish failed. See error popup.", is_error=True)

    def set_status(self, message, is_error=False, duration_ms=0):
        """Sets the status bar message, optionally auto-clearing after a duration."""
        # Always log the message
        log_level = "[STATUS ERROR]" if is_error else "[STATUS INFO]"
        print(f"{log_level} {message}")

        self.status_var.set(message)
        self.status_label.config(foreground="red" if is_error else "black")

        # Clear any existing timer
        if hasattr(self, "_status_clear_timer"):
            if self._status_clear_timer:
                self.root.after_cancel(self._status_clear_timer)
                self._status_clear_timer = None

        # Set a new timer if duration is positive
        if duration_ms > 0:
            self._status_clear_timer = self.root.after(duration_ms, self._clear_status)

    def _clear_status(self):
        """Clears the status bar message."""
        self.status_var.set("")
        self.status_label.config(foreground="black")
        self._status_clear_timer = None


    # --- News Tab Creation & Methods ---
    # (Keep existing _create_news_tab and its methods)
    def _create_news_tab(self, parent_frame):
        print("[GUI INFO] Creating News Tab...")
        parent_frame.columnconfigure(1, weight=1) # Allow entry column to expand
        parent_frame.rowconfigure(12, weight=1) # Full Content text area row

        row_index = 0

        # ID
        ttk.Label(parent_frame, text="Uniek ID:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=5)
        self.news_entry_id = ttk.Entry(parent_frame, width=50)
        self.news_entry_id.grid(column=1, row=row_index, sticky=(tk.W, tk.E), padx=5, pady=2)
        ttk.Label(parent_frame, text="bv. 'nieuwe-trainer-jan'", style="Desc.TLabel").grid(column=2, row=row_index, sticky=tk.W, padx=5)
        row_index += 1
        ttk.Label(parent_frame, text="Kleine letters, cijfers, koppeltekens (-). Moet uniek zijn.", style="Desc.TLabel").grid(column=1, row=row_index, columnspan=2, sticky=tk.W, padx=5, pady=(0, 5))
        row_index += 1

        # Date
        ttk.Label(parent_frame, text="Datum:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=5)
        self.news_entry_date = ttk.Entry(parent_frame, width=20)
        self.news_entry_date.grid(column=1, row=row_index, sticky=tk.W, padx=5, pady=2)
        self.news_entry_date.insert(0, datetime.date.today().isoformat())
        ttk.Label(parent_frame, text="Formaat: YYYY-MM-DD", style="Desc.TLabel").grid(column=2, row=row_index, sticky=tk.W, padx=5)
        row_index += 1

        # Title
        ttk.Label(parent_frame, text="Titel:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=5)
        self.news_entry_title = ttk.Entry(parent_frame, width=50)
        self.news_entry_title.grid(column=1, row=row_index, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2)
        row_index += 1
        ttk.Label(parent_frame, text="De hoofdtitel van het nieuwsbericht (verplicht).", style="Desc.TLabel").grid(column=1, row=row_index, columnspan=2, sticky=tk.W, padx=5, pady=(0, 5))
        row_index += 1

        # Category
        ttk.Label(parent_frame, text="Categorie:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=5)
        self.news_entry_category = ttk.Entry(parent_frame, width=30)
        self.news_entry_category.grid(column=1, row=row_index, sticky=tk.W, padx=5, pady=2)
        self.news_entry_category.insert(0, NEWS_DEFAULT_CATEGORY)
        ttk.Label(parent_frame, text="bv. 'Mededelingen', 'Wedstrijden'", style="Desc.TLabel").grid(column=2, row=row_index, sticky=tk.W, padx=5)
        row_index += 1

        # Image
        ttk.Label(parent_frame, text="Afbeelding:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=5)
        image_frame = ttk.Frame(parent_frame)
        image_frame.grid(column=1, row=row_index, columnspan=2, sticky=(tk.W, tk.E))
        image_frame.columnconfigure(0, weight=1)
        self.news_entry_image = ttk.Entry(image_frame, width=45)
        self.news_entry_image.grid(column=0, row=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.news_entry_image.insert(0, NEWS_DEFAULT_IMAGE)
        self.news_button_browse_image = ttk.Button(image_frame, text="Browse...", command=self._news_browse_image, width=10)
        self.news_button_browse_image.grid(column=1, row=0, sticky=tk.W)
        row_index += 1
        ttk.Label(parent_frame, text="Klik 'Browse...' om te uploaden naar /images/nieuws/.", style="Desc.TLabel").grid(column=1, row=row_index, columnspan=2, sticky=tk.W, padx=5, pady=(0, 5))
        row_index += 1

        # Summary
        ttk.Label(parent_frame, text="Samenvatting:").grid(column=0, row=row_index, sticky=tk.W, padx=5, pady=5)
        self.news_entry_summary = ttk.Entry(parent_frame, width=50)
        self.news_entry_summary.grid(column=1, row=row_index, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2)
        row_index += 1
        ttk.Label(parent_frame, text="Korte tekst voor nieuwslijst (optioneel, anders titel gebruikt).", style="Desc.TLabel").grid(column=1, row=row_index, columnspan=2, sticky=tk.W, padx=5, pady=(0, 5))
        row_index += 1

        # Full Content
        ttk.Label(parent_frame, text="Volledige Tekst:").grid(column=0, row=row_index, sticky=(tk.W, tk.N), padx=5, pady=5)
        self.news_text_full_content = scrolledtext.ScrolledText(parent_frame, width=60, height=15, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1, font=(self.default_font_family, self.default_font_size))
        self.news_text_full_content.grid(column=1, row=row_index, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=2)
        parent_frame.rowconfigure(row_index, weight=1) # Let text area expand
        row_index += 1
        ttk.Label(parent_frame, text="URLs/emails worden links. Nieuwe regels worden <br>. Basis HTML (<b>, <i>) toegestaan.", style="Desc.TLabel").grid(column=1, row=row_index, columnspan=2, sticky=tk.W, padx=5, pady=(0, 5))
        row_index += 1

        # Buttons Frame
        news_button_frame = ttk.Frame(parent_frame)
        news_button_frame.grid(column=0, row=row_index, columnspan=3, pady=10, sticky=tk.E)
        self.news_button_add = ttk.Button(news_button_frame, text="Voeg Artikel Toe & Sla Op", command=self._news_add_article)
        self.news_button_add.pack(side=tk.LEFT, padx=5)
        self.news_button_clear = ttk.Button(news_button_frame, text="Wis Formulier", command=self._news_clear_form)
        self.news_button_clear.pack(side=tk.LEFT, padx=5)

    def _news_reset_entry_states(self):
        """Resets validation state for news entries."""
        try:
            self.news_entry_id.state(["!invalid"])
            self.news_entry_date.state(["!invalid"])
            self.news_entry_title.state(["!invalid"])
            # Reset other entries if they get validation
        except tk.TclError: pass # Ignore if styles/states not supported

    def _news_browse_image(self):
        print("[NEWS DEBUG] Browse image clicked.")
        filetypes = (("Image files", "*.jpg *.jpeg *.png *.gif *.webp *.bmp"), ("All files", "*.*"))
        # Use APP_BASE_DIR as initialdir if you want it to open near the project
        initial_dir = os.path.dirname(NEWS_IMAGE_DEST_DIR_ABSOLUTE) # Start near the target folder
        source_path = filedialog.askopenfilename(title="Selecteer afbeelding", filetypes=filetypes, initialdir=initial_dir)
        if not source_path:
            self.set_status("Afbeelding selectie geannuleerd.", duration_ms=3000)
            return

        filename = os.path.basename(source_path)
        # Sanitize filename (optional but recommended)
        # filename = re.sub(r'[^\w\-.]', '_', filename) # Replace unsafe chars with underscore

        dest_path = os.path.join(NEWS_IMAGE_DEST_DIR_ABSOLUTE, filename)
        print(f"[NEWS DEBUG] Selected '{source_path}', dest: '{dest_path}'")

        try:
            os.makedirs(NEWS_IMAGE_DEST_DIR_ABSOLUTE, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Directory Fout", f"Kon map niet aanmaken:\n{NEWS_IMAGE_DEST_DIR_ABSOLUTE}\n\nFout: {e}", parent=self.root)
            self.set_status(f"Fout bij aanmaken map {NEWS_IMAGE_DEST_DIR_RELATIVE}", is_error=True)
            return

        if os.path.exists(dest_path):
            if not messagebox.askyesno("Bestand bestaat al",
                                       f"'{filename}' bestaat al in '{NEWS_IMAGE_DEST_DIR_RELATIVE}'.\nOverschrijven?", parent=self.root):
                self.set_status("Upload geannuleerd (overschrijven geweigerd).", duration_ms=4000)
                return

        try:
            shutil.copy2(source_path, dest_path) # copy2 preserves metadata
            print(f"[NEWS INFO] Copied '{source_path}' to '{dest_path}'")
            self.news_entry_image.delete(0, tk.END)
            self.news_entry_image.insert(0, filename)
            self.set_status(f"Afbeelding '{filename}' succesvol geüpload.", duration_ms=5000)
        except Exception as e:
            messagebox.showerror("Upload Fout", f"Kon afbeelding niet kopiëren naar:\n{dest_path}\n\nFout: {e}", parent=self.root)
            self.set_status(f"Fout bij uploaden afbeelding: {e}", is_error=True)

    def _news_clear_form(self):
        print("[NEWS DEBUG] Clear form clicked.")
        self._news_reset_entry_states()
        self.news_entry_id.delete(0, tk.END)
        self.news_entry_date.delete(0, tk.END)
        self.news_entry_date.insert(0, datetime.date.today().isoformat())
        self.news_entry_title.delete(0, tk.END)
        self.news_entry_category.delete(0, tk.END)
        self.news_entry_category.insert(0, NEWS_DEFAULT_CATEGORY)
        self.news_entry_image.delete(0, tk.END)
        self.news_entry_image.insert(0, NEWS_DEFAULT_IMAGE)
        self.news_entry_summary.delete(0, tk.END)
        self.news_text_full_content.delete('1.0', tk.END)
        self.set_status("Nieuws formulier gewist.", duration_ms=3000)
        self.news_entry_id.focus()

    def _news_add_article(self):
        print("[NEWS DEBUG] Add article clicked.")
        self.set_status("Verwerken nieuwsartikel...")
        self.root.update_idletasks()
        self._news_reset_entry_states() # Clear previous validation visuals

        # Get Input
        article_id = self.news_entry_id.get().strip().lower()
        article_date_str = self.news_entry_date.get().strip()
        article_title = self.news_entry_title.get().strip()
        article_category = self.news_entry_category.get().strip() or NEWS_DEFAULT_CATEGORY
        article_image = self.news_entry_image.get().strip() or NEWS_DEFAULT_IMAGE
        article_summary = self.news_entry_summary.get().strip()
        article_full_content_raw = self.news_text_full_content.get('1.0', tk.END).strip()

        # --- Validation ---
        errors = []
        focus_widget = None

        # ID Validation
        if not article_id:
            errors.append("Nieuws ID is verplicht.")
            try: self.news_entry_id.state(["invalid"]); focus_widget = self.news_entry_id
            except: pass
        elif not _news_is_valid_id(article_id):
            errors.append("Ongeldig Nieuws ID format (alleen a-z, 0-9, -).")
            try: self.news_entry_id.state(["invalid"]); focus_widget = self.news_entry_id
            except: pass

        # Date Validation
        if not article_date_str:
            errors.append("Nieuws Datum is verplicht.")
            if not focus_widget: focus_widget = self.news_entry_date
            try: self.news_entry_date.state(["invalid"])
            except: pass
        else:
            try: datetime.datetime.strptime(article_date_str, '%Y-%m-%d')
            except ValueError:
                errors.append("Ongeldig Nieuws Datum formaat (YYYY-MM-DD).")
                if not focus_widget: focus_widget = self.news_entry_date
                try: self.news_entry_date.state(["invalid"])
                except: pass

        # Title Validation
        if not article_title:
            errors.append("Nieuws Titel is verplicht.")
            if not focus_widget: focus_widget = self.news_entry_title
            try: self.news_entry_title.state(["invalid"])
            except: pass

        # Content Validation (optional, e.g., check if empty)
        # if not article_full_content_raw:
        #     errors.append("Volledige tekst mag niet leeg zijn.")
        #     if not focus_widget: focus_widget = self.news_text_full_content

        if errors:
            error_message = "Fout: " + errors[0] # Show the first error
            self.set_status(error_message, is_error=True)
            if focus_widget: focus_widget.focus()
            messagebox.showwarning("Validatie Fout", "\n".join(errors), parent=self.root)
            return

        # Load Existing Data & Check Duplicate ID
        existing_data, load_error = _news_load_existing_data(NEWS_JSON_FILE_PATH)
        if load_error:
            self.set_status(f"Fout bij laden JSON: {load_error}", is_error=True)
            messagebox.showerror("Laadfout", f"Kon {NEWS_JSON_FILE_PATH} niet laden:\n{load_error}", parent=self.root)
            return
        if any(item.get('id') == article_id for item in existing_data):
            error_message = f"Fout: Nieuws Artikel ID '{article_id}' bestaat al."
            self.set_status(error_message, is_error=True)
            try: self.news_entry_id.state(["invalid"])
            except: pass
            self.news_entry_id.focus()
            messagebox.showerror("Validatie Fout", error_message, parent=self.root)
            return

        # Process Content: Auto-link URLs/emails and convert newlines to <br>
        # Apply linking *before* newline conversion to avoid breaking URLs with <br>
        processed_content_linked = _news_auto_link_text(article_full_content_raw)
        processed_content_html = processed_content_linked.replace('\r\n', '<br>\n').replace('\n', '<br>\n') # Add newline for readability
        final_summary = article_summary or article_title # Use title if summary is empty

        # Create New Article Dict
        new_article = {
            "id": article_id,
            "date": article_date_str,
            "title": article_title,
            "category": article_category,
            "image": article_image,
            "summary": final_summary,
            "full_content": processed_content_html
        }
        print(f"[NEWS DEBUG] Prepared new article: {new_article['id']}")

        # Prepend (add to the beginning) and Save
        updated_data = [new_article] + existing_data
        save_error = _news_save_data(NEWS_JSON_FILE_PATH, updated_data)

        if save_error:
            self.set_status(f"Fout bij opslaan JSON: {save_error}", is_error=True)
            messagebox.showerror("Opslagfout", f"Kon nieuws niet opslaan:\n{save_error}", parent=self.root)
        else:
            self.set_status(f"Nieuwsartikel '{article_title}' succesvol toegevoegd.", duration_ms=5000)
            self._news_clear_form() # Clear form on success


    # --- Records Tab Creation & Methods ---
    # (Keep existing _create_records_tab and its methods)
    def _create_records_tab(self, parent_frame):
        print("[GUI INFO] Creating Records Tab...")
        # Check if BeautifulSoup is available before creating content
        if not BeautifulSoup:
            error_label = ttk.Label(parent_frame, text="Error: BeautifulSoup4 library not found.\nCannot load Records Editor.\nPlease install using: pip install beautifulsoup4", style="Error.TLabel", justify=tk.CENTER)
            error_label.pack(pady=50, padx=20, expand=True)
            print("[GUI ERROR] Records tab disabled: BeautifulSoup not found.")
            return # Stop creating this tab

        # --- Frames for Records Tab ---
        top_frame = ttk.Frame(parent_frame)
        top_frame.pack(fill=tk.X, pady=(0, 5))
        middle_frame = ttk.Frame(parent_frame)
        middle_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        bottom_frame = ttk.Frame(parent_frame)
        bottom_frame.pack(fill=tk.X, pady=(5, 0))

        # Keep track of records state within the main app instance
        self.records_structure = {}
        self.records_current_file_path = None
        self.records_current_data = [] # Holds the list of lists [discipline, name, ...]

        # --- Top Frame: Selection ---
        ttk.Label(top_frame, text="Categorie:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky=tk.W)
        self.records_category_var = tk.StringVar()
        self.records_category_combo = ttk.Combobox(top_frame, textvariable=self.records_category_var, state="disabled", width=30)
        self.records_category_combo.grid(row=0, column=1, padx=(0, 10), pady=5, sticky=tk.W)
        self.records_category_combo.bind("<<ComboboxSelected>>", self._records_update_type_dropdown)

        ttk.Label(top_frame, text="Record Type:").grid(row=0, column=2, padx=(10, 5), pady=5, sticky=tk.W)
        self.records_type_var = tk.StringVar()
        self.records_type_combo = ttk.Combobox(top_frame, textvariable=self.records_type_var, state="disabled", width=40)
        self.records_type_combo.grid(row=0, column=3, padx=(0, 10), pady=5, sticky=tk.W)

        self.records_load_button = ttk.Button(top_frame, text="Load Records", command=self._records_load, state=tk.DISABLED)
        self.records_load_button.grid(row=0, column=4, padx=(10, 0), pady=5)

        # --- Middle Frame: Treeview ---
        columns = ('discipline', 'name', 'performance', 'place', 'date')
        self.records_tree = ttk.Treeview(middle_frame, columns=columns, show='headings', selectmode='browse')
        # Set headings and initial column widths
        self.records_tree.heading('discipline', text='Discipline'); self.records_tree.column('discipline', width=150, minwidth=100, anchor=tk.W)
        self.records_tree.heading('name', text='Naam'); self.records_tree.column('name', width=200, minwidth=120, anchor=tk.W)
        self.records_tree.heading('performance', text='Prestatie'); self.records_tree.column('performance', width=100, minwidth=80, anchor=tk.CENTER)
        self.records_tree.heading('place', text='Plaats'); self.records_tree.column('place', width=120, minwidth=100, anchor=tk.W)
        self.records_tree.heading('date', text='Datum'); self.records_tree.column('date', width=100, minwidth=90, anchor=tk.CENTER)

        # Scrollbars
        vsb = ttk.Scrollbar(middle_frame, orient="vertical", command=self.records_tree.yview)
        hsb = ttk.Scrollbar(middle_frame, orient="horizontal", command=self.records_tree.xview)
        self.records_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Grid layout for Treeview and Scrollbars
        self.records_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        middle_frame.grid_rowconfigure(0, weight=1)
        middle_frame.grid_columnconfigure(0, weight=1)

        # Bind double-click event
        self.records_tree.bind("<Double-1>", self._records_on_double_click_edit)

        # --- Bottom Frame: Buttons ---
        button_area = ttk.Frame(bottom_frame)
        # Use pack for simpler layout in the bottom frame
        button_area.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.records_add_button = ttk.Button(button_area, text="Add Record", command=self._records_add_dialog, state=tk.DISABLED)
        self.records_add_button.pack(side=tk.LEFT, padx=(0,5))
        self.records_edit_button = ttk.Button(button_area, text="Edit Selected", command=self._records_edit_dialog, state=tk.DISABLED)
        self.records_edit_button.pack(side=tk.LEFT, padx=5)
        self.records_delete_button = ttk.Button(button_area, text="Delete Selected", command=self._records_delete, state=tk.DISABLED)
        self.records_delete_button.pack(side=tk.LEFT, padx=5)
        # Place Save button on the right
        self.records_save_button = ttk.Button(button_area, text="Save Changes to File", command=self._records_save, state=tk.DISABLED)
        self.records_save_button.pack(side=tk.RIGHT, padx=(5,0))

        # --- Initial Population for Records ---
        self._records_discover_and_populate_categories() # Attempt to find files on startup

    def _records_discover_and_populate_categories(self):
        print("[RECORDS GUI DEBUG] Discovering categories...")
        self.records_structure = _records_discover_files(RECORDS_BASE_DIR_ABSOLUTE)
        categories = sorted(self.records_structure.keys())

        if not categories:
             self.set_status("Error: No record category folders found!", is_error=True)
             messagebox.showerror("Setup Error", f"No category directories found inside:\n{RECORDS_BASE_DIR_ABSOLUTE}\nCheck folder structure.", parent=self.root)
             # Disable controls if no categories found
             self.records_category_combo['values'] = []
             self.records_category_var.set("")
             self.records_type_combo['values'] = []
             self.records_type_var.set("")
             self.records_category_combo.config(state=tk.DISABLED)
             self.records_type_combo.config(state=tk.DISABLED)
             self.records_load_button.config(state=tk.DISABLED)
             self._records_update_button_states(loaded=False) # Ensure action buttons are off
             return

        # Categories found, enable category selection
        self.records_category_combo['values'] = categories
        self.records_category_var.set(categories[0]) # Select the first one
        self.records_category_combo.config(state="readonly")
        self._records_update_type_dropdown() # Populate types for the initially selected category

        # Enable load button only if types are available for the selected category
        if self.records_type_combo['values']:
             self.records_load_button.config(state=tk.NORMAL)
        else:
             self.records_load_button.config(state=tk.DISABLED)

    def _records_update_type_dropdown(self, event=None):
        print("[RECORDS GUI DEBUG] Updating record type dropdown...")
        selected_category = self.records_category_var.get()
        record_types = [] # Default to empty list

        if selected_category and selected_category in self.records_structure:
            record_types = sorted(self.records_structure[selected_category].keys())

        if record_types:
            self.records_type_combo['values'] = record_types
            self.records_type_var.set(record_types[0]) # Select the first type
            self.records_type_combo.config(state="readonly")
            self.records_load_button.config(state=tk.NORMAL) # Enable load if types exist
        else:
            # No types for this category
            self.records_type_combo['values'] = []
            self.records_type_var.set("")
            self.records_type_combo.config(state=tk.DISABLED)
            self.records_load_button.config(state=tk.DISABLED) # Disable load
            print(f"[RECORDS GUI WARNING] No record types found for '{selected_category}'.")

        # Reset state when category changes
        self._records_clear_treeview()
        self._records_update_button_states(loaded=False)
        self.records_current_file_path = None
        self.records_current_data = []
        self.set_status("Select category/type and click Load Records.", duration_ms=4000)

    def _records_update_button_states(self, loaded=False):
        """ Enable/disable Add, Edit, Delete, Save buttons """
        state = tk.NORMAL if loaded else tk.DISABLED
        print(f"[RECORDS GUI DEBUG] Updating action button states: {'NORMAL' if loaded else 'DISABLED'}")
        try:
            self.records_add_button.config(state=state)
            # Edit/Delete should only be enabled if an item is selected (handle in selection event)
            self.records_edit_button.config(state=tk.DISABLED) # Default to disabled
            self.records_delete_button.config(state=tk.DISABLED) # Default to disabled
            self.records_save_button.config(state=state)
            # Add binding to enable edit/delete on selection
            if loaded:
                self.records_tree.bind("<<TreeviewSelect>>", self._records_on_selection_change)
            else:
                # Unbind when not loaded to prevent errors
                self.records_tree.unbind("<<TreeviewSelect>>")

        except tk.TclError as e:
             print(f"[RECORDS GUI WARNING] Could not update button states: {e}")

    def _records_on_selection_change(self, event=None):
        """Called when the selection in the records treeview changes."""
        selected_items = self.records_tree.selection()
        if selected_items:
            # Item selected, enable Edit and Delete
            self.records_edit_button.config(state=tk.NORMAL)
            self.records_delete_button.config(state=tk.NORMAL)
        else:
            # No item selected, disable Edit and Delete
            self.records_edit_button.config(state=tk.DISABLED)
            self.records_delete_button.config(state=tk.DISABLED)

    def _records_clear_treeview(self):
        print("[RECORDS GUI DEBUG] Clearing Treeview.")
        # Prevent selection event from firing unnecessarily during clear
        self.records_tree.unbind("<<TreeviewSelect>>")
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)
        # Re-bind after clearing if data might be loaded later
        # (Handled in _records_update_button_states)

    def _records_populate_treeview(self, data):
        print(f"[RECORDS GUI DEBUG] Populating Treeview with {len(data)} items.")
        self._records_clear_treeview()
        for i, record_row in enumerate(data):
            try:
                # Ensure record_row has exactly 5 elements, pad with "" if necessary
                padded_row = (list(record_row) + [""] * 5)[:5]
                self.records_tree.insert('', tk.END, iid=i, values=padded_row)
            except Exception as e:
                 print(f"[RECORDS GUI ERROR] Failed inserting row {i}: {record_row}\nError: {e}")
        # Re-enable edit/delete buttons (they start disabled after clear)
        self._records_on_selection_change() # Update based on potential default selection
        if data: # If there's data, ensure the selection binding is active
             self.records_tree.bind("<<TreeviewSelect>>", self._records_on_selection_change)


    def _records_load(self):
        category = self.records_category_var.get()
        record_type = self.records_type_var.get()
        print(f"[RECORDS GUI DEBUG] Load clicked. Cat='{category}', Type='{record_type}'")
        if not category or not record_type:
            messagebox.showwarning("Selection Missing", "Please select both a category and a record type.", parent=self.root)
            return

        try:
            self.records_current_file_path = self.records_structure[category][record_type]
            print(f"[RECORDS GUI DEBUG] Loading file: {self.records_current_file_path}")
        except KeyError:
            messagebox.showerror("Error", f"Internal Error: Path not found for {category} - {record_type}.\nPlease check configuration or file structure.", parent=self.root)
            self.records_current_file_path = None
            self._records_clear_treeview()
            self._records_update_button_states(loaded=False)
            self.set_status(f"Error finding path for {category} / {record_type}", is_error=True)
            return

        self.set_status(f"Loading records from {os.path.basename(self.records_current_file_path)}...")
        self.root.update_idletasks()

        # Parse the HTML file
        self.records_current_data = _records_parse_html(self.records_current_file_path)

        # Clear the treeview before potentially populating
        self._records_clear_treeview()

        if self.records_current_data is not None:
            # Successfully parsed data
            self._records_populate_treeview(self.records_current_data)
            self._records_update_button_states(loaded=True) # Enable buttons
            self.set_status(f"Loaded {len(self.records_current_data)} records from {os.path.basename(self.records_current_file_path)}.", duration_ms=5000)
        else:
            # Parsing failed
            self.records_current_data = [] # Ensure it's an empty list on failure
            self.set_status(f"Error loading records from {os.path.basename(self.records_current_file_path)}. Check console.", is_error=True)
            messagebox.showerror("Load Error", f"Failed to parse records from:\n{self.records_current_file_path}\nCheck console log for details (run from command line if needed).", parent=self.root)
            self._records_update_button_states(loaded=False) # Disable buttons
            self.records_current_file_path = None # Reset file path as load failed

    def _records_on_double_click_edit(self, event):
        print("[RECORDS GUI DEBUG] Double-click detected.")
        # Check if a file is loaded and an item is actually selected
        if not self.records_current_file_path: return
        selected_items = self.records_tree.selection()
        if not selected_items: return

        # Check if the edit button is actually enabled (it should be if selected)
        if self.records_edit_button['state'] == tk.NORMAL:
            print("[RECORDS GUI DEBUG] Initiating edit via double-click.")
            self._records_edit_dialog()
        else:
             print("[RECORDS GUI DEBUG] Double-click ignored, edit button disabled.")

    def _records_add_dialog(self):
        # Check if a file is loaded before allowing add
        if not self.records_current_file_path:
             messagebox.showwarning("Load Required", "Please load a record file before adding entries.", parent=self.root)
             return
        print("[RECORDS GUI DEBUG] Add Record dialog.")
        # Pass the callback function to handle the new data
        RecordDialog(self.root, "Add New Record", None, self._records_process_new)

    def _records_edit_dialog(self):
        print("[RECORDS GUI DEBUG] Edit Record action initiated.")
        selected_items = self.records_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Required", "Please select a record from the list to edit.", parent=self.root)
            return
        item_id = selected_items[0] # The iid is the index as a string
        print(f"[RECORDS GUI DEBUG] Editing item iid: {item_id}")
        try:
            record_index = int(item_id) # Convert iid string back to integer index
            # Get the current data for the selected row
            initial_data = self.records_current_data[record_index]
            print(f"[RECORDS GUI DEBUG] Initial data for edit: {initial_data}")
            # Open the dialog, passing initial data and the processing callback
            RecordDialog(self.root, "Edit Record", initial_data,
                         lambda data: self._records_process_edited(record_index, data))
        except (IndexError, ValueError) as e:
             print(f"[RECORDS GUI ERROR] Edit failed. Index '{item_id}' invalid or data missing: {e}")
             messagebox.showerror("Error", "Could not retrieve the selected record data for editing.\nIt might have been deleted or there was an internal error.", parent=self.root)

    def _records_process_new(self, new_data):
        """Callback function for when a new record is added via the dialog."""
        print(f"[RECORDS GUI DEBUG] Processing new record data: {new_data}")
        if new_data and len(new_data) == 5: # Check if data is valid (dialog returns list or None)
            self.records_current_data.append(new_data) # Add to the internal data list
            # Find the index of the newly added item (it's the last one)
            new_item_index = len(self.records_current_data) - 1
            new_item_iid = str(new_item_index) # Treeview iid is the string representation of the index

            # Insert the new row into the treeview *without* full repopulation for efficiency
            try:
                self.records_tree.insert('', tk.END, iid=new_item_iid, values=new_data)
                self.set_status("New record added (unsaved). Click 'Save Changes' to make permanent.", duration_ms=5000)
                # Select and scroll to the newly added item
                self.records_tree.selection_set(new_item_iid)
                self.records_tree.focus(new_item_iid)
                self.records_tree.see(new_item_iid)
            except tk.TclError as e:
                 print(f"[RECORDS GUI WARNING] TclError adding new item {new_item_iid} to treeview: {e}. Repopulating.")
                 # Fallback to full repopulation if direct insert fails
                 self._records_populate_treeview(self.records_current_data)
            except Exception as e:
                 print(f"[RECORDS GUI ERROR] Error adding new item {new_item_iid} to treeview: {e}. Repopulating.")
                 self._records_populate_treeview(self.records_current_data) # Fallback
        elif new_data:
             print(f"[RECORDS GUI WARNING] Received invalid data from Add dialog: {new_data}")
        else:
             print("[RECORDS GUI DEBUG] Add dialog cancelled or returned no data.")

    def _records_process_edited(self, record_index, updated_data):
        """Callback function for when an existing record is edited via the dialog."""
        print(f"[RECORDS GUI DEBUG] Processing edited data for index {record_index}: {updated_data}")
        if updated_data and len(updated_data) == 5: # Check if data is valid
            try:
                # Update the internal data list
                self.records_current_data[record_index] = updated_data
                # Update the specific item in the treeview
                item_iid = str(record_index)
                self.records_tree.item(item_iid, values=updated_data)
                self.set_status("Record updated (unsaved). Click 'Save Changes' to make permanent.", duration_ms=5000)
                # Ensure the edited item remains selected and visible
                self.records_tree.selection_set(item_iid)
                self.records_tree.focus(item_iid)
                self.records_tree.see(item_iid)
            except IndexError:
                 print(f"[RECORDS GUI ERROR] Edit process failed: index {record_index} out of bounds.")
                 messagebox.showerror("Error", "Failed to update record (internal index error). Please reload.", parent=self.root)
                 # Consider reloading or disabling buttons here
            except tk.TclError as e:
                 print(f"[RECORDS GUI WARNING] TclError updating item {item_iid} in treeview: {e}. Repopulating.")
                 # Fallback to full repopulation if direct update fails
                 self._records_populate_treeview(self.records_current_data)
            except Exception as e:
                 print(f"[RECORDS GUI ERROR] Error updating item {item_iid} in treeview: {e}. Repopulating.")
                 self._records_populate_treeview(self.records_current_data) # Fallback
        elif updated_data:
             print(f"[RECORDS GUI WARNING] Received invalid data from Edit dialog: {updated_data}")
        else:
             print("[RECORDS GUI DEBUG] Edit dialog cancelled or returned no data.")


    def _records_delete(self):
        print("[RECORDS GUI DEBUG] Delete action initiated.")
        selected_items = self.records_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Required", "Please select a record from the list to delete.", parent=self.root)
            return

        item_id = selected_items[0] # iid (string index)
        try:
            record_index = int(item_id)
            # Get details for confirmation message (use first 3 columns)
            record_details_list = self.records_current_data[record_index][:3]
            record_details = " | ".join(map(str, record_details_list)) # Join discipline, name, performance
            print(f"[RECORDS GUI DEBUG] Attempting to delete index {record_index}: {record_details}")

            # Confirmation dialog
            if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete this record?\n\n{record_details}", parent=self.root):
                # Delete from internal data list *first*
                del self.records_current_data[record_index]
                print(f"[RECORDS GUI DEBUG] Record deleted from internal data at index {record_index}.")

                # Remove from Treeview directly - this is complex because iids change!
                # The safest way is to repopulate the entire treeview.
                self._records_populate_treeview(self.records_current_data)
                self.set_status("Record deleted (unsaved). Click 'Save Changes' to make permanent.", duration_ms=5000)
            else:
                 print("[RECORDS GUI DEBUG] Deletion cancelled by user.")

        except (IndexError, ValueError) as e:
             print(f"[RECORDS GUI ERROR] Delete failed. Index '{item_id}' invalid or data missing: {e}")
             messagebox.showerror("Error", "Could not find the selected record to delete.\nIt might have already been removed or there was an internal error.", parent=self.root)


    def _records_save(self):
        print("[RECORDS GUI DEBUG] Save clicked.")
        if not self.records_current_file_path:
            messagebox.showerror("Error", "No record file is currently loaded. Cannot save.", parent=self.root)
            self.set_status("Save failed: No file loaded.", is_error=True)
            return

        # The data to save is the current state of self.records_current_data
        data_to_save = self.records_current_data
        filename_short = os.path.basename(self.records_current_file_path)
        print(f"[RECORDS GUI DEBUG] Preparing to save {len(data_to_save)} records to {self.records_current_file_path}")

        # Optional: Confirmation if the list is empty
        if not data_to_save:
            print("[RECORDS GUI WARNING] Saving an empty record list.")
            if not messagebox.askyesno("Confirm Empty Save",
                                       f"You are about to save an empty list to:\n{filename_short}\n\nThis will remove all records currently in that file.\nAre you sure?",
                                       icon='warning', parent=self.root):
                 self.set_status("Save cancelled (empty list confirmation declined).", duration_ms=4000)
                 return

        # Perform the save operation
        self.set_status(f"Saving changes to {filename_short}...")
        self.root.update_idletasks() # Show status update immediately
        success = _records_save_html(self.records_current_file_path, data_to_save)

        if success:
            self.set_status(f"Changes successfully saved to {filename_short}.", duration_ms=5000)
            print(f"[RECORDS INFO] Save successful: {self.records_current_file_path}")
        else:
            # Error message handled by _records_save_html's console output
            self.set_status(f"Error saving changes to {filename_short}. Check console.", is_error=True)
            messagebox.showerror("Save Error", f"Failed to save changes to:\n{self.records_current_file_path}\n\nPlease check the application's console output for detailed errors.", parent=self.root)


    # --- Calendar Tab Creation & Methods ---
    # (Keep existing _create_calendar_tab and its methods)
    def _create_calendar_tab(self, parent_frame):
        print("[GUI INFO] Creating Calendar Tab...")
        if not BeautifulSoup:
            error_label = ttk.Label(parent_frame, text="Error: BeautifulSoup4 library not found.\nCannot load Calendar Editor.\nPlease install using: pip install beautifulsoup4", style="Error.TLabel", justify=tk.CENTER)
            error_label.pack(pady=50, padx=20, expand=True)
            print("[GUI ERROR] Calendar tab disabled: BeautifulSoup not found.")
            return

        # State variable for calendar data
        self.calendar_events_data = [] # List of event dicts {'date', 'name', 'color', 'link'}
        self.calendar_file_loaded = False

        # --- Frames ---
        cal_top_frame = ttk.Frame(parent_frame)
        cal_top_frame.pack(fill=tk.X, pady=(0, 5))
        cal_middle_frame = ttk.Frame(parent_frame)
        cal_middle_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        cal_bottom_frame = ttk.Frame(parent_frame)
        cal_bottom_frame.pack(fill=tk.X, pady=(5, 0))

        # --- Top Frame: Load Button ---
        self.calendar_load_button = ttk.Button(cal_top_frame, text="Load Calendar Events from HTML", command=self._calendar_load)
        self.calendar_load_button.pack(side=tk.LEFT, padx=5, pady=5)
        # Optional Filter (Consider adding later if needed)
        # ttk.Label(cal_top_frame, text="Filter:").pack(side=tk.LEFT, padx=(10, 2), pady=5)
        # self.calendar_filter_var = tk.StringVar()
        # self.calendar_filter_entry = ttk.Entry(cal_top_frame, textvariable=self.calendar_filter_var, width=30)
        # self.calendar_filter_entry.pack(side=tk.LEFT, pady=5)
        # self.calendar_filter_entry.bind("<KeyRelease>", self._calendar_filter_treeview) # Need filter method

        # --- Middle Frame: Treeview ---
        cal_columns = ('date', 'name', 'color', 'link')
        self.calendar_tree = ttk.Treeview(cal_middle_frame, columns=cal_columns, show='headings', selectmode='browse')
        # Configure headings and sorting commands
        self.calendar_tree.heading('date', text='Date (YYYY-MM-DD)', anchor=tk.W, command=lambda: self._calendar_sort_treeview('date'))
        self.calendar_tree.column('date', width=130, minwidth=110, anchor=tk.W, stretch=tk.NO)
        self.calendar_tree.heading('name', text='Event Name', anchor=tk.W, command=lambda: self._calendar_sort_treeview('name'))
        self.calendar_tree.column('name', width=350, minwidth=200, anchor=tk.W)
        self.calendar_tree.heading('color', text='Color', anchor=tk.W, command=lambda: self._calendar_sort_treeview('color'))
        self.calendar_tree.column('color', width=80, minwidth=60, anchor=tk.W, stretch=tk.NO)
        self.calendar_tree.heading('link', text='Link (Optional)', anchor=tk.W, command=lambda: self._calendar_sort_treeview('link'))
        self.calendar_tree.column('link', width=250, minwidth=150, anchor=tk.W) # Increased width slightly

        # Scrollbars
        cal_vsb = ttk.Scrollbar(cal_middle_frame, orient="vertical", command=self.calendar_tree.yview)
        cal_hsb = ttk.Scrollbar(cal_middle_frame, orient="horizontal", command=self.calendar_tree.xview)
        self.calendar_tree.configure(yscrollcommand=cal_vsb.set, xscrollcommand=cal_hsb.set)

        # Grid layout
        self.calendar_tree.grid(row=0, column=0, sticky='nsew')
        cal_vsb.grid(row=0, column=1, sticky='ns')
        cal_hsb.grid(row=1, column=0, sticky='ew')
        cal_middle_frame.grid_rowconfigure(0, weight=1)
        cal_middle_frame.grid_columnconfigure(0, weight=1)

        # Bindings
        self.calendar_tree.bind("<Double-1>", self._calendar_on_double_click_edit)
        # Selection binding handled in _calendar_update_button_states

        # Store sort state
        self._calendar_sort_column = 'date' # Initial sort column
        self._calendar_sort_reverse = False # Initial sort direction

        # --- Bottom Frame: Buttons ---
        cal_button_area = ttk.Frame(cal_bottom_frame)
        cal_button_area.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5) # Use pack
        self.calendar_add_button = ttk.Button(cal_button_area, text="Add Event", command=self._calendar_add_dialog, state=tk.DISABLED)
        self.calendar_add_button.pack(side=tk.LEFT, padx=(0,5))
        self.calendar_edit_button = ttk.Button(cal_button_area, text="Edit Selected", command=self._calendar_edit_dialog, state=tk.DISABLED)
        self.calendar_edit_button.pack(side=tk.LEFT, padx=5)
        self.calendar_delete_button = ttk.Button(cal_button_area, text="Delete Selected", command=self._calendar_delete, state=tk.DISABLED)
        self.calendar_delete_button.pack(side=tk.LEFT, padx=5)
        self.calendar_save_button = ttk.Button(cal_button_area, text="Save Calendar Changes to File", command=self._calendar_save, state=tk.DISABLED)
        self.calendar_save_button.pack(side=tk.RIGHT, padx=(5,0))

    def _calendar_update_button_states(self, loaded=False):
        """ Enable/disable Add, Edit, Delete, Save buttons for Calendar """
        state = tk.NORMAL if loaded else tk.DISABLED
        print(f"[CALENDAR GUI DEBUG] Updating action button states: {'NORMAL' if loaded else 'DISABLED'}")
        try:
            self.calendar_add_button.config(state=state)
            # Edit/Delete depend on selection, disable initially
            self.calendar_edit_button.config(state=tk.DISABLED)
            self.calendar_delete_button.config(state=tk.DISABLED)
            self.calendar_save_button.config(state=state)

            # Add or remove selection binding
            if loaded:
                self.calendar_tree.bind("<<TreeviewSelect>>", self._calendar_on_selection_change)
            else:
                self.calendar_tree.unbind("<<TreeviewSelect>>")

        except tk.TclError as e:
             print(f"[CALENDAR GUI WARNING] Could not update calendar button states: {e}")

    def _calendar_on_selection_change(self, event=None):
        """Called when the selection in the calendar treeview changes."""
        selected_items = self.calendar_tree.selection()
        if selected_items:
            self.calendar_edit_button.config(state=tk.NORMAL)
            self.calendar_delete_button.config(state=tk.NORMAL)
        else:
            self.calendar_edit_button.config(state=tk.DISABLED)
            self.calendar_delete_button.config(state=tk.DISABLED)

    def _calendar_clear_treeview(self):
        print("[CALENDAR GUI DEBUG] Clearing Calendar Treeview.")
        # Unbind selection during clear
        self.calendar_tree.unbind("<<TreeviewSelect>>")
        for item in self.calendar_tree.get_children():
            self.calendar_tree.delete(item)
        # Binding re-added in _calendar_update_button_states if loaded

    def _calendar_populate_treeview(self):
        """Populates the calendar treeview, sorting the data first."""
        print(f"[CALENDAR GUI DEBUG] Populating Calendar Treeview with {len(self.calendar_events_data)} events.")
        self._calendar_clear_treeview()

        # Define sort key function (handles None safely)
        key_map = {'date': 'date', 'name': 'name', 'color': 'color', 'link': 'link'}
        sort_key_name = key_map.get(self._calendar_sort_column, 'date')

        def sort_func(event_dict):
            val = event_dict.get(sort_key_name) # Use .get() for safety (link might be missing/None)
            if isinstance(val, str):
                # Special handling for date strings if needed, otherwise lowercase string compare
                if sort_key_name == 'date': return val # Already YYYY-MM-DD format
                return val.lower()
            elif val is None:
                return "" # Treat None as empty string for sorting consistency
            else:
                return str(val).lower() # Convert other types (numbers?) to lowercase string

        # Sort the internal data list based on current settings
        display_data_dicts = sorted(
            self.calendar_events_data,
            key=sort_func,
            reverse=self._calendar_sort_reverse
        )

        # Populate treeview using the original index as iid
        # Create a mapping from original event dict to its original index first
        original_indices = {id(event): index for index, event in enumerate(self.calendar_events_data)}

        for event_dict in display_data_dicts: # Iterate through the *sorted* list
            try:
                # Find the original index using the object's id
                original_index = original_indices[id(event_dict)]
                item_iid = str(original_index) # Use original index as iid

                # Prepare values, ensuring link is displayed as empty string if None
                values = [
                    event_dict['date'],
                    event_dict['name'],
                    event_dict['color'],
                    event_dict.get('link') or "" # Display empty string if link is None
                ]
                self.calendar_tree.insert('', tk.END, iid=item_iid, values=values, tags=('event_row',))

            except KeyError:
                 print(f"[CALENDAR GUI WARNING] Could not find original index for event: {event_dict}")
            except Exception as e:
                 print(f"[CALENDAR GUI ERROR] Failed inserting row for event: {event_dict}\nError: {e}")

        # Update sort indicator in header
        self._calendar_update_sort_indicator()
        # Re-enable selection dependent buttons (starts disabled after clear)
        self._calendar_on_selection_change()
        if self.calendar_events_data: # Re-bind selection if there's data
            self.calendar_tree.bind("<<TreeviewSelect>>", self._calendar_on_selection_change)

    def _calendar_sort_treeview(self, col):
        """Sorts the treeview based on a column header click."""
        if col == self._calendar_sort_column:
            # Toggle direction if same column clicked again
            self._calendar_sort_reverse = not self._calendar_sort_reverse
        else:
            # New column selected, sort ascending by default
            self._calendar_sort_column = col
            self._calendar_sort_reverse = False

        print(f"[CALENDAR GUI DEBUG] Sorting by '{self._calendar_sort_column}', reverse={self._calendar_sort_reverse}")
        self._calendar_populate_treeview() # Repopulate with new sort order


    def _calendar_update_sort_indicator(self):
         """Updates the arrow indicator on the treeview column header."""
         arrow = ' ↓' if self._calendar_sort_reverse else ' ↑'
         for c in ('date', 'name', 'color', 'link'):
             # Get the base heading text (handle special cases)
             base_text = ""
             if c == 'date': base_text = "Date (YYYY-MM-DD)"
             elif c == 'name': base_text = "Event Name"
             elif c == 'color': base_text = "Color"
             elif c == 'link': base_text = "Link (Optional)"

             # Remove old arrow if present before adding new one
             # current_text = self.calendar_tree.heading(c)['text'].replace(' ↓', '').replace(' ↑', '') # Problematic if base_text contains arrows

             if c == self._calendar_sort_column:
                 self.calendar_tree.heading(c, text=base_text + arrow)
             else:
                 self.calendar_tree.heading(c, text=base_text)

    def _calendar_load(self):
        print("[CALENDAR GUI DEBUG] Load calendar clicked.")
        if not os.path.exists(CALENDAR_HTML_FILE_PATH):
             messagebox.showerror("File Not Found", f"Calendar file not found:\n{CALENDAR_HTML_FILE_PATH}", parent=self.root)
             self.set_status("Error: Calendar HTML file not found.", is_error=True)
             self._calendar_update_button_states(loaded=False)
             self.calendar_file_loaded = False
             return

        self.set_status("Loading calendar events from HTML...")
        self.root.update_idletasks()

        loaded_events = _calendar_parse_html(CALENDAR_HTML_FILE_PATH)

        # Clear existing data regardless of success
        self._calendar_clear_treeview()
        self.calendar_events_data = []

        if loaded_events is not None:
            self.calendar_events_data = loaded_events # Store the loaded data
            self.calendar_file_loaded = True
            self._calendar_sort_column = 'date' # Reset sort on load
            self._calendar_sort_reverse = False
            self._calendar_populate_treeview() # Populate treeview with loaded data
            self._calendar_update_button_states(loaded=True) # Enable buttons
            self.set_status(f"Loaded {len(self.calendar_events_data)} calendar events.", duration_ms=5000)
        else:
            # Parsing failed
            self.calendar_file_loaded = False
            self._calendar_update_button_states(loaded=False) # Ensure buttons are disabled
            self.set_status("Error loading calendar events. Check console.", is_error=True)
            messagebox.showerror("Load Error", f"Failed to parse events from:\n{CALENDAR_HTML_FILE_PATH}\nCheck console log for details.", parent=self.root)


    def _calendar_on_double_click_edit(self, event):
        print("[CALENDAR GUI DEBUG] Double-click detected.")
        if not self.calendar_file_loaded: return
        selected_items = self.calendar_tree.selection()
        if not selected_items: return

        if self.calendar_edit_button['state'] == tk.NORMAL:
             print("[CALENDAR GUI DEBUG] Initiating edit via double-click.")
             self._calendar_edit_dialog()
        else:
             print("[CALENDAR GUI DEBUG] Double-click ignored, edit button disabled.")


    def _calendar_add_dialog(self):
        if not self.calendar_file_loaded:
             messagebox.showwarning("Load Required", "Please load the calendar data before adding events.", parent=self.root)
             return
        print("[CALENDAR GUI DEBUG] Add Event dialog initiated.")
        CalendarEventDialog(self.root, "Add Calendar Event", None, self._calendar_process_new)

    def _calendar_edit_dialog(self):
        print("[CALENDAR GUI DEBUG] Edit Event action initiated.")
        selected_items = self.calendar_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Required", "Please select an event from the list to edit.", parent=self.root)
            return
        item_iid = selected_items[0] # This should be the original index as string
        try:
            record_index = int(item_iid) # Convert iid string back to original list index
            initial_data = self.calendar_events_data[record_index] # Get data from original list
            print(f"[CALENDAR GUI DEBUG] Initial data for edit (original index {record_index}): {initial_data}")
            # Pass initial data and the edit processing callback
            CalendarEventDialog(self.root, "Edit Calendar Event", initial_data,
                         lambda data: self._calendar_process_edited(record_index, data))
        except (IndexError, ValueError) as e:
             print(f"[CALENDAR GUI ERROR] Edit failed. Cannot find original index '{item_iid}': {e}")
             messagebox.showerror("Error", "Could not find the selected event data for editing.\nIt might have been deleted or there was an internal error.", parent=self.root)


    def _calendar_process_new(self, new_event_dict):
        """Callback for adding a new calendar event."""
        print(f"[CALENDAR GUI DEBUG] Processing new event data: {new_event_dict}")
        if new_event_dict: # Check if dialog returned valid data (dict)
            # Add to the main data list
            self.calendar_events_data.append(new_event_dict)
            # The new original index is simply the last index
            new_original_index = len(self.calendar_events_data) - 1
            new_item_iid = str(new_original_index)

            # Re-populate the treeview (which includes sorting)
            self._calendar_populate_treeview()
            self.set_status("New event added (unsaved). Click 'Save Changes' to make permanent.", duration_ms=5000)

            # Try to select and focus the newly added item using its original index iid
            try:
                self.calendar_tree.selection_set(new_item_iid)
                self.calendar_tree.focus(new_item_iid)
                self.calendar_tree.see(new_item_iid)
            except tk.TclError:
                print(f"[CALENDAR GUI WARNING] Could not select/focus newly added item {new_item_iid} in treeview after repopulation.")
        else:
             print("[CALENDAR GUI DEBUG] Add event dialog cancelled or returned no data.")

    def _calendar_process_edited(self, record_index, updated_event_dict):
        """Callback for editing an existing calendar event."""
        print(f"[CALENDAR GUI DEBUG] Processing edited event for original index {record_index}: {updated_event_dict}")
        if updated_event_dict: # Check if dialog returned valid data (dict)
            try:
                # Update the data in the original list using the index
                self.calendar_events_data[record_index] = updated_event_dict
                # Re-populate the treeview to reflect the change and maintain sort order
                self._calendar_populate_treeview()
                self.set_status("Event updated (unsaved). Click 'Save Changes' to make permanent.", duration_ms=5000)

                # Try to re-select the item using its original index iid
                item_iid = str(record_index)
                try:
                    # Check if the item still exists in the tree after repopulation
                    if self.calendar_tree.exists(item_iid):
                        self.calendar_tree.selection_set(item_iid)
                        self.calendar_tree.focus(item_iid)
                        self.calendar_tree.see(item_iid)
                    else:
                        print(f"[CALENDAR GUI WARNING] Item {item_iid} no longer exists in tree after edit/repopulation.")
                except tk.TclError:
                    print(f"[CALENDAR GUI WARNING] Could not re-select edited item {item_iid} in treeview after repopulation.")
            except IndexError:
                 print(f"[CALENDAR GUI ERROR] Edit process failed: original index {record_index} out of bounds.")
                 messagebox.showerror("Error", "Failed to update event (internal index error). Please reload.", parent=self.root)
        else:
             print("[CALENDAR GUI DEBUG] Edit event dialog cancelled or returned no data.")


    def _calendar_delete(self):
        print("[CALENDAR GUI DEBUG] Delete event action initiated.")
        selected_items = self.calendar_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Required", "Please select an event from the list to delete.", parent=self.root)
            return

        item_iid = selected_items[0] # The iid is the original index as a string
        try:
            record_index = int(item_iid) # Convert back to original list index
            # Get details for confirmation message
            event_details = f"{self.calendar_events_data[record_index]['date']} | {self.calendar_events_data[record_index]['name']}"
            print(f"[CALENDAR GUI DEBUG] Attempting to delete event at original index {record_index}: {event_details}")

            if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete this event?\n\n{event_details}", parent=self.root):
                # Delete the item from the *original* data list using the index
                del self.calendar_events_data[record_index]
                print(f"[CALENDAR INFO] Deleted event from internal data at original index {record_index}.")

                # Repopulate the treeview to reflect the deletion and update iids
                self._calendar_populate_treeview()
                self.set_status("Event deleted (unsaved). Click 'Save Changes' to make permanent.", duration_ms=5000)
            else:
                 print("[CALENDAR GUI DEBUG] Deletion cancelled by user.")
        except (IndexError, ValueError) as e:
             print(f"[CALENDAR GUI ERROR] Delete failed. Cannot find original index '{item_iid}': {e}")
             messagebox.showerror("Error", "Could not find the selected event to delete.\nIt might have already been removed or there was an internal error.", parent=self.root)


    def _calendar_save(self):
        print("[CALENDAR GUI DEBUG] Save calendar clicked.")
        if not self.calendar_file_loaded:
             messagebox.showwarning("Load First", "Please load the calendar data from the HTML file before attempting to save.", parent=self.root)
             self.set_status("Save failed: Calendar data not loaded.", is_error=True)
             return

        # Ensure data is sorted by date before saving (critical for correct HTML generation)
        self.calendar_events_data.sort(key=lambda x: x['date'])
        data_to_save = self.calendar_events_data
        filename_short = os.path.basename(CALENDAR_HTML_FILE_PATH)
        print(f"[CALENDAR GUI DEBUG] Saving {len(data_to_save)} events to {CALENDAR_HTML_FILE_PATH}")

        # No empty check needed - saving an empty calendar (no events) is valid

        self.set_status(f"Saving calendar changes to {filename_short}...")
        self.root.update_idletasks()
        success = _calendar_save_html(CALENDAR_HTML_FILE_PATH, data_to_save)

        if success:
            self.set_status(f"Calendar changes successfully saved to {filename_short}.", duration_ms=5000)
            print(f"[CALENDAR INFO] Save successful: {CALENDAR_HTML_FILE_PATH}")
        else:
            # Error details should be in console via _calendar_save_html
            self.set_status(f"Error saving calendar changes to {filename_short}. Check console.", is_error=True)
            messagebox.showerror("Save Error", f"Failed to save changes to:\n{CALENDAR_HTML_FILE_PATH}\n\nPlease check the application's console output for detailed errors.", parent=self.root)


    # --- Reports Tab Creation & Methods ---
    # (Keep existing _create_reports_tab and its methods)
    def _create_reports_tab(self, parent_frame):
        print("[GUI INFO] Creating Reports Tab...")
        if not BeautifulSoup:
            error_label = ttk.Label(parent_frame, text="Error: BeautifulSoup4 library not found.\nCannot load Reports Editor.\nPlease install using: pip install beautifulsoup4", style="Error.TLabel", justify=tk.CENTER)
            error_label.pack(pady=50, padx=20, expand=True)
            print("[GUI ERROR] Reports tab disabled: BeautifulSoup not found.")
            return

        # State variables for reports
        self.reports_data = {} # Dict: { "YYYY": [ {text, filename, path}, ... ], ... }
        self.reports_file_loaded = False
        self._reports_sort_column = 'year' # Default sort
        self._reports_sort_reverse = True  # Default sort: newest year first

        # --- Frames ---
        rep_controls_frame = ttk.Frame(parent_frame)
        rep_controls_frame.pack(fill=tk.X, pady=(0, 10))

        rep_tree_frame = ttk.Frame(parent_frame)
        rep_tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        rep_actions_frame = ttk.Frame(parent_frame)
        rep_actions_frame.pack(fill=tk.X, pady=(10, 0))

        # --- Controls Frame (Top: Load, Add/Upload Section) ---
        # Load Button
        self.reports_load_button = ttk.Button(rep_controls_frame, text="Load Reports from HTML", command=self._reports_load)
        self.reports_load_button.grid(row=0, column=0, rowspan=4, padx=5, pady=5, sticky=tk.W+tk.N) # Span rows and stick top-west

        # Separator
        ttk.Separator(rep_controls_frame, orient=tk.VERTICAL).grid(row=0, column=1, rowspan=4, sticky="ns", padx=15, pady=5)

        # Add/Upload Area
        ttk.Label(rep_controls_frame, text="Add New Report Link:", style="Bold.TLabel").grid(row=0, column=2, columnspan=3, sticky=tk.W, padx=5, pady=(5,2))

        # Year Selection
        ttk.Label(rep_controls_frame, text="Year:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.reports_year_var = tk.StringVar()
        self.reports_year_combo = ttk.Combobox(rep_controls_frame, textvariable=self.reports_year_var, width=12, state=tk.DISABLED) # Slightly wider
        self.reports_year_combo.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
        self.reports_year_combo.bind("<<ComboboxSelected>>", self._reports_toggle_new_year_entry)
        # New Year Entry (initially hidden/disabled)
        self.reports_new_year_entry = ttk.Entry(rep_controls_frame, width=8, state=tk.DISABLED)
        self.reports_new_year_entry.grid(row=1, column=4, sticky=tk.W, padx=5, pady=2)
        self.reports_new_year_entry.insert(0, "YYYY") # Placeholder text
        self.reports_new_year_entry.bind("<FocusIn>", lambda e: self.reports_new_year_entry.delete(0, tk.END) if self.reports_new_year_entry.get() == "YYYY" else None)
        self.reports_new_year_entry.bind("<FocusOut>", lambda e: self.reports_new_year_entry.insert(0, "YYYY") if not self.reports_new_year_entry.get() else None)


        # Link Text
        ttk.Label(rep_controls_frame, text="Link Text:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        self.reports_link_text_entry = ttk.Entry(rep_controls_frame, width=45, state=tk.DISABLED) # Increased width
        self.reports_link_text_entry.grid(row=2, column=3, columnspan=3, sticky=tk.W+tk.E, padx=5, pady=2)


        # Upload Button
        self.reports_upload_button = ttk.Button(rep_controls_frame, text="Browse Document & Add Link", command=self._reports_browse_and_upload, state=tk.DISABLED)
        self.reports_upload_button.grid(row=3, column=3, columnspan=3, sticky=tk.W, padx=5, pady=(5,5))

        # Make the column with the link text entry expand
        rep_controls_frame.columnconfigure(3, weight=1)

        # --- Tree Frame (Middle: Treeview) ---
        rep_columns = ('year', 'text', 'filename')
        self.reports_tree = ttk.Treeview(rep_tree_frame, columns=rep_columns, show='headings', selectmode='browse')

        # Configure Headings and Sorting
        self.reports_tree.heading('year', text='Year', anchor=tk.W, command=lambda: self._reports_sort_treeview('year'))
        self.reports_tree.column('year', width=80, anchor=tk.W, stretch=tk.NO)
        self.reports_tree.heading('text', text='Link Text', anchor=tk.W, command=lambda: self._reports_sort_treeview('text'))
        self.reports_tree.column('text', width=400, minwidth=250, anchor=tk.W)
        self.reports_tree.heading('filename', text='Filename (in docs folder)', anchor=tk.W, command=lambda: self._reports_sort_treeview('filename'))
        self.reports_tree.column('filename', width=350, minwidth=200, anchor=tk.W)

        # Scrollbars
        rep_vsb = ttk.Scrollbar(rep_tree_frame, orient="vertical", command=self.reports_tree.yview)
        rep_hsb = ttk.Scrollbar(rep_tree_frame, orient="horizontal", command=self.reports_tree.xview)
        self.reports_tree.configure(yscrollcommand=rep_vsb.set, xscrollcommand=rep_hsb.set)

        # Grid Layout
        self.reports_tree.grid(row=0, column=0, sticky='nsew')
        rep_vsb.grid(row=0, column=1, sticky='ns')
        rep_hsb.grid(row=1, column=0, sticky='ew')
        rep_tree_frame.grid_rowconfigure(0, weight=1)
        rep_tree_frame.grid_columnconfigure(0, weight=1)

        # Selection binding handled in _reports_update_ui_states

        # --- Actions Frame (Bottom: Delete, Save) ---
        rep_button_area = ttk.Frame(rep_actions_frame)
        rep_button_area.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5) # Use pack here

        self.reports_delete_button = ttk.Button(rep_button_area, text="Delete Selected Link", command=self._reports_delete, state=tk.DISABLED)
        self.reports_delete_button.pack(side=tk.LEFT, padx=(0,5))

        self.reports_save_button = ttk.Button(rep_button_area, text="Save Changes to HTML File", command=self._reports_save, state=tk.DISABLED)
        self.reports_save_button.pack(side=tk.RIGHT, padx=(5,0))

    def _reports_update_ui_states(self, loaded=False):
        """Updates the state of buttons and entry fields based on load status."""
        add_form_state = tk.NORMAL if loaded else tk.DISABLED
        combo_state = "readonly" if loaded else tk.DISABLED
        print(f"[REPORTS GUI DEBUG] Updating UI states: {'LOADED' if loaded else 'NOT LOADED'}")
        try:
            # Buttons dependent on load status
            self.reports_save_button.config(state=add_form_state)
            self.reports_upload_button.config(state=add_form_state) # Enable upload only when loaded

            # Delete button depends on selection, disable initially
            self.reports_delete_button.config(state=tk.DISABLED)

            # Upload Form Fields
            self.reports_year_combo.config(state=combo_state)
            self.reports_link_text_entry.config(state=add_form_state)

            # Keep New Year entry disabled unless "<Nieuw Jaar>" is selected *and* loaded
            is_new_year_selected = self.reports_year_var.get() == "<Nieuw Jaar>"
            self.reports_new_year_entry.config(state=tk.NORMAL if loaded and is_new_year_selected else tk.DISABLED)

            # Populate or clear Year Dropdown
            if loaded:
                self._reports_update_year_dropdown()
                # Bind selection event only when loaded
                self.reports_tree.bind("<<TreeviewSelect>>", self._reports_on_selection_change)
            else:
                # Clear and disable when not loaded
                self.reports_year_combo['values'] = []
                self.reports_year_var.set("")
                self.reports_link_text_entry.delete(0, tk.END)
                self.reports_new_year_entry.delete(0, tk.END)
                if not self.reports_new_year_entry.get(): self.reports_new_year_entry.insert(0, "YYYY") # Reset placeholder
                # Unbind selection event
                self.reports_tree.unbind("<<TreeviewSelect>>")

        except tk.TclError as e:
             print(f"[REPORTS GUI WARNING] Could not update reports UI states: {e}")
        except Exception as e:
             print(f"[REPORTS GUI ERROR] Unexpected error updating UI states: {e}")


    def _reports_on_selection_change(self, event=None):
        """Called when the selection in the reports treeview changes."""
        selected_items = self.reports_tree.selection()
        if selected_items:
            self.reports_delete_button.config(state=tk.NORMAL)
        else:
            self.reports_delete_button.config(state=tk.DISABLED)

    def _reports_update_year_dropdown(self):
        """Populates the year dropdown from loaded data keys."""
        if not self.reports_file_loaded:
            self.reports_year_combo['values'] = []
            self.reports_year_var.set("")
            return

        # Get existing years from data, sort numerically descending
        years = sorted([y for y in self.reports_data.keys() if y.isdigit()], key=int, reverse=True)

        current_system_year = str(datetime.date.today().year)
        new_year_option = "<Nieuw Jaar>"
        options = [new_year_option]

        # Add current system year if not already in the list of years from data
        if current_system_year not in years:
            options.append(current_system_year)

        # Add the rest of the years from the data
        options.extend(years)

        # Remove duplicates just in case (e.g., if current year was already in data)
        unique_options = []
        for opt in options:
            if opt not in unique_options:
                unique_options.append(opt)

        self.reports_year_combo['values'] = unique_options

        # Set default selection logic:
        current_selection = self.reports_year_var.get()
        if current_selection in unique_options:
             # Keep current selection if it's still valid
             pass
        elif current_system_year in unique_options:
             # Default to current system year if available
             self.reports_year_var.set(current_system_year)
        elif years:
             # Fallback to the newest year from the data
             self.reports_year_var.set(years[0])
        else:
             # Fallback to "New Year" if no other options
             self.reports_year_var.set(new_year_option)

        self._reports_toggle_new_year_entry() # Update state based on (potentially new) selection

    def _reports_toggle_new_year_entry(self, event=None):
        """Enables/disables the New Year entry based on combobox selection."""
        is_new_year_selected = self.reports_year_var.get() == "<Nieuw Jaar>"
        new_state = tk.NORMAL if self.reports_file_loaded and is_new_year_selected else tk.DISABLED

        self.reports_new_year_entry.config(state=new_state)
        if new_state == tk.NORMAL:
             # Clear placeholder on enable if needed
             if self.reports_new_year_entry.get() == "YYYY":
                 self.reports_new_year_entry.delete(0, tk.END)
             # self.reports_new_year_entry.focus() # Optional: auto-focus
        else:
             # Reset placeholder if disabled and empty
             if not self.reports_new_year_entry.get():
                 self.reports_new_year_entry.insert(0, "YYYY")


    def _reports_clear_treeview(self):
        print("[REPORTS GUI DEBUG] Clearing Reports Treeview.")
        self.reports_tree.unbind("<<TreeviewSelect>>") # Unbind during clear
        for item in self.reports_tree.get_children():
            self.reports_tree.delete(item)
        # Rebind handled by _reports_update_ui_states

    def _reports_populate_treeview(self):
        """Populates the reports treeview from self.reports_data, applying sort."""
        print(f"[REPORTS GUI DEBUG] Populating Reports Treeview with {sum(len(v) for v in self.reports_data.values())} items.")
        self._reports_clear_treeview()

        # Combine data into a flat list for easier sorting and iid generation
        flat_reports = []
        for year, reports_list in self.reports_data.items():
            for index, report_dict in enumerate(reports_list):
                # Store original year and index for creating a stable iid
                flat_reports.append({
                    'year': year,
                    'text': report_dict['text'],
                    'filename': report_dict['filename'],
                    'path': report_dict['path'], # Keep path for potential future use
                    'original_index': index # Index within its year's list in the original dict
                })

        # Define sort key function based on current sort settings
        def sort_key_func(item):
            col_value = item.get(self._reports_sort_column, "")
            if self._reports_sort_column == 'year':
                # Sort years numerically if possible, fallback for non-numeric
                try: return int(col_value)
                except (ValueError, TypeError): return 0
            elif isinstance(col_value, str):
                return col_value.lower() # Case-insensitive sort for text/filename
            return col_value # Fallback

        # Sort the flat list
        sorted_flat_reports = sorted(
            flat_reports,
            key=sort_key_func,
            reverse=self._reports_sort_reverse
        )

        # Populate the treeview using the sorted list
        for item_data in sorted_flat_reports:
            # Create a unique and recoverable iid: "year-original_index"
            # This links the treeview item back to its entry in self.reports_data[year]
            item_id = f"{item_data['year']}-{item_data['original_index']}"
            values = (item_data['year'], item_data['text'], item_data['filename'])
            try:
                self.reports_tree.insert('', tk.END, iid=item_id, values=values, tags=('report_row',))
            except Exception as e:
                print(f"[REPORTS GUI ERROR] Failed inserting report row {item_id}: {values}\nError: {e}")

        # Update sort indicator in header
        self._reports_update_sort_indicator()
        # Re-enable selection dependent buttons (starts disabled after clear)
        self._reports_on_selection_change()
        if self.reports_data: # Re-bind selection if there's data
            self.reports_tree.bind("<<TreeviewSelect>>", self._reports_on_selection_change)


    def _reports_sort_treeview(self, col):
        """Sorts the reports treeview based on column header click."""
        if col == self._reports_sort_column:
            # Toggle direction
            self._reports_sort_reverse = not self._reports_sort_reverse
        else:
            # New column, sort ascending by default (except year maybe?)
            self._reports_sort_column = col
            # Default sort direction: Descending for year, Ascending for others
            self._reports_sort_reverse = (col == 'year')

        print(f"[REPORTS GUI DEBUG] Sorting Reports by '{self._reports_sort_column}', reverse={self._reports_sort_reverse}")
        self._reports_populate_treeview() # Repopulate with new sort order


    def _reports_update_sort_indicator(self):
         """Updates the arrow indicator on the reports treeview column header."""
         arrow = ' ↓' if self._reports_sort_reverse else ' ↑'
         for c in ('year', 'text', 'filename'):
             # Get base text (adjust display names if needed)
             base_text = ""
             if c == 'year': base_text = "Year"
             elif c == 'text': base_text = "Link Text"
             elif c == 'filename': base_text = "Filename (in docs folder)"

             if c == self._reports_sort_column:
                 self.reports_tree.heading(c, text=base_text + arrow)
             else:
                 self.reports_tree.heading(c, text=base_text)


    def _reports_load(self):
        print("[REPORTS GUI DEBUG] Load reports clicked.")
        if not os.path.exists(REPORTS_HTML_FILE_PATH):
             messagebox.showerror("File Not Found", f"Reports HTML file not found:\n{REPORTS_HTML_FILE_PATH}", parent=self.root)
             self.set_status("Error: Reports HTML file not found.", is_error=True)
             self._reports_update_ui_states(loaded=False)
             self.reports_file_loaded = False
             return

        self.set_status("Loading reports from HTML...")
        self.root.update_idletasks()

        # Clear existing data before loading
        self._reports_clear_treeview()
        self.reports_data = {}
        self.reports_file_loaded = False

        # Parse the HTML
        loaded_data, error_msg = _reports_parse_html(REPORTS_HTML_FILE_PATH)

        if error_msg is None:
            # Success
            self.reports_data = loaded_data
            self.reports_file_loaded = True
            self._reports_sort_column = 'year' # Reset sort on load
            self._reports_sort_reverse = True
            self._reports_populate_treeview() # Populate with loaded data
            self._reports_update_ui_states(loaded=True) # Enable controls
            report_count = sum(len(v) for v in self.reports_data.values())
            self.set_status(f"Loaded {report_count} report links successfully.", duration_ms=5000)
        else:
            # Failure
            self._reports_update_ui_states(loaded=False) # Keep controls disabled
            self.set_status(f"Error loading reports: {error_msg}", is_error=True)
            messagebox.showerror("Load Error", f"Failed to parse reports from HTML:\n{error_msg}\nCheck console log and HTML file structure ('<div id=\"reports-section\">', H2 for years, UL.report-list > LI > A).", parent=self.root)


    def _reports_browse_and_upload(self):
        print("[REPORTS GUI DEBUG] Browse and Add Report Link clicked.")
        if not self.reports_file_loaded:
            self.set_status("Error: Load reports HTML first before adding links.", is_error=True)
            messagebox.showwarning("Load Required", "Please load the reports from the HTML file before adding new links.", parent=self.root)
            return

        # --- 1. Get and Validate Target Year ---
        selected_year_str = self.reports_year_var.get()
        target_year = None

        if selected_year_str == "<Nieuw Jaar>":
            new_year_input = self.reports_new_year_entry.get().strip()
            if not new_year_input.isdigit() or not (1900 <= int(new_year_input) <= 2100): # Basic sanity check
                messagebox.showerror("Invalid Input", "Please enter a valid 4-digit year (e.g., 2024) in the 'New Year' box.", parent=self.root)
                self.reports_new_year_entry.focus()
                return
            target_year = new_year_input
        elif selected_year_str and selected_year_str.isdigit():
            target_year = selected_year_str
        else:
            messagebox.showerror("Invalid Input", "Please select a target year from the dropdown, or select '<Nieuw Jaar>' and enter a valid year.", parent=self.root)
            self.reports_year_combo.focus()
            return

        # --- 2. Get and Validate Link Text ---
        link_text = self.reports_link_text_entry.get().strip()
        if not link_text:
             messagebox.showerror("Invalid Input", "Please enter the text to display for the report link (e.g., 'Bestuursverslag Januari').", parent=self.root)
             self.reports_link_text_entry.focus()
             return

        # --- 3. Select Source Document File ---
        filetypes = (("Document Files", "*.pdf *.doc *.docx *.odt *.xls *.xlsx *.ppt *.pptx"),
                     ("All files", "*.*"))
        # Suggest opening near the destination directory
        initial_dir = REPORTS_DOCS_DEST_DIR_ABSOLUTE if os.path.isdir(REPORTS_DOCS_DEST_DIR_ABSOLUTE) else APP_BASE_DIR
        source_path = filedialog.askopenfilename(
            title="Select Report Document to Upload",
            filetypes=filetypes,
            initialdir=initial_dir
        )
        if not source_path:
            self.set_status("Document selection cancelled.", duration_ms=3000)
            return # User cancelled dialog

        # --- 4. Prepare Destination Path and Href ---
        filename = os.path.basename(source_path)
        # Optional: Sanitize filename to remove potentially problematic characters
        # filename = re.sub(r'[^\w\-\.]', '_', filename).lower() # Example: replace unsafe chars, make lowercase

        # Ensure the destination directory exists
        try:
            os.makedirs(REPORTS_DOCS_DEST_DIR_ABSOLUTE, exist_ok=True)
            print(f"[REPORTS DEBUG] Ensured destination directory exists: {REPORTS_DOCS_DEST_DIR_ABSOLUTE}")
        except OSError as e:
            messagebox.showerror("Directory Error", f"Could not create destination directory for reports:\n{REPORTS_DOCS_DEST_DIR_ABSOLUTE}\n\nError: {e}\n\nPlease check permissions.", parent=self.root)
            self.set_status(f"Error creating destination directory: {e}", is_error=True)
            return

        dest_path_absolute = os.path.join(REPORTS_DOCS_DEST_DIR_ABSOLUTE, filename)

        # Create the relative path for the HTML href using forward slashes (POSIX style)
        # Use pathlib.PurePosixPath for correct joining regardless of OS
        href_path_relative = str(pathlib.PurePosixPath(REPORTS_DOCS_HREF_DIR_RELATIVE) / filename)

        print(f"[REPORTS DEBUG] Source Doc: '{source_path}'")
        print(f"[REPORTS DEBUG] Dest Path (Absolute): '{dest_path_absolute}'")
        print(f"[REPORTS DEBUG] Dest Path (Href Relative): '{href_path_relative}'")


        # --- 5. Check Overwrite for the *document file* ---
        if os.path.exists(dest_path_absolute):
            if not messagebox.askyesno("Confirm Overwrite",
                                       f"The document file '{filename}' already exists in the destination folder:\n'{REPORTS_DOCS_DEST_DIR_ABSOLUTE}'\n\nDo you want to replace the existing file?",
                                       icon='warning', parent=self.root):
                self.set_status("Upload cancelled (document overwrite declined).", duration_ms=4000)
                return

        # --- 6. Copy Document File ---
        try:
            shutil.copy2(source_path, dest_path_absolute) # copy2 preserves metadata
            print(f"[REPORTS INFO] Successfully copied '{filename}' to destination folder.")
            self.set_status(f"Document '{filename}' uploaded.", duration_ms=4000)
        except Exception as e:
            messagebox.showerror("Upload Error", f"Could not copy the document file to the destination:\n{dest_path_absolute}\n\nError: {e}\n\nPlease check file permissions and available disk space.", parent=self.root)
            self.set_status(f"Error copying document file: {e}", is_error=True)
            return

        # --- 7. Add Link Entry to Data Structure ---
        new_report_entry = {
            'text': link_text,
            'filename': filename, # Store just the filename
            'path': href_path_relative # Store the relative path for the href
        }

        # Ensure the year exists in the data dictionary
        if target_year not in self.reports_data:
            self.reports_data[target_year] = []
            print(f"[REPORTS INFO] Created new year entry in data: {target_year}")
            # Update dropdown immediately if a new year was added via entry box
            if selected_year_str == "<Nieuw Jaar>":
                 self._reports_update_year_dropdown() # Refresh dropdown list
                 self.reports_year_var.set(target_year) # Select the newly added year


        # Check if an entry with the exact same *filename* already exists for that year
        existing_filenames = [item['filename'] for item in self.reports_data[target_year]]
        if filename in existing_filenames:
             print(f"[REPORTS WARNING] Adding link for filename '{filename}' which already exists in year {target_year}.")
             # Ask user if they want to add another link to the same file
             if not messagebox.askyesno("Duplicate Filename Link",
                                        f"A link for the file '{filename}' already exists for the year {target_year}.\n\nDo you want to add another link entry for the same file (with different link text)?",
                                        parent=self.root):
                 self.set_status(f"Link addition cancelled (duplicate filename link declined).", duration_ms=4000)
                 # Note: We already copied the file, maybe offer to delete it? Too complex for now.
                 return

        # Append the new link entry to the list for the target year
        self.reports_data[target_year].append(new_report_entry)
        # Optional: Sort list within the year after adding? e.g., by link text
        # self.reports_data[target_year].sort(key=lambda x: x['text'].lower())

        # --- 8. Refresh UI ---
        self._reports_populate_treeview() # Refresh the treeview to show the new link
        self.set_status(f"Report link '{link_text}' added for {target_year} (unsaved).", duration_ms=5000)

        # Clear the link text field for the next entry
        self.reports_link_text_entry.delete(0, tk.END)
        # Optionally reset year selection or leave as is
        # self.reports_link_text_entry.focus() # Focus for next link text


    def _reports_delete(self):
        print("[REPORTS GUI DEBUG] Delete report link action initiated.")
        selected_items = self.reports_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Required", "Please select a report link from the list to delete.", parent=self.root)
            return

        item_id = selected_items[0] # The iid is "year-original_index"
        try:
            # Parse the iid to get the year and original index
            year, original_index_str = item_id.split('-', 1) # Split only once
            original_index = int(original_index_str)

            # Verify the data exists before proceeding
            if year not in self.reports_data or not isinstance(self.reports_data[year], list) or original_index >= len(self.reports_data[year]):
                 raise ValueError(f"Data for item ID '{item_id}' (Year: {year}, Index: {original_index}) not found in self.reports_data.")

            # Get details of the report link to be deleted for confirmation
            report_to_delete = self.reports_data[year][original_index]
            details = f"Year: {year}\nLink Text: {report_to_delete['text']}\nFilename: {report_to_delete['filename']}"
            print(f"[REPORTS GUI DEBUG] Attempting to delete link entry: ID='{item_id}', Details='{details}'")

            # Confirmation Dialog
            if messagebox.askyesno("Confirm Link Deletion",
                                   f"Are you sure you want to remove the link entry for this report?\n\n{details}\n\n"
                                   f"IMPORTANT: This action only removes the link from the HTML page.\n"
                                   f"It does NOT delete the actual document file ('{report_to_delete['filename']}') from the server/docs folder.",
                                   icon='warning', parent=self.root):

                # Delete the item from the list for that year using the original index
                del self.reports_data[year][original_index]
                print(f"[REPORTS INFO] Deleted report link entry from data structure at index {original_index} for year {year}.")

                # If the year becomes empty after deletion, remove the year key entirely
                if not self.reports_data[year]:
                    del self.reports_data[year]
                    print(f"[REPORTS INFO] Removed empty year entry from data: {year}")
                    # Update year dropdown as the list of available years has changed
                    self._reports_update_year_dropdown()

                # Refresh the treeview to reflect the removal
                # Repopulating is the safest way to handle index changes
                self._reports_populate_treeview()
                self.set_status("Report link removed (unsaved). Click 'Save Changes' to update HTML.", duration_ms=5000)
            else:
                 print("[REPORTS GUI DEBUG] Link deletion cancelled by user.")

        except (ValueError, KeyError, IndexError, TypeError) as e:
             # Catch various potential errors during parsing or access
             print(f"[REPORTS GUI ERROR] Failed to parse item ID '{item_id}' or find/delete data: {e}")
             messagebox.showerror("Error", f"Could not delete the selected report link.\nError details: {e}\n\nIt might have been removed already, or there was an internal data error. Try reloading.", parent=self.root)


    def _reports_save(self):
        print("[REPORTS GUI DEBUG] Save reports clicked.")
        if not self.reports_file_loaded:
            messagebox.showwarning("Load First", "Please load the reports data from the HTML file before saving.", parent=self.root)
            self.set_status("Save failed: Reports data not loaded.", is_error=True)
            return

        # Data to save is the current state of self.reports_data
        data_to_save = self.reports_data
        report_count = sum(len(v) for v in data_to_save.values())
        filename_short = os.path.basename(REPORTS_HTML_FILE_PATH)
        print(f"[REPORTS GUI DEBUG] Preparing to save {report_count} report links across {len(data_to_save)} years to {REPORTS_HTML_FILE_PATH}")

        # Ask for confirmation if the entire reports structure is empty
        if not data_to_save:
            if not messagebox.askyesno("Confirm Empty Save",
                                       f"The reports list is now completely empty.\nSave these changes to:\n{filename_short}?\n\n"
                                       f"(This will remove the entire content inside the '<div id=\"reports-section\">' on the page.)",
                                       icon='warning', parent=self.root):
                 self.set_status("Save cancelled (empty list confirmation declined).", duration_ms=4000)
                 return

        # Perform the save operation
        self.set_status(f"Saving report links structure to {filename_short}...")
        self.root.update_idletasks() # Show status update
        success, error_msg = _reports_save_html(REPORTS_HTML_FILE_PATH, data_to_save)

        if success:
            self.set_status(f"Report links successfully saved to {filename_short}.", duration_ms=5000)
            print(f"[REPORTS INFO] Save successful: {REPORTS_HTML_FILE_PATH}")
        else:
            # Error message from _reports_save_html is passed back
            self.set_status(f"Error saving report links: {error_msg}. Check console.", is_error=True)
            messagebox.showerror("Save Error", f"Failed to save changes to:\n{REPORTS_HTML_FILE_PATH}\n\nError: {error_msg}\n\nPlease check the application's console output for detailed errors.", parent=self.root)


    # --- Text Editor Tab Creation & Methods (NEW) ---
    def _create_text_editor_tab(self, parent_frame):
        print("[GUI INFO] Creating Text Editor Tab...")
        if not BeautifulSoup or not NavigableString or not Comment:
            error_label = ttk.Label(parent_frame, text="Error: BeautifulSoup4 library not found or incomplete.\nCannot load Text Editor.\nPlease install/reinstall using: pip install beautifulsoup4", style="Error.TLabel", justify=tk.CENTER)
            error_label.pack(pady=50, padx=20, expand=True)
            print("[GUI ERROR] Text Editor tab disabled: BeautifulSoup components missing.")
            return

        # --- State Variables ---
        self.text_editor_found_texts = [] # List of dicts: {'file_path', 'original_text', 'dom_reference', 'display_text', 'iid'}
        self.text_editor_parsed_soups = {} # Cache parsed soup objects: {file_path: soup}
        self.text_editor_selected_iid = None
        self._text_editor_scan_running = False # Flag to prevent concurrent scans

        # --- Layout Frames ---
        # Top: Scan Button and Search
        top_frame = ttk.Frame(parent_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        # Middle: Treeview (takes most space)
        tree_frame = ttk.Frame(parent_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Bottom: Editing Area and Save/Cancel
        edit_frame = ttk.Frame(parent_frame)
        edit_frame.pack(fill=tk.X, pady=(10, 0))

        # --- Top Frame Widgets ---
        self.text_editor_scan_button = ttk.Button(top_frame, text="Scan Files for Text", command=self._text_editor_scan_files)
        self.text_editor_scan_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.text_editor_search_var = tk.StringVar()
        self.text_editor_search_entry = ttk.Entry(top_frame, textvariable=self.text_editor_search_var, width=40, state=tk.DISABLED)
        self.text_editor_search_entry.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)
        self.text_editor_search_entry.bind("<KeyRelease>", self._text_editor_filter_treeview_event) # Trigger filter on key release
        ttk.Label(top_frame, text="<- Search Found Text", style="Desc.TLabel").pack(side=tk.LEFT, padx=(0,5), pady=5)


        # --- Middle Frame Widgets (Treeview) ---
        tree_columns = ('file', 'text')
        self.text_editor_tree = ttk.Treeview(tree_frame, columns=tree_columns, show='headings', selectmode='browse')

        # Configure Headings (No sorting for simplicity initially)
        self.text_editor_tree.heading('file', text='File Path')
        self.text_editor_tree.column('file', width=300, minwidth=200, anchor=tk.W)
        self.text_editor_tree.heading('text', text='Found Text Snippet')
        self.text_editor_tree.column('text', width=600, minwidth=300, anchor=tk.W) # Main column

        # Scrollbars
        tree_vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.text_editor_tree.yview)
        tree_hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.text_editor_tree.xview)
        self.text_editor_tree.configure(yscrollcommand=tree_vsb.set, xscrollcommand=tree_hsb.set)

        # Grid Layout
        self.text_editor_tree.grid(row=0, column=0, sticky='nsew')
        tree_vsb.grid(row=0, column=1, sticky='ns')
        tree_hsb.grid(row=1, column=0, sticky='ew')
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Binding selection
        self.text_editor_tree.bind("<<TreeviewSelect>>", self._text_editor_on_select)

        # --- Bottom Frame Widgets (Editor) ---
        ttk.Label(edit_frame, text="Edit Selected Text:", style="Bold.TLabel").pack(anchor=tk.W, padx=5, pady=(0,2))

        self.text_editor_edit_area = scrolledtext.ScrolledText(edit_frame, width=80, height=6, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1, state=tk.DISABLED, font=(self.default_font_family, self.default_font_size))
        self.text_editor_edit_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0,5))

        # Save/Cancel Buttons Frame
        edit_button_frame = ttk.Frame(edit_frame)
        edit_button_frame.pack(fill=tk.X, padx=5, pady=(0,5))

        self.text_editor_save_button = ttk.Button(edit_button_frame, text="Save This Change to File", command=self._text_editor_save_change, state=tk.DISABLED)
        self.text_editor_save_button.pack(side=tk.LEFT, padx=(0, 5))

        self.text_editor_cancel_button = ttk.Button(edit_button_frame, text="Cancel Edit", command=self._text_editor_cancel_edit, state=tk.DISABLED)
        self.text_editor_cancel_button.pack(side=tk.LEFT, padx=5)


    def _text_editor_find_html_files(self):
        """Finds all .html files based on the configured target paths."""
        html_files = set() # Use a set to avoid duplicates
        targets = TEXT_EDITOR_TARGET_PATHS_ABSOLUTE

        print(f"[TEXT EDITOR] Scanning targets: {targets}")
        for target_path in targets:
            if not os.path.exists(target_path):
                print(f"[TEXT EDITOR WARNING] Target path not found: {target_path}")
                continue

            if os.path.isfile(target_path):
                if target_path.lower().endswith('.html'):
                    html_files.add(target_path)
                    print(f"[TEXT EDITOR] Found file: {target_path}")
            elif os.path.isdir(target_path):
                print(f"[TEXT EDITOR] Scanning directory: {target_path}")
                for root, _, files in os.walk(target_path):
                    for filename in files:
                        if filename.lower().endswith('.html'):
                            full_path = os.path.join(root, filename)
                            html_files.add(full_path)
                            print(f"[TEXT EDITOR] Found file in dir: {full_path}")
            else:
                 print(f"[TEXT EDITOR WARNING] Target is neither file nor directory: {target_path}")

        print(f"[TEXT EDITOR] Found {len(html_files)} unique HTML files.")
        return sorted(list(html_files))


    def _text_editor_scan_files(self):
        """Scans configured HTML files, extracts text nodes, and populates the treeview."""
        if self._text_editor_scan_running:
            print("[TEXT EDITOR WARNING] Scan already in progress.")
            return
        if not BeautifulSoup or not NavigableString or not Comment:
             messagebox.showerror("Error", "BeautifulSoup library missing or incomplete. Cannot scan.", parent=self.root)
             return

        self._text_editor_scan_running = True
        self.text_editor_scan_button.config(state=tk.DISABLED, text="Scanning...")
        self.set_status("Scanning HTML files for text...")
        self.root.update_idletasks()

        # --- Clear previous results ---
        self.text_editor_found_texts = []
        self.text_editor_parsed_soups = {}
        self.text_editor_selected_iid = None
        self._text_editor_clear_treeview()
        self._text_editor_reset_edit_area()
        self.text_editor_search_var.set("")
        # --- Keep search disabled until scan determines if there's anything to search ---
        self.text_editor_search_entry.config(state=tk.DISABLED)

        files_to_scan = self._text_editor_find_html_files()
        processed_files = 0
        total_texts_found = 0

        # --- Main Scanning Loop ---
        for i, file_path in enumerate(files_to_scan):
            self.set_status(f"Scanning file {i+1}/{len(files_to_scan)}: {os.path.basename(file_path)}...")
            self.root.update_idletasks()
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # --- Parse with BeautifulSoup ---
                try:
                    soup = BeautifulSoup(content, 'lxml')
                    parser_used = 'lxml'
                except Exception:
                    try:
                        print(f"[TEXT EDITOR WARNING] lxml parser failed for {file_path}, trying html.parser.")
                        soup = BeautifulSoup(content, 'html.parser')
                        parser_used = 'html.parser'
                    except Exception as parse_err:
                        print(f"[TEXT EDITOR ERROR] Failed to parse {file_path} with any parser: {parse_err}")
                        continue # Skip this file

                print(f"[TEXT EDITOR DEBUG] Parsed {file_path} using {parser_used}")
                self.text_editor_parsed_soups[file_path] = soup # Store the parsed soup

                # --- Find and Filter Text Nodes ---
                texts_in_file = 0
                for text_node in soup.find_all(string=True):
                    # Filters (as before)
                    parent_tag = text_node.parent
                    if parent_tag and parent_tag.name in TEXT_EDITOR_EXCLUDED_TAGS: continue
                    if isinstance(text_node, Comment): continue
                    original_text = str(text_node).strip()
                    if not original_text: continue
                    # --- Store the valid text node ---
                    iid = len(self.text_editor_found_texts)
                    display_text = (original_text[:100] + '...') if len(original_text) > 100 else original_text
                    display_text = display_text.replace('\n', ' ').replace('\r', '')

                    self.text_editor_found_texts.append({
                        'file_path': file_path,
                        'original_text': str(text_node),
                        'dom_reference': text_node,
                        'display_text': display_text,
                        'iid': iid
                    })
                    texts_in_file += 1
                    total_texts_found += 1

                if texts_in_file > 0:
                     print(f"[TEXT EDITOR DEBUG] Found {texts_in_file} text snippets in {os.path.basename(file_path)}")
                processed_files += 1

            except FileNotFoundError:
                print(f"[TEXT EDITOR ERROR] File not found during scan: {file_path}")
            except Exception as e:
                import traceback
                print(f"[TEXT EDITOR ERROR] Error processing file {file_path}: {e}")
                traceback.print_exc()

        # --- Populate Treeview after scanning all files ---
        self._text_editor_populate_treeview(self.text_editor_found_texts)

        # --- Final UI Updates ---
        # *** MODIFICATION START ***
        # Enable search entry ONLY if the initial scan found *any* text items
        if self.text_editor_found_texts:
            self.text_editor_search_entry.config(state=tk.NORMAL)
            print("[TEXT EDITOR DEBUG] Enabling search entry as text items were found.")
        else:
            self.text_editor_search_entry.config(state=tk.DISABLED)
            print("[TEXT EDITOR DEBUG] Keeping search entry disabled as no text items were found.")
        # *** MODIFICATION END ***

        self.text_editor_scan_button.config(state=tk.NORMAL, text="Scan Files for Text")
        self._text_editor_scan_running = False
        if total_texts_found > 0:
            status_msg = f"Scan complete. Found {total_texts_found} text snippets in {processed_files} files. Use search box to filter."
        else:
            status_msg = f"Scan complete. No editable text snippets found in {processed_files} scanned files."
        self.set_status(status_msg, duration_ms=8000)


        # --- Populate Treeview after scanning all files ---
        self._text_editor_populate_treeview(self.text_editor_found_texts)

        # --- Final UI Updates ---
        self.text_editor_search_entry.config(state=tk.NORMAL if self.text_editor_found_texts else tk.DISABLED)
        self.text_editor_scan_button.config(state=tk.NORMAL, text="Scan Files for Text")
        self._text_editor_scan_running = False
        self.set_status(f"Scan complete. Found {total_texts_found} text snippets in {processed_files} files.", duration_ms=6000)


    def _text_editor_clear_treeview(self):
        """Clears the text editor treeview."""
        print("[TEXT EDITOR DEBUG] Clearing text editor treeview.")
        self.text_editor_tree.unbind("<<TreeviewSelect>>") # Unbind during clear
        for item in self.text_editor_tree.get_children():
            self.text_editor_tree.delete(item)
        # Re-binding happens in populate if needed


    def _text_editor_populate_treeview(self, data_list):
        """Populates the text editor treeview with items from the data list."""
        self._text_editor_clear_treeview() # Ensure it's clear first
        print(f"[TEXT EDITOR DEBUG] Populating treeview with {len(data_list)} items.")

        for item_data in data_list:
             try:
                display_path = os.path.relpath(item_data['file_path'], APP_BASE_DIR)
             except ValueError:
                display_path = item_data['file_path']

             values = (display_path, item_data['display_text'])
             try:
                self.text_editor_tree.insert('', tk.END, iid=item_data['iid'], values=values, tags=('text_row',))
             except Exception as e:
                print(f"[TEXT EDITOR GUI ERROR] Failed inserting row {item_data['iid']}: {values}\nError: {e}")
        if data_list:
            self.text_editor_tree.bind("<<TreeviewSelect>>", self._text_editor_on_select)


    def _text_editor_filter_treeview_event(self, event=None):
        """Handles key release in search box to filter treeview."""
        search_term = self.text_editor_search_var.get().lower().strip()
        print(f"[TEXT EDITOR DEBUG] Filtering treeview with term: '{search_term}'")

        # Filter the main data list
        if not search_term:
            # If search is empty, show all original items
            filtered_data = self.text_editor_found_texts
        else:
            filtered_data = [
                item for item in self.text_editor_found_texts
                # Search in the *original* (unstripped, non-truncated) text for accuracy
                if search_term in item['original_text'].lower()
            ]

        # Repopulate the treeview with the filtered results
        self._text_editor_populate_treeview(filtered_data)
        # Reset edit area when filter changes
        self._text_editor_reset_edit_area()

    def _text_editor_reset_edit_area(self):
        """Disables and clears the text editing area and buttons."""
        self.text_editor_selected_iid = None
        self.text_editor_edit_area.config(state=tk.NORMAL) # Must be normal to delete
        self.text_editor_edit_area.delete('1.0', tk.END)
        self.text_editor_edit_area.config(state=tk.DISABLED)
        self.text_editor_save_button.config(state=tk.DISABLED)
        self.text_editor_cancel_button.config(state=tk.DISABLED)


    def _text_editor_on_select(self, event=None):
        """Handles selection change in the text editor treeview."""
        selected_items = self.text_editor_tree.selection()
        if not selected_items:
            self._text_editor_reset_edit_area()
            return

        selected_iid_str = selected_items[0]
        try:
            selected_iid = int(selected_iid_str) # iid is the index
            # Find the corresponding data dictionary
            # This assumes self.text_editor_found_texts hasn't been reordered,
            # which is true as we store the index as the iid.
            data_item = self.text_editor_found_texts[selected_iid]

            self.text_editor_selected_iid = selected_iid # Store the selected index

            # Enable editor and buttons
            self.text_editor_edit_area.config(state=tk.NORMAL)
            self.text_editor_save_button.config(state=tk.NORMAL)
            self.text_editor_cancel_button.config(state=tk.NORMAL)

            # Populate editor with the *full original* text
            self.text_editor_edit_area.delete('1.0', tk.END)
            # Insert the potentially multi-line original text
            self.text_editor_edit_area.insert('1.0', data_item['original_text'])
            print(f"[TEXT EDITOR DEBUG] Selected item iid {selected_iid}. Displaying text for editing.")

        except (ValueError, IndexError, KeyError) as e:
            print(f"[TEXT EDITOR ERROR] Error retrieving data for selected iid '{selected_iid_str}': {e}")
            messagebox.showerror("Error", "Could not retrieve data for the selected text snippet.", parent=self.root)
            self._text_editor_reset_edit_area()


    def _text_editor_cancel_edit(self):
        """Cancels the current edit, resetting the edit area."""
        print("[TEXT EDITOR DEBUG] Cancel edit clicked.")
        self._text_editor_reset_edit_area()
        # Optionally clear the treeview selection
        if self.text_editor_tree.selection():
             self.text_editor_tree.selection_remove(self.text_editor_tree.selection()[0])
        self.set_status("Edit cancelled.", duration_ms=3000)


    def _text_editor_save_change(self):
        """Saves the edited text back to the corresponding HTML file."""
        if self.text_editor_selected_iid is None:
            messagebox.showwarning("No Selection", "No text snippet is selected for saving.", parent=self.root)
            return

        try:
            # Retrieve the data for the selected item using the stored iid (index)
            data_item = self.text_editor_found_texts[self.text_editor_selected_iid]
            file_path = data_item['file_path']
            text_node_reference = data_item['dom_reference'] # The crucial BS4 node object

            # Get edited text from the ScrolledText widget
            edited_text = self.text_editor_edit_area.get('1.0', tk.END).strip() # Strip whitespace from edited text? Or preserve it? Let's preserve it for now.
            edited_text = self.text_editor_edit_area.get('1.0', tk.END)[:-1] # Remove trailing newline added by get()

            # Get the original text (unstripped) for comparison
            original_stored_text = data_item['original_text']

            print(f"[TEXT EDITOR DEBUG] Saving change for iid {self.text_editor_selected_iid} in file {file_path}")
            # print(f"  Original Text: '{original_stored_text}'")
            # print(f"  Edited Text:   '{edited_text}'")

            # --- Safety Check: Ensure the node still exists in the parsed soup ---
            # This check might be complex if the soup structure changed drastically elsewhere.
            # A basic check: is the reference still valid and attached to the soup?
            if text_node_reference is None or not text_node_reference.parent:
                 messagebox.showerror("Save Error", "The original text location could not be found in the parsed file.\nThis might happen if the file structure changed significantly.\nPlease re-scan the files.", parent=self.root)
                 self.set_status("Save failed: Original text node lost.", is_error=True)
                 self._text_editor_reset_edit_area() # Reset state
                 return

            # --- Modify the Soup Object ---
            # Use replace_with() on the NavigableString node
            try:
                text_node_reference.replace_with(edited_text)
                print(f"[TEXT EDITOR DEBUG] Replaced text in BeautifulSoup object for {file_path}")
            except Exception as replace_err:
                messagebox.showerror("Save Error", f"Failed to replace text in the internal document structure.\nError: {replace_err}", parent=self.root)
                self.set_status("Save failed: Could not modify internal structure.", is_error=True)
                return

            # --- Write the *entire modified* soup back to the file ---
            modified_soup = self.text_editor_parsed_soups[file_path]
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # Use prettify for readable HTML, or str() for compact
                    f.write(modified_soup.prettify(formatter="html5"))
                    # f.write(str(modified_soup))
                print(f"[TEXT EDITOR INFO] Successfully saved modified file: {file_path}")

                # --- Update internal data and Treeview ---
                # Update the stored original text to reflect the change
                data_item['original_text'] = edited_text
                # Update the display text (truncated, no newlines)
                new_display_text = (edited_text[:100] + '...') if len(edited_text) > 100 else edited_text
                new_display_text = new_display_text.replace('\n', ' ').replace('\r', '')
                data_item['display_text'] = new_display_text
                # Update the treeview row for this item
                self.text_editor_tree.item(self.text_editor_selected_iid, values=(
                    os.path.relpath(file_path, APP_BASE_DIR) if APP_BASE_DIR in file_path else file_path, # Update path display too? No, just text.
                    new_display_text
                ))

                # Reset the edit area
                self._text_editor_reset_edit_area()
                self.set_status(f"Change saved successfully to {os.path.basename(file_path)}.", duration_ms=5000)

            except Exception as save_err:
                import traceback
                messagebox.showerror("Save Error", f"Failed to write changes to file:\n{file_path}\n\nError: {save_err}\n\nCheck file permissions.", parent=self.root)
                self.set_status(f"Save failed: Error writing file {os.path.basename(file_path)}.", is_error=True)
                traceback.print_exc()
                # Attempt to revert the change in the soup object? Complex. Best to advise re-scan.
                print("[TEXT EDITOR WARNING] File save failed. The in-memory soup object is modified but not saved.")


        except (IndexError, KeyError) as e:
            print(f"[TEXT EDITOR ERROR] Error retrieving data for selected iid '{self.text_editor_selected_iid}' during save: {e}")
            messagebox.showerror("Save Error", "Could not retrieve data for the selected text snippet to save.", parent=self.root)
            self._text_editor_reset_edit_area()
        except Exception as e:
            import traceback
            print(f"[TEXT EDITOR ERROR] Unexpected error during save: {e}")
            messagebox.showerror("Save Error", f"An unexpected error occurred during save:\n{e}", parent=self.root)
            traceback.print_exc()
            self._text_editor_reset_edit_area()



# --- Record Add/Edit Dialog Class ---
# (Keep existing RecordDialog class, ensure it handles 5 entries)
class RecordDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_data=None, callback=None):
        super().__init__(parent)
        self.transient(parent) # Keep dialog on top of parent
        self.title(title)
        self.callback = callback
        # Ensure initial_data is always a list of 5 elements, padding with "" if needed
        if initial_data and isinstance(initial_data, (list, tuple)):
             self.initial_data = (list(initial_data) + ["", "", "", "", ""])[:5]
        else:
             self.initial_data = ["", "", "", "", ""] # Default empty strings

        self.result = None # To store the data entered
        print(f"[RECORD DIALOG DEBUG] Init '{title}': {self.initial_data}")

        frame = ttk.Frame(self, padding="15")
        frame.pack(expand=True, fill=tk.BOTH)

        labels = ["Discipline:", "Naam:", "Prestatie:", "Plaats:", "Datum (bv. YYYY.MM.DD):"] # Adjusted Date label
        self.entries = []

        for i, label_text in enumerate(labels):
            ttk.Label(frame, text=label_text).grid(row=i, column=0, sticky=tk.W, padx=5, pady=5)
            entry = ttk.Entry(frame, width=40)
            entry.grid(row=i, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
            # Ensure data inserted is a string, handle None explicitly
            entry.insert(0, str(self.initial_data[i]) if self.initial_data[i] is not None else "")
            self.entries.append(entry)

        frame.columnconfigure(1, weight=1) # Allow entries to expand horizontally

        # --- Buttons ---
        button_frame = ttk.Frame(frame)
        # Place button frame below entries, spanning columns, right-aligned content
        button_frame.grid(row=len(labels), column=0, columnspan=2, pady=(15, 0), sticky=tk.E)

        # OK Button
        ok_button = ttk.Button(button_frame, text="OK", command=self.on_ok, style="Accent.TButton") # Optional style
        ok_button.pack(side=tk.RIGHT, padx=(5, 0)) # Pack right first

        # Cancel Button
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.on_cancel)
        cancel_button.pack(side=tk.RIGHT) # Pack right next (appears left of OK)


        self.grab_set() # Make the dialog modal
        self.protocol("WM_DELETE_WINDOW", self.on_cancel) # Handle closing window
        self.bind("<Return>", self.on_ok) # Allow Enter key to confirm
        self.bind("<Escape>", self.on_cancel) # Allow Esc key to cancel

        self.entries[0].focus_set() # Focus on the first entry field
        self.wait_window(self) # Wait until the dialog is closed
        print("[RECORD DIALOG DEBUG] Dialog closed.")

    def on_ok(self, event=None): # Add event parameter for binding
        # Get data from entries, stripping whitespace
        data = [entry.get().strip() for entry in self.entries]
        print(f"[RECORD DIALOG DEBUG] OK clicked. Data entered: {data}")

        # Basic Validation: Discipline and Name are required
        if not data[0]: # Discipline empty
            messagebox.showwarning("Input Required", "The 'Discipline' field cannot be empty.", parent=self)
            self.entries[0].focus_set()
            return
        if not data[1]: # Name empty
            messagebox.showwarning("Input Required", "The 'Naam' field cannot be empty.", parent=self)
            self.entries[1].focus_set()
            return

        # Optional: Add date format validation (example using regex)
        # date_pattern = r"^\d{4}\.\d{2}\.\d{2}$" # Strict YYYY.MM.DD
        # if data[4] and not re.match(date_pattern, data[4]):
        #      messagebox.showwarning("Format Incorrect", "The 'Datum' format should be YYYY.MM.DD (e.g., 2023.10.27).", parent=self)
        #      self.entries[4].focus_set()
        #      return

        # Store the validated data
        self.result = data
        # Call the callback function if provided
        if self.callback:
             self.callback(self.result)
        # Destroy the dialog window
        self.destroy()

    def on_cancel(self, event=None): # Add event parameter for binding
        print("[RECORD DIALOG DEBUG] Cancelled.")
        # Callback with None to indicate cancellation
        if self.callback:
             self.callback(None)
        # Destroy the dialog window
        self.destroy()


# --- Calendar Event Add/Edit Dialog Class ---
# (Keep existing CalendarEventDialog class)
class CalendarEventDialog(tk.Toplevel):
    def __init__(self, parent, title, initial_event_dict=None, callback=None):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.callback = callback
        self.result = None # To store the resulting dict {'date', 'name', 'color', 'link'}

        # Initialize data, ensuring defaults
        self.initial_data = initial_event_dict or {}
        default_date = datetime.date.today().isoformat()
        default_color = CALENDAR_EVENT_COLORS[0] if CALENDAR_EVENT_COLORS else "black"
        print(f"[CALENDAR DIALOG] Init '{title}': {self.initial_data}")

        # --- Main Frame ---
        frame = ttk.Frame(self, padding="15")
        frame.pack(expand=True, fill=tk.BOTH)

        # --- Widgets ---
        row_index = 0

        # Date Entry
        ttk.Label(frame, text="Date (YYYY-MM-DD):*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.entry_date = ttk.Entry(frame, width=20)
        self.entry_date.grid(row=row_index, column=1, sticky=tk.W, padx=5, pady=2)
        self.entry_date.insert(0, self.initial_data.get('date', default_date))
        row_index += 1

        # Event Name Entry
        ttk.Label(frame, text="Event Name:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.entry_name = ttk.Entry(frame, width=45) # Wider entry
        self.entry_name.grid(row=row_index, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        self.entry_name.insert(0, self.initial_data.get('name', ''))
        row_index += 1

        # Color Combobox
        ttk.Label(frame, text="Color:*").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.color_var = tk.StringVar(value=self.initial_data.get('color', default_color))
        self.combo_color = ttk.Combobox(frame, textvariable=self.color_var, values=CALENDAR_EVENT_COLORS, state="readonly", width=18)
        self.combo_color.grid(row=row_index, column=1, sticky=tk.W, padx=5, pady=2)
        # Select current color if it exists in list, otherwise default
        if self.initial_data.get('color') in CALENDAR_EVENT_COLORS:
             self.combo_color.set(self.initial_data['color'])
        else:
             self.combo_color.set(default_color)
        row_index += 1

        # Link Entry (Optional)
        ttk.Label(frame, text="Link (Optional):").grid(row=row_index, column=0, sticky=tk.W, padx=5, pady=5)
        self.entry_link = ttk.Entry(frame, width=45) # Wider entry
        self.entry_link.grid(row=row_index, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        self.entry_link.insert(0, self.initial_data.get('link') or '') # Display empty string if link is None
        row_index += 1

        # Configure Column Weight for expansion
        frame.columnconfigure(1, weight=1)

        # --- Buttons ---
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row_index, column=0, columnspan=2, pady=(15, 0), sticky=tk.E) # Right-align buttons

        ok_button = ttk.Button(button_frame, text="OK", command=self.on_ok)
        ok_button.pack(side=tk.RIGHT, padx=(5, 0))

        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.on_cancel)
        cancel_button.pack(side=tk.RIGHT)

        # --- Final Setup ---
        self.grab_set() # Modal
        self.protocol("WM_DELETE_WINDOW", self.on_cancel) # Handle close button
        self.bind("<Return>", self.on_ok) # Enter key submits
        self.bind("<Escape>", self.on_cancel) # Escape key cancels

        self.entry_date.focus_set() # Focus on first field
        self.wait_window(self) # Wait for dialog closure
        print("[CALENDAR DIALOG DEBUG] Dialog closed.")

    def on_ok(self, event=None):
        print("[CALENDAR DIALOG DEBUG] OK pressed.")
        date_str = self.entry_date.get().strip()
        name = self.entry_name.get().strip()
        color = self.color_var.get()
        link = self.entry_link.get().strip() or None # Store as None if empty string

        # --- Validation ---
        # Date Validation
        if not date_str:
            messagebox.showwarning("Input Required", "The 'Date' field cannot be empty.", parent=self)
            self.entry_date.focus_set()
            return
        try:
            # Validate and normalize date format to YYYY-MM-DD
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            normalized_date_str = date_obj.isoformat() # Ensure consistent format
        except ValueError:
            messagebox.showwarning("Invalid Format", "The 'Date' must be in YYYY-MM-DD format (e.g., 2023-10-27).", parent=self)
            self.entry_date.focus_set()
            return

        # Name Validation
        if not name:
            messagebox.showwarning("Input Required", "The 'Event Name' field cannot be empty.", parent=self)
            self.entry_name.focus_set()
            return

        # Color Validation (should always be valid due to combobox)
        if not color or color not in CALENDAR_EVENT_COLORS:
             messagebox.showerror("Internal Error", "Invalid color selected. Please report this bug.", parent=self)
             return

        # Optional: Link Validation (basic check for common prefixes)
        if link and not (link.startswith(('http://', 'https://', '/', '#', 'mailto:'))):
             # Ask if unusual link format is intentional
             if not messagebox.askyesno("Link Format Check",
                                        f"The link provided:\n'{link}'\n"
                                        f"doesn't start with a common web prefix (http, https, /, #, mailto:).\n\n"
                                        f"Is this link format correct?",
                                        icon='question', parent=self):
                  self.entry_link.focus_set()
                  return

        # --- Store Result and Callback ---
        self.result = {
            'date': normalized_date_str,
            'name': name,
            'color': color,
            'link': link # Store as None if it was empty
        }
        print(f"[CALENDAR DIALOG DEBUG] Result: {self.result}")
        if self.callback:
            self.callback(self.result) # Send the dict back
        self.destroy()

    def on_cancel(self, event=None):
        print("[CALENDAR DIALOG DEBUG] Cancelled.")
        if self.callback:
            self.callback(None) # Indicate cancellation
        self.destroy()



# --- Main Execution ---
if __name__ == "__main__":
    print("\n--- Starting Website Editor ---")
    # --- Pre-flight Checks ---
    errors_found = False
    warnings_found = False
    print("\n[Check 1] Checking Required/Used Files & Directories...")

    required_paths_to_check = {
        "Records Base Dir": RECORDS_BASE_DIR_ABSOLUTE,
        "Calendar HTML": CALENDAR_HTML_FILE_PATH,
        "Reports HTML": REPORTS_HTML_FILE_PATH,
    }
    optional_paths_to_check = {
        "News JSON": NEWS_JSON_FILE_PATH,
        "News Images Dir": NEWS_IMAGE_DEST_DIR_ABSOLUTE,
        "Reports Docs Dir": REPORTS_DOCS_DEST_DIR_ABSOLUTE,
    }
    text_editor_targets_to_check = TEXT_EDITOR_TARGET_PATHS_ABSOLUTE

    # Check Required
    for name, path in required_paths_to_check.items():
        if not os.path.exists(path):
             print(f"  - {name}: *** MISSING *** -> {path}"); errors_found = True
        elif name.endswith("Dir") and not os.path.isdir(path):
             print(f"  - {name}: *** ERROR (Not a Directory) *** -> {path}"); errors_found = True
        elif not name.endswith("Dir") and not os.path.isfile(path):
             print(f"  - {name}: *** ERROR (Not a File) *** -> {path}"); errors_found = True
        else:
             print(f"  - {name}: OK -> {path}")

    # Check Optional (Warn if missing, as app might create them)
    for name, path in optional_paths_to_check.items():
        if not os.path.exists(path):
             print(f"  - {name}: --- Optional - Not Found (will attempt creation if needed) --- -> {path}"); warnings_found = True
        elif name.endswith("Dir") and not os.path.isdir(path):
             print(f"  - {name}: *** ERROR (Not a Directory) *** -> {path}"); errors_found = True # Should be dir if exists
        elif not name.endswith("Dir") and not os.path.isfile(path):
             print(f"  - {name}: OK (Optional File Exists) -> {path}") # File existing is fine
        else:
             print(f"  - {name}: OK -> {path}")

    # Check Text Editor Targets (Warn if any specific target is missing)
    print("  - Text Editor Targets:")
    missing_targets = False
    for path in text_editor_targets_to_check:
         if not os.path.exists(path):
             print(f"    - Target Not Found: {path}"); missing_targets = True
         # else: print(f"    - Target Found: {path}") # Can be noisy
    if missing_targets:
         print("    --- Some Text Editor target paths/folders do not exist. Text Editor scan might be incomplete. ---")
         warnings_found = True
    else:
         print("    - All configured Text Editor targets exist.")


    print("\n[Check 2] Checking Libraries...")
    libraries_ok = True
    try:
        # Test essential components used
        from bs4 import BeautifulSoup, NavigableString, Comment, Tag
        print("  - BeautifulSoup4 (Core, NavigableString, Comment, Tag): OK")
    except ImportError:
        print("  - BeautifulSoup4: *** MISSING *** (Required for Records, Calendar, Reports, Text Editor)")
        libraries_ok = False; errors_found = True
    try:
        import lxml
        print("  - lxml: OK (Recommended HTML parser)")
    except ImportError:
        print("  - lxml: --- Optional - Not Found --- (html.parser will be used as fallback)")
        warnings_found = True # It's a warning as html.parser is fallback

    if not libraries_ok: print("\n[FATAL ERROR] Required Python libraries (BeautifulSoup4) are missing.")
    if errors_found:
         print("\n[FATAL ERROR] Critical setup issues found (missing required files/directories or libraries). Cannot continue.")
         try:
             root = tk.Tk(); root.withdraw()
             messagebox.showerror("Fatal Error - Setup Issue",
                                  "Missing required files, directories or libraries.\n"
                                  "Please check the console output (run from command line if needed) for details and fix the issues before running again.",
                                  parent=None)
             root.destroy()
         except Exception: pass # Ignore errors showing the final message box
         sys.exit(1) # Exit if critical errors found
    elif warnings_found:
         print("\n[SETUP WARNING] Optional files/directories missing or optional libraries not found.")
         print("The application might create missing directories, or some features might rely on fallback mechanisms.")
         try:
             root = tk.Tk(); root.withdraw()
             messagebox.showwarning("Setup Warning",
                                   "Optional files/libraries missing (e.g., lxml, news/reports dirs).\n"
                                   "Check console output for details.\n"
                                   "The application will attempt to continue.",
                                   parent=None)
             root.destroy()
         except Exception: pass # Ignore errors showing the warning box

    else:
        print("\n[Check 3] Pre-flight checks passed.")

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
        import traceback
        traceback.print_exc()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        try:
            # Ensure root exists and try showing error
            if root is None: root = tk.Tk()
            root.withdraw() # Hide window if it wasn't shown or crashed early
            messagebox.showerror("Fatal Runtime Error", f"An unexpected error occurred:\n{e}\n\nPlease check the console output for details.", parent=root)
            if root: root.destroy()
        except Exception as me:
             print(f"ALSO FAILED TO SHOW TKINTER MESSAGEBOX: {me}") # Log error showing messagebox itself
        input("\nPress Enter to exit...") # Keep console open
        sys.exit(1)
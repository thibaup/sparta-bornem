import os
import sys
import re
import json
import shutil
import pathlib
import tkinter as tk
from tkinter import messagebox
from collections import defaultdict
import traceback # Keep for error logging

try:
    # Attempt to import BeautifulSoup and specific elements
    from bs4 import BeautifulSoup, Tag, NavigableString, Comment
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    # Define dummy types if bs4 is not available to avoid NameErrors later,
    # although functions using them will fail or return errors.
    class DummyBs4Type: pass
    BeautifulSoup = DummyBs4Type
    Tag = DummyBs4Type
    NavigableString = DummyBs4Type
    Comment = DummyBs4Type
    print("\n[FATALE FOUT] BeautifulSoup4 bibliotheek niet gevonden.")
    try:
        # Attempt to show a graphical error if Tkinter is available
        root_err = tk.Tk(); root_err.withdraw()
        messagebox.showerror("Fatale Fout - Ontbrekende Bibliotheek", "Vereiste bibliotheek 'BeautifulSoup4' niet gevonden.\nInstalleer a.u.b. via:\npip install beautifulsoup4", parent=None)
        root_err.destroy()
    except Exception: pass
    # Exit here because core functionality depends on bs4
    sys.exit(1)


# Import config after potential bs4 exit
import config

# ==============================================================================
# News Utilities
# ==============================================================================

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
        data.sort(key=lambda x: x.get('date', '0000-00-00'), reverse=True)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return None # Success
    except Exception as e:
        msg = f"Opslaan nieuws data naar '{filepath}': {e}"
        traceback.print_exc()
        return msg

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

# ==============================================================================
# Records Utilities
# ==============================================================================

def records_discover_files(base_dir):
    """Discovers record category directories and HTML files within them."""
    record_structure = {}
    if not os.path.isdir(base_dir):
        print(f"[UTILS][RECORDS] Basis map niet gevonden: {base_dir}")
        return {}
    try:
        # List directories (categories) in the base directory
        categories = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))])
        for category in categories:
            category_path = os.path.join(base_dir, category)
            record_structure[category] = {}
            try:
                # List HTML files in the category directory
                files = sorted([f for f in os.listdir(category_path) if f.lower().endswith('.html')])
                for filename in files:
                    base_name = os.path.splitext(filename)[0]
                    # Create a display name from the filename (e.g., 'indoor-records' -> 'Indoor Records')
                    record_type_name = ' '.join(word.capitalize() for word in base_name.split('-'))
                    record_structure[category][record_type_name] = os.path.join(category_path, filename)
            except OSError as e:
                print(f"[UTILS][RECORDS] Kon map niet lezen {category_path}: {e}")
    except OSError as e:
        print(f"[UTILS][RECORDS] Fout bij toegang tot basis map {base_dir}: {e}")
        return {}
    return record_structure

def records_parse_html(html_path):
    """Parses a records HTML file to extract data from the table."""
    if not BS4_AVAILABLE: return None
    records = []
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            # Try lxml first, fallback to html.parser
            try: soup = BeautifulSoup(f, 'lxml')
            except Exception: f.seek(0); soup = BeautifulSoup(f, 'html.parser')

        # Find the specific table, then its body
        table = soup.find('table', class_='records-table')
        tbody = table.find('tbody') if table else None
        # If specific table/tbody not found, try finding any tbody as a fallback
        if not tbody: tbody = soup.find('tbody')
        if not tbody:
            print(f"[UTILS][RECORDS] Geen <tbody> gevonden in {html_path}")
            return None # Cannot proceed without a tbody

        # Iterate through rows directly within the tbody
        for row in tbody.find_all('tr', recursive=False):
            # Get text from each cell in the row
            cells = [td.get_text(strip=True) for td in row.find_all('td', recursive=False)]
            # Expecting 5 columns for a valid record
            if len(cells) == 5:
                records.append(cells)
            # else: print warning?
        return records
    except FileNotFoundError:
        print(f"[UTILS][RECORDS] Bestand niet gevonden: {html_path}")
        return None
    except Exception as e:
        print(f"[UTILS][RECORDS] Fout bij parsen {html_path}: {e}")
        traceback.print_exc()
        return None

def records_save_html(html_path, records_data):
    """Saves records data back into the HTML file's table body."""
    if not BS4_AVAILABLE: return False
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
             # Try lxml first, fallback to html.parser
             try: soup = BeautifulSoup(f, 'lxml')
             except Exception: f.seek(0); soup = BeautifulSoup(f, 'html.parser')

        # Find the specific table body, fallback to any tbody
        table = soup.find('table', class_='records-table')
        tbody = table.find('tbody') if table else None
        if not tbody: tbody = soup.find('tbody')
        if not tbody:
            print(f"[UTILS][RECORDS] Kan <tbody> niet vinden in {html_path} om op te slaan.")
            return False

        # Clear existing content
        tbody.clear()
        tbody.append("\n") # Add newline for formatting

        # Create new rows from data
        for record_row in records_data:
            new_tr = soup.new_tag('tr')
            new_tr.append("\n  ") # Indent
            for cell_data in record_row:
                new_td = soup.new_tag('td')
                # Ensure cell data is string, handle None
                new_td.string = str(cell_data) if cell_data is not None else ""
                new_tr.append(new_td)
                new_tr.append("\n  ") # Formatting
            # Remove last newline/indent before closing tr
            if new_tr.contents and isinstance(new_tr.contents[-1], NavigableString) and not new_tr.contents[-1].strip():
                new_tr.contents.pop()
            new_tr.append("\n")
            tbody.append(new_tr)
            tbody.append("\n") # Formatting between rows

        # Write the modified HTML back to the file
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(soup.prettify(formatter="html5")) # Use html5 formatter for better output
        return True # Success
    except FileNotFoundError:
        print(f"[UTILS][RECORDS] Bestand niet gevonden voor opslaan: {html_path}")
        return False
    except Exception as e:
        print(f"[UTILS][RECORDS] Fout bij opslaan records naar {html_path}: {e}")
        traceback.print_exc()
        return False

# ==============================================================================
# Calendar Utilities
# ==============================================================================

def calendar_parse_html(html_path):
    """Parses a calendar HTML file to extract event data."""
    if not BS4_AVAILABLE: return None
    events = []
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            try: soup = BeautifulSoup(f, 'lxml')
            except Exception: f.seek(0); soup = BeautifulSoup(f, 'html.parser')

        # Find all month sections
        month_grids = soup.find_all('section', class_='month-grid')
        if not month_grids:
             print("[UTILS][CALENDAR] Geen secties met class 'month-grid' gevonden.")
             return None

        for month_section in month_grids:
            # Extract month and year from title
            month_title_tag = month_section.find('h2', class_='month-title')
            if not month_title_tag: continue
            match = re.match(r'(\w+)\s+(\d{4})', month_title_tag.get_text(strip=True), re.IGNORECASE)
            if not match: continue
            month_name_nl, year_str = match.groups()
            month_num = config.DUTCH_MONTH_MAP.get(month_name_nl.lower())
            if not month_num: continue;
            year = int(year_str)

            # Iterate through actual day cells (exclude padding days)
            for day_div in month_section.select('.calendar-days .calendar-day:not(.padding-day)'):
                day_num_tag = day_div.find('span', class_='day-number')
                if not day_num_tag: continue
                try:
                    day = int(day_num_tag.get_text(strip=True))
                    current_date_str = f"{year:04d}-{month_num:02d}-{day:02d}"
                except ValueError: continue # Skip if day number is not valid integer

                # Find all event spans within the day div
                for event_span in day_div.find_all('span', class_='calendar-event', recursive=False):
                    event_name = ""
                    event_link = None
                    event_color = "black" # Default color

                    # Check for a link within the event span
                    link_tag = event_span.find('a')
                    if link_tag:
                        event_name = link_tag.get_text(strip=True)
                        event_link = link_tag.get('href')
                    else:
                        # If no link, get text directly from the span
                        event_name = event_span.get_text(strip=True)

                    # Extract color from class attribute (e.g., 'event-green')
                    span_classes = event_span.get('class', [])
                    for css_class in span_classes:
                        if css_class.startswith('event-') and css_class.split('-')[1] in config.CALENDAR_EVENT_COLORS:
                            event_color = css_class.split('-')[1]
                            break

                    # Add event if a name was found
                    if event_name:
                        events.append({
                            'date': current_date_str,
                            'name': event_name,
                            'color': event_color,
                            'link': event_link # Will be None if no link found
                        })

        # Sort events by date ascending
        events.sort(key=lambda x: x['date'])
        return events
    except FileNotFoundError:
        print(f"[UTILS][CALENDAR] Kalender bestand niet gevonden: {html_path}")
        return None
    except Exception as e:
        print(f"[UTILS][CALENDAR] Fout bij parsen kalender bestand {html_path}: {e}")
        traceback.print_exc()
        return None

def calendar_save_html(html_path, events_data):
    """Saves event data back into the calendar HTML structure."""
    if not BS4_AVAILABLE: return False
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
             try: soup = BeautifulSoup(f, 'lxml')
             except Exception: f.seek(0); soup = BeautifulSoup(f, 'html.parser')

        # Group events by date for efficient lookup
        events_by_date = defaultdict(list)
        for event in events_data:
            events_by_date[event['date']].append(event)

        # Find all month sections
        month_grids = soup.find_all('section', class_='month-grid')
        if not month_grids:
            print("[UTILS][CALENDAR] Kan niet opslaan: Geen secties met class 'month-grid' gevonden in HTML.")
            return False

        for month_section in month_grids:
            # Get month and year for this section
            month_title_tag = month_section.find('h2', class_='month-title');
            if not month_title_tag: continue
            match = re.match(r'(\w+)\s+(\d{4})', month_title_tag.get_text(strip=True), re.IGNORECASE);
            if not match: continue
            month_name_nl, year_str = match.groups(); month_num = config.DUTCH_MONTH_MAP.get(month_name_nl.lower());
            if not month_num: continue;
            year = int(year_str)

            # Process each valid day cell
            for day_div in month_section.select('.calendar-days .calendar-day:not(.padding-day)'):
                # Remove all existing event spans first
                for old_event in day_div.find_all('span', class_='calendar-event', recursive=False):
                    # Also remove preceding newline/whitespace if possible for cleaner output
                    prev_sibling = old_event.find_previous_sibling()
                    if isinstance(prev_sibling, NavigableString) and not prev_sibling.strip():
                        prev_sibling.extract()
                    old_event.decompose()

                # Get the day number and construct the date string
                day_num_tag = day_div.find('span', class_='day-number');
                if not day_num_tag: continue
                try:
                    day = int(day_num_tag.get_text(strip=True))
                    current_date_str = f"{year:04d}-{month_num:02d}-{day:02d}"
                except ValueError: continue

                # If there are events for this date, add them back
                if current_date_str in events_by_date:
                    # Add events sorted by name for consistent order within a day
                    for event in sorted(events_by_date[current_date_str], key=lambda x: x.get('name','')):
                        # Create new span for the event
                        new_event_span = soup.new_tag('span',
                                                      attrs={'class': f"calendar-event event-{event.get('color', 'black')}"})
                        # Set title attribute for potential tooltips
                        new_event_span['title'] = event.get('name', '')

                        # Add link inside if it exists
                        if event.get('link'):
                            link_tag = soup.new_tag('a', href=event['link'])
                            link_tag.string = event.get('name', '')
                            new_event_span.append(link_tag)
                        else:
                            # Otherwise, just set the text content
                            new_event_span.string = event.get('name', '')

                        # Append the new span and a newline for formatting
                        day_div.append("\n        ") # Indentation
                        day_div.append(new_event_span)
                    # Add final newline after last event for the day, adjusting indentation
                    last_sibling = day_div.contents[-1]
                    if isinstance(last_sibling, Tag) and last_sibling.name == 'span':
                         day_div.append("\n      ") # Correct closing indentation relative to day_div
                    elif isinstance(last_sibling, NavigableString): # Adjust if last item was newline already
                         last_sibling.replace_with("\n      ")


        # Write the modified HTML back
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(soup.prettify(formatter="html5"))
        return True # Success
    except FileNotFoundError:
        print(f"[UTILS][CALENDAR] Kalender bestand niet gevonden voor opslaan: {html_path}")
        return False
    except Exception as e:
        print(f"[UTILS][CALENDAR] Fout bij opslaan kalender bestand {html_path}: {e}")
        traceback.print_exc()
        return False

# ==============================================================================
# Reports Utilities
# ==============================================================================

def reports_parse_html(html_path):
    """Parses the reports HTML file to extract links grouped by year."""
    if not BS4_AVAILABLE: return None, "BeautifulSoup niet beschikbaar"
    reports_data = {}
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            try: soup = BeautifulSoup(f, 'lxml')
            except Exception: f.seek(0); soup = BeautifulSoup(f, 'html.parser')

        # Find the main container div
        reports_section = soup.find('div', id='reports-section')
        if not reports_section:
            msg = "Kon '<div id=\"reports-section\">' niet vinden."
            return None, msg

        current_year = None
        # Iterate through direct children of the container
        for element in reports_section.children:
             if not isinstance(element, Tag): continue # Skip non-tag elements like newlines

             # If it's an H2, try to extract the year
             if element.name == 'h2':
                 year_match = re.search(r'(\d{4})', element.get_text())
                 current_year = year_match.group(1) if year_match else None
                 if current_year:
                     reports_data.setdefault(current_year, []) # Initialize year list if needed
                 #else: print warning?

             # If it's a UL with the correct class and we have a current year context
             elif element.name == 'ul' and 'report-list' in element.get('class', []) and current_year:
                 # Process list items
                 for li in element.find_all('li', recursive=False):
                     a_tag = li.find('a', recursive=False)
                     # Ensure link tag exists and has an href
                     if a_tag and a_tag.get('href'):
                         report_text = a_tag.get_text(strip=True)
                         report_path = a_tag.get('href')
                         # Extract filename from the path
                         report_filename = pathlib.PurePosixPath(report_path).name
                         # Add if all parts are valid
                         if report_text and report_path and report_filename:
                             reports_data[current_year].append({
                                 'text': report_text,
                                 'filename': report_filename,
                                 'path': report_path
                             })

        # Return data sorted by year descending
        return dict(sorted(reports_data.items(), key=lambda item: int(item[0]), reverse=True)), None
    except FileNotFoundError:
        msg = f"Bestand niet gevonden: {html_path}"
        return None, msg
    except Exception as e:
        msg = f"Fout bij parsen verslagen {html_path}: {e}"
        traceback.print_exc()
        return None, msg

def reports_save_html(html_path, reports_data):
    """Saves the reports data back into the HTML file structure."""
    if not BS4_AVAILABLE: return False, "BeautifulSoup niet beschikbaar"
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
             try: soup = BeautifulSoup(f, 'lxml')
             except Exception: f.seek(0); soup = BeautifulSoup(f, 'html.parser')

        # Find the container div
        reports_section = soup.find('div', id='reports-section')
        if not reports_section:
            msg = "Kan '<div id=\"reports-section\">' niet vinden."
            return False, msg

        # Clear existing content within the div
        reports_section.clear()
        reports_section.append("\n") # Initial newline

        # Iterate through years sorted descending
        for year in sorted(reports_data.keys(), key=int, reverse=True):
            year_reports = reports_data[year]
            # Skip years with no reports
            if not year_reports: continue

            # Create and add H2 for the year
            h2_tag = soup.new_tag('h2')
            h2_tag.string = f"Verslagen {year}"
            reports_section.append(h2_tag)
            reports_section.append("\n")

            # Create and add UL for the reports
            ul_tag = soup.new_tag('ul', attrs={'class': 'report-list'})
            ul_tag.append("\n  ") # Indent
            reports_section.append(ul_tag)
            reports_section.append("\n")

            # Add LI for each report, sorted by text for consistency
            for report in sorted(year_reports, key=lambda x: x.get('text','')):
                li_tag = soup.new_tag('li')
                # Create the link
                a_tag = soup.new_tag('a', href=report['path'], target='_blank')
                a_tag.string = report['text']
                li_tag.append(a_tag)
                ul_tag.append(li_tag)
                ul_tag.append("\n  ") # Indent/newline after li

            # Remove last newline/indent before closing ul
            if ul_tag.contents and isinstance(ul_tag.contents[-1], NavigableString) and not ul_tag.contents[-1].strip():
                ul_tag.contents.pop()
            ul_tag.append("\n")


        # Write the modified HTML
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(soup.prettify(formatter="html5"))
        return True, None # Success
    except FileNotFoundError:
        msg = f"Bestand niet gevonden voor opslaan: {html_path}"
        return False, msg
    except Exception as e:
        msg = f"Fout bij opslaan verslagen naar {html_path}: {e}"
        traceback.print_exc()
        return False, msg

# ==============================================================================
# Trainers & Times Utilities
# ==============================================================================

def trainers_parse_html(html_path):
    """Parses the trainers and times HTML file."""
    if not BS4_AVAILABLE: return None, "BeautifulSoup niet beschikbaar"
    # Initialize with default structure to prevent KeyErrors later
    # Added trainer_category_order to store the sequence of H3/H4 tags
    parsed_data = {
        'times': {},
        'contacts': {'vertrouwenspersoon': {}, 'jeugdcoordinator': {}},
        'trainers': {},
        'trainer_category_order': [] # NEW: Store original category order
        }
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            try: soup = BeautifulSoup(f, 'lxml')
            except Exception: f.seek(0); soup = BeautifulSoup(f, 'html.parser')

        # --- Parse Times Table ---
        table = soup.find('table', class_='training-table')
        if table and table.tbody:
            for row in table.tbody.find_all('tr', recursive=False):
                cells = row.find_all('td', recursive=False)
                if len(cells) == 2:
                    # Use get_text with a separator for category name robustness
                    category_text = cells[0].get_text(separator=' ', strip=True)
                    # Normalize & handling
                    category = category_text.replace(' & ', '&') # Consolidate spaces around &
                    category = ' & '.join(c.strip() for c in category.split('&')) # Ensure single space

                    times_list = []
                    ul = cells[1].find('ul')
                    if ul:
                        for li in ul.find_all('li', recursive=False):
                            day_tag = li.find('strong')
                            day = day_tag.get_text(strip=True).replace(':', '') if day_tag else 'Unknown Day'

                            # Extract time text more carefully
                            time_text_parts = []
                            after_day = False if day_tag else True # Start collecting if no day tag
                            for node in li.contents:
                                if node == day_tag:
                                    after_day = True
                                    continue
                                if after_day and isinstance(node, NavigableString):
                                    part = str(node).strip()
                                    # Stop if we hit the note tag implicitly
                                    if part.startswith('(') and li.find('em'): break
                                    if part: time_text_parts.append(part)
                                elif after_day and isinstance(node, Tag) and node.name != 'em':
                                    # Include text from unexpected tags if needed, but ignore 'em'
                                    part = node.get_text(strip=True)
                                    if part: time_text_parts.append(part)

                            time_text = ' '.join(time_text_parts).strip()

                            note_tag = li.find('em')
                            # Extract note text specifically from the <em> tag
                            note = note_tag.get_text(strip=True).strip('()') if note_tag else None
                            if day != 'Unknown Day' and time_text: # Ensure day and time were found
                                times_list.append({'day': day, 'time': time_text, 'note': note})
                        if times_list: # Only add category if times were found
                            parsed_data['times'][category] = times_list


        # --- Parse Contacts ---
        # Helper function to parse a contact div
        def parse_contact_info(contact_div):
            contact = {'name': '', 'email': '', 'phone': '', 'img': ''}
            if not contact_div: return contact

            name_tag = contact_div.find('strong')
            if name_tag: contact['name'] = name_tag.get_text(strip=True)

            email_tag = contact_div.find('a', href=lambda href: href and href.startswith('mailto:'))
            if email_tag: contact['email'] = email_tag.get_text(strip=True)

            # Find phone number more robustly
            phone_text = ''
            # Look for a 'p' tag containing 'Tel:'
            tel_p = contact_div.find('p', string=re.compile(r'Tel:\s*'))
            if tel_p:
                # Extract text after 'Tel:'
                phone_text = tel_p.get_text(strip=True).replace('Tel:', '').strip()
            else:
                # Fallback regex on the whole div text if specific p tag not found
                 phone_match = re.search(r'Tel:\s*(.*)', contact_div.get_text(), re.IGNORECASE | re.DOTALL)
                 if phone_match: phone_text = phone_match.group(1).strip().split('\n')[0] # Take first line after Tel:

            contact['phone'] = phone_text.replace('–', '').strip() # Clean up dashes

            img_tag = contact_div.find('img')
            if img_tag and img_tag.get('src'): contact['img'] = img_tag['src']
            return contact

        vertrouwens_h2 = soup.find('h2', string=re.compile(r'Vertrouwenspersoon', re.I))
        if vertrouwens_h2:
            v_div = vertrouwens_h2.find_next_sibling('div', class_='person-info')
            parsed_data['contacts']['vertrouwenspersoon'] = parse_contact_info(v_div)

        jeugd_h2 = soup.find('h2', string=re.compile(r'Jeugdco[öo]rdinator', re.I)) # Handle ö or o
        if jeugd_h2:
            j_div = jeugd_h2.find_next_sibling('div', class_='person-info')
            parsed_data['contacts']['jeugdcoordinator'] = parse_contact_info(j_div)


        # --- Parse Trainers ---
        trainers_h2 = soup.find('h2', string=re.compile(r'^\s*Trainers\s*$', re.I))
        if trainers_h2:
            current_h3_category = None
            current_h4_category = None # Track sub-category specifically

            for element in trainers_h2.find_next_siblings():
                if element.name == 'h2': break # Stop at the next main section header

                target_category_for_ul = None # Determine category key before processing UL

                if element.name == 'h3':
                    current_h3_category = element.get_text(strip=True)
                    current_h4_category = None # Reset sub-category
                    target_category_for_ul = current_h3_category
                    # Ensure category exists and add to order list if new
                    parsed_data['trainers'].setdefault(target_category_for_ul, [])
                    if target_category_for_ul not in parsed_data['trainer_category_order']:
                         parsed_data['trainer_category_order'].append(target_category_for_ul)

                elif element.name == 'h4':
                    if current_h3_category: # H4 only makes sense under an H3
                        sub_category_name = element.get_text(strip=True)
                        target_category_for_ul = f"{current_h3_category} - {sub_category_name}"
                        current_h4_category = target_category_for_ul # Update specific h4 tracker
                        # Ensure category exists and add to order list if new
                        parsed_data['trainers'].setdefault(target_category_for_ul, [])
                        if target_category_for_ul not in parsed_data['trainer_category_order']:
                             parsed_data['trainer_category_order'].append(target_category_for_ul)
                    else: # H4 without preceding H3? Handle gracefully
                        target_category_for_ul = element.get_text(strip=True) + " (Geen H3)"
                        current_h4_category = target_category_for_ul
                        current_h3_category = None
                        parsed_data['trainers'].setdefault(target_category_for_ul, [])
                        if target_category_for_ul not in parsed_data['trainer_category_order']:
                             parsed_data['trainer_category_order'].append(target_category_for_ul)

                elif element.name == 'ul':
                    # Use the category determined by the immediately preceding H3/H4
                    # If target_category_for_ul is still None here, it means a UL appeared unexpectedly
                    current_list_category = current_h4_category if current_h4_category else current_h3_category
                    if current_list_category:
                         # Ensure the category key exists (might have been created by h3/h4 already)
                         trainers_list = parsed_data['trainers'].setdefault(current_list_category, [])
                         for li in element.find_all('li', recursive=False):
                            # Extract details carefully from li contents
                            trainer_name = ''
                            trainer_email = ''
                            trainer_phone = ''
                            name_parts = []
                            email_tag = li.find('a', href=lambda href: href and href.startswith('mailto:'))

                            if email_tag:
                                trainer_email = email_tag.get('href').replace('mailto:', '').strip()

                            potential_phone_sep = None
                            for content in li.contents:
                                if content == email_tag: break
                                if isinstance(content, NavigableString):
                                    text = str(content).strip()
                                    if '|' in text and not potential_phone_sep:
                                         parts = text.split('|', 1)
                                         name_parts.append(parts[0].strip())
                                         potential_phone_sep = '|' + parts[1].strip()
                                         break
                                    elif text:
                                        name_parts.append(text)
                                elif isinstance(content, Tag): pass # Ignore other tags for name parts

                            trainer_name = ' '.join(p for p in name_parts if p).rstrip(':').strip()

                            phone_search_text = li.get_text()
                            phone_match = re.search(r'\|\s*([\d\s/]+)\s*$', phone_search_text)
                            if phone_match: trainer_phone = phone_match.group(1).strip()
                            elif potential_phone_sep: trainer_phone = potential_phone_sep.lstrip('|').strip()

                            if trainer_name:
                                trainers_list.append({ # Append to the list for this category
                                    'name': trainer_name,
                                    'email': trainer_email or None,
                                    'phone': trainer_phone or None
                                })
                    # else: No active category for this UL, skip or log warning

        # Clean up empty trainer categories from the dictionary (but keep order list intact)
        parsed_data['trainers'] = {k: v for k, v in parsed_data['trainers'].items() if v}

        return parsed_data, None

    except FileNotFoundError:
        return None, f"Bestand niet gevonden: {html_path}"
    except Exception as e:
        msg = f"Fout bij parsen trainers HTML ({type(e).__name__}): {e}"
        traceback.print_exc() # Print full traceback for debugging
        return None, msg


def trainers_save_html(html_path, data):
    """Saves the trainers and times data back into the HTML file, preserving order."""
    if not BS4_AVAILABLE: return False, "BeautifulSoup niet beschikbaar"
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            try: soup = BeautifulSoup(f, 'lxml')
            except Exception: f.seek(0); soup = BeautifulSoup(f, 'html.parser')

        # --- Save Times ---
        table = soup.find('table', class_='training-table')
        if table and table.tbody:
            # Store original category order from the data dictionary if it exists
            # Fallback to keys (which might be insertion order in newer Pythons)
            time_category_keys = list(data.get('times', {}).keys())

            # Clear existing rows
            for tr in table.tbody.find_all('tr', recursive=False):
                tr.decompose()

            # Add rows from data, maintaining the original order
            for category in time_category_keys: # Iterate using the stored/original key order
                times_list = data.get('times', {}).get(category)
                if not times_list: continue # Skip if category has no times

                new_tr = soup.new_tag('tr')
                new_tr.append("\n     ") # Indentation helper

                # Category Cell
                td_cat = soup.new_tag('td')
                td_cat.append("\n      ")
                cat_parts = category.split(' & ')
                for i, part in enumerate(cat_parts):
                    strong_tag = soup.new_tag('strong')
                    strong_tag.string = part.strip()
                    td_cat.append(strong_tag)
                    if i < len(cat_parts) - 1:
                         td_cat.append(' & ') # Add separator back
                td_cat.append("\n     ")
                new_tr.append(td_cat)
                new_tr.append("\n     ")

                # Times Cell
                td_times = soup.new_tag('td')
                td_times.append("\n      ")
                ul = soup.new_tag('ul')
                ul.append("\n       ") # Indent
                # Sort times by day before saving (internal order within LI doesn't affect table row order)
                for item in sorted(times_list, key=lambda x: x.get('day','')):
                    li = soup.new_tag('li')
                    li.append("\n        ") # Indent
                    strong_day = soup.new_tag('strong')
                    strong_day.string = f"{item['day']}:"
                    li.append(strong_day)
                    # Add space before time, handle potential None
                    li.append(f" {item.get('time', '')}")
                    if item.get('note'):
                        li.append(" ") # Space before note
                        em_note = soup.new_tag('em')
                        em_note.string = f"({item['note']})" # Add parentheses back
                        li.append(em_note)
                    li.append("\n       ") # End li
                    ul.append(li)
                    ul.append("\n       ") # After li
                # Remove last newline/indent before closing ul
                if ul.contents and isinstance(ul.contents[-1], NavigableString) and not ul.contents[-1].strip():
                     ul.contents.pop()
                ul.append("\n      ")
                td_times.append(ul)
                td_times.append("\n     ") # End td
                new_tr.append(td_times)
                new_tr.append("\n    ") # End tr

                table.tbody.append(new_tr)
                table.tbody.append("\n") # After tr

        # --- Save Contacts ---
        # Helper function (no changes needed from previous version)
        def update_contact_info(contact_div, contact_data, soup_instance):
            """Updates contact info within a div, modifying existing elements robustly."""
            if not contact_div or not contact_data: return

            # --- Get existing elements or create placeholders ---
            name_p = contact_div.find('p', recursive=False) # Assume first P is name
            email_p = None
            phone_p = None
            img_tag = contact_div.find('img', recursive=False)

            # Find email P by link structure
            email_a_tag = contact_div.find('a', href=lambda href: href and href.startswith('mailto:'))
            if email_a_tag:
                email_p = email_a_tag.find_parent('p')

            # Find phone P by text content
            for p_tag in contact_div.find_all('p', recursive=False):
                 if p_tag != name_p and p_tag != email_p and "Tel:" in p_tag.get_text():
                      phone_p = p_tag
                      break # Found phone P

            # --- Update/Create Name ---
            name_val = contact_data.get('name', '')
            if name_p:
                 strong_tag = name_p.find('strong')
                 if strong_tag:
                      strong_tag.string = name_val
                 else: # Rebuild if structure invalid
                      name_p.clear(); name_p.append("\n       ")
                      new_strong = soup_instance.new_tag('strong'); new_strong.string = name_val
                      name_p.append(new_strong); name_p.append("\n      ")
            else: # Create name <p>
                 name_p = soup_instance.new_tag('p'); name_p.append("\n       ")
                 new_strong = soup_instance.new_tag('strong'); new_strong.string = name_val
                 name_p.append(new_strong); name_p.append("\n      ")
                 # Insert at the beginning (before img if it exists)
                 if img_tag: img_tag.insert_before(name_p); img_tag.insert_before("\n     ")
                 else: contact_div.insert(0, name_p); contact_div.insert(0, "\n     ")

            # --- Update/Create Email ---
            email_val = contact_data.get('email')
            if email_val: # We want email displayed
                if email_p: # Modify existing email paragraph
                     email_a = email_p.find('a')
                     if email_a: # Modify existing link
                          email_a['href'] = f"mailto:{email_val}"
                          email_a.string = email_val
                     else: # Link missing, rebuild content carefully
                          email_p.clear(); email_p.append("E-mail: ")
                          new_a = soup_instance.new_tag('a', href=f"mailto:{email_val}"); new_a.string = email_val
                          email_p.append(new_a)
                else: # Create new email paragraph
                     email_p = soup_instance.new_tag('p'); email_p.append("E-mail: ")
                     new_a = soup_instance.new_tag('a', href=f"mailto:{email_val}"); new_a.string = email_val
                     email_p.append(new_a)
                     # Ensure name_p is the actual tag, not None
                     if name_p and name_p.parent: name_p.insert_after(email_p); name_p.insert_after("\n     ") # Insert after name
                     else: contact_div.insert(1, email_p); contact_div.insert(1, "\n     ") # Fallback

            else: # We want no email / placeholder
                 if email_p: # Modify existing paragraph
                      email_p.clear(); email_p.append("E-mail: –")

            # --- Update/Create Phone ---
            phone_val = contact_data.get('phone')
            if phone_val: # We want phone displayed
                 if phone_p: # Tag exists, update content
                      phone_p.string = f"Tel: {phone_val}"
                 else: # Tag missing, create and insert
                      phone_p = soup_instance.new_tag('p'); phone_p.string = f"Tel: {phone_val}"
                      # Find the correct insertion point (after name or email p)
                      ref_p = email_p if email_p and email_p.parent else name_p if name_p and name_p.parent else None
                      if ref_p: ref_p.insert_after(phone_p); ref_p.insert_after("\n     ")
                      else: contact_div.insert(2, phone_p); contact_div.insert(2, "\n     ") # Fallback

            else: # We want no phone / placeholder
                 if phone_p: # Modify existing paragraph
                      phone_p.string = "Tel: –"

            # --- Update Image ---
            img_val = contact_data.get('img')
            name_val = contact_data.get('name', 'Persoon')
            if img_tag:
                 img_tag['src'] = img_val if img_val else '/images/personen/trainer-leeg.png'
                 img_tag['alt'] = f"Foto {name_val}"
            elif img_val: # Add img tag if missing
                 img_tag = soup_instance.new_tag('img', src=img_val, alt=f"Foto {name_val}")
                 contact_div.append("\n     "); contact_div.append(img_tag)


        vertrouwens_data = data.get('contacts', {}).get('vertrouwenspersoon')
        if vertrouwens_data:
            vertrouwens_h2 = soup.find('h2', string=re.compile(r'Vertrouwenspersoon', re.I))
            if vertrouwens_h2:
                v_div = vertrouwens_h2.find_next_sibling('div', class_='person-info')
                if v_div: update_contact_info(v_div, vertrouwens_data, soup) # Pass soup

        jeugd_data = data.get('contacts', {}).get('jeugdcoordinator')
        if jeugd_data:
            jeugd_h2 = soup.find('h2', string=re.compile(r'Jeugdco[öo]rdinator', re.I))
            if jeugd_h2:
                j_div = jeugd_h2.find_next_sibling('div', class_='person-info')
                if j_div: update_contact_info(j_div, jeugd_data, soup) # Pass soup


        # --- Save Trainers ---
        trainers_h2 = soup.find('h2', string=re.compile(r'^\s*Trainers\s*$', re.I))
        if trainers_h2:
             # Remove existing h3/h4/ul sections after Trainers H2 more carefully
             elements_to_remove = []
             current_element = trainers_h2.find_next_sibling()
             while current_element:
                 next_sibling = current_element.find_next_sibling() # Get next before potential removal
                 if current_element.name == 'h2': break # Stop at next section
                 # Remove H3, H4, UL and whitespace nodes between them
                 if current_element.name in ['h3', 'h4', 'ul'] or \
                    (isinstance(current_element, NavigableString) and not str(current_element).strip()):
                     elements_to_remove.append(current_element)
                 current_element = next_sibling

             for elem in elements_to_remove:
                 if elem and elem.parent: # Check if it hasn't been removed already
                    elem.decompose()

             # Add new h3/h4/ul sections based on data, USING THE STORED ORDER
             last_element_inserted = trainers_h2
             main_category_written = None # Track the last H3 written

             # Use the stored category order if available, otherwise fallback (less ideal)
             category_order = data.get('trainer_category_order', sorted(data.get('trainers', {}).keys()))

             for category in category_order: # Iterate using the stored/retrieved order
                 trainers_list = data.get('trainers', {}).get(category) # Use .get for safety
                 if not trainers_list: continue # Skip empty/missing categories

                 # Check if it's a sub-category
                 if ' - ' in category:
                     parts = category.split(' - ', 1)
                     current_main_category = parts[0]
                     sub_category_name = parts[1]
                     # Add H3 only if it's a new main category being encountered
                     if current_main_category != main_category_written:
                         h3_tag = soup.new_tag('h3'); h3_tag.string = current_main_category
                         last_element_inserted.insert_after(h3_tag); last_element_inserted.insert_after("\n   ")
                         last_element_inserted = h3_tag
                         main_category_written = current_main_category # Update tracker
                     # Add H4 for the sub-category
                     h4_tag = soup.new_tag('h4'); h4_tag.string = sub_category_name
                     last_element_inserted.insert_after(h4_tag); last_element_inserted.insert_after("\n   ")
                     last_element_inserted = h4_tag
                 else: # It's a main category
                     h3_tag = soup.new_tag('h3'); h3_tag.string = category
                     last_element_inserted.insert_after(h3_tag); last_element_inserted.insert_after("\n   ")
                     last_element_inserted = h3_tag
                     main_category_written = category # Update tracker

                 # Add the UL for the current category/sub-category
                 ul = soup.new_tag('ul')
                 ul.append("\n    ") # Indent
                 # Iterate through trainers IN THE ORDER THEY ARE STORED (don't sort here)
                 for trainer in trainers_list:
                     li = soup.new_tag('li')
                     li.append("\n     ") # Indent
                     # Add name directly
                     li.append(trainer['name'])
                     if trainer.get('email'):
                         li.append(': ')
                         a_tag = soup.new_tag('a', href=f"mailto:{trainer['email']}")
                         a_tag.string = trainer['email']
                         li.append(a_tag)
                     if trainer.get('phone'):
                         li.append(f" | {trainer['phone']}") # Add separator
                     li.append("\n    ") # End li
                     ul.append(li)
                     ul.append("\n    ") # After li
                 # Remove last newline/indent before closing ul
                 if ul.contents and isinstance(ul.contents[-1], NavigableString) and not ul.contents[-1].strip():
                     ul.contents.pop()
                 ul.append("\n   ")
                 last_element_inserted.insert_after(ul); last_element_inserted.insert_after("\n  ") # Less indent after ul
                 last_element_inserted = ul


        # Save the modified soup
        with open(html_path, 'w', encoding='utf-8') as f:
            # Use html5 formatter for better output control
            f.write(soup.prettify(formatter="html5"))
        return True, None

    except FileNotFoundError:
        return False, f"Bestand niet gevonden: {html_path}"
    except Exception as e:
        msg = f"Fout bij opslaan trainers HTML ({type(e).__name__}): {e}"
        traceback.print_exc() # Print detailed traceback
        return False, msg


# ==============================================================================
# General HTML / Text / Image Utilities
# ==============================================================================

def general_html_find_files(targets_abs):
    """Finds all HTML files within specified target paths (files or directories)."""
    html_files = set()
    for target_path in targets_abs:
        if not os.path.exists(target_path): continue
        if os.path.isfile(target_path):
            # If it's a file, check if it's HTML
            if target_path.lower().endswith(('.html', '.htm')):
                html_files.add(target_path)
        elif os.path.isdir(target_path):
            # If it's a directory, walk through it
            for root, _, files in os.walk(target_path):
                for filename in files:
                    if filename.lower().endswith(('.html', '.htm')):
                        full_path = os.path.join(root, filename)
                        html_files.add(full_path)
    # Return sorted list and count
    return sorted(list(html_files)), len(html_files)

def text_editor_parse_file(file_path, parsed_soups_dict, found_texts_list):
    """Parses an HTML file to find editable text snippets."""
    if not BS4_AVAILABLE: return 0
    texts_in_file = 0; total_texts_so_far = len(found_texts_list)
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
        # Parse with lxml fallback to html.parser
        try: soup = BeautifulSoup(content, 'lxml')
        except Exception:
            try: soup = BeautifulSoup(content, 'html.parser')
            except Exception as parse_err:
                print(f"[UTILS][TEXT] Kon {file_path} niet parsen: {parse_err}")
                return 0 # Cannot parse

        # Store the parsed soup object for potential reuse (e.g., by image parser)
        parsed_soups_dict[file_path] = soup

        # Find all text nodes
        for text_node in soup.find_all(string=True):
            parent_tag = text_node.parent
            # Skip text inside excluded tags (like <script>, <style>)
            if parent_tag and parent_tag.name in config.TEXT_EDITOR_EXCLUDED_TAGS: continue
            # Skip comments
            if isinstance(text_node, Comment): continue
            # Get stripped text content
            original_text = str(text_node).strip()
            # Skip empty text nodes
            if not original_text: continue

            # Assign unique ID based on order found
            iid = total_texts_so_far + texts_in_file
            # Create display text (truncated and cleaned)
            display_text = (original_text[:100] + '...') if len(original_text) > 100 else original_text
            display_text = display_text.replace('\n', ' ').replace('\r', '')

            # Add found text data to the list
            found_texts_list.append({
                'file_path': file_path,        # Path to the HTML file
                'original_text': str(text_node), # The raw text, including original whitespace
                'dom_reference': text_node,    # Direct reference to the bs4 text node
                'display_text': display_text,  # Cleaned text for display
                'iid': iid                     # Unique ID for the Treeview
            })
            texts_in_file += 1
        return texts_in_file
    except FileNotFoundError: return 0
    except Exception as e:
        print(f"[UTILS][TEXT] Fout bij verwerken {file_path}: {e}")
        traceback.print_exc(); return 0

def images_parse_file(file_path, parsed_soups_dict, found_images_list):
    """Parses an HTML file to find local image references."""
    if not BS4_AVAILABLE: return 0
    images_in_file = 0; total_images_so_far = len(found_images_list)
    try:
        # Reuse parsed soup if available from text editor scan
        if file_path in parsed_soups_dict:
            soup = parsed_soups_dict[file_path]
        else:
            # Otherwise, parse the file now
            with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
            try: soup = BeautifulSoup(content, 'lxml')
            except Exception:
                try: soup = BeautifulSoup(content, 'html.parser')
                except Exception as parse_err:
                    print(f"[UTILS][IMG] Kon {file_path} niet parsen: {parse_err}")
                    return 0
            # Store the newly parsed soup
            parsed_soups_dict[file_path] = soup

        # Find all <img> tags with a 'src' attribute
        for img_tag in soup.find_all('img', src=True):
            src_attr = img_tag['src'].strip()
            # Skip empty, data URIs, or external URLs
            if not src_attr or src_attr.startswith(('data:', 'http:', 'https:')):
                continue

            # Assign unique ID
            iid = total_images_so_far + images_in_file

            # Resolve the absolute path and check existence
            img_abs_path = "Error Resolving Path"
            exists = False
            try:
                # Make path relative to APP_BASE_DIR
                # Handle paths starting with / correctly relative to base dir
                relative_src_path = src_attr.lstrip('/')
                img_abs_path = os.path.abspath(os.path.join(config.APP_BASE_DIR, relative_src_path))
                exists = os.path.isfile(img_abs_path)
            except Exception as path_err:
                print(f"[UTILS][IMG] Fout bij oplossen pad '{src_attr}' in {file_path}: {path_err}")

            # Add image data to the list
            found_images_list.append({
                'html_file': file_path,     # HTML file where the image is used
                'src': src_attr,            # Original src attribute value
                'dom_reference': img_tag,   # Reference to the bs4 <img> tag
                'abs_path': img_abs_path,   # Resolved absolute path
                'exists': exists,           # Whether the file exists
                'iid': iid                  # Unique ID for the Treeview (if needed per instance)
            })
            images_in_file += 1
        return images_in_file
    except FileNotFoundError: return 0
    except Exception as e:
        print(f"[UTILS][IMG] Fout bij verwerken {file_path}: {e}")
        traceback.print_exc(); return 0
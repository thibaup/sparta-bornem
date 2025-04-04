import os
import sys
import pathlib

if getattr(sys, 'frozen', False):
    APP_BASE_DIR = os.path.dirname(sys.executable)
elif __file__:
    APP_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
else:
    APP_BASE_DIR = os.getcwd()

NEWS_JSON_RELATIVE_PATH = os.path.join('html', 'nieuws', 'nieuws-data.json')
NEWS_JSON_FILE_PATH = os.path.join(APP_BASE_DIR, NEWS_JSON_RELATIVE_PATH)
NEWS_IMAGE_DEST_DIR_RELATIVE = os.path.join('images', 'nieuws')
NEWS_IMAGE_DEST_DIR_ABSOLUTE = os.path.join(APP_BASE_DIR, NEWS_IMAGE_DEST_DIR_RELATIVE)
NEWS_DEFAULT_CATEGORY = "Algemeen"
NEWS_DEFAULT_IMAGE = "nieuws-beeld.png"

RECORDS_BASE_DIR_RELATIVE = os.path.join('html', 'clubrecords')
RECORDS_BASE_DIR_ABSOLUTE = os.path.join(APP_BASE_DIR, RECORDS_BASE_DIR_RELATIVE)

CALENDAR_HTML_RELATIVE_PATH = os.path.join('html', 'wedstrijden', 'kalender.html')
CALENDAR_HTML_FILE_PATH = os.path.join(APP_BASE_DIR, CALENDAR_HTML_RELATIVE_PATH)
CALENDAR_EVENT_COLORS = ["green", "blue", "red", "black"]
DUTCH_MONTH_MAP = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12
}

REPORTS_HTML_RELATIVE_PATH = os.path.join('html', 'downloads', 'bestuursverslagen.html')
REPORTS_HTML_FILE_PATH = os.path.join(APP_BASE_DIR, REPORTS_HTML_RELATIVE_PATH)
REPORTS_DOCS_HREF_DIR_RELATIVE = '/docs/bestuursvergadering'
REPORTS_DOCS_DEST_DIR_ABSOLUTE = os.path.join(APP_BASE_DIR, 'docs', 'bestuursvergadering')

TRAINERS_HTML_RELATIVE_PATH = os.path.join('html', 'info', 'training.html') # Adjusted path as per user HTML
TRAINERS_HTML_FILE_PATH = os.path.join(APP_BASE_DIR, TRAINERS_HTML_RELATIVE_PATH)

HTML_SCAN_TARGET_PATHS_RELATIVE = [
    'index.html',
    os.path.join('html'),
]
HTML_SCAN_TARGET_PATHS_ABSOLUTE = [os.path.join(APP_BASE_DIR, p) for p in HTML_SCAN_TARGET_PATHS_RELATIVE]

TEXT_EDITOR_EXCLUDED_TAGS = ['script', 'style']

IMAGE_PREVIEW_MAX_WIDTH = 300
IMAGE_PREVIEW_MAX_HEIGHT = 250
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
    str(pathlib.Path(p).as_posix()): os.path.join(APP_BASE_DIR, p)
    for p in IMAGE_COMMON_DIRS_RELATIVE
}

# Print config for verification during startup (optional but helpful)
print(f"[CONFIG] APP_BASE_DIR: {APP_BASE_DIR}")
print(f"[CONFIG] Nieuws JSON: {NEWS_JSON_FILE_PATH}")
print(f"[CONFIG] Nieuws Afbeeldingen: {NEWS_IMAGE_DEST_DIR_ABSOLUTE}")
print(f"[CONFIG] Records Basis: {RECORDS_BASE_DIR_ABSOLUTE}")
print(f"[CONFIG] Kalender HTML: {CALENDAR_HTML_FILE_PATH}")
print(f"[CONFIG] Verslagen HTML: {REPORTS_HTML_FILE_PATH}")
print(f"[CONFIG] Verslagen Docs: {REPORTS_DOCS_DEST_DIR_ABSOLUTE}")
print(f"[CONFIG] Trainers HTML: {TRAINERS_HTML_FILE_PATH}")
print(f"[CONFIG] HTML Scan Doelen: {HTML_SCAN_TARGET_PATHS_ABSOLUTE}")
print(f"[CONFIG] Afbeelding Mappen: {IMAGE_COMMON_DIRS_ABSOLUTE}")
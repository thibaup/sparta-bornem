import os
import sys
import pathlib
import re


# Determine APP_BASE_DIR
if getattr(sys, 'frozen', False):
    app_base_dir_temp = os.path.dirname(sys.executable)
elif __file__:
    app_base_dir_temp = os.path.dirname(os.path.abspath(__file__))
else:
    app_base_dir_temp = os.getcwd()
APP_BASE_DIR = app_base_dir_temp


def sanitize_for_path(name):
    """Sanitizes a string to be safe for use in filenames or paths."""
    if name is None: return ""
    name_str = str(name).lower()
    name_str = re.sub(r'\s+', '_', name_str)
    name_str = re.sub(r'[^\w\-.]', '', name_str)
    return name_str[:50]


APP_VERSION = "1.5.2.0"
UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/thibaup/sparta-bornem/main/update.json"
FALLBACK_UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/thibaup/sparta-bornem/main/update.json"
DEBUG_UPDATER = False

GIT_TARGET_BRANCH = "main"
GIT_STASH_EXCLUDES = ["ThibertaWebsiteEditor-*.exe", "update.json", ".editor-recovery/"]

DEV_UPDATE_TARGET = r""


# --- News ---
NEWS_JSON_RELATIVE_PATH = os.path.join('html', 'nieuws', 'nieuws-data.json')
NEWS_JSON_FILE_PATH = os.path.join(APP_BASE_DIR, NEWS_JSON_RELATIVE_PATH)
NEWS_IMAGE_DEST_DIR_RELATIVE = os.path.join('images', 'nieuws') # Defined here
NEWS_IMAGE_DEST_DIR_ABSOLUTE = os.path.join(APP_BASE_DIR, NEWS_IMAGE_DEST_DIR_RELATIVE)
NEWS_DEFAULT_CATEGORY = "Algemeen"
NEWS_PLACEHOLDER_IMAGE = "placeholder-news.png"
NEWS_DEFAULT_IMAGE = NEWS_PLACEHOLDER_IMAGE
NEWS_PLACEHOLDER_IMAGE_PATH_REL = os.path.join(NEWS_IMAGE_DEST_DIR_RELATIVE, NEWS_PLACEHOLDER_IMAGE)
NEWS_PLACEHOLDER_IMAGE_HREF = f"/{str(pathlib.Path(NEWS_IMAGE_DEST_DIR_RELATIVE).as_posix())}/{NEWS_PLACEHOLDER_IMAGE}"

# --- Records ---
RECORDS_BASE_DIR_RELATIVE = os.path.join('html', 'clubrecords')
RECORDS_BASE_DIR_ABSOLUTE = os.path.join(APP_BASE_DIR, RECORDS_BASE_DIR_RELATIVE)
RECORDS_JSON_PATH = os.path.join(RECORDS_BASE_DIR_ABSOLUTE, 'records.json')


KALENDER_JSON_RELATIVE_PATH = os.path.join('html', 'wedstrijden', 'json', 'kalender.json')
KALENDER_JSON_FILE_PATH = os.path.join(APP_BASE_DIR, KALENDER_JSON_RELATIVE_PATH)
CALENDAR_EVENT_COLORS = ["green", "blue", "red", "black"]
DUTCH_MONTH_MAP = {
    'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12
}
MONTH_MAP_NL_FULL = {
    1: "Januari", 2: "Februari", 3: "Maart", 4: "April", 5: "Mei", 6: "Juni",
    7: "Juli", 8: "Augustus", 9: "September", 10: "Oktober", 11: "November", 12: "December"
}
DAYS_ORDER = {
    'Maandag': 0, 'Dinsdag': 1, 'Woensdag': 2, 'Donderdag': 3,
    'Vrijdag': 4, 'Zaterdag': 5, 'Zondag': 6
}

# --- Reports ---
REPORTS_HTML_RELATIVE_PATH = os.path.join('html', 'downloads', 'bestuursverslagen.html')
REPORTS_HTML_FILE_PATH = os.path.join(APP_BASE_DIR, REPORTS_HTML_RELATIVE_PATH)
REPORTS_DOCS_DEST_DIR_ABSOLUTE = os.path.join(APP_BASE_DIR, 'docs', 'bestuursvergadering')
_reports_docs_dest_rel_pathobj = pathlib.Path(os.path.relpath(REPORTS_DOCS_DEST_DIR_ABSOLUTE, APP_BASE_DIR))
REPORTS_DOCS_HREF_DIR_RELATIVE = '/' + _reports_docs_dest_rel_pathobj.as_posix()


# --- Trainers (JSON based) ---
TRAINERS_JSON_RELATIVE_PATH = os.path.join('html', 'info', 'json', 'trainers.json')
TRAINERS_JSON_FILE_PATH = os.path.join(APP_BASE_DIR, TRAINERS_JSON_RELATIVE_PATH)

TRAINER_GROUP_IMG_HREF_BASE = '/images/personen/groups'
TRAINER_GROUP_IMG_DIR_RELATIVE = TRAINER_GROUP_IMG_HREF_BASE.lstrip('/') # Defined here
TRAINER_GROUP_IMG_DIR_ABSOLUTE = os.path.join(APP_BASE_DIR, TRAINER_GROUP_IMG_DIR_RELATIVE)

DEFAULT_TRAINER_GROUP_MAIN_IMG_TEMPLATE = "{category_name_sanitized}_main.jpg"
DEFAULT_TRAINER_GROUP_MAIN_IMG_ALT_TEMPLATE = "Foto {category_name}"
DEFAULT_TRAINER_GROUP_THUMB_TEMPLATE = "{category_name_sanitized}_thumb{index}.jpg"
DEFAULT_TRAINER_GROUP_THUMB_ALT_TEMPLATE = "{category_name} Actie {index}"
DEFAULT_TRAINER_GROUP_THUMB_COUNT = 5
DEFAULT_TRAINER_GROUP_MAIN_IMG_SRC = "/images/personen/placeholder_group_main.jpg"

# --- Contacts (related to Trainers JSON) ---
CONTACTS_IMG_DIR_REL = os.path.join('images', 'personen', 'contacts') # Defined here
CONTACTS_IMG_DIR_ABS = os.path.join(APP_BASE_DIR, CONTACTS_IMG_DIR_REL)
CONTACTS_IMG_HREF_BASE = '/images/personen/contacts'
DEFAULT_CONTACT_IMG_SRC = "/images/personen/trainer-leeg.png"

# --- Sponsors ---
SPONSOR_CATEGORIES = {
    "Hoofdsponsors": {
        "html_path_rel": os.path.join('html', 'info', 'hoofdsponsors.html'),
        "img_dir_rel": os.path.join('images', 'sponsers', 'hoofdsponsers'),
        "img_href_base": '/images/sponsers/hoofdsponsers'
    },
    "Grote Sponsors": {
        "html_path_rel": os.path.join('html', 'info', 'grotesponsors.html'),
        "img_dir_rel": os.path.join('images', 'sponsers', 'grote sponsers'),
        "img_href_base": '/images/sponsers/grote sponsers'
    },
    "Sponsors": {
        "html_path_rel": os.path.join('html', 'info', 'sponsors.html'),
        "img_dir_rel": os.path.join('images', 'sponsers', 'sponsers'),
        "img_href_base": '/images/sponsers/sponsers'
    }
}
for cat_info in SPONSOR_CATEGORIES.values():
    cat_info["html_path_abs"] = os.path.join(APP_BASE_DIR, cat_info["html_path_rel"])
    cat_info["img_dir_abs"] = os.path.join(APP_BASE_DIR, cat_info["img_dir_rel"])


BESTUUR_HTML_RELATIVE_PATH_OLD = os.path.join('html', 'info', 'bestuur.html')
BESTUUR_HTML_FILE_PATH_OLD = os.path.join(APP_BASE_DIR, BESTUUR_HTML_RELATIVE_PATH_OLD)

BESTUUR_JSON_RELATIVE_PATH = os.path.join('html', 'info', 'json', 'bestuur.json')
BESTUUR_JSON_FILE_PATH = os.path.join(APP_BASE_DIR, BESTUUR_JSON_RELATIVE_PATH)

BESTUUR_IMAGE_DEST_DIR_RELATIVE = os.path.join('images', 'personen', 'bestuur')
BESTUUR_IMAGE_DEST_DIR_ABSOLUTE = os.path.join(APP_BASE_DIR, BESTUUR_IMAGE_DEST_DIR_RELATIVE)
BESTUUR_IMAGE_HREF_BASE = '/' + pathlib.PurePosixPath(BESTUUR_IMAGE_DEST_DIR_RELATIVE).as_posix() + '/'
DEFAULT_BESTUUR_IMAGE_SRC = '/images/personen/trainer-leeg.png'

JURY_JSON_RELATIVE_PATH = os.path.join('html', 'info', 'json', 'juryleden.json')
JURY_JSON_FILE_PATH = os.path.join(APP_BASE_DIR, JURY_JSON_RELATIVE_PATH)

JURY_IMAGE_DEST_DIR_RELATIVE = os.path.join('images', 'personen', 'jury')
JURY_IMAGE_DEST_DIR_ABSOLUTE = os.path.join(APP_BASE_DIR, JURY_IMAGE_DEST_DIR_RELATIVE)
JURY_IMAGE_HREF_BASE = '/' + pathlib.PurePosixPath(JURY_IMAGE_DEST_DIR_RELATIVE).as_posix() + '/'
DEFAULT_JURY_IMAGE_SRC = '/images/personen/trainer-leeg.png'


# --- Ages ---
AGES_HTML_RELATIVE_PATH = os.path.join('html', '(Nieuwe) leden', 'leeftijden.html')
AGES_HTML_FILE_PATH = os.path.join(APP_BASE_DIR, AGES_HTML_RELATIVE_PATH)

# --- FAQ ---
FAQ_JSON_RELATIVE_PATH = os.path.join('html', '(Nieuwe) leden', 'faq-data.json')
FAQ_JSON_FILE_PATH = os.path.join(APP_BASE_DIR, FAQ_JSON_RELATIVE_PATH)

# --- Images page ---
IMAGES_JSON_RELATIVE_PATH = os.path.join('html', 'images', 'images-data.json')
IMAGES_JSON_FILE_PATH = os.path.join(APP_BASE_DIR, IMAGES_JSON_RELATIVE_PATH)
IMAGES_ASSET_DIR_RELATIVE = os.path.join('images', 'images')
IMAGES_ASSET_DIR_ABSOLUTE = os.path.join(APP_BASE_DIR, IMAGES_ASSET_DIR_RELATIVE)
IMAGES_ASSET_HREF_BASE = '/' + pathlib.Path(IMAGES_ASSET_DIR_RELATIVE).as_posix()
IMAGES_MAX_FILE_BYTES = 2 * 1024 * 1024
IMAGES_MAX_DIMENSION = 2400
IMAGES_SUPPORTED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tif', '.tiff', '.svg')

# --- General HTML Scanning & Editing ---
HTML_SCAN_TARGET_PATHS_RELATIVE = ['index.html', 'html']
HTML_SCAN_TARGET_PATHS_ABSOLUTE = [os.path.join(APP_BASE_DIR, p) for p in HTML_SCAN_TARGET_PATHS_RELATIVE]
TEXT_EDITOR_EXCLUDED_TAGS = ['script', 'style', 'head', 'header', 'footer', 'nav']

# --- Image & PDF Utilities ---
IMAGE_PREVIEW_MAX_WIDTH = 300
IMAGE_PREVIEW_MAX_HEIGHT = 250

# Define all image directory relative paths BEFORE they are used in IMAGE_COMMON_DIRS_RELATIVE
_image_common_dirs_relative_set = {
    'images',
    os.path.join('images', 'pagina'),
    os.path.join('images', 'sponsers'),
    NEWS_IMAGE_DEST_DIR_RELATIVE,
    IMAGES_ASSET_DIR_RELATIVE,
    os.path.join('images', 'personen'),
    BESTUUR_IMAGE_DEST_DIR_RELATIVE,
    JURY_IMAGE_DEST_DIR_RELATIVE,
    CONTACTS_IMG_DIR_REL,
    TRAINER_GROUP_IMG_DIR_RELATIVE,
}

for cat_info in SPONSOR_CATEGORIES.values():
    _image_common_dirs_relative_set.add(cat_info["img_dir_rel"])

IMAGE_COMMON_DIRS_RELATIVE = sorted(list(filter(None, _image_common_dirs_relative_set)))

IMAGE_COMMON_DIRS_ABSOLUTE = {
    str(pathlib.Path(p).as_posix()): os.path.join(APP_BASE_DIR, p.replace('/', os.sep))
    for p in IMAGE_COMMON_DIRS_RELATIVE
}
IMAGE_PATH_RESOLVE_ERROR_MARKER = "Fout bij Oplossen Pad"

# PDF variables
_reports_docs_rel_path_for_pdf_common_obj = pathlib.Path(os.path.relpath(REPORTS_DOCS_DEST_DIR_ABSOLUTE, APP_BASE_DIR)) # Renamed object
REPORTS_DOCS_DEST_DIR_RELATIVE_FOR_PDF_LIST = _reports_docs_rel_path_for_pdf_common_obj.as_posix() # Variable to use in list
DOWNLOADS_HTML_FILE_PATH = os.path.join(APP_BASE_DIR, 'html', 'downloads', 'downloads.html')
DOWNLOADS_DOCS_DEST_DIR_ABSOLUTE = os.path.join(APP_BASE_DIR, 'docs')
DOWNLOADS_DOCS_HREF_DIR_RELATIVE = '/docs'


PDF_PREVIEW_MAX_WIDTH = 300
PDF_PREVIEW_MAX_HEIGHT = 400

PDF_COMMON_DIRS_RELATIVE = list(set([
    'docs',
    REPORTS_DOCS_DEST_DIR_RELATIVE_FOR_PDF_LIST, # Using the explicitly defined variable
]))
PDF_COMMON_DIRS_ABSOLUTE = {
    p: os.path.join(APP_BASE_DIR, p.replace('/', os.sep))
    for p in PDF_COMMON_DIRS_RELATIVE if p
}
PDF_PATH_RESOLVE_ERROR_MARKER = "PDF Pad Resolutie Fout"

# --- General App Settings ---
HEADER_FILE_PATH = os.path.join(APP_BASE_DIR, "_header.html")
REPO_URL = "https://github.com/thibaup/sparta-bornem"
GIT_TARGET_BRANCH = 'main'


print("-" * 20)
print("Configuration Loaded")
print(f"APP_BASE_DIR: {APP_BASE_DIR}")
print(f"News JSON Path: {NEWS_JSON_FILE_PATH}")
print(f"Trainers JSON Path: {TRAINERS_JSON_FILE_PATH}")
print(f"Bestuur JSON Path: {BESTUUR_JSON_FILE_PATH}")
print("-" * 20)

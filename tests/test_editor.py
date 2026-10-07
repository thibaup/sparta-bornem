"""Editor regression checks. Writes and Git operations use isolated temp folders."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bs4 import BeautifulSoup
from PIL import Image
import config
import utils
from app import WebsiteEditorApp, PreviewManager
from tabs.calendar_tab import MonthManagerDialog
from tabs.bestuur_tab import BestuurTab, JuryTab
from tabs.documents_tab import DocumentsTab
from tabs.faq_tab import FaqDialog, FaqTab
from tabs.images_tab import ImagesTab
from tabs.media_manager_tab import MediaManagerTab
from tabs.news_tab import NewsTab
from tabs.sponsors_tab import SponsorsTab
from tabs.text_editor_tab import TextEditorTab
from tabs.trainers_tab import TrainersTab, GroupImageManagerDialog


class FileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='editor-regression-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def test_failed_writes_and_copies_preserve_originals(self):
        target = self.base / 'saved.txt'
        target.write_text('original', encoding='utf-8')
        with self.assertRaises(RuntimeError):
            with utils.atomic_text_writer(target) as file:
                file.write('partial')
                raise RuntimeError('simulated interruption')
        self.assertEqual(target.read_text(encoding='utf-8'), 'original')
        with patch('utils.os.replace', side_effect=PermissionError('locked')):
            with self.assertRaises(PermissionError):
                utils.atomic_write_text(target, 'replacement')
        source = self.base / 'source.txt'
        source.write_text('new', encoding='utf-8')
        def broken_copy(source, destination):
            Path(destination).write_bytes(b'partial')
            raise OSError('disk full')
        with patch('utils.shutil.copy2', side_effect=broken_copy):
            with self.assertRaises(OSError):
                utils.atomic_copy_file(source, target)
        self.assertEqual(target.read_text(encoding='utf-8'), 'original')
        self.assertFalse(list(self.base.glob('.*.tmp')))

    def test_duplicate_asset_names_never_overwrite_existing_content(self):
        source = self.base / 'source' / 'photo.jpg'
        source.parent.mkdir()
        source.write_bytes(b'new photo')
        target = self.base / 'uploads' / 'photo.jpg'
        target.parent.mkdir()
        target.write_bytes(b'existing photo')
        first = Path(utils.copy_new_asset(source, target))
        second = Path(utils.copy_new_asset(source, target))
        self.assertEqual(target.read_bytes(), b'existing photo')
        self.assertEqual(first.name, 'photo_1.jpg')
        self.assertEqual(second.name, 'photo_2.jpg')
        self.assertEqual(first.read_bytes(), b'new photo')
        self.assertEqual(Path(utils.copy_new_asset(target, target)), target)

    def test_calendar_save_leaves_event_indices_and_dirty_state_unchanged(self):
        data = {'events': [{'date': '2026-12-01', 'name': 'late'}, {'date': '2026-01-01', 'name': 'early'}]}
        original = copy.deepcopy(data)
        self.assertIsNone(utils.kalender_save_json_data(self.base / 'calendar.json', data))
        self.assertEqual(data, original)
        saved = json.loads((self.base / 'calendar.json').read_text(encoding='utf-8'))
        self.assertEqual([event['name'] for event in saved['events']], ['early', 'late'])

    def test_invalid_json_schemas_are_rejected_without_rewriting_files(self):
        samples = [
            (utils.images_gallery_load_json_data, {'folders': 'wrong'}),
            (utils.images_gallery_load_json_data, {'folders': [{'id': '../outside', 'images': []}]}),
            (utils.images_gallery_load_json_data, {'folders': [{'id': 'same'}, {'id': 'same'}]}),
            (utils.kalender_load_json_data, []),
            (utils.kalender_load_json_data, {'events': ['wrong']}),
            (utils.kalender_load_json_data, {'events': [], 'displayedMonths': [[2026, 13]]}),
            (utils.news_load_existing_data, [{'id': 'same'}, {'id': 'same'}]),
            (utils.trainers_load_json_data, {'trainerGroups': 'wrong'}),
            (utils.trainers_load_json_data, {'contacts': [{'role': 'same'}, {'role': 'same'}]}),
            (utils.bestuur_load_json_data, {'boardMembers': ['wrong']}),
            (utils.jury_load_json_data, []),
        ]
        for loader, data in samples:
            with self.subTest(loader=loader.__name__, data=data):
                path = self.base / 'invalid.json'
                text = json.dumps(data)
                path.write_text(text, encoding='utf-8')
                _, error = loader(path)
                self.assertTrue(error)
                self.assertEqual(path.read_text(encoding='utf-8'), text)

    def test_local_urls_resolve_relative_to_html_and_reject_escaping_paths(self):
        page = self.base / 'html' / 'page.html'
        page.parent.mkdir()
        image = self.base / 'images' / 'photo.png'
        image.parent.mkdir()
        image.write_bytes(b'image')
        with patch.object(config, 'APP_BASE_DIR', str(self.base)):
            self.assertEqual(utils.resolve_site_path('../images/photo.png?v=2#preview', page), str(image))
            self.assertEqual(utils.resolve_site_path('/images/photo.png'), str(image))
            for bad in ('../../outside', '/../../outside', '//example.com/a', 'https://example.com/a', 'C:/outside'):
                with self.subTest(path=bad), self.assertRaises(ValueError):
                    utils.resolve_site_path(bad)

    def test_image_scans_refresh_dom_and_resolve_relative_paths(self):
        page = self.base / 'html' / 'page.html'
        page.parent.mkdir()
        cache, found = {}, []
        with patch.object(config, 'APP_BASE_DIR', str(self.base)):
            page.write_text('<img src="../images/a.png?v=1">', encoding='utf-8')
            utils.images_parse_file(str(page), cache, found)
            self.assertEqual(found[0]['abs_path'], str(self.base / 'images' / 'a.png'))
            page.write_text('<img src="../images/b.png">', encoding='utf-8')
            fresh = []
            utils.images_parse_file(str(page), cache, fresh)
            self.assertEqual(fresh[0]['src'], '../images/b.png')

    def test_age_row_edits_preserve_introduction_markup(self):
        page = self.base / 'ages.html'
        page.write_text('<html><body><p>Season <strong>2026-2027</strong> <a href="/join">join</a></p>'
                        '<table class="age-table"><tbody><tr><td>Junior</td><td>2007</td></tr></tbody></table></body></html>', encoding='utf-8')
        rows, text, error = utils.ages_parse_html(page)
        self.assertIsNone(error)
        before = str(BeautifulSoup(page.read_text(encoding='utf-8'), 'html.parser').p)
        rows[0]['years'] = '2008'
        success, error = utils.ages_save_html(page, rows, text)
        self.assertTrue(success, error)
        self.assertEqual(str(BeautifulSoup(page.read_text(encoding='utf-8'), 'html.parser').p), before)

    def test_sponsor_roundtrip_preserves_picture_attributes_and_other_grid_content(self):
        page = self.base / 'sponsors.html'
        page.write_text('<html><body><div class="sponsor-grid"><h2>Supporters</h2>'
                        '<div class="sponsor-item custom" data-owner="club"><a href="/old" aria-label="Sponsor">'
                        '<picture><source srcset="/a.webp" type="image/webp"><img src="/a.jpg" alt="A" loading="lazy"></picture>'
                        '<span>Caption</span></a></div></div></body></html>', encoding='utf-8')
        sponsors, error = utils.sponsors_parse_html(page)
        self.assertIsNone(error)
        sponsors[0]['alt'] = 'Changed'
        success, error = utils.sponsors_save_html(page, sponsors)
        self.assertTrue(success, error)
        soup = BeautifulSoup(page.read_text(encoding='utf-8'), 'html.parser')
        self.assertEqual(soup.select_one('.sponsor-grid h2').get_text(strip=True), 'Supporters')
        item = soup.select_one('.sponsor-item')
        self.assertEqual(item['data-owner'], 'club')
        self.assertEqual(item.img['loading'], 'lazy')
        self.assertEqual(item.source['srcset'], '/a.webp')
        self.assertEqual(item.img['alt'], 'Changed')
        self.assertEqual(item.span.get_text(strip=True), 'Caption')


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.cleanup_root)
        self.temp = tempfile.TemporaryDirectory(prefix='editor-ui-regression-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.app = SimpleNamespace(root=self.root, set_status=Mock(), default_font_family='Segoe UI',
                                   default_font_size=10, desc_font_size=9, bold_font_weight='bold')

    def cleanup_root(self):
        self.root.update_idletasks()
        for callback in self.root.tk.call('after', 'info'):
            self.root.after_cancel(callback)
        self.root.destroy()

    def text_tab(self, html):
        path = self.base / 'text.html'
        path.write_text(html, encoding='utf-8')
        with patch.object(config, 'APP_BASE_DIR', str(self.base)):
            tab = TextEditorTab(tk.Frame(self.root), self.app)
        tab.current_file_path = str(path)
        tab._load_file_into_editor()
        return tab, path

    def test_text_noop_save_preserves_whitespace_and_empty_site_containers(self):
        html = '<html><body><p> One\n  <strong> bold </strong> text </p><div id="dynamic-results"></div>' \
               '<ul><li>• Literal bullet</li></ul><pre>  A\n    B\n</pre></body></html>'
        tab, path = self.text_tab(html)
        before = BeautifulSoup(html, 'lxml')
        tab._save_file()
        after = BeautifulSoup(path.read_text(encoding='utf-8'), 'lxml')
        self.assertEqual(str(after.body), str(before.body))
        self.assertFalse(tab.has_unsaved_changes())

    def test_duplicate_text_nodes_can_be_edited_independently(self):
        tab, path = self.text_tab('<html><body><p>Same</p><p>Same</p></body></html>')
        self.assertEqual(len(tab.node_map), 2)
        node, meta = list(tab.node_map.items())[0]
        block_tags = [tag for tag, block in tab.block_id_to_tag.items() if block is node.parent]
        start, end = tab.editor.tag_ranges(meta['id'])
        tab.editor.delete(start, end)
        tab.editor.insert(start, 'Changed', (meta['id'], *block_tags))
        tab._save_file()
        soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
        self.assertEqual([p.get_text() for p in soup.find_all('p')], ['Changed', 'Same'])

    def test_text_failed_save_keeps_original_and_reports_failure(self):
        tab, path = self.text_tab('<html><body><p>Original</p></body></html>')
        original = path.read_bytes()
        tab.editor.insert('1.0', 'New ')
        with patch('utils.os.replace', side_effect=PermissionError('locked')), patch('tabs.text_editor_tab.messagebox.showerror'):
            tab._save_file()
        self.assertEqual(path.read_bytes(), original)
        self.assertTrue(tab.has_unsaved_changes())
        self.assertTrue(self.app.set_status.call_args.kwargs.get('is_error'))

    def test_calendar_year_switch_keeps_both_years_selections(self):
        dialog = MonthManagerDialog.__new__(MonthManagerDialog)
        dialog.year_var = tk.IntVar(self.root, value=2027)
        dialog._displayed_year = 2026
        dialog.vars = {(2026, i): tk.BooleanVar(self.root, value=i in (1, 4)) for i in range(1, 13)}
        dialog.selected_by_year = {2026: {2}, 2027: {9}}
        dialog._build_checks = Mock()
        dialog._switch_year()
        self.assertEqual(dialog.selected_by_year, {2026: {1, 4}, 2027: {9}})
        dialog._build_checks.assert_called_once_with(2027)

    def test_trainer_edits_keep_position_and_new_groups_use_existing_placeholder(self):
        tab = TrainersTab.__new__(TrainersTab)
        tab.app = self.app
        tab._populate_trainers_treeview = Mock()
        tab.trainers_data = {'trainerGroups': [{'groupName': 'A', 'trainers': [{'name': 'First'}, {'name': 'Second'}]}]}
        tab._process_trainer_edit({'groupName': 'A', 'name': 'Changed'}, 'A', 0)
        self.assertEqual([item['name'] for item in tab.trainers_data['trainerGroups'][0]['trainers']], ['Changed', 'Second'])
        tab._process_trainer_edit({'groupName': 'B', 'name': 'New'})
        group = tab.trainers_data['trainerGroups'][1]
        self.assertTrue(os.path.isfile(utils.get_abs_path(group['mainPhoto']['src'])))
        self.assertEqual(group['thumbnails'], [])

    def test_sponsor_edit_reselects_edited_item(self):
        tab = SponsorsTab.__new__(SponsorsTab)
        tab.app = self.app
        tab.sponsor_data = {'A': {'data': [{'img_src': '/first.jpg'}, {'img_src': '/last.jpg'}]}}
        tab.category_var = tk.StringVar(self.root, value='A')
        tab.sponsors_tree = Mock()
        tab._display_sponsors_for_category = Mock()
        tab._process_sponsor_edit({'category': 'A', 'img_src': '/changed.jpg'}, 0, '0', 'A')
        tab.sponsors_tree.selection_set.assert_called_once_with('0')
        self.assertEqual(tab.sponsor_data['A']['data'][1]['img_src'], '/last.jpg')

    def gallery_tab(self, folders):
        tab = ImagesTab.__new__(ImagesTab)
        tab.app, tab.parent = self.app, tk.Frame(self.root)
        tab.data = {'folders': copy.deepcopy(folders)}
        tab._loaded = True
        tab.selected_folder_id = folders[0]['id']
        tab.selected_image_index = 0
        tab._populate_folders = Mock()
        tab._populate_images = Mock()
        utils.remember_editor_state(tab, tab.data)
        return tab

    def test_gallery_failed_delete_never_deletes_assets_or_changes_saved_model(self):
        image = {'src': '/images/images/a/photo.jpg', 'filename': 'photo.jpg'}
        tab = self.gallery_tab([{'id': 'a', 'title': 'A', 'images': [image]}])
        before = copy.deepcopy(tab.data)
        tab._delete_owned_image_file = Mock()
        tab._delete_owned_folder_dir = Mock()
        with patch('tabs.images_tab.messagebox.askyesno', return_value=True), patch('tabs.images_tab.messagebox.showerror'), \
             patch('utils.images_gallery_save_json_data', return_value='disk full'):
            tab._remove_image()
            self.assertEqual(tab.data, before)
            tab._delete_folder()
            self.assertEqual(tab.data, before)
        tab._delete_owned_image_file.assert_not_called()
        tab._delete_owned_folder_dir.assert_not_called()

    def test_gallery_commits_metadata_before_cleanup_and_preserves_shared_images(self):
        image = {'src': '/images/images/a/photo.jpg', 'filename': 'photo.jpg'}
        path = self.base / 'gallery.json'
        tab = self.gallery_tab([{'id': 'a', 'title': 'A', 'images': [image]}])
        def cleanup(image):
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['folders'][0]['images'], [])
            return True
        tab._delete_owned_image_file = Mock(side_effect=cleanup)
        with patch.object(config, 'IMAGES_JSON_FILE_PATH', str(path)), patch('tabs.images_tab.messagebox.askyesno', return_value=True):
            tab._remove_image()
        tab._delete_owned_image_file.assert_called_once()
        tab = self.gallery_tab([{'id': 'a', 'title': 'A', 'images': [image]}, {'id': 'b', 'title': 'B', 'images': [image]}])
        tab._delete_owned_image_file = Mock()
        with patch.object(config, 'IMAGES_JSON_FILE_PATH', str(path)), patch('tabs.images_tab.messagebox.askyesno', return_value=True):
            tab._remove_image()
        tab._delete_owned_image_file.assert_not_called()

    def test_duplicate_downloads_use_selected_row_identity_after_sorting(self):
        from tkinter import ttk
        tab = DocumentsTab.__new__(DocumentsTab)
        tab.downloads = [{'text': 'Same', 'filename': 'same.pdf', 'path': '/first/same.pdf'},
                         {'text': 'Same', 'filename': 'same.pdf', 'path': '/second/same.pdf'}]
        tab.dl_tree = ttk.Treeview(self.root, columns=('text', 'filename'))
        tab._dl_sort_col, tab._dl_sort_reverse = 'text', True
        tab._dl_populate()
        tab.dl_tree.selection_set('1')
        self.assertEqual(tab._dl_index(('Same', 'same.pdf')), 1)

    def test_news_failed_save_keeps_model_and_unsaved_draft(self):
        path = self.base / 'news.json'
        path.write_text('[]', encoding='utf-8')
        with patch.object(config, 'NEWS_JSON_FILE_PATH', str(path)):
            tab = NewsTab(tk.Frame(self.root), self.app)
            tab.news_entry_title.insert(0, 'Draft')
            self.assertTrue(tab.has_unsaved_changes())
            with patch('utils.news_save_data', return_value='disk full'), patch('tabs.news_tab.messagebox.showerror'):
                tab._news_save_or_update_article()
            self.assertEqual(tab.news_data, [])
            self.assertEqual(path.read_text(encoding='utf-8'), '[]')
            self.assertTrue(tab.has_unsaved_changes())
            with patch('utils.messagebox.askyesno', return_value=False):
                tab._news_clear_form()
            self.assertEqual(tab.news_entry_title.get(), 'Draft')

    def test_news_asset_is_retained_on_cancelled_discard_then_removed_on_confirmed_clear(self):
        path = self.base / 'news.json'
        path.write_text('[]', encoding='utf-8')
        source = self.base / 'new-photo.png'
        Image.new('RGB', (8, 8), 'red').save(source)
        destination = self.base / 'images' / 'nieuws'
        with patch.object(config, 'APP_BASE_DIR', str(self.base)), patch.object(config, 'NEWS_JSON_FILE_PATH', str(path)), \
             patch.object(config, 'NEWS_IMAGE_DEST_DIR_ABSOLUTE', str(destination)):
            tab = NewsTab(tk.Frame(self.root), self.app)
            with patch('tabs.news_tab.filedialog.askopenfilename', return_value=str(source)):
                tab._news_browse_image()
            uploaded = destination / tab.news_entry_image.get()
            self.assertTrue(uploaded.exists())
            with patch('utils.messagebox.askyesno', return_value=False):
                tab._news_clear_form()
            self.assertTrue(uploaded.exists())
            with patch('utils.messagebox.askyesno', return_value=True):
                tab._news_clear_form()
            self.assertFalse(uploaded.exists())

    def test_cancelled_nested_trainer_dialog_cleans_only_its_new_import(self):
        source = self.base / 'new-photo.png'
        Image.new('RGB', (8, 8), 'red').save(source)
        target = self.base / 'images' / 'personen' / 'new-photo.png'
        with patch.object(config, 'APP_BASE_DIR', str(self.base)), patch.object(GroupImageManagerDialog, 'wait_window'):
            dialog = GroupImageManagerDialog(self.root, {'groupName': 'Test', 'mainPhoto': {}, 'thumbnails': []}, self.app, Mock())
            details = {'_source_path_to_copy': str(source), '_dest_path_abs_for_copy': str(target),
                       '_prospective_web_src': '/images/personen/new-photo.png'}
            self.assertTrue(dialog._handle_file_copy(details))
            dialog.current_main_photo_details = details
            self.assertTrue(target.exists())
            dialog.on_cancel()
            self.assertFalse(target.exists())

    def test_media_rotation_preserves_format_and_refuses_to_flatten_animation(self):
        path = self.base / 'photo.png'
        Image.new('RGB', (12, 8), 'red').save(path)
        tab = MediaManagerTab.__new__(MediaManagerTab)
        tab.app = self.app
        tab.selected_image_data = {'abs_path': str(path), 'filename': path.name}
        tab.images_tree = Mock()
        tab.images_tree.exists.return_value = False
        tab._images_scan_files = Mock()
        with patch('tabs.media_manager_tab.messagebox.askyesno', return_value=True):
            tab._images_rotate_selected()
        with Image.open(path) as image:
            self.assertEqual((image.format, image.size), ('PNG', (8, 12)))
        animated = self.base / 'animation.gif'
        Image.new('RGB', (5, 5), 'red').save(animated, save_all=True, append_images=[Image.new('RGB', (5, 5), 'blue')], duration=100, loop=0)
        before = animated.read_bytes()
        tab.selected_image_data = {'abs_path': str(animated), 'filename': animated.name}
        with patch('tabs.media_manager_tab.messagebox.askyesno', return_value=True), patch('tabs.media_manager_tab.messagebox.showwarning'):
            tab._images_rotate_selected()
        self.assertEqual(animated.read_bytes(), before)

    def test_media_replacement_rejects_a_different_format_without_changing_target(self):
        target, source = self.base / 'photo.jpg', self.base / 'photo.png'
        Image.new('RGB', (12, 8), 'red').save(target)
        Image.new('RGB', (12, 8), 'blue').save(source)
        original = target.read_bytes()
        tab = MediaManagerTab.__new__(MediaManagerTab)
        tab.app = self.app
        tab.selected_image_data = {'abs_path': str(target), 'filename': target.name}
        with patch('tabs.media_manager_tab.messagebox.askyesno', return_value=True), \
             patch('tabs.media_manager_tab.filedialog.askopenfilename', return_value=str(source)), \
             patch('tabs.media_manager_tab.messagebox.showerror') as error:
            tab._images_replace_file()
        self.assertEqual(target.read_bytes(), original)
        error.assert_called_once()

    def test_invalid_gallery_reload_preserves_previous_model_and_disables_writes(self):
        tab = self.gallery_tab([{'id': 'a', 'title': 'A', 'images': []}])
        original = copy.deepcopy(tab.data)
        tab._update_folder_buttons = Mock()
        tab._update_image_buttons = Mock()
        with patch('utils.images_gallery_load_json_data', return_value=({}, 'invalid')), \
             patch('tabs.images_tab.messagebox.showerror'), patch('tabs.images_tab.messagebox.showwarning'), \
             patch('utils.images_gallery_save_json_data') as save:
            self.assertFalse(tab.reload_data())
            self.assertFalse(tab._save_data())
        self.assertEqual(tab.data, original)
        self.assertFalse(tab._loaded)
        save.assert_not_called()

    def test_invalid_people_reload_retains_existing_drafts_with_saving_disabled(self):
        for tab_type, data_key, list_key, loader, method, flag in [
            (BestuurTab, 'full_bestuur_data', 'boardMembers', 'bestuur_load_json_data', '_load_bestuur', 'bestuur_file_loaded'),
            (JuryTab, 'full_jury_data', 'juryMembers', 'jury_load_json_data', '_load_jury', 'jury_file_loaded'),
        ]:
            with self.subTest(tab=tab_type.__name__):
                tab = tab_type(tk.Frame(self.root), self.app)
                data = getattr(tab, data_key)
                data[list_key][0]['name'] = 'Unsaved draft'
                before = copy.deepcopy(data)
                with patch('utils.confirm_discard_changes', return_value=True), \
                     patch('utils.' + loader, return_value=(None, 'invalid')), \
                     patch('tabs.bestuur_tab.messagebox.showerror'):
                    self.assertFalse(getattr(tab, method)())
                self.assertEqual(getattr(tab, data_key), before)
                self.assertFalse(getattr(tab, flag))
                self.assertTrue(tab.has_unsaved_changes())

    def test_automatic_reload_preserves_drafts_and_reports_failed_tabs(self):
        app = WebsiteEditorApp.__new__(WebsiteEditorApp)
        app.root, app.set_status = self.root, Mock()
        dirty, clean = Mock(), Mock()
        dirty.has_unsaved_changes.return_value = True
        clean.has_unsaved_changes.return_value = False
        clean._calendar_load_from_json.side_effect = OSError('locked')
        app.tab_managers = {'news': dirty, 'calendar': clean}
        app._discarding_changes = False
        self.assertFalse(app._reload_all_tabs(automatic=True))
        dirty._news_load_and_populate_treeview.assert_not_called()
        self.assertFalse(app._discarding_changes)
        self.assertTrue(app.set_status.call_args.kwargs['is_error'])
        with patch('app.messagebox.askyesno', return_value=False):
            app._reload_all_tabs()
        self.assertEqual(clean._calendar_load_from_json.call_count, 1)

    def test_close_cancellation_retains_drafts_and_busy_jobs_cannot_be_closed(self):
        app = WebsiteEditorApp.__new__(WebsiteEditorApp)
        app.root, app.set_status = self.root, Mock()
        app._destroy_app = Mock()
        app._has_unpublished_changes = Mock(return_value=False)
        manager = Mock()
        manager.has_unsaved_changes.return_value = True
        app.tab_managers, app._busy = {'news': manager}, False
        with patch('app.messagebox.askyesno', return_value=False):
            app._on_close()
        app._destroy_app.assert_not_called()
        app._has_unpublished_changes.assert_not_called()
        app._busy = True
        app._on_close()
        app._destroy_app.assert_not_called()

    def test_faq_failed_save_leaves_dialog_and_draft_open_for_retry(self):
        path = self.base / 'faq.json'
        path.write_text('[]', encoding='utf-8')
        with patch.object(config, 'FAQ_JSON_FILE_PATH', str(path)):
            tab = FaqTab(tk.Frame(self.root), self.app)
            # Skip the modal wait so the test can drive the real widgets directly.
            with patch.object(FaqDialog, 'wait_window'):
                dialog = FaqDialog(self.root, 'Test', {'question': 'Draft?', 'answer': 'Draft answer'},
                                   on_save=lambda result: tab._commit([result], 0, 'saved'))
            with patch('tabs.faq_tab.save_faq_entries', side_effect=OSError('disk full')), patch('tabs.faq_tab.messagebox.showerror'):
                dialog._save()
            self.assertTrue(dialog.winfo_exists())
            self.assertEqual(dialog.question.get(), 'Draft?')
            self.assertEqual(tab.entries, [])
            dialog._save()
            self.assertFalse(dialog.winfo_exists())
            self.assertEqual(tab.entries[0]['question'], 'Draft?')

    def test_all_tabs_initialize_clean_and_git_overlay_restores_editing(self):
        with patch.object(WebsiteEditorApp, '_perform_initial_load'), patch.object(WebsiteEditorApp, '_check_for_app_update'), \
             patch.object(PreviewManager, '_start_server'), patch('tkinter.messagebox.showerror') as errors:
            app = WebsiteEditorApp(self.root)
            self.root.update_idletasks()
            self.assertEqual(len(app.tab_managers), 13)
            self.assertEqual(app._unsaved_tab_keys(), [])
            app.toggle_interaction(False)
            self.assertTrue(app._busy)
            self.assertTrue(app._busy_overlay.winfo_exists())
            app.toggle_interaction(True)
            self.assertFalse(app._busy)
            self.assertIsNone(app._busy_overlay)
            errors.assert_not_called()
            app._closing = True


class GitWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='editor-git-regression-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.remote = self.base / 'remote.git'
        self.client, self.other = self.base / 'client', self.base / 'other'
        self.git(self.base, 'init', '--bare', '--initial-branch=main', str(self.remote))
        self.git(self.base, 'clone', str(self.remote), str(self.client))
        for key, value in [('user.name', 'Test'), ('user.email', 'test@example.invalid')]:
            self.git(self.client, 'config', key, value)
        (self.client / 'content.txt').write_text('original\n', encoding='utf-8')
        self.git(self.client, 'add', '.')
        self.git(self.client, 'commit', '-m', 'initial')
        self.git(self.client, 'push', '-u', 'origin', 'main')
        self.git(self.base, 'clone', str(self.remote), str(self.other))
        for key, value in [('user.name', 'Test'), ('user.email', 'test@example.invalid')]:
            self.git(self.other, 'config', key, value)
        self.app = WebsiteEditorApp.__new__(WebsiteEditorApp)
        self.commands = []
        self.app._ensure_git_configs = Mock()
        self.app._run_git_command = self.run_command
        self.app._run_git_index_safe = self.run_command
        self.fail_pull = False

    def git(self, cwd, *args):
        result = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return result.stdout.strip()

    def run_command(self, command, description):
        self.commands.append(command)
        if self.fail_pull and command[1] == 'pull':
            return subprocess.CompletedProcess(command, 1, stdout='', stderr='simulated network failure')
        return subprocess.run(command, cwd=self.client, capture_output=True, text=True, encoding='utf-8')

    def update_remote(self, filename, text):
        (self.other / filename).write_text(text, encoding='utf-8')
        self.git(self.other, 'add', '.')
        self.git(self.other, 'commit', '-m', 'upstream change')
        self.git(self.other, 'push', 'origin', 'main')

    def test_failed_pull_restores_work_and_preserves_preexisting_stash(self):
        (self.client / 'content.txt').write_text('previous stash\n', encoding='utf-8')
        self.git(self.client, 'stash', 'push', '-m', 'preexisting')
        previous = self.git(self.client, 'rev-parse', 'refs/stash')
        (self.client / 'content.txt').write_text('staged work\n', encoding='utf-8')
        self.git(self.client, 'add', '.')
        (self.client / 'content.txt').write_text('unstaged work\n', encoding='utf-8')
        (self.client / 'untracked.txt').write_text('untracked work', encoding='utf-8')
        self.fail_pull = True
        success, message = self.app._publication_workflow('test')
        self.assertFalse(success, message)
        self.assertEqual((self.client / 'content.txt').read_text(encoding='utf-8'), 'unstaged work\n')
        self.assertEqual(self.git(self.client, 'show', ':content.txt'), 'staged work')
        self.assertTrue((self.client / 'untracked.txt').exists())
        self.assertEqual(self.git(self.client, 'rev-parse', 'refs/stash'), previous)

    def test_conflicts_preserve_local_stash_and_upstream_without_automatic_overwrite(self):
        (self.client / 'content.txt').write_text('local work\n', encoding='utf-8')
        self.update_remote('content.txt', 'remote work\n')
        success, message = self.app._publication_workflow('test')
        self.assertFalse(success)
        self.assertIn('stash', message)
        self.assertEqual(self.git(self.client, 'show', 'HEAD:content.txt'), 'remote work')
        self.assertEqual(self.git(self.client, 'show', 'refs/stash:content.txt'), 'local work')
        self.assertFalse(any(command[1] in ('checkout', 'push') for command in self.commands))

    def test_successful_publication_preserves_both_sides_and_uses_normal_push(self):
        (self.client / 'content.txt').write_text('local work\n', encoding='utf-8')
        self.update_remote('upstream.txt', 'remote work\n')
        success, message = self.app._publication_workflow('test')
        self.assertTrue(success, message)
        self.assertEqual(self.git(self.remote, 'show', 'main:content.txt'), 'local work')
        self.assertEqual(self.git(self.remote, 'show', 'main:upstream.txt'), 'remote work')
        self.assertEqual(self.git(self.client, 'stash', 'list'), '')
        self.assertFalse(any('--force-with-lease' in command for command in self.commands))

    def test_publication_keeps_excluded_manifest_change_local(self):
        (self.client / 'update.json').write_text('original manifest', encoding='utf-8')
        self.git(self.client, 'add', 'update.json')
        self.git(self.client, 'commit', '-m', 'add manifest')
        self.git(self.client, 'push', 'origin', 'main')
        (self.client / 'update.json').write_text('local excluded change', encoding='utf-8')
        self.git(self.client, 'add', 'update.json')
        (self.client / 'content.txt').write_text('website change\n', encoding='utf-8')
        success, message = self.app._publication_workflow('test')
        self.assertTrue(success, message)
        self.assertEqual(self.git(self.remote, 'show', 'main:update.json'), 'original manifest')
        self.assertEqual((self.client / 'update.json').read_text(encoding='utf-8'), 'local excluded change')


if __name__ == '__main__':
    unittest.main()

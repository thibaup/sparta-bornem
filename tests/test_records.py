"""Regression checks for the record editor; all writes use temporary files."""
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bs4 import BeautifulSoup
import utils
from tabs.records_tab import RecordsTab, _split_names


class RecordsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'records.html'
        self.addCleanup(self.temp.cleanup)

    def parse_rows(self, rows):
        self.path.write_text('<html><body><main class="container"><table class="records-table">'
                             '<tbody>' + rows + '</tbody></table></main></body></html>', encoding='utf-8')
        return utils.records_parse_html(self.path)['records']

    def save(self, records):
        success, error = utils.records_save_html(self.path, records, 'Mail naar', 'test@example.com', ['Bericht'], 'Test')
        self.assertTrue(success, error)
        return utils.records_parse_html(self.path)['records']

    def test_escaped_relay_breaks_and_padding(self):
        records = self.parse_rows('<tr><td>4x100m</td><td>Ann&lt;br&gt;Bo&lt;br&gt;Cy&lt;br&gt;Di</td>'
                                  '<td>51″25&lt;br&gt;&lt;br&gt;&lt;br&gt;</td><td>Bornem&lt;br&gt;&lt;br&gt;</td>'
                                  '<td>2026.05.17&lt;br&gt;</td></tr>')
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['names'], ['Ann', 'Bo', 'Cy', 'Di'])
        self.assertEqual(records[0]['performance'], '51″25')
        for _ in range(3):
            self.assertEqual(self.save(records), records)
        soup = BeautifulSoup(self.path.read_text(encoding='utf-8'), 'html.parser')
        self.assertEqual(len(soup.select('tbody tr')), 1)
        self.assertEqual(len(soup.select('tbody br')), 3)

    def test_distinct_ties_and_teams_survive(self):
        records = self.parse_rows('<tr><td>100m</td><td>Ann<br>Bo</td><td>12″50</td><td>Bornem</td><td>2026.05.17</td></tr>'
                                  '<tr><td>4x100m</td><td>Ann<br>Bo<br>Cy<br>Di</td><td>51″25</td><td>Bornem</td><td>2026.05.17</td></tr>'
                                  '<tr><td>4x100m</td><td>El<br>Fa<br>Gi<br>Ho</td><td>51″25</td><td>Bornem</td><td>2026.05.17</td></tr>')
        self.assertEqual(len(records), 4)
        self.assertEqual([r['names'] for r in records[:2]], [['Ann'], ['Bo']])
        self.assertEqual(self.save(records), records)
        self.assertEqual(len(BeautifulSoup(self.path.read_text(encoding='utf-8'), 'html.parser').select('tbody tr')), 4)

    def test_inline_formatting_empty_slots_and_shared_values(self):
        records = self.parse_rows('<tr><td>Hoogspringen</td><td><strong>Ann</strong> van <em>Dam</em></td>'
                                  '<td>1.60m</td><td>Bornem<br><br>Gent</td><td>2020<br>2021<br>2022</td></tr>')
        self.assertEqual(len(records), 3)
        self.assertEqual([r['names'] for r in records], [['Ann van Dam']] * 3)
        self.assertEqual([r['performance'] for r in records], ['1.60m'] * 3)
        self.assertEqual([r['place'] for r in records], ['Bornem', '', 'Gent'])
        self.assertEqual(self.save(records), records)

    def test_legacy_combined_teams_keep_boundaries(self):
        records = self.parse_rows('<tr><td>4x100m</td><td>A<br>B<br>C<br>D<br>E<br>F<br>G<br>H</td>'
                                  '<td>50<br><br><br><br>51</td><td>Bornem</td><td>2020</td></tr>')
        self.assertEqual([r['names'] for r in records], [list('ABCD'), list('EFGH')])
        self.assertEqual(self.save(records), records)

    def test_user_text_is_not_html_or_a_name_separator(self):
        names = ['Doe, John', 'Ann / Bo', '<script>alert(1)</script>', 'literal <br> text', 'A & B']
        record = dict(discipline='Team race', names=names, performance='<br>', place='A & B', date='2026')
        self.assertEqual(self.save([record]), [record])
        soup = BeautifulSoup(self.path.read_text(encoding='utf-8'), 'html.parser')
        self.assertIsNone(soup.find('script'))
        for name in names:
            self.assertEqual(_split_names(name), [name])
        self.assertEqual(_split_names('A, B / C; D', split_commas=True), list('ABCD'))

    def test_all_61_pages_round_trip_without_data_loss(self):
        base = Path(__file__).resolve().parents[1] / 'html' / 'clubrecords'
        pages = list(base.rglob('*.html'))
        self.assertEqual(len(pages), 61)
        for page in pages:
            with self.subTest(page=page.name):
                data = utils.records_parse_html(page)
                self.assertIsNotNone(data)
                self.path.write_bytes(page.read_bytes())
                for _ in range(2):
                    success, error = utils.records_save_html(self.path, data['records'], data['prefix'], data['email'],
                                                             data['general_messages'], page.stem)
                    self.assertTrue(success, error)
                    self.assertEqual(utils.records_parse_html(self.path), data)

    def test_navigation_cancel_and_message_edits(self):
        root = tk.Tk()
        root.withdraw()
        self.addCleanup(root.destroy)
        self.save([dict(discipline='100m', names=['Ann'], performance='12', place='Bornem', date='2026')])
        other = self.path.with_name('other.html')
        other.write_bytes(self.path.read_bytes())
        app = SimpleNamespace(root=root, set_status=lambda *args, **kwargs: None)
        with patch.object(utils, 'records_discover_files', return_value={'Category': {'Original': str(self.path), 'Other': str(other)}}):
            tab = RecordsTab(tk.Frame(root), app)
            original_iid, other_iid = list(tab.nav_tree_map)
            tab.nav_tree.selection_set(original_iid)
            root.update()
            self.assertEqual(tab.messages_text.get('1.0', 'end-1c'), 'Bericht')
            self.assertFalse(tab._data_dirty)
            tab.messages_text.insert('end', ' via paste')
            root.update()
            self.assertTrue(tab._data_dirty)
            for target in (other_iid, tab.nav_tree.parent(original_iid)):
                with patch('tabs.records_tab.messagebox.askyesno', return_value=False):
                    tab.nav_tree.selection_set(target)
                    root.update()
                self.assertEqual(tab.nav_tree.selection(), (original_iid,))
                self.assertEqual(tab.records_current_file_path, str(self.path))
                self.assertTrue(tab._data_dirty)
            tab._records_discover_and_populate_categories()
            root.update()
            self.assertEqual(tab.records_current_file_path, str(self.path))
            self.assertTrue(tab._data_dirty)
            tab._records_save()
            self.assertFalse(tab._data_dirty)
            self.assertIn('Clubrecords Original', self.path.read_text(encoding='utf-8'))
            self.assertEqual(utils.records_parse_html(self.path)['general_messages'], ['Bericht via paste'])


if __name__ == '__main__':
    unittest.main()

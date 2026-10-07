import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import os
import traceback
import re
import uuid
from collections import defaultdict
from collections.abc import MutableMapping

try:
    from bs4 import Tag, NavigableString, BeautifulSoup, Comment
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

import config
import utils

BLOCK_TAGS = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'li', 'blockquote', 'hr', 'table', 'form', 'header', 'footer', 'section', 'article', 'aside'}
HIGHLIGHT_COLOR = "#007bff"
WEBSITE_BASE_FONT_PX = 16.0

class IdentityNodeMap(MutableMapping):
    """BeautifulSoup strings with equal text still belong to distinct DOM nodes."""
    def __init__(self):
        self._nodes = {}

    def __getitem__(self, node):
        return self._nodes[id(node)][1]

    def __setitem__(self, node, value):
        self._nodes[id(node)] = (node, value)

    def __delitem__(self, node):
        del self._nodes[id(node)]

    def __iter__(self):
        return (node for node, _ in self._nodes.values())

    def __len__(self):
        return len(self._nodes)

class TextEditorTab:
    PLACEHOLDER = '\u200b'

    def __init__(self, parent_frame, app_instance):
        self.parent = parent_frame
        self.app = app_instance
        self.current_file_path = None
        self.current_soup = None
        self.node_map = IdentityNodeMap()
        self.block_id_to_tag = {}
        self.html_files = []
        self.size_tag_cache = {}
        self._pending_insert_start = None
        self._pending_node_target = None
        self._pending_size_target = None
        self._post_reload_focus_token = None
        self._create_widgets()
        self._scan_and_populate_files()

    def _create_widgets(self):
        self.parent.grid_rowconfigure(0, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        if not BS4_AVAILABLE:
            error_label = ttk.Label(self.parent, text="Error: BeautifulSoup4 library is missing.", style="Error.TLabel", justify=tk.CENTER)
            error_label.grid(row=0, column=0, pady=50, padx=20, sticky='nsew')
            return

        main_pane = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        main_pane.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)

        left_pane = ttk.Frame(main_pane, width=300)
        left_pane.grid_rowconfigure(2, weight=1)
        left_pane.grid_columnconfigure(0, weight=1)
        main_pane.add(left_pane, weight=1)

        right_pane = ttk.Frame(main_pane)
        right_pane.grid_rowconfigure(1, weight=1)
        right_pane.grid_columnconfigure(0, weight=1)
        main_pane.add(right_pane, weight=3)

        scan_button = ttk.Button(left_pane, text="Bestanden vernieuwen", command=self._scan_and_populate_files)
        scan_button.grid(row=0, column=0, sticky='ew', padx=5, pady=(0, 5))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._filter_file_tree)
        search_entry = ttk.Entry(left_pane, textvariable=self.search_var)
        search_entry.grid(row=1, column=0, sticky='ew', padx=5, pady=(0, 5))

        tree_frame = ttk.Frame(left_pane)
        tree_frame.grid(row=2, column=0, sticky='nsew', padx=5)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.file_tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        self.file_tree.grid(row=0, column=0, sticky='nsew')
        self.file_tree.bind('<<TreeviewSelect>>', self._on_file_select)

        tree_vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.file_tree.yview)
        tree_vsb.grid(row=0, column=1, sticky='ns')
        self.file_tree.configure(yscrollcommand=tree_vsb.set)

        toolbar = ttk.Frame(right_pane, style="Card.TFrame", padding=5)
        toolbar.grid(row=0, column=0, sticky='ew', pady=(0, 5))

        self.save_button = ttk.Button(toolbar, text="Opslaan", command=self._save_file, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.highlight_button = ttk.Button(toolbar, text="Markeren", command=self._apply_highlight, state=tk.DISABLED)
        self.highlight_button.pack(side=tk.LEFT, padx=5)

        self.bold_button = ttk.Button(toolbar, text="Vet", command=self._make_bold, state=tk.DISABLED)
        self.bold_button.pack(side=tk.LEFT, padx=5)

        self.link_button = ttk.Button(toolbar, text="Maak Link", command=self._make_link, state=tk.DISABLED)
        self.link_button.pack(side=tk.LEFT, padx=5)

        self.font_size_var = tk.StringVar(value="16")
        self.font_size_combo = ttk.Combobox(
            toolbar,
            textvariable=self.font_size_var,
            width=5,
            state="readonly",
            values=[str(v) for v in (10, 11, 12, 13, 14, 15, 16, 16.8, 18, 20, 24, 28, 32, 36, 40, 48)]
        )
        self.font_size_combo.pack(side=tk.LEFT, padx=(12, 4))

        self.font_size_btn = ttk.Button(toolbar, text="Lettergrootte", command=self._apply_font_size_from_ui, state=tk.DISABLED)
        self.font_size_btn.pack(side=tk.LEFT, padx=4)

        self.editor = scrolledtext.ScrolledText(
            right_pane,
            width=80,
            height=20,
            wrap=tk.WORD,
            relief=tk.SUNKEN,
            borderwidth=1,
            state=tk.DISABLED,
            font=(self.app.default_font_family, int(round(WEBSITE_BASE_FONT_PX))),
            undo=True,
            maxundo=-1,
            spacing3=4,
            exportselection=False
        )

        self.ul_button = ttk.Button(toolbar, text="Opsommingstekens", command=self._make_unordered_list, state=tk.DISABLED)
        self.ul_button.pack(side=tk.LEFT, padx=5)

        self.ol_button = ttk.Button(toolbar, text="Genummerde lijst", command=self._make_ordered_list, state=tk.DISABLED)
        self.ol_button.pack(side=tk.LEFT, padx=5)

        self.editor.grid(row=1, column=0, sticky='nsew')

        self.editor.bind("<Control-s>", lambda event: self._save_file())
        self.editor.bind("<Button-3>", self._show_context_menu)
        self.editor.bind("<<Modified>>", self._on_text_modified)

        self.editor.tag_config("bold", font=(self.app.default_font_family, int(round(WEBSITE_BASE_FONT_PX)), 'bold'))
        self.editor.tag_config("link", foreground="#0000EE", underline=True)
        self.editor.tag_config("highlight", foreground=HIGHLIGHT_COLOR)

        self._bind_typing_behavior()

    def _bind_typing_behavior(self):
        self.editor.bind("<KeyPress>", self._on_keypress, add="+")
        self.editor.bind("<Return>", self._on_return, add="+")
        self.editor.bind("<<Paste>>", self._on_paste, add="+")
        self.editor.bind("<KeyPress-BackSpace>", self._guard_backspace, add="+")
        self.editor.bind("<KeyPress-Delete>", self._guard_delete, add="+")
        self.editor.bind("<KeyRelease-BackSpace>", self._after_edit_purge, add="+")
        self.editor.bind("<KeyRelease-Delete>", self._after_edit_purge, add="+")
        self.editor.bind("<<Cut>>", self._after_edit_purge, add="+")

    def _purge_deleted_blocks_in_memory(self):
        if not self.current_soup:
            return
        to_remove = []
        for block_id, bs_block in list(self.block_id_to_tag.items()):
            try:
                ranges = self.editor.tag_ranges(block_id)
            except tk.TclError:
                ranges = []
            if not ranges and isinstance(bs_block, Tag):
                to_remove.append((block_id, bs_block))
        for block_id, bs_block in to_remove:
            parent = getattr(bs_block, 'parent', None)
            bs_block.decompose()
            self._remove_block_descendant_mappings(bs_block)
            try:
                self.editor.tag_remove(block_id, "1.0", tk.END)
            except tk.TclError:
                pass
            self.block_id_to_tag.pop(block_id, None)
            if parent and isinstance(parent, Tag) and parent.name in ('ul', 'ol') and not parent.find('li'):
                parent.decompose()


    def _after_edit_purge(self, event=None):
        if not self.current_soup:
            return
        def run():
            self._reconcile_nodes_with_editor()
            self._purge_deleted_blocks_in_memory()
            self._purge_deleted_ephemeral_in_memory()
            self._ensure_block_separators()
        self.editor.after_idle(run)


    def _block_is_nonempty(self, block_id):
        ranges = self.editor.tag_ranges(block_id)
        if not ranges:
            return False
        txt = self.editor.get(ranges[0], ranges[-1])
        txt = txt.replace('• ', '').replace(self.PLACEHOLDER, '').strip()
        return txt != ''

    def _guard_backspace(self, event=None):
        if not self.current_soup:
            return
        try:
            idx = self.editor.index("insert")
        except tk.TclError:
            return
        try:
            ch = self.editor.get(f"{idx}-1c")
        except tk.TclError:
            ch = ''
        if ch != '\n':
            return
        prev_block = self._nearest_block_before_index(idx)
        next_block = self._nearest_block_after_index(idx)
        if not prev_block or not next_block:
            return
        pr = self.editor.tag_ranges(prev_block)
        nr = self.editor.tag_ranges(next_block)
        if not pr or not nr:
            return
        prev_end = pr[-1]
        next_start = nr[0]
        between = self.editor.get(prev_end, next_start)
        newlines = between.count('\n')
        if newlines <= 1 and self._block_is_nonempty(prev_block) and self._block_is_nonempty(next_block):
            return "break"

    def _guard_delete(self, event=None):
        if not self.current_soup:
            return
        try:
            idx = self.editor.index("insert")
        except tk.TclError:
            return
        try:
            ch = self.editor.get(idx)
        except tk.TclError:
            ch = ''
        if ch != '\n':
            return
        prev_block = self._nearest_block_before_index(idx)
        next_block = self._nearest_block_after_index(idx)
        if not prev_block or not next_block:
            return
        pr = self.editor.tag_ranges(prev_block)
        nr = self.editor.tag_ranges(next_block)
        if not pr or not nr:
            return
        prev_end = pr[-1]
        next_start = nr[0]
        between = self.editor.get(prev_end, next_start)
        newlines = between.count('\n')
        if newlines <= 1 and self._block_is_nonempty(prev_block) and self._block_is_nonempty(next_block):
            return "break"

    def _ensure_block_separators(self):
        if not self.current_soup:
            return
        blocks = []
        for tag in self.editor.tag_names():
            if not tag.startswith("block_"):
                continue
            r = self.editor.tag_ranges(tag)
            if not r:
                continue
            blocks.append((self._index_tuple(r[0]), r[0], r[-1], tag))
        blocks.sort(key=lambda x: x[0])

        filtered = []
        for _, s, e, t in blocks:
            if filtered:
                last_s, last_e, _ = filtered[-1]
                if self._index_tuple(s) >= self._index_tuple(last_s) and self._index_tuple(e) <= self._index_tuple(last_e):
                    continue
            filtered.append((s, e, t))

        for i in range(len(filtered) - 1):
            prev_end = filtered[i][1]
            next_start = filtered[i + 1][0]
            if self.editor.compare(next_start, "<=", prev_end):
                continue
            if self.editor.get(prev_end, next_start).count("\n") >= 1:
                continue
            if self._block_is_nonempty(filtered[i][2]) and self._block_is_nonempty(filtered[i + 1][2]):
                self.editor.insert(next_start, "\n")

    def _purge_deleted_ephemeral_in_memory(self):
        if not self.current_soup:
            return
        removed_any = False
        to_remove = []
        for block_id, bs_block in list(self.block_id_to_tag.items()):
            try:
                ranges = self.editor.tag_ranges(block_id)
            except tk.TclError:
                ranges = []
            if not isinstance(bs_block, Tag):
                continue
            if 'data-editor-ephemeral' not in self._safe_attrs(bs_block):
                continue
            empty = True
            if ranges:
                text = self.editor.get(ranges[0], ranges[-1])
                text = text.replace('• ', '').replace(self.PLACEHOLDER, '').strip()
                empty = text == ''
            if empty:
                to_remove.append((block_id, bs_block))
        for block_id, bs_block in to_remove:
            parent = getattr(bs_block, 'parent', None)
            bs_block.decompose()
            self._remove_block_descendant_mappings(bs_block)
            try:
                self.editor.tag_remove(block_id, "1.0", tk.END)
            except tk.TclError:
                pass
            self.block_id_to_tag.pop(block_id, None)
            if parent and isinstance(parent, Tag) and parent.name in ('ul', 'ol') and not parent.find('li'):
                parent.decompose()
            removed_any = True
        if removed_any:
            pass

    def _get_bsnode_by_id(self, node_id):
        for n, meta in self.node_map.items():
            if meta["id"] == node_id:
                return n, meta
        return None, None

    def _replace_bsnode_text(self, bs_node, new_text):
        meta = self.node_map.get(bs_node)
        if new_text is None:
            new_text = ''
        if new_text == '':
            if getattr(bs_node, 'parent', None):
                bs_node.extract()
            if meta:
                self.node_map.pop(bs_node, None)
            return None
        new_node = NavigableString(new_text)
        try:
            bs_node.replace_with(new_node)
        except Exception:
            parent = getattr(bs_node, 'parent', None)
            if parent:
                parent.insert_before(new_node)
                try:
                    bs_node.extract()
                except Exception:
                    pass
            else:
                new_node = bs_node
        if meta:
            self.node_map.pop(bs_node, None)
            meta["display_text"] = new_text
            meta["offset_map"] = [(i, i + 1) for i in range(len(new_text))]
            self.node_map[new_node] = meta
        return new_node


    def _reconcile_nodes_with_editor(self):
        if not self.current_soup:
            return

        id_to_node = {meta["id"]: bs_node for bs_node, meta in self.node_map.items()}

        node_positions = []
        for tag in self.editor.tag_names():
            if not tag.startswith("node_"):
                continue
            ranges = self.editor.tag_ranges(tag)
            if not ranges:
                continue
            node_positions.append((self.editor.index(ranges[0]), self.editor.index(ranges[-1]), tag))

        node_positions.sort(key=lambda x: self._index_tuple(x[0]))

        seen_ids = set()

        for start_pos, end_pos, node_id in node_positions:
            bs_node = id_to_node.get(node_id)
            if not bs_node:
                continue
            seen_ids.add(node_id)

            if not getattr(bs_node, 'parent', None):
                fresh, _ = self._get_bsnode_by_id(node_id)
                if fresh is None:
                    continue
                bs_node = fresh

            parent = getattr(bs_node, 'parent', None)
            if not parent:
                continue

            text_slice = self.editor.get(start_pos, end_pos)
            if self.PLACEHOLDER in text_slice:
                text_slice = text_slice.replace(self.PLACEHOLDER, '')

            if self.node_map.get(bs_node, {}).get("display_text", str(bs_node)) != text_slice:
                self._replace_bsnode_text(bs_node, text_slice)

        for bs_node, meta in list(self.node_map.items()):
            if meta["id"] not in seen_ids:
                parent = getattr(bs_node, 'parent', None)
                if parent:
                    bs_node.extract()
                self.node_map.pop(bs_node, None)

        self._cleanup_empty_blocks()



    def _remove_block_descendant_mappings(self, bs_block):
        removed_ids = set()
        for child in list(bs_block.descendants):
            if isinstance(child, NavigableString) and child in self.node_map:
                meta = self.node_map.pop(child, None)
                if meta and "id" in meta:
                    removed_ids.add(meta["id"])
        for tag_id in removed_ids:
            try:
                self.editor.tag_remove(tag_id, "1.0", tk.END)
            except tk.TclError:
                pass

    def _on_keypress(self, event):
        if not self.current_soup:
            return
        if not event.char or len(event.char) != 1 or ord(event.char) < 32:
            return
        try:
            self._pending_insert_start = self.editor.index("insert")
        except tk.TclError:
            self._pending_insert_start = None
            return
        right_tags = self.editor.tag_names("insert")
        try:
            left_tags = self.editor.tag_names("insert-1c")
        except tk.TclError:
            left_tags = []
        right_node = next((t for t in right_tags if t.startswith("node_")), None)
        left_node = next((t for t in left_tags if t.startswith("node_")), None)
        right_size = next((t for t in right_tags if t.startswith("fs_")), None)
        left_size = next((t for t in left_tags if t.startswith("fs_")), None)
        self._pending_node_target = right_node or left_node
        if not self._pending_node_target:
            prev_info = self._nearest_node_before_index("insert")
            if prev_info:
                self._pending_node_target = prev_info[0]
            else:
                next_info = self._nearest_node_after_index("insert")
                if next_info:
                    self._pending_node_target = next_info[0]
        self._pending_size_target = right_size or left_size
        if not self._pending_size_target and self._pending_node_target:
            r = self.editor.tag_ranges(self._pending_node_target)
            if r:
                size_tags = [t for t in self.editor.tag_names(r[0]) if t.startswith("fs_")]
                if size_tags:
                    self._pending_size_target = size_tags[0]
        self._pending_block_target = self._block_tag_at_index("insert") or self._nearest_block_before_index("insert")
        self.editor.after_idle(self._apply_pending_insert_tags)



    def _apply_pending_insert_tags(self):
        if not self._pending_insert_start:
            return
        try:
            end_index = self.editor.index("insert")
        except tk.TclError:
            return
        if self.editor.compare(self._pending_insert_start, ">=", end_index):
            return
        if self._pending_node_target:
            for t in self.editor.tag_names():
                if t.startswith("node_") and t != self._pending_node_target:
                    self.editor.tag_remove(t, self._pending_insert_start, end_index)
            self.editor.tag_add(self._pending_node_target, self._pending_insert_start, end_index)
        if self._pending_size_target:
            for t in self.editor.tag_names():
                if t.startswith("fs_") and t != self._pending_size_target:
                    self.editor.tag_remove(t, self._pending_insert_start, end_index)
            self.editor.tag_add(self._pending_size_target, self._pending_insert_start, end_index)
        if getattr(self, "_pending_block_target", None):
            self.editor.tag_add(self._pending_block_target, self._pending_insert_start, end_index)
        self._pending_insert_start = None
        self._pending_node_target = None
        self._pending_size_target = None
        self._pending_block_target = None


    def _on_paste(self, event=None):
        if not self.current_soup:
            return
        try:
            start = self.editor.index("insert")
        except tk.TclError:
            return
        right_tags = self.editor.tag_names("insert")
        try:
            left_tags = self.editor.tag_names("insert-1c")
        except tk.TclError:
            left_tags = []
        node_tag = next((t for t in right_tags if t.startswith("node_")), None) or next((t for t in left_tags if t.startswith("node_")), None)
        size_tag = next((t for t in right_tags if t.startswith("fs_")), None) or next((t for t in left_tags if t.startswith("fs_")), None)
        self._pending_block_target = self._block_tag_at_index("insert") or self._nearest_block_before_index("insert")
        def fix():
            try:
                end = self.editor.index("insert")
            except tk.TclError:
                return
            if self.editor.compare(start, "==", end):
                return
            if node_tag:
                for t in self.editor.tag_names():
                    if t.startswith("node_") and t != node_tag:
                        self.editor.tag_remove(t, start, end)
                self.editor.tag_add(node_tag, start, end)
            if size_tag:
                for t in self.editor.tag_names():
                    if t.startswith("fs_") and t != size_tag:
                        self.editor.tag_remove(t, start, end)
                self.editor.tag_add(size_tag, start, end)
            if getattr(self, "_pending_block_target", None):
                self.editor.tag_add(self._pending_block_target, start, end)
            self._pending_block_target = None
        self.editor.after_idle(fix)


    def _current_node_text(self, node_id, meta):
        r = self.editor.tag_ranges(node_id)
        if not r:
            return ''
        text = self.editor.get(r[0], r[-1]).rstrip('\n')
        if meta.get("bullet") and text.startswith('• '):
            text = text[2:].lstrip()
        return text

    def _display_offsets_in_node(self, node_id, meta, part_start, part_end):
        r = self.editor.tag_ranges(node_id)
        if not r:
            return 0, 0
        node_start = r[0]
        bullet_len = 0
        try:
            preview = self.editor.get(node_start, r[-1])
            if meta.get("bullet") and preview.startswith('• '):
                bullet_len = 2
        except tk.TclError:
            pass
        s = max(0, len(self.editor.get(node_start, part_start)) - bullet_len)
        e = max(0, len(self.editor.get(node_start, part_end)) - bullet_len)
        node_text = self._current_node_text(node_id, meta)
        n = len(node_text)
        s = min(s, n)
        e = min(e, n)
        return s, e

    def _should_skip_node(self, element):
        if not isinstance(element, Tag):
            return False
        attrs = self._safe_attrs(element)
        if attrs.get('id') in ('header-placeholder', 'footer-placeholder', 'latest-news-grid'):
            return True
        return False




    def _set_trailing_newlines(self, count):
        try:
            tail = self.editor.get('end-200c', 'end-1c')
        except tk.TclError:
            tail = ''
        cur = 0
        for ch in reversed(tail):
            if ch == '\n':
                cur += 1
            else:
                break
        if cur > count:
            for _ in range(cur - count):
                try:
                    self.editor.delete('end-2c', 'end-1c')
                except tk.TclError:
                    break
        elif cur < count:
            self.editor.insert(tk.END, '\n' * (count - cur))

    def _insert_after_tag(self, ref_tag, new_tag, boundary_index):
        if isinstance(ref_tag, Tag) and getattr(ref_tag, "parent", None):
            ref_tag.insert_after(new_tag)
            return
        next_block = self._nearest_block_after_index(boundary_index)
        next_tag = self.block_id_to_tag.get(next_block)
        if isinstance(next_tag, Tag) and getattr(next_tag, "parent", None):
            next_tag.insert_before(new_tag)
            return
        (self.current_soup.body or self.current_soup).append(new_tag)

    def _clamp_index_to_block(self, index, block_id):
        ranges = self.editor.tag_ranges(block_id)
        if not ranges:
            return index
        b_start, b_end = ranges[0], ranges[-1]
        if self.editor.compare(index, "<", b_start):
            return b_start
        if self.editor.compare(index, ">", b_end):
            return b_end
        return index


    def _on_return(self, event):
        if not self.current_soup:
            return "break"
        self._apply_pending_insert_tags()
        try:
            self.editor.update_idletasks()
        except tk.TclError:
            pass
        try:
            insert_index = self.editor.index("insert")
        except tk.TclError:
            return "break"

        block_id = self._block_tag_at_index(insert_index) or self._nearest_block_before_index(insert_index)
        if not block_id:
            token = uuid.uuid4().hex
            new_block = self.current_soup.new_tag('p')
            new_block['data-editor-focus'] = token
            new_block['data-editor-ephemeral'] = '1'
            new_block.append(NavigableString(self.PLACEHOLDER))
            (self.current_soup.body or self.current_soup).append(new_block)
            self._post_reload_focus_token = token
            self._refresh_editor_from_soup()
            return "break"

        ranges = self.editor.tag_ranges(block_id)
        if not ranges:
            return "break"
        b_start, b_end = ranges[0], ranges[-1]

        logical_index = self._clamp_index_to_block(insert_index, block_id)
        nodes = self._nodes_overlapping_range(b_start, b_end)

        block_tag = self.block_id_to_tag.get(block_id)
        if not isinstance(block_tag, Tag):
            return "break"

        cut_node = None
        cut_meta = None
        cut_offset = None
        prev_tuple = None

        for n_start, n_end, node_id, bs_node, meta in nodes:
            if self.editor.compare(logical_index, "<", n_start):
                if prev_tuple:
                    cut_node, cut_meta = prev_tuple[3], prev_tuple[4]
                    cut_offset = len(self._current_node_text(prev_tuple[2], prev_tuple[4]))
                else:
                    cut_node, cut_meta = bs_node, meta
                    cut_offset = 0
                break
            if self.editor.compare(logical_index, ">=", n_start) and self.editor.compare(logical_index, "<=", n_end):
                cut_node, cut_meta = bs_node, meta
                s, _ = self._display_offsets_in_node(node_id, meta, logical_index, logical_index)
                cut_offset = s
                break
            prev_tuple = (n_start, n_end, node_id, bs_node, meta)

        if cut_node is None:
            last_text = None
            for child in reversed(list(block_tag.descendants)):
                if isinstance(child, NavigableString) and child in self.node_map:
                    last_text = child
                    break
            if last_text is not None:
                cut_node = last_text
                cut_meta = self.node_map[last_text]
                cut_offset = len(self._current_node_text(cut_meta["id"], cut_meta))
            else:
                cut_offset = 0

        if block_tag.name == 'li':
            parent_list = block_tag.parent
            if not isinstance(parent_list, Tag):
                return "break"
            new_li = self.current_soup.new_tag('li')
            self._copy_attrs(block_tag, new_li)
            token = uuid.uuid4().hex
            new_li['data-editor-focus'] = token
            moved_any = False

            if isinstance(cut_node, NavigableString) and cut_meta is not None and cut_offset is not None:
                if not getattr(cut_node, 'parent', None) and "id" in cut_meta:
                    fresh, _ = self._get_bsnode_by_id(cut_meta["id"])
                    if fresh is not None:
                        cut_node = fresh
                node_text = self._current_node_text(cut_meta["id"], cut_meta)
                left = node_text[:cut_offset]
                right = node_text[cut_offset:]
                self._replace_bsnode_text(cut_node, left)
                if right:
                    new_li.append(NavigableString(right))
                    moved_any = True

            siblings_to_move = []
            found = False
            for child in list(block_tag.contents):
                if found:
                    siblings_to_move.append(child)
                if child is cut_node or (isinstance(child, Tag) and isinstance(cut_node, NavigableString) and cut_node in child.descendants):
                    found = True
            for n in siblings_to_move:
                n.extract()
                new_li.append(n)
                moved_any = True

            if not moved_any:
                new_li['data-editor-ephemeral'] = '1'
                new_li.append(NavigableString(self.PLACEHOLDER))

            block_tag.insert_after(new_li)
            self._post_reload_focus_token = token
            self._refresh_editor_from_soup()
            return "break"

        new_block = self.current_soup.new_tag(block_tag.name if block_tag.name in BLOCK_TAGS else 'p')
        self._copy_attrs(block_tag, new_block)
        token = uuid.uuid4().hex
        new_block['data-editor-focus'] = token
        moved_any = False

        if isinstance(cut_node, NavigableString) and cut_meta is not None and cut_offset is not None:
            if not getattr(cut_node, 'parent', None) and "id" in cut_meta:
                fresh, _ = self._get_bsnode_by_id(cut_meta["id"])
                if fresh is not None:
                    cut_node = fresh
            node_text = self._current_node_text(cut_meta["id"], cut_meta)
            left = node_text[:cut_offset]
            right = node_text[cut_offset:]
            self._replace_bsnode_text(cut_node, left)
            if right:
                new_block.append(NavigableString(right))
                moved_any = True

        siblings_to_move = []
        found_in_tree = False
        for child in list(block_tag.contents):
            if found_in_tree:
                siblings_to_move.append(child)
            if child is cut_node or (isinstance(child, Tag) and isinstance(cut_node, NavigableString) and cut_node in child.descendants):
                found_in_tree = True
        for n in siblings_to_move:
            n.extract()
            new_block.append(n)
            moved_any = True

        if not moved_any:
            new_block['data-editor-ephemeral'] = '1'
            new_block.append(NavigableString(self.PLACEHOLDER))

        self._insert_after_tag(block_tag, new_block, b_end)
        self._post_reload_focus_token = token
        self._refresh_editor_from_soup()
        return "break"




    def _index_tuple(self, idx):
        return tuple(map(int, str(idx).split('.')))

    def _nearest_block_after_index(self, index):
        candidates = []
        for tag in self.editor.tag_names():
            if not tag.startswith("block_"):
                continue
            ranges = self.editor.tag_ranges(tag)
            if not ranges:
                continue
            b_start = ranges[0]
            if self.editor.compare(b_start, ">=", index):
                candidates.append((b_start, tag))
        if not candidates:
            return None
        candidates.sort(key=lambda x: self._index_tuple(x[0]))
        return candidates[0][1]

    def _nearest_node_after_index(self, index):
        candidates = []
        for tag in self.editor.tag_names():
            if not tag.startswith("node_"):
                continue
            ranges = self.editor.tag_ranges(tag)
            if not ranges:
                continue
            n_start = ranges[0]
            if self.editor.compare(n_start, ">=", index):
                candidates.append((n_start, tag))
        if not candidates:
            return None
        candidates.sort(key=lambda x: self._index_tuple(x[0]))
        tag = candidates[0][1]
        for bs_node, meta in self.node_map.items():
            if meta["id"] == tag:
                return tag, bs_node, meta
        return None


    def _is_effectively_empty(self, tag):
        if not tag:
            return True
        media = {'img', 'video', 'iframe', 'table', 'form'}
        if any(isinstance(c, Tag) and c.name in media for c in tag.descendants):
            return False
        txt = tag.get_text().replace('\xa0', '').replace('\u200b', '').strip()
        return txt == ''


    def _refresh_editor_from_soup(self):
        self.editor.config(state=tk.NORMAL)
        self._load_body_into_editor()
        self._maybe_focus_after_reload(in_memory=True)

    def _block_tag_at_index(self, index):
        tags_here = self.editor.tag_names(index)
        bid = next((t for t in tags_here if t.startswith("block_")), None)
        if bid:
            return bid
        try:
            left = self.editor.index(f"{index}-1c")
            tags_left = self.editor.tag_names(left)
            bid = next((t for t in tags_left if t.startswith("block_")), None)
            if bid:
                return bid
        except tk.TclError:
            pass
        return self._nearest_block_before_index(index)


    def _nearest_block_before_index(self, index):
        candidates = []
        for tag in self.editor.tag_names():
            if not tag.startswith("block_"):
                continue
            ranges = self.editor.tag_ranges(tag)
            if not ranges:
                continue
            b_end = ranges[-1]
            if self.editor.compare(b_end, "<=", index):
                candidates.append((b_end, tag))
        if not candidates:
            return None
        candidates.sort(key=lambda x: list(map(int, str(x[0]).split('.'))))
        return candidates[-1][1]

    def _nodes_overlapping_range(self, start, end):
        id_to_meta = {meta["id"]: (bs_node, meta) for bs_node, meta in self.node_map.items()}
        result = []
        for tag in self.editor.tag_names():
            if not tag.startswith("node_"):
                continue
            if tag not in id_to_meta:
                continue
            ranges = self.editor.tag_ranges(tag)
            if not ranges:
                continue
            n_start, n_end = ranges[0], ranges[-1]
            if self.editor.compare(n_end, "<=", start):
                continue
            if self.editor.compare(n_start, ">=", end):
                continue
            bs_node, meta = id_to_meta[tag]
            result.append((n_start, n_end, tag, bs_node, meta))
        result.sort(key=lambda x: list(map(int, str(x[0]).split('.'))))
        return result

    def _display_to_original_offset(self, node_start, insert_index, meta):
        try:
            node_text_display = self.editor.get(node_start, self.editor.tag_ranges(meta["id"])[-1])
        except tk.TclError:
            return None
        bullet_len = 2 if meta["bullet"] and node_text_display.startswith('• ') else 0
        try:
            disp_from_node_start = max(0, len(self.editor.get(node_start, insert_index)) - bullet_len)
        except tk.TclError:
            return None
        disp_from_node_start = min(disp_from_node_start, len(meta["offset_map"]))
        if disp_from_node_start == 0:
            return 0
        if disp_from_node_start >= len(meta["offset_map"]):
            return meta["offset_map"][-1][1]
        return meta["offset_map"][disp_from_node_start][0]

    def _nearest_block_ancestor(self, node):
        cur = node.parent if hasattr(node, 'parent') else None
        while cur and getattr(cur, 'name', None) != '[document]':
            if cur.name in BLOCK_TAGS:
                return cur
            cur = cur.parent
        return None

    def _copy_attrs(self, src, dst):
        if not isinstance(src, Tag) or not isinstance(dst, Tag):
            return
        for k, v in self._safe_attrs(src).items():
            if k in ('id', 'data-editor-focus'):
                continue
            dst.attrs[k] = v


    def _get_node_at_index(self, index):
        tags = self.editor.tag_names(index)
        node_id = next((t for t in tags if t.startswith("node_")), None)
        if not node_id:
            return None, None, None
        for bs_node, meta in self.node_map.items():
            if meta["id"] == node_id:
                return node_id, bs_node, meta
        return None, None, None

    def _nearest_node_before_index(self, index):
        nodes = []
        for tag in self.editor.tag_names():
            if not tag.startswith("node_"):
                continue
            ranges = self.editor.tag_ranges(tag)
            if not ranges:
                continue
            start = ranges[0]
            end = ranges[-1]
            if self.editor.compare(end, "<=", index):
                nodes.append((end, tag))
        if not nodes:
            return None
        nodes.sort(key=lambda x: list(map(int, str(x[0]).split('.'))))
        tag = nodes[-1][1]
        for bs_node, meta in self.node_map.items():
            if meta["id"] == tag:
                return tag, bs_node, meta
        return None

    def _on_text_modified(self, event=None):
        pass

    def _scan_and_populate_files(self):
        if not utils.confirm_discard_changes(self):
            return
        self.html_files, _ = utils.general_html_find_files(config.HTML_SCAN_TARGET_PATHS_ABSOLUTE)
        self._filter_file_tree()
        self._reset_editor_state()

    def has_unsaved_changes(self):
        return bool(self.current_file_path and self.editor.edit_modified())

    def _text_editor_scan_files(self):
        self._scan_and_populate_files()

    def _filter_file_tree(self, *args):
        for i in self.file_tree.get_children():
            self.file_tree.delete(i)
        search_term = self.search_var.get().lower().replace("\\", "/")
        tree_data = defaultdict(list)
        for path in self.html_files:
            rel_path = os.path.relpath(path, config.APP_BASE_DIR).replace("\\", "/")
            if search_term in rel_path.lower():
                parts = rel_path.split('/')
                tree_data['/'.join(parts[:-1])].append(parts[-1])
        nodes = {}
        for path in sorted(tree_data.keys()):
            parts = path.split('/')
            parent_iid = ''
            if path:
                for i, part in enumerate(parts):
                    current_path = '/'.join(parts[:i+1])
                    if current_path not in nodes:
                        nodes[current_path] = self.file_tree.insert(parent_iid, 'end', text=part, open=bool(search_term))
                    parent_iid = nodes[current_path]
            for filename in sorted(tree_data[path]):
                full_path = os.path.join(config.APP_BASE_DIR, path, filename).replace("\\", "/")
                self.file_tree.insert(parent_iid, 'end', text=filename, values=[full_path])

    def _parse_html(self, content):
        try:
            return BeautifulSoup(content, 'lxml')
        except Exception:
            return BeautifulSoup(content, 'html.parser')

    def _reset_editor_state(self):
        self.current_file_path = None
        self.current_soup = None
        self.node_map = IdentityNodeMap()
        self.block_id_to_tag = {}
        self.editor.config(state=tk.NORMAL)
        self.editor.delete('1.0', tk.END)
        self.editor.config(state=tk.DISABLED)
        self.editor.edit_reset()
        for btn in [self.save_button, self.highlight_button, self.bold_button, self.link_button, self.font_size_btn, self.ul_button, self.ol_button]:
            btn.config(state=tk.DISABLED)
        self.app.set_status("Select a file to edit.")

    def _on_file_select(self, event=None):
        selection = self.file_tree.selection()
        if not selection:
            return
        item = self.file_tree.item(selection[0])
        if not item.get('values'):
            return
        file_path = item['values'][0]
        if self.current_file_path == file_path:
            return
        if self.editor.edit_modified():
            if not messagebox.askyesno("Unsaved Changes", "You have unsaved changes. Are you sure you want to switch files?"):
                self.file_tree.selection_remove(selection[0])
                return
        self.current_file_path = file_path
        self._load_file_into_editor()

    def _load_file_into_editor(self):
        if not self.current_file_path:
            return
        self.app.set_status(f"Loading {os.path.basename(self.current_file_path)}...")
        try:
            with open(self.current_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.current_soup = self._parse_html(content)
            self.editor.config(state=tk.NORMAL)
            self._load_body_into_editor()
            for btn in [self.save_button, self.highlight_button, self.bold_button, self.link_button, self.font_size_btn, self.ul_button, self.ol_button]:
                btn.config(state=tk.NORMAL)
            self.app.set_status(f"Editing {os.path.basename(self.current_file_path)}")
            self._maybe_focus_after_reload()
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Error Loading File", f"Could not parse the HTML file:\n{e}")
            self._reset_editor_state()

    def _collapse_with_map(self, s):
        if not s:
            return '', []
        if s.strip() == '':
            if '\n' in s or '\r' in s:
                return '', []
            return ' ', [(0, len(s))]
        out_chars = []
        map_pairs = []
        i = 0
        n = len(s)
        while i < n:
            c = s[i]
            if c.isspace():
                j = i + 1
                while j < n and s[j].isspace():
                    j += 1
                out_chars.append(' ')
                map_pairs.append((i, j))
                i = j
            else:
                out_chars.append(c)
                map_pairs.append((i, i + 1))
                i += 1
        return ''.join(out_chars), map_pairs


    def _load_body_into_editor(self):
        self.node_map = IdentityNodeMap()
        self.block_id_to_tag = {}
        self.editor.config(state=tk.NORMAL)
        self.editor.delete('1.0', tk.END)
        if self.current_soup and self.current_soup.body:
            self._traverse_and_insert(self.current_soup.body, set())
        self.editor.edit_modified(False)

    def _extract_font_size_from_style(self, style_str):
        if not style_str:
            return None
        m = re.search(r'font-size\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*px', style_str, flags=re.I)
        if not m:
            return None
        try:
            return float(m.group(1))
        except:
            return None

    def _px_to_editor_size(self, px_value):
        if px_value is None:
            px_value = WEBSITE_BASE_FONT_PX
        return max(1, int(round(px_value)))

    def _get_node_styles(self, node):
        is_bold = False
        is_link = False
        is_highlight = False
        font_size_px = WEBSITE_BASE_FONT_PX
        temp_node = node
        while temp_node and temp_node.name != '[document]':
            if temp_node.name in ['strong', 'b']:
                is_bold = True
            if temp_node.name == 'a':
                is_link = True
            attrs = self._safe_attrs(temp_node)
            classes = attrs.get('class') or []
            if isinstance(classes, str):
                classes = classes.split()
            if 'highlight' in classes:
                is_highlight = True
            style = attrs.get('style')
            if style:
                size = self._extract_font_size_from_style(style)
                if size:
                    font_size_px = size
                    break
            if temp_node.name == 'h1':
                font_size_px = WEBSITE_BASE_FONT_PX * 2.2
                break
            if temp_node.name == 'h2':
                font_size_px = WEBSITE_BASE_FONT_PX * 1.8
                break
            if temp_node.name == 'h3':
                font_size_px = WEBSITE_BASE_FONT_PX * 1.17
                break
            temp_node = temp_node.parent
        return is_bold, is_link, is_highlight, font_size_px

    def _ensure_size_tag(self, px_size, is_bold):
        editor_size = self._px_to_editor_size(px_size)
        key = (editor_size, bool(is_bold))
        if key in self.size_tag_cache:
            return self.size_tag_cache[key]
        tag_name = f"fs_{editor_size}{'_b' if is_bold else ''}"
        font_config = (self.app.default_font_family, editor_size)
        if is_bold:
            font_config += ('bold',)
        self.editor.tag_config(tag_name, font=font_config)
        self.size_tag_cache[key] = tag_name
        return tag_name


    def _make_unordered_list(self):
        self._apply_list('ul')

    def _make_ordered_list(self):
        self._apply_list('ol')

    def _collect_selected_blocks(self, sel_start, sel_end):
        blocks = []
        for tag in self.editor.tag_names():
            if not tag.startswith("block_"):
                continue
            ranges = self.editor.tag_ranges(tag)
            if not ranges:
                continue
            b_start, b_end = ranges[0], ranges[-1]
            if self.editor.compare(b_end, "<=", sel_start):
                continue
            if self.editor.compare(b_start, ">=", sel_end):
                continue
            bs_block = self.block_id_to_tag.get(tag)
            if isinstance(bs_block, Tag):
                blocks.append((self._index_tuple(b_start), bs_block))
        blocks.sort(key=lambda x: x[0])
        out = []
        seen = set()
        for _, b in blocks:
            if id(b) not in seen:
                seen.add(id(b))
                out.append(b)
        return out


    def _merge_adjacent_lists(self, list_tag):
        if not isinstance(list_tag, Tag):
            return
        changed = True
        while changed:
            changed = False
            prev_sib = list_tag.find_previous_sibling(True)
            if isinstance(prev_sib, Tag) and prev_sib.name == list_tag.name:
                for li in list(list_tag.find_all('li', recursive=False)):
                    prev_sib.append(li.extract())
                list_tag.decompose()
                list_tag = prev_sib
                changed = True
                continue
            next_sib = list_tag.find_next_sibling(True)
            if isinstance(next_sib, Tag) and next_sib.name == list_tag.name:
                for li in list(next_sib.find_all('li', recursive=False)):
                    list_tag.append(li.extract())
                next_sib.decompose()
                changed = True


    def _apply_list(self, list_type):
        if not self.current_soup:
            return
        try:
            sel_start = self.editor.index(tk.SEL_FIRST)
            sel_end = self.editor.index(tk.SEL_LAST)
            has_selection = True
        except tk.TclError:
            has_selection = False

        blocks_in_order = []
        if has_selection:
            blocks_in_order = self._collect_selected_blocks(sel_start, sel_end)
        else:
            try:
                insert_index = self.editor.index("insert")
            except tk.TclError:
                return
            block_id = self._block_tag_at_index(insert_index) or self._nearest_block_before_index(insert_index)
            if block_id and block_id in self.block_id_to_tag:
                b = self.block_id_to_tag[block_id]
                if b:
                    blocks_in_order.append(b)

        if not blocks_in_order:
            return

        all_li_same_parent_same_type = all(isinstance(b, Tag) and b.name == 'li' and getattr(b.parent, 'name', None) == list_type for b in blocks_in_order)
        if all_li_same_parent_same_type:
            parents = {b.parent for b in blocks_in_order}
            if len(parents) == 1:
                return

        groups = defaultdict(list)
        for b in blocks_in_order:
            p = getattr(b, 'parent', None)
            if isinstance(p, Tag):
                groups[p].append(b)

        for parent, blocks in groups.items():
            siblings_tags = [c for c in parent.children if isinstance(c, Tag)]
            ordered = []
            for b in blocks:
                if b in siblings_tags:
                    ordered.append((siblings_tags.index(b), b))
            if not ordered:
                continue
            ordered.sort(key=lambda x: x[0])

            runs = []
            cur = [ordered[0]]
            for i in range(1, len(ordered)):
                if ordered[i][0] == ordered[i-1][0] + 1:
                    cur.append(ordered[i])
                else:
                    runs.append(cur)
                    cur = [ordered[i]]
            runs.append(cur)

            for run in runs:
                first_block = run[0][1]
                new_list = self.current_soup.new_tag(list_type)
                first_block.insert_before(new_list)

                for _, blk in run:
                    if blk.name == 'li' and getattr(blk.parent, 'name', None) == list_type:
                        new_list.append(blk.extract())
                    else:
                        li = self.current_soup.new_tag('li')
                        while blk.contents:
                            li.append(blk.contents[0].extract())
                        blk.decompose()
                        new_list.append(li)

                self._merge_adjacent_lists(new_list)

        self._save_file()



    def _traverse_and_insert(self, element, bullets_inserted_set):
        if self._should_skip_node(element):
            return
        if isinstance(element, Comment) or getattr(element, "name", None) in ['script', 'style', 'noscript']:
            return
        if getattr(element, "name", None) == 'br':
            self.editor.insert(tk.END, '\n')
            return

        if isinstance(element, Tag):
            if element.name in ('ul', 'ol'):
                list_start = self.editor.index('end-1c')
                for child in element.children:
                    self._traverse_and_insert(child, bullets_inserted_set)
                list_end = self.editor.index('end-1c')
                if self.editor.compare(list_end, ">", list_start):
                    self._set_trailing_newlines(2)
                return

            if element.name == 'li':
                try:
                    last_char = self.editor.get('end-2c', 'end-1c')
                except tk.TclError:
                    last_char = ''
                if last_char and last_char != '\n':
                    self.editor.insert(tk.END, '\n')

                start_idx = self.editor.index('end-1c')
                self.editor.insert(tk.END, '• ')
                bullets_inserted_set.add(element)

                for child in element.children:
                    self._traverse_and_insert(child, bullets_inserted_set)

                end_idx = self.editor.index('end-1c')
                if self.editor.compare(end_idx, ">", start_idx):
                    block_id = f"block_{uuid.uuid4().hex}"
                    self.editor.tag_add(block_id, start_idx, end_idx)
                    self.block_id_to_tag[block_id] = element

                self._set_trailing_newlines(1)
                return

            if element.name in BLOCK_TAGS:
                start_idx = self.editor.index('end-1c')
                for child in element.children:
                    self._traverse_and_insert(child, bullets_inserted_set)
                end_idx = self.editor.index('end-1c')
                if self.editor.compare(end_idx, ">", start_idx):
                    block_id = f"block_{uuid.uuid4().hex}"
                    self.editor.tag_add(block_id, start_idx, end_idx)
                    self.block_id_to_tag[block_id] = element
                    self._set_trailing_newlines(2)
                return


            for child in element.children:
                self._traverse_and_insert(child, bullets_inserted_set)
            return

        if isinstance(element, NavigableString):
            original_text = str(element)
            if not element.find_parent(['pre', 'textarea']) and original_text.strip() == '' and ('\n' in original_text or '\r' in original_text):
                return
            if element.find_parent(['pre', 'textarea']):
                display_text = original_text
                offset_map = [(i, i + 1) for i in range(len(original_text))]
            else:
                display_text, offset_map = self._collapse_with_map(original_text)
            if display_text == '':
                return

            node_id = f"node_{uuid.uuid4().hex}"
            is_bold, is_link, is_highlight, font_size_px = self._get_node_styles(element.parent)
            tags_to_apply = [node_id]
            if is_link:
                tags_to_apply.append('link')
            if is_highlight:
                tags_to_apply.append('highlight')
            size_tag = self._ensure_size_tag(font_size_px, is_bold)
            tags_to_apply.append(size_tag)

            parent_li = element.find_parent('li')
            try:
                prev_two = self.editor.get('end-3c', 'end-1c')
            except tk.TclError:
                prev_two = ''
            if display_text.startswith(' ') and (not prev_two or prev_two.endswith('\n') or bool(parent_li)):
                display_text = display_text[1:]
                offset_map = offset_map[1:] if len(offset_map) > 1 else offset_map

            if display_text == '':
                return

            self.editor.insert(tk.END, display_text, tuple(tags_to_apply))
            self.node_map[element] = {
                "id": node_id,
                "offset_map": offset_map,
                "display_text": display_text,
                "bullet": False
            }
            return





    def _get_tag_text(self, tag_name):
        ranges = self.editor.tag_ranges(tag_name)
        if not ranges:
            return ''
        return self.editor.get(ranges[0], ranges[-1])

    def _strip_focus_attrs_in_memory(self):
        if not self.current_soup:
            return
        for tag in list(self.current_soup.find_all(attrs={"data-editor-focus": True})):
            if isinstance(tag, Tag) and 'data-editor-focus' in tag.attrs:
                del tag.attrs['data-editor-focus']

    def _write_current_soup(self, reload_editor=True, strip_focus_attrs=False):
        if not self.current_file_path or not self.current_soup:
            return False
        try:
            if strip_focus_attrs:
                for tag in self.current_soup.find_all(attrs={"data-editor-focus": True}):
                    if isinstance(tag, Tag) and 'data-editor-focus' in tag.attrs:
                        del tag.attrs['data-editor-focus']
            with utils.atomic_text_writer(self.current_file_path) as f:
                f.write(str(self.current_soup))
            if reload_editor:
                self._load_file_into_editor()
            else:
                self.app.set_status("Saved", duration_ms=1500)
            return True
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Save Error", f"An error occurred while saving the file:\n{e}")
            self.app.set_status("Save failed.", is_error=True)
            return False

    def _safe_attrs(self, tag):
        try:
            a = getattr(tag, 'attrs', None)
            return a if isinstance(a, dict) else {}
        except Exception:
            return {}


    def _cleanup_empty_blocks(self):
        if not self.current_soup:
            return
        protected_ids = {'header-placeholder', 'footer-placeholder', 'latest-news-grid'}
        removable = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote', 'div', 'section', 'article', 'aside'}
        media_tags = {'img', 'video', 'iframe', 'table', 'form'}
        for tag in list(self.current_soup.find_all(True)):
            if not isinstance(tag, Tag):
                continue
            attrs = self._safe_attrs(tag)
            if attrs.get('id') in protected_ids:
                continue
            if 'data-editor-ephemeral' in attrs:
                if self._is_effectively_empty(tag):
                    parent = tag.parent
                    tag.decompose()
                    if parent and isinstance(parent, Tag) and parent.name in ('ul', 'ol') and not parent.find('li'):
                        parent.decompose()
                    continue
                if isinstance(getattr(tag, 'attrs', None), dict):
                    tag.attrs.pop('data-editor-ephemeral', None)
            if tag.name in removable and 'data-editor-ephemeral' in attrs:
                has_media = any(isinstance(c, Tag) and c.name in media_tags for c in tag.descendants)
                if not has_media and self._is_effectively_empty(tag):
                    parent = tag.parent
                    tag.decompose()
                    if parent and isinstance(parent, Tag) and parent.name in ('ul', 'ol') and not parent.find('li'):
                        parent.decompose()



    def _save_file(self):
        if not self.current_file_path or not self.current_soup:
            return
        self.app.set_status("Saving...")
        try:
            self._reconcile_nodes_with_editor()
            self._purge_deleted_blocks_in_memory()
            if self._write_current_soup(reload_editor=True, strip_focus_attrs=True):
                self.app.set_status(f"Successfully saved {os.path.basename(self.current_file_path)}", duration_ms=3000)
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Save Error", f"An error occurred while saving the file:\n{e}")
            self.app.set_status("Save failed.", is_error=True)




    def _maybe_focus_after_reload(self, in_memory=False):
        if not self._post_reload_focus_token:
            return
        token = self._post_reload_focus_token
        target_tag = None
        for t in self.current_soup.find_all(attrs={"data-editor-focus": True}):
            if isinstance(t, Tag) and t.get('data-editor-focus') == token:
                target_tag = t
                break
        if not target_tag:
            self._post_reload_focus_token = None
            return
        target_node = None
        for child in target_tag.descendants:
            if isinstance(child, NavigableString):
                target_node = child
                break
        if target_node is None:
            placeholder_node = NavigableString(self.PLACEHOLDER)
            target_tag.append(placeholder_node)
            target_node = placeholder_node
            self._load_body_into_editor()
        meta = self.node_map.get(target_node)
        if not meta:
            self._load_body_into_editor()
            meta = self.node_map.get(target_node)
        if meta:
            ranges = self.editor.tag_ranges(meta["id"])
            if ranges:
                start = ranges[0]
                self.editor.mark_set("insert", start)
                self.editor.see("insert")
        if 'data-editor-focus' in target_tag.attrs:
            del target_tag.attrs['data-editor-focus']
            if in_memory:
                self._strip_focus_attrs_in_memory()
            else:
                self._write_current_soup(reload_editor=False, strip_focus_attrs=True)
        self._post_reload_focus_token = None

    def _calc_original_offsets(self, node_start, part_start, part_end, meta):
        node_text_display = self.editor.get(node_start, self.editor.tag_ranges(meta["id"])[-1])
        bullet_len = 2 if meta["bullet"] and node_text_display.startswith('• ') else 0
        start_disp = max(0, len(self.editor.get(node_start, part_start)) - bullet_len)
        end_disp = max(0, len(self.editor.get(node_start, part_end)) - bullet_len)
        start_disp = min(start_disp, len(meta["offset_map"]))
        end_disp = min(end_disp, len(meta["offset_map"]))
        if start_disp == end_disp:
            return None, None
        start_orig = meta["offset_map"][start_disp][0]
        end_orig = meta["offset_map"][end_disp - 1][1]
        return start_orig, end_orig

    def _perform_structural_change(self, builder):
        try:
            sel_start = self.editor.index(tk.SEL_FIRST)
            sel_end = self.editor.index(tk.SEL_LAST)
        except tk.TclError:
            messagebox.showinfo("Geen selectie", "Selecteer alstublieft tekst om opmaak toe te passen.")
            return
        tags_in_selection = self.editor.tag_names(sel_start)
        node_id = next((t for t in tags_in_selection if t.startswith("node_")), None)
        if not node_id:
            messagebox.showinfo("Selectiefout", "Opmaak moet worden toegepast binnen een enkele tekstblok.")
            return
        r = self.editor.tag_ranges(node_id)
        if not r or self.editor.compare(sel_end, '>', r[-1]):
            messagebox.showinfo("Selectiefout", "Opmaak moet worden toegepast binnen een enkele tekstblok.")
            return
        id_to_meta = {meta["id"]: (bs_node, meta) for bs_node, meta in self.node_map.items()}
        if node_id not in id_to_meta:
            return
        bs_node, meta = id_to_meta[node_id]
        if not bs_node or not bs_node.parent:
            return
        s, e = self._display_offsets_in_node(node_id, meta, sel_start, sel_end)
        if s >= e:
            return
        node_text = self._current_node_text(node_id, meta)
        before = node_text[:s]
        selected = node_text[s:e]
        after = node_text[e:]
        wrapped = builder(selected)
        bs_node.replace_with(NavigableString(before), wrapped, NavigableString(after))
        self.editor.edit_modified(True)
        self._save_file()

    def _perform_structural_change_across_nodes(self, builder):
        try:
            sel_start = self.editor.index(tk.SEL_FIRST)
            sel_end = self.editor.index(tk.SEL_LAST)
        except tk.TclError:
            messagebox.showinfo("Geen selectie", "Selecteer alstublieft tekst om opmaak toe te passen.")
            return
        id_to_meta = {meta["id"]: (bs_node, meta) for bs_node, meta in self.node_map.items()}
        overlaps = []
        for tag in self.editor.tag_names():
            if not tag.startswith("node_"):
                continue
            ranges = self.editor.tag_ranges(tag)
            if not ranges:
                continue
            node_start, node_end = ranges[0], ranges[-1]
            if self.editor.compare(node_end, "<=", sel_start):
                continue
            if self.editor.compare(node_start, ">=", sel_end):
                continue
            if tag in id_to_meta:
                bs_node, meta = id_to_meta[tag]
                if bs_node and bs_node.parent:
                    overlaps.append((node_start, node_end, tag, bs_node, meta))
        if not overlaps:
            return
        overlaps.sort(key=lambda x: list(map(int, str(x[0]).split('.'))))
        for node_start, node_end, tag, bs_node, meta in overlaps:
            part_start = sel_start if self.editor.compare(sel_start, ">", node_start) else node_start
            part_end = sel_end if self.editor.compare(sel_end, "<", node_end) else node_end
            s, e = self._display_offsets_in_node(tag, meta, part_start, part_end)
            if s >= e:
                continue
            node_text = self._current_node_text(tag, meta)
            before = node_text[:s]
            selected = node_text[s:e]
            after = node_text[e:]
            wrapped = builder(selected)
            bs_node.replace_with(NavigableString(before), wrapped, NavigableString(after))
        self.editor.edit_modified(True)
        self._save_file()


    def _apply_highlight(self):
        def builder(txt):
            t = self.current_soup.new_tag('span')
            t['class'] = 'highlight'
            t.string = txt
            return t
        self._perform_structural_change_across_nodes(builder)

    def _make_bold(self):
        def builder(txt):
            t = self.current_soup.new_tag('strong')
            t.string = txt
            return t
        self._perform_structural_change(builder)

    def _make_link(self):
        url = simpledialog.askstring("Link URL", "Voer de URL van de link in:", parent=self.app.root)
        if not url:
            return
        def builder(txt):
            t = self.current_soup.new_tag('a', href=url)
            t.string = txt
            return t
        self._perform_structural_change(builder)

    def _apply_font_size_from_ui(self):
        try:
            size = float(self.font_size_var.get())
        except ValueError:
            messagebox.showinfo("Lettergrootte", "Selecteer alstublieft een geldige lettergrootte.")
            return
        def builder(txt):
            t = self.current_soup.new_tag('span')
            t['style'] = f'font-size:{size}px;'
            t.string = txt
            return t
        self._perform_structural_change(builder)

    def _is_button_like(self, tag):
        attrs = self._safe_attrs(tag)
        classes = attrs.get('class') or []
        if isinstance(classes, str):
            classes = classes.split()
        if any(c.lower() in ('cta-button', 'button', 'btn', 'btn-primary', 'btn-secondary') for c in classes):
            return True
        if str(attrs.get('role', '')).lower() == 'button':
            return True
        return False

    def _clear_link_keep_anchor(self, link_tag):
        link_tag['href'] = ''
        self._save_file()


    def _show_context_menu(self, event):
        menu = tk.Menu(self.editor, tearoff=0)
        cursor_index = self.editor.index(f"@{event.x},{event.y}")
        tags = self.editor.tag_names(cursor_index)
        node_id = next((t for t in tags if t.startswith("node_")), None)
        id_to_node_map = {meta["id"]: bs_node for bs_node, meta in self.node_map.items()}
        if not node_id or not id_to_node_map.get(node_id):
            return
        bs_node = id_to_node_map.get(node_id)
        parent = bs_node.parent
        while parent and parent.name != '[document]':
            if parent.name == 'a':
                if self._is_button_like(parent):
                    menu.add_command(label="Link bewerken", command=lambda p=parent: self._edit_link(p))
                    menu.add_command(label="Link leegmaken", command=lambda p=parent: self._clear_link_keep_anchor(p))
                else:
                    menu.add_command(label="Link bewerken", command=lambda p=parent: self._edit_link(p))
                    menu.add_command(label="Link verwijderen", command=lambda p=parent: self._unwrap_tag(p))
            if parent.name in ['strong', 'b']:
                menu.add_command(label="Vetgedrukt verwijderen", command=lambda p=parent: self._unwrap_tag(p))
            if hasattr(parent, 'has_attr') and parent.has_attr('class') and 'highlight' in parent['class']:
                menu.add_command(label="Markering verwijderen", command=lambda p=parent: self._unwrap_tag(p))
            if hasattr(parent, 'has_attr') and parent.has_attr('style') and 'font-size' in parent['style']:
                menu.add_command(label="Verwijder lettergrootte", command=lambda p=parent: self._remove_font_size(p))
            parent = parent.parent
        if menu.index(tk.END) is not None:
            menu.tk_popup(event.x_root, event.y_root)


    def _edit_link(self, link_tag):
        current_href = link_tag.get('href', '')
        new_href = simpledialog.askstring("Link-URL bewerken", "Voer de nieuwe URL in:", initialvalue=current_href, parent=self.app.root)
        if new_href is not None:
            link_tag['href'] = new_href
            self._save_file()

    def _unwrap_tag(self, tag_to_unwrap):
        if getattr(tag_to_unwrap, 'name', None) == 'a' and self._is_button_like(tag_to_unwrap):
            messagebox.showinfo("Niet toegestaan", "Deze link is een knop. Verwijder de knop om de link te verwijderen.")
            return
        tag_to_unwrap.unwrap()
        self._save_file()


    def _remove_font_size(self, tag_with_style):
        old_style = tag_with_style.get('style', '')
        new_style = re.sub(r'font-size\s*:\s*[^;]+;?', '', old_style).strip()
        if new_style:
            tag_with_style['style'] = new_style
        else:
            if 'style' in tag_with_style.attrs:
                del tag_with_style['style']
        if tag_with_style.name == 'span' and not tag_with_style.attrs:
            tag_with_style.unwrap()
        self._save_file()

def create_text_editor_tab(parent_frame, app_instance):
    return TextEditorTab(parent_frame, app_instance)

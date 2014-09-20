from gzip import GzipFile
from os import makedirs
from os.path import dirname, join, abspath
from pickle import load, dump
import sublime
import sublime_plugin


class OrgmodeStore(sublime_plugin.EventListener):

    def __init__(self, *args, **kwargs):
        self.debug = False
        self.db = {}
        self.store = join(
            abspath(sublime.packages_path()),
            'Settings',
            'orgmode-store.bin.gz')
        try:
            makedirs(dirname(self.store))
        except:
            pass
        try:
            with GzipFile(self.store, 'rb') as f:
                self.db = load(f)
        except:
            self.db = {}

        self.on_load(sublime.active_window().active_view())
        for window in sublime.windows():
            self.on_load(window.active_view())

    def on_load(self, view):
        self.restore(view, 'on_load')

    def on_deactivated(self, view):
        window = view.window()
        if not window:
            window = sublime.active_window()
        index = window.get_view_index(view)
        if index != (-1, -1):  # if the view was not closed
            self.save(view, 'on_deactivated')

    def on_activated(self, view):
        self.restore(view, 'on_activated')

    def on_pre_close(self, view):
        self.save(view, 'on_pre_close')

    def on_pre_save(self, view):
        self.save(view, 'on_pre_save')

    def save(self, view, where='unknow'):
        if view is None or not view.file_name():
            return

        if view.is_loading():
            sublime.set_timeout(lambda: self.save(view, where), 100)
            return

        _id = self.view_index(view)
        if _id not in self.db:
            self.db[_id] = {}

        # if the result of the new collected data is different
        # from the old data, then will write to disk
        # this will hold the old value for comparison
        old_db = dict(self.db[_id])

        # if the size of the view change outside the application skip
        # restoration
        self.db[_id]['id'] = int(view.size())

        # marks
        self.db[_id]['m'] = [[item.a, item.b]
                       for item in view.get_regions("mark")]
        if self.debug:
            print('marks: ' + str(self.db[_id]['m']))

        # previous folding save, to be able to refold
        if 'f' in self.db[_id] and list(self.db[_id]['f']) != []:
            self.db[_id]['pf'] = list(self.db[_id]['f'])

        # folding
        self.db[_id]['f'] = [[item.a, item.b] for item in view.folded_regions()]
        if self.debug:
            print('fold: ' + str(self.db[_id]['f']))

        # write to disk only if something changed
        if old_db != self.db[_id] or where == 'on_deactivated':
            with GzipFile(self.store, 'wb') as f:
                dump(self.db, f, -1)

    def view_index(self, view):
        window = view.window()
        if not window:
            window = sublime.active_window()
        index = window.get_view_index(view)
        return str(window.id()) + str(index)

    def restore(self, view, where='unknow'):
        if view is None or not view.file_name():
            return

        if view.is_loading():
            sublime.set_timeout(lambda: self.restore(view, where), 100)
            return

        _id = self.view_index(view)
        if self.debug:
            print('-----------------------------------')
            print('RESTORING from: ' + where)
            print('file: ' + view.file_name())
            print('_id: ' + _id)

        if _id in self.db:
            # fold
            rs = []
            for r in self.db[_id]['f']:
                rs.append(sublime.Region(int(r[0]), int(r[1])))
            if len(rs):
                view.fold(rs)
                if self.debug:
                    print("fold: " + str(rs))

            # marks
            rs = []
            for r in self.db[_id]['m']:
                rs.append(sublime.Region(int(r[0]), int(r[1])))
            if len(rs):
                view.add_regions(
                    "mark", rs, "mark", "dot", sublime.HIDDEN | sublime.PERSISTENT)
                if self.debug:
                    print('marks: ' + str(self.db[_id]['m']))


class OrgmodeFoldingCommand(sublime_plugin.TextCommand):
    """
    Bind to TAB key, and if the current line is not
    a headline, a \t would be inserted.
    """

    def run(self, edit):
        (row,col) = self.view.rowcol(self.view.sel()[0].begin())
        line = row + 1
        print(line)
        for s in self.view.sel():
            r = self.view.full_line(s)
            if self._is_region_folded(r.b + 1, self.view):
                self.view.run_command("unfold")
                return

        pt = self.view.text_point(line, 0)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(pt))
        self.view.run_command("fold")

    def _is_region_folded(self, region, view):
        for i in view.folded_regions():
            if i.contains(region):
                return True
        return False

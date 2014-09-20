'''
Settings in orgmode.sublime-settings are:
- orgmode.open_link.resolvers: See DEFAULT_OPEN_LINK_RESOLVERS.
- orgmode.open_link.resolver.abstract.commands: See DEFAULT_OPEN_LINK_COMMANDS in resolver.abstract.
For more settings see headers of specific resolvers.
'''

import sys
import re
import os.path
import sublime
import sublime_plugin
import fnmatch
import datetime


try:
    import importlib
except ImportError:
    pass


DEFAULT_OPEN_LINK_RESOLVERS = [
    'http',
    'https',
    'prompt',
    'redmine',
    'jira',
    'crucible',
    'fisheye',
    'email',
    'local_file',
]


class OrgmodeNewTaskDocCommand(sublime_plugin.WindowCommand):

    def run(self):
        view = self.window.new_file()
        view.set_syntax_file('Packages/orgmode/orgmode.tmLanguage')


def find_resolvers():
    base = os.path.dirname(os.path.abspath(__file__))
    path = base + '/resolver'
    available_resolvers = {}
    for root, dirnames, filenames in os.walk(base + '/resolver'):
        for filename in fnmatch.filter(filenames, '*.py'):
            module_path = 'orgmode.resolver.' + filename.split('.')[0]
            if sys.version_info[0] < 3:
                module_path = 'resolver.' + filename.split('.')[0]
                name = filename.split('.')[0]
                module = __import__(module_path, globals(), locals(), name)
                module = reload(module)
            else:
                module = importlib.import_module(module_path)
            if '__init__' in filename or 'abstract' in filename:
                continue
            available_resolvers[filename.split('.')[0]] = module
    return available_resolvers
available_resolvers = find_resolvers()


class OrgmodeOpenLinkCommand(sublime_plugin.TextCommand):

    def __init__(self, *args, **kwargs):
        super(OrgmodeOpenLinkCommand, self).__init__(*args, **kwargs)
        settings = sublime.load_settings('orgmode.sublime-settings')
        wanted_resolvers = settings.get(
            'orgmode.open_link.resolvers', DEFAULT_OPEN_LINK_RESOLVERS)
        self.resolvers = [available_resolvers[name].Resolver(self.view)
                          for name in wanted_resolvers]

    def resolve(self, content):
        for resolver in self.resolvers:
            result = resolver.resolve(content)
            if result is not None:
                return resolver, result
        return None, None

    def is_valid_scope(self, sel):
        scope_name = self.view.scope_name(sel.end())
        return 'orgmode.link' in scope_name

    def extract_content(self, region):
        content = self.view.substr(region)
        if content.startswith('[[') and content.endswith(']]'):
            content = content[2:-2]
        return content

    def run(self, edit):
        view = self.view
        for sel in view.sel():
            if not self.is_valid_scope(sel):
                continue
            region = view.extract_scope(sel.end())
            content = self.extract_content(region)
            resolver, content = self.resolve(content)
            if content is None:
                sublime.error_message('Could not resolve link:\n%s' % content)
                continue
            resolver.execute(content)


class OrgmodeOpenPythonRefCommand(OrgmodeOpenLinkCommand):

    def __init__(self, *args, **kwargs):
        super(OrgmodeOpenPythonRefCommand, self).__init__(*args, **kwargs)
        pattern = r'.+", line (?P<line>\d+), in (?P<symbol>.+)$'
        self.regex = re.compile(pattern)

    def is_valid_scope(self, sel):
        scope_name = self.view.scope_name(sel.end())
        return 'filepath reference orgmode.python.traceback' in scope_name

    def extract_content(self, region):
        content = self.view.substr(region)
        outer_region = self.view.extract_scope(region.end() + 1)
        scope_name = self.view.scope_name(region.end() + 1)
        # print scope_name
        if 'reference orgmode.python.traceback' in scope_name:
            outer_content = self.view.substr(outer_region)
            # print outer_content
            match = self.regex.match(outer_content)
            if match:
                # print match.groupdict()
                content += ':%s' % match.group('line')
        return content


class OrgmodeCycleInternalLinkCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        view = self.view
        sels = view.sel()
        sel = sels[0]
        if 'orgmode.link.internal' not in view.scope_name(sel.end()):
            return
        region = view.extract_scope(sel.end())
        content = view.substr(region).strip()
        if content.startswith('{{') and content.endswith('}}'):
            content = '* %s' % content[2:-2]
        found = self.view.find(content, region.end(), sublime.LITERAL)
        if not found:  # Try wrapping around buffer.
            found = self.view.find(content, 0, sublime.LITERAL)
        same = region.a == found.a and region.b == found.b
        if not found or same:
            sublime.status_message('No sibling found for: %s' % content)
            return
        found = view.extract_scope(found.begin())
        sels.clear()
        sels.add(sublime.Region(found.begin()))
        try:
            import show_at_center_and_blink
            view.run_command('show_at_center_and_blink')
        except ImportError:
            view.show_at_center(found)


class AbstractCheckboxCommand(sublime_plugin.TextCommand):

    def __init__(self, *args, **kwargs):
        super(AbstractCheckboxCommand, self).__init__(*args, **kwargs)
        indent_pattern = r'^(\s*).*$'
        summary_pattern = r'(\[\d*[/]\d*\])'
        checkbox_pattern = r'(\[[X ]\])'
        self.indent_regex = re.compile(indent_pattern)
        self.summary_regex = re.compile(summary_pattern)
        self.checkbox_regex = re.compile(checkbox_pattern)

    def get_indent(self, content):
        if isinstance(content, sublime.Region):
            content = self.view.substr(content)
        match = self.indent_regex.match(content)
        indent = match.group(1)
        return indent

    def find_parent(self, region):
        view = self.view
        row, col = view.rowcol(region.begin())
        line = view.line(region)
        content = view.substr(line)
        # print content
        indent = len(self.get_indent(content))
        # print repr(indent)
        row -= 1
        found = False
        while row >= 0:
            point = view.text_point(row, 0)
            line = view.line(point)
            content = view.substr(line)
            if len(content.strip()):
                cur_indent = len(self.get_indent(content))
                if cur_indent < indent:
                    found = True
                    break
            row -= 1
        if found:
            # print row
            point = view.text_point(row, 0)
            line = view.line(point)
            return line

    def find_children(self, region):
        view = self.view
        row, col = view.rowcol(region.begin())
        line = view.line(region)
        content = view.substr(line)
        # print content
        indent = len(self.get_indent(content))
        # print repr(indent)
        row += 1
        child_indent = None
        children = []
        last_row, _ = view.rowcol(view.size())
        while row <= last_row:
            point = view.text_point(row, 0)
            line = view.line(point)
            content = view.substr(line)
            summary = self.get_summary(line)
            if summary and content.lstrip().startswith("*"):
                 break
            if self.checkbox_regex.search(content):
                cur_indent = len(self.get_indent(content))
                # check for end of descendants
                if cur_indent <= indent:
                    break
                # only immediate children
                if child_indent is None:
                    child_indent = cur_indent
                if cur_indent == child_indent:
                    children.append(line)
            row += 1
        return children

    def find_siblings(self, child, parent):
        view = self.view
        row, col = view.rowcol(parent.begin())
        parent_indent = self.get_indent(parent)
        child_indent = self.get_indent(child)
        # print '***', repr(parent_indent), repr(child_indent)
        siblings = []
        row += 1
        last_row, _ = view.rowcol(view.size())
        while row <= last_row:  # Don't go past end of document.
            line = view.text_point(row, 0)
            line = view.line(line)
            content = view.substr(line)
            # print content
            if len(content.strip()):
                cur_indent = self.get_indent(content)
                if len(cur_indent) <= len(parent_indent):
                    # print 'OUT'
                    break  # Indent same as parent found!
                if len(cur_indent) == len(child_indent):
                    # print 'MATCH'
                    siblings.append((line, content))
            row += 1
        return siblings

    def get_summary(self, line):
        view = self.view
        row, _ = view.rowcol(line.begin())
        content = view.substr(line)
        # print content
        match = self.summary_regex.search(content)
        if not match:
            return None
        # summary = match.group(1)
        # print(repr(summary))
        # print dir(match), match.start(), match.span()
        col_start, col_stop = match.span()
        return sublime.Region(
            view.text_point(row, col_start),
            view.text_point(row, col_stop),
        )

    def get_checkbox(self, line):
        view = self.view
        row, _ = view.rowcol(line.begin())
        content = view.substr(line)
        # print content
        match = self.checkbox_regex.search(content)
        if not match:
            return None
        # checkbox = match.group(1)
        # print repr(checkbox)
        # print dir(match), match.start(), match.span()
        col_start, col_stop = match.span()
        return sublime.Region(
            view.text_point(row, col_start),
            view.text_point(row, col_stop),
        )

    def is_checked(self, line):
        return '[X]' in self.view.substr(line)

    def recalc_summary(self, region):
        # print('recalc_summary')
        children = self.find_children(region)
        if not len(children) > 0:
            return (0, 0)
        # print children
        num_children = len(children)
        checked_children = len(
            [child for child in children if self.is_checked(child)])
        # print ('checked_children: ' + str(checked_children) + ', num_children: ' + str(num_children))
        return (num_children, checked_children)

    def update_line(self, edit, region, parent_update=True):
        print ('update_line', self.view.rowcol(region.begin())[0]+1)
        (num_children, checked_children) = self.recalc_summary(region)
        if not num_children > 0:
            return False
        # update region checkbox
        if checked_children == num_children:
            self.toggle_checkbox(edit, region, True)
        else:
            self.toggle_checkbox(edit, region, False)
        # update region summary
        self.update_summary(edit, region, checked_children, num_children)

        children = self.find_children(region)
        for child in children:
            line = self.view.line(child)
            summary = self.get_summary(self.view.line(child))
            if summary:
                return self.update_line(edit, line, parent_update=False)

        if parent_update:
            parent = self.find_parent(region)
            if parent:
                self.update_line(edit, parent)

        return True

    def update_summary(self, edit, region, checked_children, num_children):
        # print('update_summary', self.view.rowcol(region.begin())[0]+1)
        view = self.view
        summary = self.get_summary(region)
        if not summary:
            return False
        # print('checked_children: ' + str(checked_children) + ', num_children: ' + str(num_children))
        view.replace(edit, summary, '[%d/%d]' % (
            checked_children, num_children))

    def toggle_checkbox(self, edit, region, checked=None, recurse_up=False, recurse_down=False):
        # print 'toggle_checkbox', self.view.rowcol(region.begin())[0]+1
        view = self.view
        checkbox = self.get_checkbox(region)
        if not checkbox:
            return False
        # if checked is not specified, toggle checkbox
        if checked is None:
            checked = not self.is_checked(checkbox)
        view.replace(edit, checkbox, '[%s]' % (
            'X' if checked else ' '))
        if recurse_down:
            # all children should follow
            children = self.find_children(region)
            for child in children:
                self.toggle_checkbox(edit, child, checked, recurse_down=True)
        if recurse_up:
            # update parent
            parent = self.find_parent(region)
            if parent:
                self.update_line(edit, parent)


class OrgmodeToggleCheckboxCommand(AbstractCheckboxCommand):

    def run(self, edit):
        view = self.view
        backup = []
        for sel in view.sel():
            if 'orgmode.checkbox' not in view.scope_name(sel.end()):
                continue
            backup.append(sel)
            checkbox = view.extract_scope(sel.end())
            line = view.line(checkbox)
            self.toggle_checkbox(edit, line, recurse_up=True, recurse_down=True)
        view.sel().clear()
        for region in backup:
            view.sel().add(region)


class OrgmodeRecalcCheckboxSummaryCommand(AbstractCheckboxCommand):

    def run(self, edit):
        view = self.view
        backup = []
        for sel in view.sel():
            if 'orgmode.checkbox.summary' not in view.scope_name(sel.end()):
                continue
            backup.append(sel)
            summary = view.extract_scope(sel.end())
            line = view.line(summary)
            self.update_line(edit, line)
        view.sel().clear()
        for region in backup:
            view.sel().add(region)


class OrgmodeLinkCompletions(sublime_plugin.EventListener):

    def on_query_completions(self, view, prefix, locations):
        import os
        from glob import glob
        # print 'view =', view
        # print 'preifx =', prefix
        # print 'locations =', locations
        location = locations[0]
        if not 'orgmode.link' in view.scope_name(location):
            return []
        region = view.extract_scope(location)
        content = view.substr(region)
        inner_region = region
        if content.startswith('[[') and content.endswith(']]'):
            content = content[2:-2]
            inner_region = sublime.Region(region.begin() + 2, region.end() - 2)
        if not inner_region.contains(location):
            return []
        content = view.substr(sublime.Region(inner_region.begin(), location))
        content = os.path.expandvars(content)
        content = os.path.expanduser(content)
        # print 'region =', region
        # print 'content =', content
        path, base = os.path.split(content)
        # print 'split =', path, base
        if not len(path):
            path = os.path.dirname(view.file_name())
        if not os.path.exists(path):
            path = os.path.join(os.path.dirname(view.file_name()), path)
        # print 'path =', path, base
        pattern = os.path.join(path, '%s*' % base)
        # print 'pattern =', pattern
        files = glob(pattern)
        basename = os.path.basename
        isdir = os.path.isdir
        for pos, item in enumerate(files[:]):
            expr = basename(item)
            snippet = basename(item)
            if isdir(item):
                expr += '/'
                snippet += '/'
            files[pos] = (expr, snippet)
        # print 'files =', files
        if not files:
            return [(base + '/', base)]
        return files


class OrgmodeDateCompleter(sublime_plugin.EventListener):

    def on_query_completions(self, view, prefix, locations):
        if not has_file_ext(view, "org"):
            return []
        self.settings = sublime.load_settings('orgmode.sublime-settings')
        self.date_format = self.settings.get(
            'orgmode.autocomplete.date', "%Y-%m-%d %H:%M")
        self.date_format_cmd = self.settings.get(
            'orgmode.autocomplete.date.cmd', "date")

        return [
            (self.date_format_cmd, datetime.datetime.now().strftime(
                self.date_format)),
            ("week", str(datetime.datetime.now().isocalendar()[1])),
        ]

def has_file_ext(view, ext):
    """Returns ``True`` if view has file extension ``ext``.
    ``ext`` may be specified with or without leading ``.``.
    """
    if not view.file_name(): return False
    if not ext.strip().replace('.', ''): return False
  
    if not ext.startswith('.'):
        ext = '.' + ext
  
    return view.file_name().endswith(ext)
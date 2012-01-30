'''
Settings in Global.sublime-settings are:
- orgmode.open_link.resolvers: See DEFAULT_OPEN_LINK_RESOLVERS.
- orgmode.open_link.resolver.abstract.commands: See DEFAULT_OPEN_LINK_COMMANDS in resolver.abstract.
For more settings see headers of specific resolvers.
'''

import sys
import re
import os.path
import sublime
import sublime_plugin


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


def find_resolvers():
    from os.path import splitext
    from glob import glob
    path = 'resolver'
    files = glob('%s/*.py' % path)
    available_resolvers = dict()
    for pos, file_ in enumerate(files[:]):
        name = os.path.splitext(file_)[0]
        patharr = name.split(os.path.sep)
        module, name = '.'.join(patharr), patharr[-1:]
        module = __import__(module, globals(), locals(), name)
        module = reload(module)
        if '__init__' in file_ or 'abstract' in file_:
            continue
        name = name[0]
        # print name, module
        available_resolvers[name] = module
    return available_resolvers
available_resolvers = find_resolvers()


class OrgmodeOpenLinkCommand(sublime_plugin.TextCommand):

    def __init__(self, *args, **kwargs):
        super(OrgmodeOpenLinkCommand, self).__init__(*args, **kwargs)
        settings = sublime.load_settings('Global.sublime-settings')
        wanted_resolvers = settings.get('orgmode.open_link.resolvers', DEFAULT_OPEN_LINK_RESOLVERS)
        self.resolvers = [available_resolvers[name].Resolver(self.view) \
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
        self.indent_regex = re.compile(indent_pattern)
        self.summary_regex = re.compile(summary_pattern)

    def get_indent(self, content):
        if type(content) is sublime.Region:
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
        indent = self.get_indent(content)
        # print repr(indent)
        row -= 1
        found = False
        while row >= 0:
            point = view.text_point(row, 0)
            line = view.line(point)
            content = view.substr(line)
            if len(content.strip()):
                cur_indent = self.get_indent(content)
                if len(cur_indent) < len(indent):
                    found = True
                    break
            row -= 1
        if found:
            # print row
            point = view.text_point(row, 0)
            line = view.line(point)
            return line

    def find_child(self, region):
        view = self.view
        row, col = view.rowcol(region.begin())
        line = view.line(region)
        content = view.substr(line)
        # print content
        indent = self.get_indent(content)
        # print repr(indent)
        row += 1
        found = False
        last_row, _ = view.rowcol(view.size())
        while row <= last_row:
            point = view.text_point(row, 0)
            line = view.line(point)
            content = view.substr(line)
            if len(content.strip()):
                cur_indent = self.get_indent(content)
                if len(cur_indent) > len(indent):
                    found = True
                    break
            row += 1
        if found:
            # print row
            point = view.text_point(row, 0)
            line = view.line(point)
            return line

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
        # print repr(summary)
        # print dir(match), match.start(), match.span()
        col_start, col_stop = match.span()
        return sublime.Region(
            view.text_point(row, col_start),
            view.text_point(row, col_stop),
        )

    def recalc_summary(self, edit, parent, child):
        view = self.view
        # print parent, child
        summary = self.get_summary(parent)
        if not summary:
            return False
        children = self.find_siblings(view.line(child), parent)
        # print children
        num_children = len(children)
        checked_children = len(filter(lambda child: '[X]' in child[1], children))
        # print checked_children, num_children
        view.replace(edit, summary, '[%d/%d]' % (checked_children, num_children))
        return True


class OrgmodeToggleCheckboxCommand(AbstractCheckboxCommand):

    def run(self, edit):
        view = self.view
        backup = []
        for sel in view.sel():
            if 'orgmode.checkbox' not in view.scope_name(sel.end()):
                continue
            backup.append(sel)
            child = view.extract_scope(sel.end())
            content = view.substr(child)
            if '[X]' in content:
                content = content.replace('[X]', '[ ]')
            elif '[ ]' in content:
                content = content.replace('[ ]', '[X]')
            view.replace(edit, child, content)
            parent = self.find_parent(child)
            if parent:
                self.recalc_summary(edit, parent, child)
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
            parent = view.line(summary)
            child = self.find_child(parent)
            if child:
                self.recalc_summary(edit, parent, child)
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

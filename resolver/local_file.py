'''
Settings in Global.sublime-settings are:
- orgmode.open_link.resolver.local_file.pattern: See PATTERN_DEFAULT.
- orgmode.open_link.resolver.local_file.force_into_sublime: See FORCE_LOAD_DEFAULT.
'''

import re
import os
from fnmatch import fnmatch

import sublime

from abstract import AbstractLinkResolver


PATTERN_SETTING = 'orgmode.open_link.resolver.local_file.pattern'
PATTERN_DEFAULT = r'^(?P<filepath>.+?)(?::(?P<row>\d+)(?::(?P<col>\d+))?)?$'

FORCE_LOAD_SETTING = 'orgmode.open_link.resolver.local_file.force_into_sublime'
FORCE_LOAD_DEFAULT = ['*.txt', '*.org', '*.py', '*.rb', '*.html', '*.css', '*.js', '*.php', '*.c', '*.cpp', '*.h']


class Resolver(AbstractLinkResolver):
    '''
    @todo: If the link is a local org-file open it directly via sublime, otherwise use OPEN_LINK_COMMAND.
    '''

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        self.force_load_patterns = get(FORCE_LOAD_SETTING, FORCE_LOAD_DEFAULT)

    def file_is_excluded(self, filepath):
        basename = os.path.basename(filepath)
        for pattern in self.force_load_patterns:
            if fnmatch(basename, pattern):
                print 'found in force_load_patterns'
                return False
        #danne  hack here
        return True

        folder_exclude_patterns = self.settings.get('folder_exclude_patterns')
        if basename in folder_exclude_patterns:
            print 'found in folder_exclude_patterns'
            return True
        file_exclude_patterns = self.settings.get('file_exclude_patterns')
        for pattern in file_exclude_patterns:
            if fnmatch(basename, pattern):
                print 'found in file_exclude_patterns'
                return True
        return False

    def expand_path(self, filepath):
        filepath = os.path.expandvars(filepath)
        filepath = os.path.expanduser(filepath)

        # print filepath
        match = self.regex.match(filepath)
        if match:
            filepath, row, col = match.group('filepath'), match.group('row'), match.group('col')
            # print filepath, row, col
        else:
            row = None
            col = None

        drive, filepath = os.path.splitdrive(filepath)
        if not filepath.startswith('/'):  # If filepath is relative...
            cwd = os.path.dirname(self.view.file_name())
            testfile = os.path.join(cwd, filepath)
            if os.path.exists(testfile):  # See if it exists here...
                filepath = testfile
        #danne  hack here
        #filepath = ':'.join([drive, filepath]) if drive else filepath
        filepath = ''.join([drive, filepath]) if drive else filepath
        print 'filepath: '+filepath
        #danne  hack here
        #if os.path.exists(filepath) and not self.file_is_excluded(filepath):
        if not self.file_is_excluded(filepath):
            if row: filepath += ':%s' % row
            if col: filepath += ':%s' % col
            print 'file_is_excluded'
            self.view.window().open_file(filepath, sublime.ENCODED_POSITION)
            return True

        return filepath

    def replace(self, content):
        content = self.expand_path(content)
        return content

    def execute(self, content):
        if content is not True:
            print 'normal open'
            return super(Resolver, self).execute(content)

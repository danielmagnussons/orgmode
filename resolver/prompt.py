'''
Settings in Global.sublime-settings are:
- orgmode.open_link.resolver.prompt.pattern: See PATTERN_DEFAULT.
- orgmode.open_link.resolver.prompt.path: See PROMPT_DEFAULT.
'''

import re
import sys
import subprocess
import sublime
from abstract import AbstractRegexLinkResolver

DEFAULT_OPEN_PROMPT_LINK_COMMANDS = dict(
    darwin=['open'],
    win32=['cmd', '/C'],
    linux=['gnome-terminal'],
)


PATTERN_SETTING = 'orgmode.open_link.resolver.prompt.pattern'
PATTERN_DEFAULT = r'^(cmd:|prompt:)(?P<path>.+)$'
PROMPT_SETTING = 'orgmode.open_link.resolver.prompt.path'
PROMPT_DEFAULT_WIN32 = 'start cmd.exe /K "cd /d %s"'
PROMPT_DEFAULT_LINUX = '--working-directory=%s'


class Resolver(AbstractRegexLinkResolver):

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        self.link_commands = self.settings.get(
            'orgmode.open_link.resolver.abstract.commands', DEFAULT_OPEN_PROMPT_LINK_COMMANDS)
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        if sys.platform == 'win32':
            self.url = get(PROMPT_SETTING, PROMPT_DEFAULT_WIN32)
        else:
            self.url = get(PROMPT_SETTING, PROMPT_DEFAULT_LINUX)

    def replace(self, match):
        return self.url % match.group('path')

    def get_link_command(self):
        platform = sys.platform
        for key, val in self.link_commands.iteritems():
            if key in platform:
                return val
        return None

    def execute(self, content):
        command = self.get_link_command()
        if not command:
            sublime.error_message(
                'Could not get link opener command.\nNot yet supported.')
            return None

        content = content.encode(sys.getfilesystemencoding())

        if sys.platform != 'win32':
            cmd = command + [content]
        else:
            cmd = command + ['start ' + content]

        print 'PROMPT*****'
        print repr(content)
        print cmd
        sublime.status_message('Executing: %s' % cmd)
        if sys.platform != 'win32':
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        stdout, stderr = process.communicate()
        if stdout:
            stdout = unicode(stdout, sys.getfilesystemencoding())
            sublime.status_message(stdout)
        if stderr:
            stderr = unicode(stderr, sys.getfilesystemencoding())
            sublime.error_message(stderr)

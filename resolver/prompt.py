
import re
import sys
import subprocess
import sublime
from .abstract import AbstractRegexLinkResolver

DEFAULT_OPEN_PROMPT_LINK_COMMANDS = dict(
    darwin=['open', '-a', 'Terminal'],
    win32=['cmd'],
    linux=['gnome-terminal'],
)


PATTERN_SETTING = 'orgmode.open_link.resolver.prompt.pattern'
PATTERN_DEFAULT = r'^(cmd:|prompt:)(?P<path>.+)$'
PROMPT_SETTING = 'orgmode.open_link.resolver.prompt.path'
PROMPT_DEFAULT_WIN32 = '%s'
PROMPT_DEFAULT_LINUX = '--working-directory=%s'


class Resolver(AbstractRegexLinkResolver):

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        self.link_commands = self.settings.get(
            'orgmode.open_link.resolver.abstract.commands', DEFAULT_OPEN_PROMPT_LINK_COMMANDS)
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        if sys.platform == 'win32' or sys.platform == 'darwin':
            self.url = get(PROMPT_SETTING, PROMPT_DEFAULT_WIN32)
        else:
            self.url = get(PROMPT_SETTING, PROMPT_DEFAULT_LINUX)
 
    def replace(self, match):
        return self.url % match.group('path')

    def get_link_command(self):
        platform = sys.platform
        for key, val in self.link_commands.items():
            if key in platform:
                return val
        return None

    def execute(self, content):
        command = self.get_link_command()
        if not command:
            sublime.error_message(
                'Could not get link opener command.\nNot yet supported.')
            return None

        if sys.version_info[0] < 3:
            content = content.encode(sys.getfilesystemencoding())

        if sys.platform != 'win32':
            cmd = command + [content]
        else:
            cmd = 'cmd /C start cmd.exe /K "cd /d '+content+'"'

        print('PROMPT*****')
        print(repr(content))
        print(cmd)
        # \"cd /d c:\dev\apps\"' is not recognized as an internal or external command,
        sublime.status_message('Executing: %s' % cmd)
        if sys.platform != 'win32':
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        stdout, stderr = process.communicate()
        if stdout:
            stdout = str(stdout, sys.getfilesystemencoding())
            sublime.status_message(stdout)
        if stderr:
            stderr = str(stderr, sys.getfilesystemencoding())
            sublime.error_message(stderr)

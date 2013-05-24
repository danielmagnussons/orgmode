
import sys
import re
import subprocess
import sublime
from .abstract import AbstractRegexLinkResolver

try:
    import urllib.request, urllib.parse, urllib.error
except ImportError:
    import urllib



PATTERN_SETTING = 'orgmode.open_link.resolver.http.pattern'
PATTERN_DEFAULT = r'^(http):(?P<url>.+)$'
URL_SETTING = 'orgmode.open_link.resolver.http.url'
URL_DEFAULT = 'http:%s'


DEFAULT_OPEN_HTTP_LINK_COMMANDS = dict(
    darwin=['open'],
    win32=['cmd', '/C'],
    linux=['xdg-open'],
)


class Resolver(AbstractRegexLinkResolver):

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        self.url = get(URL_SETTING, URL_DEFAULT)
        self.link_commands = self.settings.get(
            'orgmode.open_link.resolver.abstract.commands', DEFAULT_OPEN_HTTP_LINK_COMMANDS)

    def replace(self, match):
        return self.url % match.group('url')

    def execute(self, content):
        command = self.get_link_command()
        if not command:
            sublime.error_message(
                'Could not get link opener command.\nNot yet supported.')
            return None
            
        # cmd.exe quote is needed, http://ss64.com/nt/syntax-esc.html
        # escape these: ^\  ^&  ^|  ^>  ^<  ^^
        if sys.platform == 'win32':
            content = content.replace("^", "^^")
            content = content.replace("&", "^&")
            content = content.replace("\\", "^\\")
            content = content.replace("|", "^|")
            content = content.replace("<", "^<")
            content = content.replace(">", "^>")


        if sys.version_info[0] < 3:
            content = content.encode(sys.getfilesystemencoding())

        if sys.platform != 'win32':
            cmd = command + [content]
        else:
            cmd = command + ['start ' + content]

        print('HTTP*****')
        print(repr(content), content)
        print(repr(cmd))
        print(cmd)
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

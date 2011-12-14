'''
Settings in Global.sublime-settings are:
- orgmode.open_link.resolver.prompt.pattern: See PATTERN_DEFAULT.
- orgmode.open_link.resolver.prompt.path: See PROMPT_DEFAULT.
'''

import re

from abstract import AbstractRegexLinkResolver


PATTERN_SETTING = 'orgmode.open_link.resolver.prompt.pattern'
PATTERN_DEFAULT = r'^(cmd:|prompt:)(?P<path>.+)$'
PROMPT_SETTING = 'orgmode.open_link.resolver.prompt.path'
PROMPT_DEFAULT = 'start cmd.exe /K "cd /d %s"'


class Resolver(AbstractRegexLinkResolver):

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        self.url = get(PROMPT_SETTING, PROMPT_DEFAULT)

    def replace(self, match):
        return self.url % match.group('path')

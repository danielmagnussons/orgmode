'''
Settings in Global.sublime-settings are:
- orgmode.open_link.resolver.crucible.pattern: See PATTERN_DEFAULT.
- orgmode.open_link.resolver.crucible.url: See URL_DEFAULT.
'''

import re

from abstract import AbstractRegexLinkResolver


PATTERN_SETTING = 'orgmode.open_link.resolver.crucible.pattern'
PATTERN_DEFAULT = r'^(crucible|cru|cr):(?P<review>.+)$'
URL_SETTING = 'orgmode.open_link.resolver.crucible.url'
URL_DEFAULT = 'http://sandbox.fisheye.atlassian.com/cru/%s'


class Resolver(AbstractRegexLinkResolver):

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        self.url = get(URL_SETTING, URL_DEFAULT)

    def replace(self, match):
        return self.url % match.group('review')

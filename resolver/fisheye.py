'''
Settings in Global.sublime-settings are:
- orgmode.open_link.resolver.fisheye.pattern: See PATTERN_DEFAULT.
- orgmode.open_link.resolver.fisheye.url: See URL_DEFAULT.
'''

import re

from abstract import AbstractRegexLinkResolver


PATTERN_SETTING = 'orgmode.open_link.resolver.fisheye.pattern'
PATTERN_DEFAULT = r'^(fisheye|fish|fe):(?P<repo>[^/]+)(/(?P<rev>.+))?$'
URL_SETTING = 'orgmode.open_link.resolver.fisheye.url'
URL_DEFAULT = 'http://sandbox.fisheye.atlassian.com/changelog/%s'


class Resolver(AbstractRegexLinkResolver):

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        self.url = get(URL_SETTING, URL_DEFAULT)

    def replace(self, match):
        match = match.groupdict()
        url = self.url % match['repo']
        if match['rev']:
            url += '?cs=%s' % match['rev']
        return url

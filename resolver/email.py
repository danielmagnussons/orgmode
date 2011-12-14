'''
Settings in Global.sublime-settings are:
- orgmode.open_link.resolver.email.pattern: See PATTERN_DEFAULT.
- orgmode.open_link.resolver.email.url: See URL_DEFAULT.
'''

import re

from abstract import AbstractRegexLinkResolver


PATTERN_SETTING = 'orgmode.open_link.resolver.email.pattern'
PATTERN_DEFAULT = r'^(?P<type>email|mailto):(?P<email>[^/]+)(/(?P<subject>.+))?$'
URL_SETTING = 'orgmode.open_link.resolver.email.url'
URL_DEFAULT = 'mailto:%s'


class Resolver(AbstractRegexLinkResolver):

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        self.url = get(URL_SETTING, URL_DEFAULT)

    def replace(self, match):
        match = match.groupdict()
        # print match
        if match['type'] == 'mailto':
            url = self.url % match['email']
            if match['subject']:
                url += '?subject=%s' % match['subject']
            return url
        if match['type'] == 'email':
            return dict(email=match['email'], path=match['subject'])

    def execute(self, content):
        if type(content) is dict and 'email' in content:
            import sublime
            # TODO Implement email opener here.
            sublime.error_message('Email opener not implemented yet.')
            raise NotImplemented()
        else:
            return super(Resolver, self).execute(content)

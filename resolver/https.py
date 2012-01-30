'''
Settings in Global.sublime-settings are:
- orgmode.open_link.resolver.http.pattern: See PATTERN_DEFAULT.
- orgmode.open_link.resolver.http.url: See URL_DEFAULT.
'''

import re
import urllib
import sys
import subprocess

import sublime

from abstract import AbstractRegexLinkResolver

#TODO: support https...!
PATTERN_SETTING = 'orgmode.open_link.resolver.https.pattern'
PATTERN_DEFAULT = r'^(https):(?P<url>.+)$'
URL_SETTING = 'orgmode.open_link.resolver.https.url'
URL_DEFAULT = 'https:%s'



DEFAULT_OPEN_HTTP_LINK_COMMANDS = dict(
    # Standard universal can opener for OSX.
    darwin=['open'],
    win32=['cmd', '/C'],
)


class Resolver(AbstractRegexLinkResolver):

    def __init__(self, view):
        super(Resolver, self).__init__(view)
        get = self.settings.get
        pattern = get(PATTERN_SETTING, PATTERN_DEFAULT)
        self.regex = re.compile(pattern)
        self.url = get(URL_SETTING, URL_DEFAULT)
        self.link_commands = self.settings.get('orgmode.open_link.resolver.abstract.commands', DEFAULT_OPEN_HTTP_LINK_COMMANDS)

    def replace(self, match):    	
        return self.url % match.group('url')

    def execute(self, content):
        command = self.get_link_command()
        if not command:
            sublime.error_message('Could not get link opener command.\nNot yet supported.')
            return None
        
        #TODO: abit windows hacky here.
        #works: cmd /c "start http://www.sublimetext.com/forum/viewtopic.php?f=5^&t=916"
        #cmd.exe quote is needed, http://ss64.com/nt/syntax-esc.html
        #escape these: ^\  ^&  ^|  ^>  ^<  ^^ 
        content = content.replace("^", "^^");
        content = content.replace("&", "^&");
        content = content.replace("\\", "^\\");
        content = content.replace("|", "^|");
        content = content.replace("<", "^<");
        content = content.replace(">", "^>");
        
        content = content.encode(sys.getfilesystemencoding())        
        cmd = command + ['start '+content]

        print 'HTTP*****'
        print repr(content), content
        print repr(cmd)
        print cmd
        sublime.status_message('Executing: %s' % cmd)
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        stdout, stderr = process.communicate()
        if stdout:
            stdout = unicode(stdout, sys.getfilesystemencoding())
            sublime.status_message(stdout)
        if stderr:
            stderr = unicode(stderr, sys.getfilesystemencoding())
            sublime.error_message(stderr)
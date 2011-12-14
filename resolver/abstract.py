# -*- coding: utf-8 -*-
'''
Settings in Global.sublime-settings are:
- orgmode.open_link.resolver.abstract.commands: See DEFAULT_OPEN_LINK_COMMANDS.
- orgmode.open_link.resolver.abstract.arg_list_wrapper: Optional wrapper for e.g. virtualenv.
'''

import sys
import subprocess

import sublime


DEFAULT_OPEN_LINK_COMMANDS = dict(
    # Standard universal can opener for OSX.
    darwin=['open'],

    # Found at:
    # - http://frank.zinepal.com/open-a-file-in-the-default-application-using
    # - http://commandwindows.com/tipsandtricks.htm#startcommand

    win32=['cmd', '/C', 'start'],

    # Dunno yet - help anyone?
    # linux= FIXME ???
)


class AbstractLinkResolver(object):

    def __init__(self, view):
        super(AbstractLinkResolver, self).__init__()
        self.view = view
        self.settings = sublime.load_settings('Global.sublime-settings')
        self.link_commands = self.settings.get('orgmode.open_link.resolver.abstract.commands', DEFAULT_OPEN_LINK_COMMANDS)

    def extract(self, content):
        return content

    def replace(self, content):
        return content

    def resolve(self, content):
        match = self.extract(content)
        if not match:
            return None
        return self.replace(match)

    def get_link_command(self):
        platform = sys.platform
        for key, val in self.link_commands.iteritems():
            if key in platform:
                return val
        return None

    def execute(self, content):
        command = self.get_link_command()
        if not command:
            sublime.error_message('Could not get link opener command.\nPlatform not yet supported.')
            return None
        
        content = content.encode(sys.getfilesystemencoding())
        cmd = command + [content]
        arg_list_wrapper = self.settings.get("orgmode.open_link.resolver.abstract.arg_list_wrapper", [])
        if arg_list_wrapper:  # NOTE never use shell=True below.
            cmd = arg_list_wrapper + [' '.join(cmd)]
            source_filename = '\"'+self.view.file_name()+'\"'
            cmd += [source_filename]
            #TODO: hack here (outcommented)
            #cmd += ['--origin', source_filename, '--quiet']
        print '*****'
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
        


class AbstractRegexLinkResolver(AbstractLinkResolver):

    def __init__(self, view):
        super(AbstractRegexLinkResolver, self).__init__(view)
        self.regex = None

    def extract(self, content):
        if self.regex is None:
            return content
        match = self.regex.match(content)
        return match

    def replace(self, match):
        return match.groups()[1]

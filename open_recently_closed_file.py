import sublime, sublime_plugin
import os
import hashlib

# Plugin to provide access to the history of accessed files
# https://gist.github.com/gists/1133602
# 
# To run the plugin:
# view.run_command("open_recently_closed_file")
# Or add keymap entries:
# { "keys": ["ctrl+shift+t"], "command": "open_recently_closed_file"},
# { "keys": ["ctrl+alt+shift+t"], "command": "open_recently_closed_file", "args": {"show_quick_panel": false}  },
# { "keys": ["ctrl+alt+shift+t"], "command": "open_recently_closed_file", "args": {"current_project_only": false}  },
# TODO use api function to get current project name rather than a hash of the folder names
HISTORY_SETTINGS_FILE = 'FileHistory.sublime-settings'
HISTORY_MAX_ENTRIES=100

def get_history(setting_name):
    """load the history using sublime's built-in functionality for accessing settings"""
    history = sublime.load_settings(HISTORY_SETTINGS_FILE)
    if history.has(setting_name):
        return clean_history(setting_name)
    else:
        return []

def set_history(setting_name, setting_values):
    """save the history using sublime's built-in functionality for accessing settings"""
    history = sublime.load_settings(HISTORY_SETTINGS_FILE)
    history.set(setting_name, setting_values)
    sublime.save_settings(HISTORY_SETTINGS_FILE)

def clean_history(setting_name):
    # Get a list of files that no longer exist
    history = sublime.load_settings(HISTORY_SETTINGS_FILE)
    file_history = history.get(setting_name)
    missing_files = []
    for filename in file_history:
        if not os.path.exists(filename):
            missing_files.append(filename)

    # Remove the missing files from the setting and save
    for filename in missing_files:
        while filename in file_history:
            file_history.remove(filename)
    history.set(setting_name, file_history)
    return file_history

def get_current_project_hash():
    m = hashlib.md5()
    for path in sublime.active_window().folders():
        m.update(path)
    return m.hexdigest()


class OpenRecentlyClosedFileEvent(sublime_plugin.EventListener):
    """class to keep a history of the files that have been opened and closed"""

    def on_close(self, view):
        self.add_to_history(view, 'closed', 'opened')

        project_name = get_current_project_hash()
        self.add_to_history(view, project_name+'_closed', project_name+'_opened')

    def on_load(self, view):
        self.add_to_history(view, 'opened', 'closed')

        project_name = get_current_project_hash()
        self.add_to_history(view, project_name+'_opened', project_name+'_closed')

    def add_to_history(self, view, add_to_setting, remove_from_setting):
        filename = os.path.normpath(view.file_name()) if view.file_name() else None
        if filename != None:
            add_to_list = get_history(add_to_setting)
            remove_from_list = get_history(remove_from_setting)

            # remove this file from both of the lists
            while filename in remove_from_list:
                remove_from_list.remove(filename)
            while filename in add_to_list:
                add_to_list.remove(filename)

            # add this file to the top of the "add_to_list" (but only if the file actually exists)
            if os.path.exists(filename):
                add_to_list.insert(0, filename)

            # write the history back (making sure to limit the length of the histories)
            set_history(add_to_setting, add_to_list[0:HISTORY_MAX_ENTRIES])
            set_history(remove_from_setting, remove_from_list[0:HISTORY_MAX_ENTRIES])

class OpenRecentlyClosedFileCommand(sublime_plugin.WindowCommand):
    """class to either open the last closed file or show a quick panel with the file access history (closed files first)"""

    def run(self, show_quick_panel=True, current_project_only=True):
        self.reload_history(current_project_only)
        if show_quick_panel:
            self.window.show_quick_panel(self.display_list, self.open_file, True)
        else:
            self.open_file(0)

    def reload_history(self, current_project_only):
        # get the file history (put the list of closed files first)
        history = sublime.load_settings(HISTORY_SETTINGS_FILE)
        if current_project_only:
            project_name = get_current_project_hash()
            self.file_list = get_history(project_name+'_closed') + get_history(project_name+'_opened')
        else:
            self.file_list = get_history('closed') + get_history('opened')

        # prepare the display list with file name and path separated
        self.display_list = []
        for filePath in self.file_list:
            self.display_list.append([os.path.basename(filePath), os.path.dirname(filePath)])

    def open_file(self, index):
        if index >= 0 and len(self.file_list) > index:
            self.window.open_file(self.file_list[index])

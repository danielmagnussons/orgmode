
'''
http://www.sublimetext.com/forum/viewtopic.php?f=5&t=2738

https://github.com/optilude/SublimeTextMisc


Put this in your "Packages" directory and then configure "Key bindings - User" to use it. I use these keybindings for it on OS X:

  { "keys": ["alt+left"], "command": "navigation_history_back"},
  { "keys": ["alt+right"], "command": "navigation_history_forward"}

'''


import sublime, sublime_plugin
from collections import deque

MAX_SIZE = 64
LINE_THRESHOLD = 2

class Location(object):
    """A location in the history
    """
    def __init__(self, path, line, col):
        self.path = path
        self.line = line
        self.col = col
    
    def __eq__(self, other):
        return self.path == other.path and self.line == other.line
    
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __nonzero__(self):
        return (self.path is not None and self.line is not None)

    def near(self, other):
        return self.path == other.path and abs(self.line - other.line) <= LINE_THRESHOLD

    def copy(self):
        return Location(self.path, self.line, self.col)

class History(object):
    """Keep track of the history for a single window
    """

    def __init__(self, max_size=MAX_SIZE):
        self._current = None                # current location as far as the
                                            # history is concerned
        self._back = deque([], max_size)    # items before self._current
        self._forward = deque([], max_size) # items after self._current
        
        self._last_movement = None          # last recorded movement
    
    def record_movement(self, location):
        """Record movement to the given location, pushing history if
        applicable
        """

        if location:
            if self.has_changed(location):
                self.push(location)
            self.mark_location(location)

    def mark_location(self, location):
        """Remember the current location, for the purposes of being able
        to do a has_changed() check.
        """
        self._last_movement = location.copy()
    
    def has_changed(self, location):
        """Determine if the given location combination represents a
        significant enough change to warrant pushing history.
        """

        return self._last_movement is None or not self._last_movement.near(location)
    
    def push(self, location):
        """Push the given location to the back history. Clear the forward
        history.
        """

        if self._current is not None:
            self._back.append(self._current.copy())
        self._current = location.copy()
        self._forward.clear()

    def back(self):
        """Move backward in history, returning the location to jump to.
        Returns None if no history.
        """

        if not self._back:
            return None
        
        self._forward.appendleft(self._current)
        self._current = self._back.pop()
        self._last_movement = self._current # preempt, so we don't re-push
        return self._current

    def forward(self):
        """Move forward in history, returning the location to jump to.
        Returns None if no history.
        """

        if not self._forward:
            return None
        
        self._back.append(self._current)
        self._current = self._forward.popleft()
        self._last_movement = self._current # preempt, so we don't re-push
        return self._current

_histories = {} # window id -> History

def get_history():
    """Get a History object for the current window,
    creating a new one if required
    """

    window = sublime.active_window()
    if window is None:
        return None

    window_id = window.id()
    history = _histories.get(window_id, None)
    if history is None:
        _histories[window_id] = history = History()
    return history

class NavigationHistoryRecorder(sublime_plugin.EventListener):
    """Keep track of history
    """

    def on_selection_modified(self, view):
        """When the selection is changed, possibly record movement in the
        history
        """
        history = get_history()
        if history is None:
            return

        path = view.file_name()
        row, col = view.rowcol(view.sel()[0].a)
        history.record_movement(Location(path, row + 1, col + 1))
    
    # def on_close(self, view):
    #     """When a view is closed, check to see if the window was closed too
    #     and clean up orphan histories
    #     """
    #
    #     # XXX: This doesn't work - event runs before window is removed
    #     # from sublime.windows()
    #
    #     windows_with_history = set(_histories.keys())
    #     window_ids = set([w.id() for w in sublime.windows()])
    #     closed_windows = windows_with_history.difference(window_ids)
    #     for window_id in closed_windows:
    #         del _histories[window_id]

class NavigationHistoryBack(sublime_plugin.TextCommand):
    """Go back in history
    """

    def run(self, edit):
        history = get_history()
        if history is None:
            return

        location = history.back()
        if location:
            window = sublime.active_window()
            window.open_file("%s:%d:%d" % (location.path, location.line, location.col), sublime.ENCODED_POSITION)

class NavigationHistoryForward(sublime_plugin.TextCommand):
    """Go forward in history
    """

    def run(self, edit):
        history = get_history()
        if history is None:
            return

        location = history.forward()
        if location:
            window = sublime.active_window()
            window.open_file("%s:%d:%d" % (location.path, location.line, location.col), sublime.ENCODED_POSITION)
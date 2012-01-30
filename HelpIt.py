'''
    Integrated from http://www.sublimetext.com/forum/viewtopic.php?f=5&t=2674
    Plugin inspired and modified from http://www.sublimetext.com/forum/viewtopic.php?f=5&t=2242
    
    keys;
        { "keys": ["alt+f1"], "command": "help_it" }
'''
import sublime
import sublime_plugin
import webbrowser
import re

class helpItCommand(sublime_plugin.TextCommand):

    """
    This will search a word in a language's documenation or google it with it's scope otherwise
    """

    def run(self, edit):
        if len(self.view.file_name()) > 0:
            settings = sublime.load_settings('HelpIt.sublime-settings');
            item = None
            word = self.view.substr(self.view.word(self.view.sel()[0].begin()))
            scope = self.view.scope_name(self.view.sel()[0].begin()).strip()
            getlang = scope.split('.')
            language = getlang[-1]
            if language == 'basic':
                language = getlang[-2]
            
            if language == 'html': #HTML shows up A LOT for internal CSS, PHP and JS
                if 'php' in getlang:
                    language = 'php'
                elif 'js' in getlang:
                    language = 'js'
                elif 'css' in getlang:
                    language = 'css'
            
            #Map languages if needed. For example: Map .less files to .css searches
            print 'language: '+language
            if settings.get(language) is not None:
                print 'lang found in settings: '+language
                item = settings.get(language)
                if 'map' in item:
                    language = item['map']

            sublime.status_message('helpIt invoked-- ' + 'Scope: ' + scope + ' Word: ' + word + ' Language: ' + language)
            for region in self.view.sel():
                phrase = self.view.substr(region)
                search = 'http://google.com/search?q=%s'                
                custom = False 

                #Define our search term
                if not region.empty():
                    term = phrase
                else:
                    term = word

                
                if item != None:
                    if 'sub' in item: #check for sub searches based on our term
                        subs = item['sub']
                        for sub in subs:
                            if 'contains' in sub and 'url' in sub: #Make sure we have everything
                                if term.count(sub['contains']):
                                    if 'remove' in sub:
                                        term = re.sub(sub['remove'], '', term)
                                    search = sub['url']
                                    custom = True
                                    break

                    if not custom:
                        if type(item) == unicode:
                            search = item
                            custom = True
                        elif 'url' in item:
                            search = item['url']   
                            custom = True

                if not custom:
                    term += " " + language

                try:
                    search = search % (term)
                    print search
                except TypeError:
                    print "No replacements"

                webbrowser.open_new_tab(search)
        else:
            pass

    def is_enabled(self):
        return self.view.file_name() and len(self.view.file_name()) > 0
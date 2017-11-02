# Notifier example from tutorial
#
# See: http://github.com/seb-m/pyinotify/wiki/Tutorial
#
import time
import pyinotify
from pprint import pprint

wm = pyinotify.WatchManager()  # Watch Manager
mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_MODIFY | pyinotify.IN_MOVED_TO | pyinotify.IN_MOVED_FROM |pyinotify.IN_MOVE_SELF | pyinotify.IN_DELETE_SELF # watched events

class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CREATE(self, event):
        print(event)
        print "Creating:", event.pathname

    def process_IN_DELETE(self, event):
        print "Removing:", event.pathname

    def process_IN_MODIFY(self, event):
        print "Modify:", event.pathname

    # mv ../a.txt ./
    def process_IN_MOVED_TO(self, event):
        print "MoveTo", event.pathname

    # mv a.txt ../
    def process_IN_MOVED_FROM(self, event):
        print "MoveFROM", event.pathname

    def process_IN_MOVE_SELF(self, event):
        print "MoveSELF", event.pathname
        wm.rm_watch(event.wd)

    def process_IN_DELETE_SELF(self, event):
        print "DeleteSELF", event.pathname

handler = EventHandler()
notifier = pyinotify.Notifier(wm, handler)
# notifier.coalesce_events()

wdd = wm.add_watch('.', mask)
pprint(wdd)
notifier.loop()

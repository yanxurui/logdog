from __future__ import print_function
import os
import logging

# you can even call basicConfig to customize the log
LOG_FILE = 'logdog.log'
LOG_LEVEL = 'DEBUG'
# use logger in handler
logger = logging.getLogger(__name__)

INTEVAL = 10

DAEMONIZE = True
DIR = os.path.abspath('.')
PID_FILE = 'logdog.pid'
STDOUT = 'logdog.out'
STDERR = 'logdog.err'


class MyHandler(object):
    def __init__(self):
        self.count = 0

    def __call__(self, file, lines):
        print(lines, end='')
        self.count += 1

DOGS = {
    "test": {
        "paths": ["a.log", "b.log"],
        "handler": MyHandler(),
        "includes": [r"wrong"],
        "excludes": [r"long"]
    },
    "glob": {
        "paths": ["logs/**/*.log"],
        "handler": MyHandler(),
        "includes": [r"wrong"],
    }
}

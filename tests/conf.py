import os
import logging

LOG_FILE = 'logdogs.log'
LOG_LEVEL = 'INFO'
# you can even call basicConfig to customize the log instead

INTEVAL = 10 # seconds

DAEMONIZE = True
DIR = os.path.abspath('.')
PID_FILE = 'logdogs.pid'
STDOUT = 'logdogs.out'
STDERR = 'logdogs.err'
# the above 4 configurations only work when DAEMONIZE is True

logger = logging.getLogger(__name__)

class MyHandler(object):
    def __init__(self):
        self.count = 0

    def __call__(self, file, lines):
        self.count += 1
        logger.info('...')
        # Do whatever you want here...

DOGS = {
    "test": {
        "paths": ["a.log", "b.log"],
        "handler": MyHandler(),
        "includes": [r"wrong"],
        "excludes": [r"nothing"]
    },
    "glob": {
        "paths": ["**/*.log"],
        "handler": MyHandler(),
        "includes": [r"(?!)wrong"],
    }
}

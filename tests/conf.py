from __future__ import print_function

import logging

LOG_FILE = 'logdog.log'
LOG_LEVEL = 'DEBUG'

DAEMONIZE = True
PID_FILE = '/tmp/logdog.pid'
STDOUT = '/tmp/logdog.out'
STDERR = '/tmp/logdog.err'

logger = logging.getLogger(__name__)

class MyHandler(object):
    def __init__(self):
        self.count = 0

    def __call__(self, line, file):
        print(line, end='')
        self.count += 1
        # log to LOG_FILE
        # logger.debug('handle %d lines' % self.count)

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

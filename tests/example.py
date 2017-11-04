#!/usr/bin/env
# coding=utf-8

import os
import logging

from logdogs import LogDogs

# config log
# if ommitted, log to standard output
logging.basicConfig(
    filename='logdogs.log',
    format='%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s',
    level=logging.INFO
)

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
        "includes": [r"wrong"],
    }
}

logdogs = LogDogs(DOGS)
logdogs.run(
    5,
    daemon=True,
    pid='logdogs.pid',
    stdout='logdogs.out',
    stderr='logdogs.err',
    working_directory=os.path.abspath('.')
)

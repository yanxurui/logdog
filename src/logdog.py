# standard libraries
from __future__ import print_function

import os
import sys
import re
import time
import logging
import traceback
from collections import defaultdict
from stat import ST_DEV, ST_INO

# third party modules
import glob2
import daemon
from daemon import pidfile

# my own module
from pyconfig import *

logger = logging.getLogger(__name__)


class Log(object):
    """
    a log file is represented by a Log object
    """
    logs_map = {} # {path: log object}


    def __init__(self, path, dogs, new=False):
        self.path = path
        self.dogs = dogs
        self.total = 0
        self.half = None
        self.old = False
        self.f = open(path)
        sres = os.fstat(self.f.fileno())
        self.dev, self.ino = sres[ST_DEV], sres[ST_INO]
        self.logs_map[path] = self
        
        if new:
            # process all logs if the log file is newly created
            self.process()
        else:
            # ignore old logs
            self.f.seek(0, 2) # seek to the end

    def __repr__(self):
        return '<%s path=%s, dogs=%s>' % (self.__class__.__name__, self.path, self.dogs)

    def readlines(self):
        """
        tail all lines since last time
        """
        lines = []
        while True:
            line = self.f.readline() # Retain newline. Return empty string at EOF
            if line:
                if self.half:
                    line = self.half + line
                    self.half = None
                if line.endswith('\n'):
                    lines.append(line)
                else:
                    # read half line
                    self.half = line
                    break
            else:
                # reach the end of the file
                break
        return lines

    def process(self):
        """
        log file has been changed, call dogs to process line by line
        """
        lines = self.readlines()
        self.total += len(lines)
        logger.debug('%s process %d/%d lines' % (self, len(lines), self.total))
        if lines:
            for dog in self.dogs:
                dog.process(self.path, lines)

        if self.old and len(lines) == 0:
            del self.logs[self.path]
            return

        # check rotate
        try:
            # stat the file by path, checking for existence
            sres = os.stat(self.path)
        except OSError as err:
            if err.errno == errno.ENOENT:
                sres = None
            else:
                logger.error('\n'+traceback.format_exc())
        if not sres or sres[ST_DEV] != self.dev or sres[ST_INO] != self.ino:
            logger.warn('%s is moved' % self)
            self.old = True
            del self.logs_map[self.path]
            self.logs_map[self.path+'-unknow-path'] = self


class Filter(object):
    def __init__(self, includes, excludes):
        self.includes = includes
        self.excludes = excludes
        self.re_includes = [re.compile(i) for i in includes]
        self.re_excludes = [re.compile(e) for e in excludes]

    def __call__(self, line):
        # or
        m = 1
        for r in self.re_includes:
            m = r.search(line)
            if m:
                break
        if m is None:
            return False
        # and
        for r in self.re_excludes:
            m = r.search(line)
            if m:
                return False
        return True

    def __repr__(self):
        return '<%s includes=%s, excludes=%s>' % (self.__class__.__name__, self.includes, self.excludes)


class Handler(object):
    """
    default handler for log event
    """
    def __call__(self, file, lines):
        print(lines, end='')


class Dog(object):
    """
    A Dog consists of:
    1. a group of log files specified by glob pattern
    2. a filter defined by includes and excludes
    3. a handler function or a callable object
    """
    dogs = []
    dogs_map = defaultdict(set) # {path: set([dog object])}

    def __init__(self, name, paths, handler=Handler(), includes=[], excludes=[]):
        self.name = name
        self.paths = paths
        self.filter = Filter(includes, excludes)
        self.handler = handler
        self.dogs.append(self)
        self.watch(True)

    def watch(self, init=False):
        for path in self.paths:
            for file in glob2.iglob(path):
                self.dogs_map[path].add(self)
                if file not in Log.logs_map:
                    logger.info('%s watch %s' % (self, file))
                    if init:
                        Log(file, self.dogs_map[path])
                    else:
                        Log(file, self.dogs_map[path], new=True)

    def __repr__(self):
        return '<%s name=%s>' % (self.__class__.__name__, self.name)

    def process(self, pathname, lines):
        lines = filter(self.filter, lines)
        logger.info('%s process %d lines of %s' % (self, len(lines), pathname))
        if lines:
            self.handler(pathname, lines)


# count is for the sake of test
count = 0
def process():
    global count
    count += 1
    logger.info('loop %d' % count)

    for log in Log.logs_map.values():
        log.process()
    for dog in Dog.dogs:
        dog.watch()

def init(config):
    # config log
    # if filename is None, log to standard output
    logging.basicConfig(
        filename=config.LOG_FILE,
        format='%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s',
        level=getattr(logging, config.LOG_LEVEL, 'WARNING')
    )

    logger.info('start from %s' % os.path.abspath('.'))
    for name, attrs in config.DOGS.items():
        Dog(name, **attrs)

def loop(inteval):
    # infinite loop
    while True:
        time.sleep(config.INTEVAL)
        try:
            process()
        except:
            logger.error('\n'+traceback.format_exc())

def main(config):
    if config.DAEMONIZE:
        pid, stdout, stderr = None, None, None
        if config.PID_FILE:
            pid = pidfile.TimeoutPIDLockFile(config.PID_FILE, 3)
        if config.STDOUT:
            stdout = open(config.STDOUT, 'a')
        if config.STDERR:
            stderr = open(config.STDOUT, 'a')
        context = daemon.DaemonContext(
            working_directory=config.DIR,
            pidfile=pid,
            stdout=stdout,
            stderr=stderr)
        context.open()
    
    init(config)
    loop(config.INTEVAL)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '-c':
        config_path = sys.argv[2]
        config = Config(
            config_path,
            Field('LOG_FILE'),
            Field('LOG_LEVEL', default='WARNING'),
            Field('INTEVAL', types=int, default=10),
            Field('DAEMONIZE', types=bool, default=False),
            Field('PID_FILE'),
            Field('STDOUT'),
            Field('STDERR'),
            Field('DOGS', types=dict, required=True)
        )
    else:
        # best way to exit script: https://stackoverflow.com/a/19747562/6088837
        # exit status will be one
        sys.exit('Usage: python -m logdog -c your-config.py')
    main(config)


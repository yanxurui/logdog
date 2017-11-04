"""
A daemon to monitor keywords in any log files specified by glob pattern
"""

# standard libraries
from __future__ import print_function

import os
import sys
import re
import time
import logging
import traceback
import atexit
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
    def __init__(self, path, dogs, new=False):
        self.path = path
        self.dogs = dogs
        self.total = 0
        self.half = None
        self.old = False
        self.f = open(path)
        sres = os.fstat(self.f.fileno())
        self.dev, self.ino = sres[ST_DEV], sres[ST_INO]
        logger.info('watch %s' % self)
        if not new:
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
        if log file has been appended, call dogs to process
        """
        lines = self.readlines()
        self.total += len(lines)
        logger.debug('%s process %d/%d lines' % (self, len(lines), self.total))
        if lines:
            for dog in self.dogs:
                dog.process(self.path, lines)
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
            logger.warning('%s is moved' % self)
            self.old = True
        # return number of rows
        return len(lines)

    def close(self):
        # is this necessary?
        self.f.close()


class Filter(object):
    """
    define filter contion by includes and excludes regex
    """
    def __init__(self, includes, excludes):
        self.includes = includes
        self.excludes = excludes
        self.re_includes = [re.compile(i) for i in includes]
        self.re_excludes = [re.compile(e) for e in excludes]

    def __call__(self, line):
        """
        return True if the line meets requirements
        """
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
    def __init__(self, name, paths, handler=Handler(), includes=[], excludes=[]):
        self.name = name
        self.paths = paths
        self.filter = Filter(includes, excludes)
        self.handler = handler

    def files(self):
        """
        a generator to return all files watched by this dog
        """
        for path in self.paths:
            for file in glob2.iglob(path):
                yield file

    def __repr__(self):
        return '<%s name=%s>' % (self.__class__.__name__, self.name)

    def process(self, pathname, lines):
        """
        process the new lines from a file in a loop
        """
        lines = list(filter(self.filter, lines))
        logger.info('%s process %d lines of %s' % (self, len(lines), pathname))
        if lines:
            self.handler(pathname, lines)


class LogDogs(object):
    """
    manager all dogs and logs
    """
    def __init__(self, config):
        self.count = 0
        self.inteval = config.INTEVAL
        self.logs_map = {} # {path: log object}
        self.old_logs_map = {} # {path: log object}
        self.dogs = []
        self.dogs_map = defaultdict(set) # {path: set([dog object])}

        # a dirty way to avoid `ResourceWarning: unclosed file` in python3
        atexit.register(self.terminate)

        # config log
        # if filename is None, log to standard output
        logging.basicConfig(
            filename=config.LOG_FILE,
            format='%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s',
            level=getattr(logging, config.LOG_LEVEL)
        )

        logger.info('start from %s' % os.path.abspath('.'))

        for name, attrs in config.DOGS.items():
            dog = Dog(name, **attrs)
            self.dogs.append(dog)
            for file in dog.files():
                if dog not in self.dogs_map[file]:
                    self.dogs_map[file].add(dog)
                if file not in self.logs_map:
                    log = Log(file, self.dogs_map[file])
                    self.logs_map[file] = log

    def do_process(self, log):
        """
        call log's process
        """
        old = log.old
        n = log.process()
        if old and n == 0:
            # there is no more log so remove it
            logger.warning('remove %s' % log)
            self.old_logs_map[log.path].close()
            del self.old_logs_map[log.path]
        elif log.old:
            # move to old_logs
            del self.logs_map[log.path]
            if log.path in self.old_logs_map:
                self.old_logs_map[log.path].close()
            self.old_logs_map[log.path] = log

    def process(self):
        """
        run every X seconds
        check current and newly created log files
        """
        self.count += 1
        logger.info('loop %d' % self.count)

        for log in list(self.logs_map.values()):
            self.do_process(log)
        for log in list(self.old_logs_map.values()):
            self.do_process(log)
        for dog in self.dogs:
            for file in dog.files():
                if dog not in self.dogs_map[file]:
                    self.dogs_map[file].add(dog)
                if file not in self.logs_map:
                    log = Log(file, self.dogs_map[file], new=True)
                    self.logs_map[file] = log
                    # process all logs if the log file is newly created
                    self.do_process(log)

    def run(self):
        """
        infinite loop
        """
        while True:
            time.sleep(self.inteval)
            try:
                self.process()
            except:
                logger.error('\n'+traceback.format_exc())

    def terminate(self):
        logger.info('close files')
        for log in self.logs_map.values():
            log.close()


def main():
    # parse config
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
        sys.exit('Usage: logdogs -c your-config.py')

    # start daemon
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
    # start logdogs
    logdogs = LogDogs(config)
    logdogs.run()


if __name__ == '__main__':
    main()


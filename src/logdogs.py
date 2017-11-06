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
from email.mime.text import MIMEText
from smtplib import SMTP, SMTP_SSL

# third party modules
import glob2
from daemon import DaemonContext, pidfile


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


class MailHandler(object):
    def __init__(self, user, pwd, server, port=None, ssl=True, to_addrs=[]):
        if port is None:
            if ssl:
                port = 465
            else:
                port = 25
        self.user = user
        self.pwd = pwd
        self.server = server
        self.port = port
        self.ssl = ssl
        self.to_addrs = to_addrs

        self.create_conn()

    def create_conn(self):
        if self.ssl:
            conn = SMTP_SSL(self.server, self.port)
        else:
            conn = SMTP(self.server, self.port)
        logger.warning('connected')
        conn.login(self.user, self.pwd)
        self.conn = conn

    def test_conn_open(self):
        try:
            status = self.conn.noop()[0]
        except:  # smtplib.SMTPServerDisconnected
            status = -1
        return True if status == 250 else False

    def sendmail(self, to_addrs, msg):
        if not self.test_conn_open():
            self.create_conn()
        self.conn.sendmail(self.user, to_addrs, msg)

    def __call__(self, file, lines):
        msg = MIMEText('\n'.join(lines), 'plain')
        msg['Subject']= '[logdogs]' + file
        msg['From'] = self.user
        self.sendmail(self.to_addrs, msg.as_string())


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
            try:
                self.handler(pathname, lines)
            except:
                logger.error('\n'+traceback.format_exc())

class LogDogs(object):
    """
    manager all dogs and logs
    """
    def __init__(self, DOGS):
        self.count = 0
        self.logs_map = {} # {path: log object}
        self.old_logs_map = {} # {path: log object}
        self.dogs = []
        self.dogs_map = defaultdict(set) # {path: set([dog object])}

        # a dirty way to avoid `ResourceWarning: unclosed file` in python3
        atexit.register(self.terminate)

        logger.info('start from %s' % os.path.abspath('.'))

        for name, attrs in DOGS.items():
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
        new_logs = []
        for dog in self.dogs:
            for file in dog.files():
                if dog not in self.dogs_map[file]:
                    self.dogs_map[file].add(dog)
                if file not in self.logs_map:
                    # process all logs if the log file is newly created
                    log = Log(file, self.dogs_map[file], new=True)
                    self.logs_map[file] = log
                    new_logs.append(log)
        for log in new_logs:
            self.do_process(log)

    def run(self, inteval, daemon=False, pid=None, stdout=None, stderr=None, **kargs):
        """
        arguments after daemon only work when daemon is True
        kargs are passed to python-daemon
        """
        if daemon:
            if pid:
                pid = pidfile.TimeoutPIDLockFile(pid, 1)
            if stdout:
                stdout = open(stdout, 'a')
            if stderr:
                stderr = open(stderr, 'a')

            # preserve files in python daemon: https://stackoverflow.com/a/13696380/6088837
            fds = set()
            for log in self.logs_map.values():
                fds.add(log.f.fileno())
            for h in logging.root.handlers:
                if isinstance(h, logging.StreamHandler):
                    fds.add(h.stream.fileno())
                elif isinstance(h, logging.SyslogHandler):
                    fds.add(h.socket.fileno())
                else:
                    # what else?
                    pass
            context = DaemonContext(
                pidfile=pid,
                stdout=stdout,
                stderr=stderr,
                files_preserve=list(fds),
                **kargs)
            context.open()

        while True:
            time.sleep(inteval)
            try:
                self.process()
            except:
                logger.error('\n'+traceback.format_exc())

    def terminate(self):
        logger.info('close files')
        for log in self.logs_map.values():
            log.close()


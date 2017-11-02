# standard libraries
import os
import sys
import re
import time
import logging
import importlib
from collections import defaultdict
import pdb

# third party modules
import glob2
from glob2.fnmatch import fnmatch
import pyinotify


class Log(object):
    """
    a log file is represented by a Log object
    """
    logs={}

    def __init__(self, path, new):
        self.path = path
        self._f = open(path)
        self.logs[path] = self
        if new:
            # if the log file is newly created, write events are missed before watch the file 
            self.process()
        else:
            # ignore old logs
            self._f.seek(0, 2) # seek to the end

    def __repr__(self):
        return '<%s path=%s, pos=%d>' % (self.__class__.__name__, self.path, self._f.tell())

    def read(self):
        """
        a generator for read line
        """
        while True:
            line = self._f.readline() # Retain newline. Return empty string at EOF
            if line:
                yield line
            else:
                break

    def process(self):
        """
        log file has been changed, call dogs to process line by line
        """
        i = 0
        for line in self.read():
            i += 1
            Dog.process(self.path, line)
        logger.info('%s process %d line(s)' % (self, i))


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
    def __call__(self, line, file):
        print(line)


class Dog(object):
    """
    A Dog consists of:
    1. a group of log files specified by glob pattern
    2. a filter defined by includes and excludes
    3. a handler function or a callable object
    """
    dogs=defaultdict(set)

    def __init__(self, name, paths, handler=Handler(), includes=[], excludes=[]):
        self.name = name
        self.paths = []
        self.filter = Filter(includes, excludes)
        self.handler = handler

        for path in paths:
            path = os.path.abspath(path)
            # pyinotify's daemon process will chdir to /
            # so it's necessary to save abspath which is relative to the current directory
            self.paths.append(path)
            if glob2.has_magic(path):
                # for glob pattern
                # list files which match the pattern
                for file in glob2.iglob(path):
                    self.dogs[file].add(self)
                # also watch the longest non-magic path
                while True:
                    path, _ = os.path.split(path)
                    if not glob2.has_magic(path):
                        break
            else:
                # for normal file
                assert not os.path.isdir(path), 'should not be a directory'
                # if the file does not exist, watch the directory instead
            while not os.path.exists(path):
                path, _ = os.path.split(path)
            self.dogs[path].add(self)

    def __repr__(self):
        return '<%s name=%s, paths=%s, filter=%s, handler=%s>' % (self.__class__.__name__, self.name, self.paths, self.filter, self.handler)

    @classmethod
    def watchall(cls):
        for path in cls.dogs.keys():
            cls.watch(path)

    @classmethod
    def watch(cls, path, new=False):
        """
        watch file or directory
        """
        assert os.path.exists(path)
        if os.path.isfile(path):
            logger.info('watch file %s' % path)
            # if file is newly created, it's safer to watch first then create log
            wm.add_watch(path, pyinotify.IN_MODIFY | pyinotify.IN_MOVE_SELF)
            log = Log(path, new)
            logger.debug('log: %s' % log)
        else:
            logger.info('watch directory %s' % path)
            wdd = wm.add_watch(path, pyinotify.IN_CREATE, rec=True)
            for p in wdd.keys():
                cls.dogs[p] = cls.dogs[path]

    @classmethod
    def create(cls, path, pathname):
        """
        a new file/sub-directory is created
        path is the directory being watched
        """
        assert path in cls.dogs
        if os.path.isdir(pathname):
            cls.dogs[pathname] = cls.dogs[path]
            cls.watch(pathname)
            # the files created in this directory are missed before the directory being watched
            # so add them to watch recursively here
            for name in os.listdir(pathname):
                cls.create(pathname, os.path.join(pathname, name))
        else:
            if pathname not in cls.dogs:
                # has not been watched before
                for dog in cls.dogs[path]:
                    for path in dog.paths:
                        if fnmatch(pathname, path):
                            cls.dogs[pathname].add(dog)
                if pathname in cls.dogs:
                    logger.debug('watched by %s' % cls.dogs[pathname])
                else:
                    # does not match glob pattern
                    logger.info('%s does not match any pattern' % pathname)
                    return

            # there are 2 cases:
            # 1. old file is moved and a new file is created
            #   - in this case the old log object is replaced
            # 2. log file is created for the first time
            cls.watch(pathname, True)

    @classmethod
    def delete(cls, pathname):
        """
        file being watched is deleted
        if the parent directory exists and not being watched then watch it
        """
        directory = os.path.dirname(pathname)
        if os.path.isdir(directory) and directory not in cls.dogs:
            cls.dogs[directory] = cls.dogs[pathname]
            cls.watch(directory)

    @classmethod
    def process(cls, pathname, line):
        """
        a new line has been appended to the log file
        """
        for dog in cls.dogs[pathname]:
            if dog.filter(line):
                dog.handler(line, pathname)


class EventHandler(pyinotify.ProcessEvent):
    """
    event handler for pyinotify
    """
    def process_IN_CREATE(self, event):
        logger.debug('CREATE %s' % event)
        Dog.create(event.path, event.pathname)

    def process_IN_MODIFY(self, event):
        logger.debug('MODIFY %s' % event)
        log = Log.logs[event.pathname]
        log.process()

    def process_IN_MOVE_SELF(self, event):
        """
        log rotate triggers this event
        just remove the watch for now
        """
        logger.debug('MOVE_SELF %s' % event)
        wm.rm_watch(event.wd)
        Dog.delete(event.pathname)


# global(module) variable
logger = logging.getLogger(__name__)
wm = pyinotify.WatchManager()
handler = EventHandler()
notifier = pyinotify.Notifier(wm, handler)


def load_config():
    config = None
    if len(sys.argv) == 3:
        if sys.argv[1] == '-c':
            config = sys.argv[2]
            if os.path.exists(sys.argv[2]):
                sys.path.insert(1, os.path.dirname(os.path.abspath(config)))
                return importlib.import_module(os.path.splitext(os.path.basename(config))[0])
    return None


def main(config):
    daemonize = getattr(config, 'DAEMONIZE', False)

    # config log
    # if filename is None, log to standard output
    logging.basicConfig(
        filename=getattr(config, 'LOG_FILE', None),
        format='%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s',
        level=getattr(logging, getattr(config, 'LOG_LEVEL', 'WARNING'))
    )

    logger.info('init dogs')

    for name, attrs in config.DOGS.items():
        Dog(name, **attrs)
    Dog.watchall()

    # block...
    logger.info('start watch')
    notifier.loop(
        daemonize=daemonize,
        pid_file=getattr(config, 'PID_FILE', None),
        stdout=getattr(config, 'STDOUT', '/dev/null'),
        stderr=getattr(config, 'STDERR', '/dev/null')
    )
    logger.warn('exit')


if __name__ == '__main__':
    config = load_config()
    if not config:
        # best way to exit script: https://stackoverflow.com/a/19747562/6088837
        # exit status will be one
        sys.exit('Usage: %s -c your-config.py' % sys.argv[0])
    main(config)


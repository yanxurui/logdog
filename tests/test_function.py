from __future__ import print_function

import os
import sys
from time import sleep
import signal
import unittest
import shutil

if sys.version_info[0] > 2:
    from queue import Queue
else:
    from Queue import Queue

from logdogs import LogDogs

# create object and set attributes: https://stackoverflow.com/a/2827664/6088837
class Config(object):
    def __init__(self, **kargs):
        self.LOG_FILE = 'logdogs.log'
        self.LOG_LEVEL = 'DEBUG'
        self.INTEVAL = 0.1 # not used
        for k, v in kargs.items():
            setattr(self, k, v)

class TestFunction(unittest.TestCase):

    def setUp(self):
        # opened files
        self.files = []
        self.q = Queue()
        self.rm('logdogs.log')
        self.rm('a.log')
        self.rm('b.log')
        self.rm('logs')

    def tearDown(self):
        self.assertTrue(self.q.empty())
        for f in self.files:
            f.close()

    def rm(self, path):
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)

    def handler(self, file, lines):
        # print(lines)
        self.q.put(lines)

    def open(self, path):
        # w: create an empty file or truncate if it exists
        f = open(path, 'w')
        self.files.append(f)
        return f

    def write(self, f, s):
        # it's not easy to write str to file without bufferring in both py2 and py3
        f.write(s)
        f.flush()


    def test_1_file(self):
        """
        the simplest case
        """
        config = Config(
            DOGS = {
                'test': {
                    'paths': ['a.log'],
                    'includes': ['wrong'],
                    'excludes': ['long'],
                    'handler': self.handler
                }
            }
        )
        f = self.open('a.log')
        logdogs = LogDogs(config)

        self.write(f, 'hello world\n')
        logdogs.process()
        self.assertTrue(self.q.empty())

        self.write(f, 'something wrong\nwhats wrong\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['something wrong\n', 'whats wrong\n'])

        self.write(f, 'a long wrong answer\n')
        logdogs.process()
        self.assertTrue(self.q.empty())


    def test_ignore_old_logs(self):
        """
        old logs in the log file are ignored
        """
        config = Config(
            DOGS = {
                'test': {
                    'paths': ['a.log'],
                    'includes': ['wrong'],
                    'handler': self.handler
                }
            }
        )
        f = self.open('a.log')
        self.write(f, 'you are on a wrong way\n')
        logdogs = LogDogs(config)

        self.write(f, 'hello world\n')
        logdogs.process()
        self.assertTrue(self.q.empty())

        self.write(f, 'something wrong\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['something wrong\n'])


    def test_rotate(self):
        """
        log file is moved and a new one is created
        """
        config = Config(
            DOGS = {
                'test': {
                    'paths': ['a.log'],
                    'includes': ['wrong'],
                    'handler': self.handler
                }
            }
        )
        f = self.open('a.log')
        logdogs = LogDogs(config)

        self.write(f, 'something wrong\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['something wrong\n'])

        shutil.move('a.log', 'b.log')
        self.write(f, 'whats wrong\n')
        # nginx will still log to old log file before reopen signal is handled
        # in some cases the last few logs are missing

        # write to new file immediately
        f = self.open('a.log')
        self.write(f, 'all is wrong\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['whats wrong\n'])
        self.assertEqual(self.q.get_nowait(), ['all is wrong\n'])


    def test_2_files(self):
        """
        a dog can watch more than 1 files
        """
        config = Config(
            DOGS = {
                'test': {
                    'paths': ['a.log', 'b.log'],
                    'includes': ['wrong'],
                    'handler': self.handler
                }
            }
        )
        f1 = self.open('a.log')
        f2 = self.open('b.log')
        logdogs = LogDogs(config)

        self.write(f1, 'something wrong\n')
        self.write(f2, 'whats wrong\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['something wrong\n'])
        self.assertEqual(self.q.get_nowait(), ['whats wrong\n'])


    def test_overlap(self):
        """
        2 dogs can watch the same file
        """
        config = Config(
            DOGS = {
                'test1': {
                    'paths': ['a.log'],
                    'includes': ['error', 'wrong'],
                    'handler': self.handler
                },
                'test2': {
                    'paths': ['a.log'],
                    'includes': ['warning', 'wrong'],
                    'handler': self.handler
                }
            }
        )
        f = self.open('a.log')
        logdogs = LogDogs(config)

        self.write(f, 'an error\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['an error\n'])

        self.write(f, 'a warning\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['a warning\n'])

        self.assertTrue(self.q.empty())

        self.write(f, 'something wrong\n')
        logdogs.process()
        # received 2 times
        self.assertEqual(self.q.get_nowait(), ['something wrong\n'])
        self.assertEqual(self.q.get_nowait(), ['something wrong\n'])


    def test_not_exists(self):
        """
        log file is not required to exist before watch
        """
        config = Config(
            DOGS = {
                'test': {
                    'paths': ['a.log'],
                    'includes': ['wrong'],
                    'handler': self.handler
                }
            }
        )
        logdogs = LogDogs(config)

        # create file after watch
        f = self.open('a.log')

        self.write(f, 'something wrong\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['something wrong\n'])


    def test_2_not_exists(self):
        """
        bug: the same dog watch the same path(.) twice
        """
        config = Config(
            DOGS = {
                'test': {
                    'paths': ['a.log', 'b.log'],
                    'includes': ['wrong'],
                    'handler': self.handler
                }
            }
        )
        logdogs = LogDogs(config)

        # create file after watch
        f = self.open('a.log')
        self.write(f, 'something wrong\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['something wrong\n'])
        # q must be empty now


    def test_glob(self):
        """
        glob pattern can be used in path
        """
        config = Config(
            DOGS = {
                'test': {
                    'paths': ['logs/*.log'],
                    'includes': ['wrong'],
                    'handler': self.handler
                }
            }
        )
        os.makedirs('logs')
        f = self.open('logs/a.log')
        logdogs = LogDogs(config)

        self.write(f, 'something wrong\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['something wrong\n'])

        f = self.open('logs/b.log')

        self.write(f, 'whats wrong\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['whats wrong\n'])


    def test_glob_recursively(self):
        """
        ** can be used in glob pattern
        """
        config = Config(
            DOGS = {
                'test': {
                    'paths': ['logs/**/*.log'],
                    'includes': ['wrong'],
                    'handler': self.handler
                }
            }
        )

        os.makedirs('logs/b')
        os.makedirs('logs/c')
        fa = self.open('logs/a.log')
        fb = self.open('logs/b/b.log')
        logdogs = LogDogs(config)

        self.write(fa, 'something wrong\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['something wrong\n'])

        self.write(fb, 'you are wrong\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['you are wrong\n'])

        # create a new log file
        fc = self.open('logs/c/c.log')
        self.write(fc, 'Am I wrong?\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['Am I wrong?\n'])

        # create a new sub-directory
        os.makedirs('logs/d')
        fd = self.open('logs/d/d.log')
        self.write(fd, 'wrong! wrong! wrong!\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['wrong! wrong! wrong!\n'])


    def test_half_line(self):
        """
        bug: half line will be read if the log is being written at the same time
        """
        config = Config(
            DOGS = {
                'test': {
                    'paths': ['a.log'],
                    'includes': ['wrong'],
                    'handler': self.handler
                }
            }
        )
        # create an empty file or truncate if it exists
        f = self.open('a.log')
        logdogs = LogDogs(config)

        self.write(f, 'something w')
        logdogs.process()
        self.assertTrue(self.q.empty())

        self.write(f, 'rong\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['something wrong\n'])


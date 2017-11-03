from __future__ import print_function

import os
import sys
from time import sleep
import signal
import unittest
import shutil
from Queue import Queue

import logdog

# create object and set attributes: https://stackoverflow.com/a/2827664/6088837
class Config(object):
    def __init__(self, **kargs):
        self.LOG_FILE = 'logdog.log'
        self.LOG_LEVEL = 'DEBUG'
        for k, v in kargs.items():
            setattr(self, k, v)

class TestFunction(unittest.TestCase):

    def setUp(self):
        reload(logdog)
        self.q = Queue()
        self.rm('logdog.log')
        self.rm('a.log')
        self.rm('b.log')
        self.rm('logs')

    def tearDown(self):
        self.assertTrue(self.q.empty())

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
        # 0: not bufferring
        return open(path, 'w', 0)


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
        logdog.init(config)

        f.write('hello world\n')
        logdog.process()
        self.assertTrue(self.q.empty())

        f.write('something wrong\nwhats wrong\n')
        logdog.process()
        self.assertEqual(self.q.get_nowait(), ['something wrong\n', 'whats wrong\n'])

        f.write('a long wrong answer\n')
        logdog.process()
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
        f.write('you are on a wrong way\n')
        logdog.init(config)

        f.write('hello world\n')
        logdog.process()
        self.assertTrue(self.q.empty())

        f.write('something wrong\n')
        logdog.process()
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
        logdog.init(config)

        f.write('something wrong\n')
        logdog.process()
        self.assertEqual(self.q.get_nowait(), ['something wrong\n'])

        shutil.move('a.log', 'b.log')
        f.write('whats wrong\n')
        # nginx will still log to old log file before reopen signal is handled
        # in some cases the last few logs are missing

        # write to new file immediately
        f = self.open('a.log')
        f.write('all is wrong\n')
        logdog.process()
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
        logdog.init(config)

        f1.write('something wrong\n')
        f2.write('whats wrong\n')
        logdog.process()
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
        logdog.init(config)

        f.write('an error\n')
        logdog.process()
        self.assertEqual(self.q.get_nowait(), ['an error\n'])

        f.write('a warning\n')
        logdog.process()
        self.assertEqual(self.q.get_nowait(), ['a warning\n'])

        self.assertTrue(self.q.empty())

        f.write('something wrong\n')
        logdog.process()
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
        logdog.init(config)

        # create file after watch
        f = self.open('a.log')

        f.write('something wrong\n')
        logdog.process()
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
        logdog.init(config)

        # create file after watch
        f1 = self.open('a.log')
        f1.write('something wrong\n')
        logdog.process()
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
        f1 = self.open('logs/a.log')
        logdog.init(config)

        f1.write('something wrong\n')
        logdog.process()
        self.assertEqual(self.q.get_nowait(), ['something wrong\n'])

        f2 = self.open('logs/b.log')

        f2.write('whats wrong\n')
        logdog.process()
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
        logdog.init(config)

        fa.write('something wrong\n')
        logdog.process()
        self.assertEqual(self.q.get_nowait(), ['something wrong\n'])

        fb.write('you are wrong\n')
        logdog.process()
        self.assertEqual(self.q.get_nowait(), ['you are wrong\n'])

        # create a new log file
        fc = self.open('logs/c/c.log')
        fc.write('Am I wrong?\n')
        logdog.process()
        self.assertEqual(self.q.get_nowait(), ['Am I wrong?\n'])

        # create a new sub-directory
        os.makedirs('logs/d')
        fd = self.open('logs/d/d.log')
        fd.write('wrong! wrong! wrong!\n')
        logdog.process()
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
        logdog.init(config)

        f.write('something w')
        logdog.process()
        self.assertTrue(self.q.empty())

        f.write('rong\n')
        logdog.process()
        self.assertEqual(self.q.get_nowait(), ['something wrong\n'])


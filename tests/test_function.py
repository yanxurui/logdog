from __future__ import print_function

import os
import sys
from time import sleep
import signal
import unittest
import shutil
from multiprocessing import Process, Queue

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
        self.q = Queue()
        self.rm('logdog.log')
        self.rm('a.log')
        self.rm('b.log')
        self.rm('logs')
        print()

    def tearDown(self):
        self.assertTrue(self.p.is_alive())
        #Ctrl-c
        os.kill(self.p.pid, signal.SIGINT)
        self.assertTrue(self.q.empty())

    def start(self, config):
        p = Process(target=logdog.main, args=(config,))
        p.start()
        self.p = p
        sleep(0.1)

    def rm(self, path):
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)

    def handler(self, line, file):
        # print(line, end='')
        self.q.put(line)

    def open(self, path):
        return open(path, 'w', 0)

    def write(self, f, s):
        f.write(s)
        sleep(.2)


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
        # create an empty file or truncate if it exists
        f = self.open('a.log')
        self.start(config)

        self.write(f, 'hello world\n')
        self.assertTrue(self.q.empty())

        self.write(f, 'something wrong\n')
        self.assertEqual(self.q.get_nowait(), 'something wrong\n')

        self.write(f, 'a long wrong answer\n')
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
        self.start(config)

        self.write(f, 'hello world\n')
        self.assertTrue(self.q.empty())

        self.write(f, 'something wrong\n')
        self.assertEqual(self.q.get_nowait(), 'something wrong\n')


    def test_rotate(self):
        """
        the simplest case
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
        self.start(config)

        self.write(f, 'something wrong\n')
        self.assertEqual(self.q.get_nowait(), 'something wrong\n')

        shutil.move('a.log', 'b.log')
        self.write(f, 'whats wrong\n')
        # it's a problem in some cases for example:
        # nginx will still log to old log file before reopen signal is handled
        # the last few logs are missing
        self.assertTrue(self.q.empty())

        # write to new file
        f = self.open('a.log')
        self.write(f, 'something wrong\n')
        self.assertEqual(self.q.get_nowait(), 'something wrong\n')


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
        self.start(config)

        self.write(f1, 'something wrong\n')
        self.assertEqual(self.q.get_nowait(), 'something wrong\n')

        self.write(f2, 'whats wrong\n')
        self.assertEqual(self.q.get_nowait(), 'whats wrong\n')


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
        self.start(config)

        self.write(f, 'an error\n')
        self.assertEqual(self.q.get_nowait(), 'an error\n')

        self.write(f, 'a warning\n')
        self.assertEqual(self.q.get_nowait(), 'a warning\n')

        self.assertTrue(self.q.empty())

        self.write(f, 'something wrong\n')
        # received 2 times
        self.assertEqual(self.q.get_nowait(), 'something wrong\n')
        self.assertEqual(self.q.get_nowait(), 'something wrong\n')


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
        self.start(config)

        # create file after watch
        f = self.open('a.log')

        self.write(f, 'something wrong\n')
        self.assertEqual(self.q.get_nowait(), 'something wrong\n')


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
        self.start(config)

        # create file after watch
        f1 = self.open('a.log')
        self.write(f1, 'something wrong\n')
        self.assertEqual(self.q.get_nowait(), 'something wrong\n')
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
        self.start(config)

        self.write(f1, 'something wrong\n')
        self.assertEqual(self.q.get_nowait(), 'something wrong\n')

        f2 = self.open('logs/b.log')

        self.write(f2, 'whats wrong\n')
        self.assertEqual(self.q.get_nowait(), 'whats wrong\n')


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
        self.start(config)

        self.write(fa, 'something wrong\n')
        self.assertEqual(self.q.get_nowait(), 'something wrong\n')

        self.write(fb, 'you are wrong\n')
        self.assertEqual(self.q.get_nowait(), 'you are wrong\n')

        # create a new log file
        fc = self.open('logs/c/c.log')
        self.write(fc, 'Am I wrong?\n')
        self.assertEqual(self.q.get_nowait(), 'Am I wrong?\n')

        # create a new sub-directory
        os.makedirs('logs/d')
        fd = self.open('logs/d/d.log')
        self.write(fd, 'wrong! wrong! wrong!\n')
        self.assertEqual(self.q.get_nowait(), 'wrong! wrong! wrong!\n')


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
        self.start(config)

        self.write(f, 'something w')
        self.assertTrue(self.q.empty())

        self.write(f, 'rong\n')
        self.assertEqual(self.q.get_nowait(), 'something wrong\n')


    def test_slow_handler(self):
        """
        a handler takes long time to complete
        """
        def handler(line, file):
            # print(line, end='')
            sleep(1)
            self.q.put(line)

        config = Config(
            DOGS = {
                'test': {
                    'paths': ['a.log'],
                    'includes': ['wrong'],
                    'handler': handler
                }
            }
        )
        # create an empty file or truncate if it exists
        f = self.open('a.log')
        self.start(config)

        # trigger 2 MODIFY events, the 1st process all lines
        self.write(f, 'wrong\n')
        f.write('something wrong\n')
        f.write('something wrong\n')
        f.write('something wrong\n')

        sleep(4.1)
        for i in range(4):
            self.q.get()

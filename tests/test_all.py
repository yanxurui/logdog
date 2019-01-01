from __future__ import print_function

import os
import sys
from time import sleep
import logging
import unittest
import shutil
import shlex, subprocess
import signal
import collections

if sys.version_info[0] > 2:
    from queue import Queue
else:
    from Queue import Queue

from logdogs import LogDogs

logging.basicConfig(
    filename='logdogs.log',
    format='%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s',
    level=logging.DEBUG
)

class Common(object):
    def rm(self, path):
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)

    def see(self, file, keywords):
        """check the file for keyword in the given order

        [description]

        Arguments:
            file {str} -- [log file or outptu file]
            keywords {list(str)} -- [keywords in their occurence order]
        """
        if not type(keywords) in (list, tuple):
            keywords = [keywords]
        with open(file) as f:
            i = 0
            for line in f:
                if keywords[i] in line:
                    i += 1
                    if not i < len(keywords):
                        break
            self.assertEqual(i, len(keywords))

    def sh(self, cmd, ok=True, out=None):
        """execute a command and wait for process to terminate

        [description]

        Arguments:
            cmd {str} -- command to execute

        Keyword Arguments:
            ok {bool} -- [returncode is 0?] (default: {True})
            out {str} -- [look for this str in the stdout or stderr] (default: {None})
        """
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = p.communicate()
        if ok:
            self.assertEqual(p.returncode, 0)
        else:
            self.assertNotEqual(p.returncode, 0)
        if out:
            self.assertIn(out, stdout+stderr)

    def pgrep(self, cmd):
        """a wrapper of pgrep command

        [description]

        Arguments:
            cmd {str} -- [full command name]

        """
        cmd = ['pgrep', '-f'] + shlex.split(cmd)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        self.assertEqual(p.returncode, 0)
        pids = stdout.decode().strip().split('\n')
        return pids


class TestFunction(unittest.TestCase, Common):
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
        DOGS = {
            'test': {
                'paths': ['a.log'],
                'includes': ['wrong'],
                'excludes': ['long'],
                'handler': self.handler
            }
        }
        f = self.open('a.log')
        logdogs = LogDogs(DOGS)

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
        DOGS = {
            'test': {
                'paths': ['a.log'],
                'includes': ['wrong'],
                'handler': self.handler
            }
        }
        f = self.open('a.log')
        self.write(f, 'you are on a wrong way\n')
        logdogs = LogDogs(DOGS)

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
        DOGS = {
            'test': {
                'paths': ['a.log'],
                'includes': ['wrong'],
                'handler': self.handler
            }
        }
        f = self.open('a.log')
        logdogs = LogDogs(DOGS)

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
        DOGS = {
            'test': {
                'paths': ['a.log', 'b.log'],
                'includes': ['wrong'],
                'handler': self.handler
            }
        }
        f1 = self.open('a.log')
        f2 = self.open('b.log')
        logdogs = LogDogs(DOGS)

        self.write(f1, 'something wrong\n')
        self.write(f2, 'whats wrong\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['something wrong\n'])
        self.assertEqual(self.q.get_nowait(), ['whats wrong\n'])


    def test_overlap(self):
        """
        2 dogs can watch the same file
        """
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
        f = self.open('a.log')
        logdogs = LogDogs(DOGS)

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
        DOGS = {
            'test': {
                'paths': ['a.log'],
                'includes': ['wrong'],
                'handler': self.handler
            }
        }
        logdogs = LogDogs(DOGS)

        # create file after watch
        f = self.open('a.log')

        self.write(f, 'something wrong\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['something wrong\n'])


    def test_2_not_exists(self):
        """
        bug: the same dog watch the same path(.) twice
        """
        DOGS = {
            'test': {
                'paths': ['a.log', 'b.log'],
                'includes': ['wrong'],
                'handler': self.handler
            }
        }
        logdogs = LogDogs(DOGS)

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
        DOGS = {
            'test': {
                'paths': ['logs/*.log'],
                'includes': ['wrong'],
                'handler': self.handler
            }
        }
        os.makedirs('logs')
        f = self.open('logs/a.log')
        logdogs = LogDogs(DOGS)

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
        DOGS = {
            'test': {
                'paths': ['logs/**/*.log'],
                'includes': ['wrong'],
                'handler': self.handler
            }
        }

        os.makedirs('logs/b')
        os.makedirs('logs/c')
        fa = self.open('logs/a.log')
        fb = self.open('logs/b/b.log')
        logdogs = LogDogs(DOGS)

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
        DOGS = {
            'test': {
                'paths': ['a.log'],
                'includes': ['wrong'],
                'handler': self.handler
            }
        }
        # create an empty file or truncate if it exists
        f = self.open('a.log')
        logdogs = LogDogs(DOGS)

        self.write(f, 'something w')
        logdogs.process()
        self.assertTrue(self.q.empty())

        self.write(f, 'rong\n')
        logdogs.process()
        self.assertEqual(self.q.get_nowait(), ['something wrong\n'])


class TestAcceptance(unittest.TestCase, Common):
    def setUp(self):
        if os.path.isfile('logdogs.pid'):
            with open('logdogs.pid') as f:
                os.kill(int(f.read()), signal.SIGTERM)
        self.rm('logdogs.log')
        self.rm('logdogs.out')
        self.rm('logdogs.err')
        self.rm('logdogs.pid')
        self.rm('a.log')
        self.rm('b.log')
        self.rm('logs')

    def test_example(self):
        cmd = 'python example.py'
        self.sh(cmd)
        pid = self.pgrep(cmd)[0]
        self.see('logdogs.pid', pid)
        self.see('logdogs.log', ['start from'])
        sleep(6)
        self.see('logdogs.log', 'loop 1')
        self.see('logdogs.log', 'process 0 lines of logdogs.log')

        self.sh('echo wrong >> a.log')
        sleep(5)
        self.see('logdogs.log', 'loop 2')
        self.see('logdogs.log', ['process 1 lines of a.log', 'process 1 lines of a.log'])

        self.sh('kill %s' % pid)
        sleep(.1)
        self.see('logdogs.err', 'Terminating on signal 15')
        self.see('logdogs.log', 'close files')


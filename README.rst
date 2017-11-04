logdogs
=======

.. image:: https://img.shields.io/travis/yanxurui/logdogs/master.svg
    :target: https://travis-ci.org/yanxurui/logdogs

.. image:: https://img.shields.io/pypi/v/logdogs.svg
    :target: https://pypi.org/project/logdogs

.. image:: https://img.shields.io/pypi/pyversions/logdogs.svg
    :target: https://pypi.org/project/logdogs

.. image:: https://img.shields.io/pypi/status/logdogs.svg
    :target: https://pypi.org/project/logdogs


A daemon to monitor keywords in any log files specified by glob pattern.

In the background log files are checked periodically by dogs and user
defined handlers are called when error lines are detected according the
keyword regex.

features
--------

-  glob path
-  regex keywords
-  compatible with logrotate
-  custmize handler function or callable object
-  log files don't have to exist before watch
-  a dog can watch multiple logs and a log can be watched by multiple
   dogs

usage
-----

install::

    pip install logdogs

start::

    logdogs -c conf.py

stop::

    kill <pid>

pid file will be removed automatically.

conf.py is your config file which contains upper case module variables
as configuration. Here is an example:

.. code:: python

    import os
    import logging

    LOG_FILE = 'logdogs.log'
    LOG_LEVEL = 'INFO'
    # you can even call basicConfig to customize the log instead

    INTEVAL = 10 # seconds

    DAEMONIZE = True
    DIR = os.path.abspath('.')
    PID_FILE = 'logdogs.pid'
    STDOUT = 'logdogs.out'
    STDERR = 'logdogs.err'
    # the above 4 configurations only work when DAEMONIZE is True

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
            "includes": [r"(?!)wrong"],
        }
    }

In this case, logdogs will run as a daemon process in current directory
and check log files every 10 seconds. a.log and b.log will be watched
both by dog test and glob. When a line containing ``wrong`` but not
``nothing`` is written to a.log, both dogs' handler will be called.

The effective variables in config file are described as below.

config
------

DOGS
~~~~

A Dog consists of:

1. a group of log files specified by glob pattern
2. a filter defined by includes and excludes
3. a handler function or a callable object

DOG is a dict in the form of ``{name: attribute}`` where ``name`` is not
important and ``attribute`` is a dict containing the following keys:

handler
^^^^^^^

a handler is a function which has the following signature::

    def handler(file, lines):
        """
        file is the absolute path of the log file.
        lines is a list of the lines includes newline characters(\n)
        """
        pass

the default handler is a callable object of::

    class Handler(object):
        """
        default handler for log event
        """
        def __call__(self, file, lines):
            print(lines)

It's up to you to deal with the log line in this handler such as
mailing, send to wechat and etc.

includes & excludes
^^^^^^^^^^^^^^^^^^^

They are regular expressions and both are optional. The handler is
called if any regex in includes is found in the line and any regex in
excludes is not found in the line. That is to say, ``or`` logic is
applied in the includes and ``and`` logic is applied in the excludes.

path
^^^^

path is a list, it supports the following forms:

1. single file: ``['/var/logs/a.log']``
2. multiple files: ``['/var/logs/a.log', '/var/logs/b.log']``
3. glob pattern: ``['/var/logs/*.log']``
4. recursive glob (similar as globstar on bash): ``['/var/logs/**/*.log']``

-  In the last 2 cases, a log file is not required to exist when monitor
   starts
-  The same log file can overlap in multiple dog block

INTEVAL
~~~~~~~

seconds for sleep between checks

log
~~~

-  LOG_FILE: specify log file. logs are printed to stdout if not
   specified
-  LOG_LEVEL(WARNING): which log level to use

daemonize
~~~~~~~~~

-  DAEMONIZE(False): whether to start a daemon process running in the
   backgroup, **the following configs only take effect when DAEMONIZE is
   True**
-  DIR: set the working directory, **default is /**
-  PID_FILE: pid file path
-  STDOUT: where to redirect stdout(print exception traceback for
   example)
-  STDERR: where to redirect sterr

Development
-----------

::

    python setup.py develop

test
~~~~

::

    python -m unittest -v test_function.TestFunction

todo
~~~~

-  more handlers
-  threading

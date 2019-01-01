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

Log files are checked periodically in the background by dogs and user
defined handlers are called when error lines are detected according to the
keyword regex.

features
--------

-  glob path
-  regex keywords
-  compatible with logrotate
-  custmize handler function or callable object, a MailHandler is provided
-  log files don't have to exist before watch
-  a dog can watch multiple log files and a log file can be watched by multiple
   dogs too

usage
-----

install::

    pip install logdogs


Here is an example:

.. code:: python

    #!/usr/bin/env
    # coding=utf-8

    import os
    import logging

    from logdogs import LogDogs, MailHandler

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
            "handler": MailHandler('you@example.com', 'your password', server, port=465, ssl=True, to_addrs=['receiver1@example.com']),
            "includes": [r"wrong"],
        }
    }

    logdogs = LogDogs(DOGS)
    logdogs.run(
        10,
        daemon=True,
        pid='logdogs.pid',
        stdout='logdogs.out',
        stderr='logdogs.err',
        working_directory=os.path.abspath('.')
    )



In this case, logdogs will run as a daemon process in current directory
and check log files every 10 seconds. a.log and b.log will be watched
both by dog test and glob. When a line containing ``wrong`` but not
``nothing`` is written to a.log, both dogs' handler will be called. Dog glob will send eamil to your mailbox.


API
------

``LogDogs.__init__``
~~~~~~~~~~~~~~~~~~~~

::

    LogDogs.__init__(self, DOGS)

A Dog consists of:

1. a group of log files specified by glob pattern
2. a filter defined by includes and excludes
3. a handler function or a callable object

DOGS is a dict in the form of ``{name: attribute}`` where ``name`` is not
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


``LogDogs.run``
~~~~~~~~~~~~~~~~~

::

    LogDogs.run(self, inteval, daemon=False, pid=None, stdout=None, stderr=None, **kargs)

inteval
^^^^^^^

seconds for sleep between checks

daemonize
^^^^^^^^^

-  daemon(False): whether to start a daemon process running in the
   backgroup, **the following configs only take effect when DAEMONIZE is
   True**
-  pid: pid file path
-  stdout: where to redirect stdout(print)
-  stderr: where to redirect sterr(exception traceback)
-  kargs: other keywords arguments accepted by python-daemon'sDaemonContext for example working_directory which **is / by default**

Development
-----------

::

    python setup.py develop

test
~~~~

::

    python -m unittest -v test_all

todo
~~~~

-  more handlers
-  threading

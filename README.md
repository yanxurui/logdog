# a multiple logs monitor

Logs are checked periodically by dogs in the backgroup. Lines match the keyword patterns are processed by user defined handler.

## features
* glob path
* regex keywords
* support logrotate
* custmize handler
* does not require log file to exist before watch
* a dog can watch multiple logs and a log can be watched by multiple dogs


## usage
install
```
pip install logdogs
```
start
```
logdogs -c conf.py
```
stop
```
kill <pid>
```

conf.py is your config file which contains upper case module variables as configuration. An example can be found [here](yanxurui/logdogs/blob/master/tests/conf.py). The effective variables are classified as follows:


## config

### INTEVAL
seconds for sleep between checks

### dog
A Dog consists of:

1. a group of log files specified by glob pattern
2. a filter defined by includes and excludes
3. a handler function or a callable object

DOG is a dict in the form of `{name: attribute}` where `name` is not important and `attribute` is a dict containing the following keys:

#### handler
a handler is a function which has the following signature
```
def handler(file, lines):
	"""
	`file` is the absolute path of the log file.
	`lines` includes newline character(\n)
	"""
	pass
```

the default handler is a callable object of:
```
class Handler(object):
    """
    default handler for log event
    """
    def __call__(self, file, lines):
        print(line, end='')

```
It's up to you to deal with the log line in this handler such as mailing, send to wechat and etc.

#### includes & excludes
They are regular expressions and both are optional.
The handler is called if any regex in includes is found in the line and any regex in excludes is not found in the line.
That is to say, `or` logic is applied in the includes and `and` logic is applied in the excludes.


#### path
path is a list, it supports the following forms:

1. single file: ['/var/logs/a.log']
2. multiple files: ['/var/logs/a.log', '/var/logs/b.log']
3. glob pattern: ['/var/logs/*.log']
4. recursive glob (similar as globstar on bash): ['/var/logs/**/*.log']

* In the last 2 cases, a log file is not required to exist when monitor starts
* The same log file can overlap in multiple dog block


### log
* LOG_FILE: specify log file. logs are printed to stdout if not specified
* LOG_LEVEL(WARNING): which log level to use


### daemonize
* DAEMONIZE(False): whether to start a daemon process running in the backgroup, **the following configs only take effect when DAEMONIZE is True**
* PID_FILE: pid file path
* STDOUT: where to redirect stdout(pyinotify's internal log)
* STDERR: where to redirect sterr(exception traceback)

according to python-daemon:

* Be cautious that `PID_FILE` `STDOUT` `STDERR` must be writtable by the current user and they are relative to root `/`


## Development

```
python setup.py develop
```

### test
```
python -m unittest -v test_function.TestFunction
```

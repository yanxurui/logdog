# a realtime logs monitor

## features
* real time
* glob path
* regex keywords
* support logrotate
* custmize handler
* does not require log file to exist before watch
* a dog can watch multiple logs and a log can be watched by multiple dogs


## usage
install
```
git clone https://github.com/yanxurui/logdog
cd logdog
python setup.py install
```
start
```
python2.7 -m logdog -c conf.py
```
stop
```
kill -s SIGINT <pid>
```

conf.py is your config file which contains upper case module variables as configuration. An example can be found [here](yanxurui/logdog/blob/master/conf.py). The effective variables are classified as follows:

### dog
A Dog consists of:

1. a group of log files specified by glob pattern
2. a filter defined by includes and excludes
3. a handler function or a callable object

DOG is a dict in the form of `{name: attribute}` where `name` is not important and `attribute` is a dict containing the following keys:

#### handler
a handler is a function which has the following signature
```
def handler(line, file):
	"""
	`line` includes newline character(\n)
	`file` is the absolute path of the log file.
	"""
	pass
```

the default handler is a callable object of:
```
class Handler(object):
    """
    default handler for log event
    """
    def __call__(self, line, file):
        print(line, end='')

```
It's up to you to deal with the log line in this handler such as mailing, send to wechat and etc. It's a bad idea to do time consuming tasks here because it will delay other other logs' handling even though it won't cause write event missing.


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

according to pyinotify:

* Be cautious that `PID_FILE` `STDOUT` `STDERR` must be writtable by the current user and they are relative to root `/`
* `STDOUT` and `STDERR` should not be the same file otherwise they will overwrite each other.


## Development

```
python setup.py develop
```

### test
```
python2.7 -m unittest -v test_function
```

### benchmark
```
cd tests
chmod +x benchmark.sh
./benchmark.sh
```

### inotify test

This tool requires inotify to work.
Here are some test cases on an Arch Linux(Linux version 4.11.7)

#### watched file is renamed
```
watch a.txt

mv a.txt b.txt
MoveSELF /home/yanxurui/test/keepcoding/python/io/a.txt-unknown-path

echo bbb>>b.txt
Modify: /home/yanxurui/test/keepcoding/python/io/a.txt-unknown-path

mv b.txt a.txt
MoveSELF /home/yanxurui/test/keepcoding/python/io/a.txt-unknown-path
```

#### watched file is moved to parent directory
```
watch a.txt

mv a.txt ../
MoveSELF /home/yanxurui/test/keepcoding/python/io/a.txt-unknown-path

mv ../a.txt ./
MoveSELF /home/yanxurui/test/keepcoding/python/io/a.txt-unknown-path
```

#### watch a file repeatedly
```
watch a.txt
watch a.txt

echo aaa >> a.txt
Modify: /home/yanxurui/test/keepcoding/python/io/a.txt
```

#### watch a file again after rm watch
```
watch a.txt
{'a.txt': 1}
mv a.txt ../
rm_watch 1
touch a.txt
add_watch a.txt
{'a.txt': 2}
```

#### watch a file and its directory at the same time
```
touch a.txt
watch .
watch a.txt

echo aaa >> a.txt
Modify: /home/yanxurui/test/keepcoding/python/io/a.txt
Modify: /home/yanxurui/test/keepcoding/python/io/a.txt

mv a.txt b.txt
MoveFROM /home/yanxurui/test/keepcoding/python/io/a.txt
MoveTo /home/yanxurui/test/keepcoding/python/io/b.txt
MoveSELF /home/yanxurui/test/keepcoding/python/io/b.txt
```

#### watch recursively
```
tree logs
logs
└── a
    └── a.txt

watch logs rec
{'logs': 1, 'logs/a': 2}

touch logs/a/b.txt
path=logs/a
```

LOG_FILE = 'logdog.log'
LOG_LEVEL = 'DEBUG'

DAEMONIZE = True
PID_FILE = '/tmp/logdog.pid'
STDOUT = '/tmp/logdog.out'
STDERR = '/tmp/logdog.err'

class MyHandler(object):
    def __call__(self, line):
        print(line)

DOGS = {
    "test": {
        "paths": ["a.log", "b.log"],
        "handler": MyHandler(),
        "includes": [r"wrong"],
        "excludes": [r"long"]
    },
    "glob": {
        "paths": ["logs/**/*.log"],
        "handler": MyHandler(),
        "includes": [r"wrong"],
    }
}


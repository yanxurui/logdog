import os
import sys
import importlib

"""
use python module as config
"""

class Field(object):
    def __init__(self, name, types=str, default=None, required=False):
        self.name = name
        self.types = types
        self.default = default
        self.required = required

    def check(self, module):
        # required
        if not hasattr(module, self.name):
            if self.required: 
                raise Exception('field %s is required' % self.name)
            else:
                # default
                setattr(module, self.name, self.default)
                return

        v = getattr(module, self.name)
        # types
        if type(self.types) in (list, tuple):
            if type(v) not in self.types:
                raise Exception('field %s type(%s) is not any type in %s' % (self.name, type(v), self.types))
        else:
            assert(type(self.types) is type)
            if type(v) is not self.types:
                raise Exception('field %s type(%s) does not match %s' % (self.name, type(v), self.types))


class Config(object):
    def __init__(self, path, *fields):
        """wrapper for the config module
        
        1. load config from a pure python file
        2. check fields
        
        Arguments:
            path {str} -- path to the config file
            fields {list} -- [a list of Field object]
        """
        self._bool = True
        self._config = self.load(path)
        for field in fields:
            field.check(self._config)

    def __getattr__(self, name):
        return getattr(self._config, name, None)

    def load(self, path):
        if os.path.exists(path):
            sys.path.insert(1, os.path.dirname(os.path.abspath(path)))
            return importlib.import_module(os.path.splitext(os.path.basename(path))[0])
        else:
            raise Exception('file %s does not exist' % path)

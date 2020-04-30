# Import OrderedDict from here instead of the standard library to avoid
# an import loop.  Yes I know this is stupid but I named the collections
# module before I knew anything about collections.OrderedDict.
from collections import OrderedDict

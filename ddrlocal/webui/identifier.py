import os

from django.conf import settings
from django.http import HttpRequest

from DDR.models.identifier import Identifier as DDRIdentifier


class Identifier(DDRIdentifier):

    def __init__(self, *args, **kwargs):
        if kwargs and 'request' in kwargs:
            request = kwargs.pop('request')
        elif args and isinstance(args[0], HttpRequest):
            argz = [a for a in args]
            args = argz
            request = args.pop(0)
        else:
            request = None
        if request:
            object_id = [
                part
                for part in request.META['PATH_INFO'].split(os.path.sep)
                if part
            ][1]
            kwargs['id'] = object_id
        kwargs['base_path'] = settings.MEDIA_BASE
        super(Identifier, self).__init__(*args, **kwargs)
    
    def __repr__(self):
        return "<webui.models.Identifier %s:%s>" % (self.model, self.id)

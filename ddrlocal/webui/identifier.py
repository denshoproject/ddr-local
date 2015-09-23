import os

from django.conf import settings

from DDR.models.identifier import Identifier as DDRIdentifier


class Identifier(DDRIdentifier):

    def __repr__(self):
        return "<webui.models.Identifier %s:%s>" % (self.model, self.id)
    
    @staticmethod
    def from_id(object_id):
        return DDRIdentifier.from_id(object_id, settings.MEDIA_BASE)
    
    @staticmethod
    def from_request(request):
        object_id = [
            part
            for part in request.META['PATH_INFO'].split(os.path.sep)
            if part
        ][1]
        return DDRIdentifier.from_id(object_id, settings.MEDIA_BASE)

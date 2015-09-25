import os

from django.conf import settings
from django.core.urlresolvers import reverse
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

    def breadcrumbs(self):
        """Returns list of URLs,titles for printing object breadcrumbs.
        
        >>> i = Identifier(id='ddr-test-123-456-master-acbde12345')
        >>> i.breadcrumbs()
        [
          {'url:'/ui/ddr-testing-300/', 'label':'ddr-testing-300'},
          {'url:'/ui/ddr-testing-300-1/', 'label':'1'},
          {'url:'/ui/ddr-testing-300-1/master/', 'label':'master'},
          {'url:'', 'label':'37409ecadb'},
        ]
        """
        lineage = self.lineage()[:-2]  # start with collection
        cid = lineage.pop()
        crumb = {
            'url': reverse('webui-%s' % cid.model, kwargs=cid.parts),
            'label': cid.id,
        }
        crumbs = [crumb]
        lineage.reverse()
        for i in lineage:
            crumb = {
                'url': reverse('webui-%s' % i.model, kwargs=i.parts),
                'label': i.parts.values()[-1],
            }
            crumbs.append(crumb)
        return crumbs


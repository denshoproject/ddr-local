import os

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpRequest

from DDR.identifier import Identifier as DDRIdentifier
from DDR.identifier import CHILDREN_ALL, MODULES, VALID_COMPONENTS
from DDR.identifier import MODEL_CLASSES as DDR_MODEL_CLASSES
from DDR.identifier import IdentifierFormatException
from DDR.identifier import ELASTICSEARCH_CLASSES
from DDR.identifier import ELASTICSEARCH_CLASSES_BY_MODEL
from DDR.identifier import ELASTICSEARCH_LIST_FIELDS
from DDR.identifier import INHERITABLE_FIELDS

# TODO this isn't too far removed from hard-coding...
MODEL_CLASSES = {}
for k,v in DDR_MODEL_CLASSES.iteritems():
    v['module'] = v['module'] = 'webui.models'
    MODEL_CLASSES[k] = v


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
        return "<%s.%s %s:%s>" % (self.__module__, self.__class__.__name__, self.model, self.id)
    
    def absolute_url(self):
        return reverse('webui-%s' % self.model, args=[self.id])
    
    def object_class(self, mappings=MODEL_CLASSES):
        """Identifier's object class according to mappings.
        """
        return super(Identifier, self).object_class(mappings=MODEL_CLASSES)
    
    def object(self, mappings=MODEL_CLASSES):
        return super(Identifier, self).object_class(mappings).from_identifier(self)
    
    def parent(self, stubs=False):
        parent_parts = self._parent_parts()
        for model in self._parent_models(stubs):
            idparts = parent_parts
            idparts['model'] = model
            try:
                return Identifier(idparts, base_path=self.basepath)
            except IdentifierFormatException:
                pass
        return None
    
    def child(self, model, idparts, base_path=settings.MEDIA_BASE):
        return super(Identifier, self).child(model, idparts, base_path=base_path)
    
    def breadcrumbs(self, endpoint=''):
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
        lineage = self.lineage(stubs=True)[:-2]  # start with collection
        cid = lineage.pop()
        crumb = {
            'url': reverse('webui-%s' % cid.model, args=[cid.id]),
            'label': cid.id,
        }
        crumbs = [crumb]
        lineage.reverse()
        for i in lineage:
            crumb = {
                'url': reverse('webui-%s' % i.model, args=[i.id]),
                'label': i.parts.values()[-1],
            }
            crumbs.append(crumb)
        if endpoint:
            crumb = {
                'url': '',
                'label': endpoint,
            }
            crumbs.append(crumb)
        # endpoint is never linked
        crumbs[-1]['url'] = ''
        return crumbs

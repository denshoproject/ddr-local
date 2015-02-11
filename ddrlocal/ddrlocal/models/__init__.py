import logging
logger = logging.getLogger(__name__)

from DDR.models import Collection as DDRCollection
from DDR.models import Entity as DDREntity
from DDR.models import File as DDRFile

class DDRLocalCollection( DDRCollection ):
    """
    Subclass of DDR.models.Collection (renamed).
    Used to contain functions for reading/writing collection.json and ead.xml,
    but now is only here to prevent import clashing between DDR.models.Collection
    and webui.models.Collection.
    """

    def __init__(self, *args, **kwargs):
        super(DDRLocalCollection, self).__init__(*args, **kwargs)
    
    def __repr__(self):
        """Returns string representation of object.
        
        >>> c = DDRLocalCollection('/tmp/ddr-testing-123')
        >>> c
        <DDRLocalCollection ddr-testing-123>
        """
        return "<DDRLocalCollection %s>" % (self.id)

class DDRLocalEntity( DDREntity ):
    """
    Subclass of DDR.models.Entity (renamed).
    Used to contain functions for reading/writing entity.json and mets.xml,
    but now is only here to prevent import clashing between DDR.models.Entity
    and webui.models.Entity.
    """
    
    def __init__(self, *args, **kwargs):
        super(DDRLocalEntity, self).__init__(*args, **kwargs)

class DDRLocalFile( DDRFile ):
    """
    Subclass of DDR.models.File (renamed).
    """
    
    def __init__(self, *args, **kwargs):
        super(DDRLocalFile, self).__init__(*args, **kwargs)
    
    def __repr__(self):
        return "<DDRLocalFile %s (%s)>" % (self.basename, self.basename_orig)

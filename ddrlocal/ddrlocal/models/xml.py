import ConfigParser
import logging
logger = logging.getLogger(__name__)
import os

from lxml import etree

from DDR import TEMPLATE_EAD


def load_template(filename):
    template = ''
    with open(filename, 'r') as f:
        template = f.read()
    return template


class EAD( object ):
    """Encoded Archival Description (EAD) file.
    """
    path = None
    collection_path = None
    filename = None
    tree = None
    xml = None
    
    def __init__( self, collection ):
        self.collection_path = collection.path
        self.filename = collection.ead_path
        self.path = collection.ead_path
        self.path_rel = os.path.basename(self.path)
        self.read()
        #logger.debug('\n{}'.format(etree.tostring(self.tree, pretty_print=True)))
    
    @staticmethod
    def create( path ):
        logger.debug('    EAD.create({})'.format(path))
        t = load_template(TEMPLATE_EAD)
        with open(path, 'w') as f:
            f.write(t)
    
    def read( self ):
        #logger.debug('    EAD.read({})'.format(self.filename))
        with open(self.filename, 'r') as f:
            self.xml = f.read()
            self.tree = etree.fromstring(self.xml)
    
    def write( self ):
        logger.debug('    EAD.write({})'.format(self.filename))
        xml = etree.tostring(self.tree, pretty_print=True)
        with open(self.filename, 'w') as f:
            f.write(xml)
    
    def update_dsc( self, collection ):
        """Repopulates <ead><dsc> based on collection.entities().
        
        TODO Instead of creating a new <dsc>, read current data then recreate with additional files
        
        <dsc type="combined">
          <head>Inventory</head>
          <c01>
            <did>
              <unittitle eid="{eid}">{title}</unittitle>
            </did>
          </c01>
        </dsc>
        """
        # build new <dsc> element
        dsc = etree.Element('dsc', type='combined')
        head = etree.SubElement(dsc, 'head')
        head.text = 'Inventory'
        n = 0
        for entity in collection.entities():
            n = n + 1
            # add c01, did, unittitle
            c01 = etree.SubElement(dsc, 'c01')
            did = etree.SubElement(c01, 'did')
            unittitle = etree.SubElement(did, 'unittitle')
            unittitle.set('eid', entity.uid)
            unittitle.text = 'Entity description goes here'
        # swap out existing one
        tags = self.tree.xpath('/ead/dsc')
        if tags:
            dsc_old = tags[0]
            self.tree.replace(dsc_old, dsc)
        else:
            ead = self.tree.xpath('/ead')[0]
            etree.SubElement(ead, dsc)

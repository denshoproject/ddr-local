import logging
logger = logging.getLogger(__name__)
import os

from lxml import etree



#MODULE_PATH   = os.path.dirname(os.path.abspath(__file__))
#TEMPLATE_PATH = os.path.join(MODULE_PATH, 'templates')
#EAD_TEMPLATE  = os.path.join(TEMPLATE_PATH, 'collection_ead.xml.tpl')
#METS_TEMPLATE = os.path.join(TEMPLATE_PATH, 'entity_mets.xml.tpl' )

NAMESPACES = {
    'mets':  'http://www.loc.gov/standards/mets/mets.xsd',
    'mix':   'http://www.loc.gov/mix/v10',
    'mods':  'http://www.loc.gov/mods/v3',
    'rts':   'http://cosimo.stanford.edu/sdr/metsrights/',
    'xlink': 'http://www.w3.org/1999/xlink',
    'xsi':   'http://www.w3.org/2001/XMLSchema-instance',}

NAMESPACES_TAGPREFIX = {}
for k,v in NAMESPACES.iteritems():
    NAMESPACES_TAGPREFIX[k] = '{%s}' % v

NAMESPACES_XPATH = {'m': NAMESPACES['mets'],}

NSMAP = {None : NAMESPACES['mets'],}



#def load_template(filename):
#    template = ''
#    with open(filename, 'r') as f:
#        template = f.read()
#    return template



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
    
 #   @staticmethod
 #   def create( path ):
 #       logger.debug('    EAD.create({})'.format(path))
 #       t = load_template(EAD_TEMPLATE)
 #       with open(path, 'w') as f:
 #           f.write(t)

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


class METS( object ):
    """Metadata Encoding and Transmission Standard (METS) file.
    """
    path = None
    entity_path = None
    filename = None
    tree = None
    xml = None
    
    def __init__( self, entity ):
        self.entity_path = entity.path
        self.filename = entity.mets_path
        self.path = entity.mets_path
        self.read()
        #logger.debug('\n{}'.format(etree.tostring(self.tree, pretty_print=True)))
    
#    @staticmethod
#    def create( path ):
#        logger.debug('    METS.create({})'.format(path))
#        t = load_template(METS_TEMPLATE)
#        with open(path, 'w') as f:
#            f.write(t)
    
    def read( self ):
        #logger.debug('    METS.read({})'.format(self.filename))
        with open(self.filename, 'r') as f:
            self.xml = f.read()
            self.tree = etree.fromstring(self.xml)
    
    def write( self ):
        logger.debug('    METS.write({})'.format(self.filename))
        xml = etree.tostring(self.tree, pretty_print=True)
        with open(self.filename, 'w') as f:
            f.write(xml)
    
    def update_filesec( self, entity ):
        """Repopulates <mets:mets><mets:fileSec> based on entity files.
        
        TODO Instead of creating a new <fileSec>, read current data then recreate with additional files
        
        <mets:fileSec>
          <mets:fileGrp USE="image/master">
            <mets:file GROUPID="GID1" ID="FID1" ADMID="ADM1 ADM5" SEQ="1" MIMETYPE="image/tiff" CREATED="2003-01-22T00:00:00.0">
              <mets:FLocat LOCTYPE="URL" xlink:href="http://nma.berkeley.edu/ark:/28722/bk0001j1m10" />
            </mets:file>
          </mets:fileGrp>
          <mets:fileGrp USE="image/thumbnail">
            <mets:file GROUPID="GID1" ID="FID2" SEQ="1" ADMID="ADM2 ADM6" MIMETYPE="image/gif" CREATED="2003-01-22T00:00:00.0">
              <mets:FLocat LOCTYPE="URL" xlink:href="http://nma.berkeley.edu/ark:/28722/bk0001j1m2j" />
            </mets:file>
          </mets:fileGrp>
        </mets:fileSec>
        """
        NS = NAMESPACES_TAGPREFIX
        ns = NAMESPACES_XPATH
        payload_path = entity.files_path
        
        def relative_path(entity_path, payload_file):
            """return relative path to payload
            """
            if entity_path[-1] != '/':
                entity_path = '{}/'.format(entity_path)
            return payload_file.replace(entity_path, '')
        
        # <mets:fileSec>
        filesec = etree.Element(NS['mets']+'fileSec', nsmap=NSMAP)
        n = 0
        for md5,path in entity.checksums('md5'):
            n = n + 1
            use = 'unknown'
            path = relative_path(entity.path, path)
            # mets:fileGrp, mets:file, mets:Flocat
            fileGrp = etree.SubElement(filesec, NS['mets']+'fileGrp', USE=use)
            ffile = etree.SubElement(
                fileGrp, NS['mets']+'file',
                GROUPID='GID1',
                ID='FID1',
                ADMID='ADM1 ADM5',
                SEQ='1',
                MIMETYPE='image/tiff',
                CREATED='',
                CHECKSUM=md5, CHECKSUMTYPE='md5')
            flocat = etree.SubElement(ffile, NS['mets']+'FLocat', LOCTYPE='URL',)
            flocat.set(NS['xlink']+'href', path)
        
        # swap out existing one
        tags = self.tree.xpath('/m:mets/m:fileSec', namespaces=ns)
        if tags:
            filesec_old = tags[0]
            self.tree.replace(filesec_old, filesec)
        else:
            rtags = self.tree.xpath('/m:mets', namespaces=ns)
            if rtags:
                root = rtags[0]
                etree.SubElement(root, filesec)

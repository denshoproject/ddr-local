from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import os



#MODULE_PATH   = os.path.dirname(os.path.abspath(__file__))
#TEMPLATE_PATH = os.path.join(MODULE_PATH, 'templates')
#COLLECTION_JSON_TEMPLATE = os.path.join(TEMPLATE_PATH, 'collection.json.tpl' )
#ENTITY_JSON_TEMPLATE = os.path.join(TEMPLATE_PATH, 'entity.json.tpl' )

#def load_template(filename):
#    template = ''
#    with open(filename, 'r') as f:
#        template = f.read()
#    return template



class CollectionJSON():
    path = None
    path_rel = None
    collection_path = None
    filename = None
    data = None
    
    def __init__( self, collection ):
        self.collection_path = collection.path
        self.filename = collection.json_path
        self.path = collection.json_path
        self.path_rel = os.path.basename(self.path)
        self.read()
    
#    @staticmethod
#    def create( path ):
#        logger.debug('    CollectionJSON.create({})'.format(path))
#        tpl = load_template(COLLECTION_JSON_TEMPLATE)
#        with open(path, 'w') as f:
#            f.write(tpl)
    
    def read( self ):
        #logger.debug('    CollectionJSON.read({})'.format(self.filename))
        with open(self.filename, 'r') as f:
            self.data = json.loads(f.read())
     
    def write( self ):
        logger.debug('    CollectionJSON.write({})'.format(self.filename))
        json_pretty = json.dumps(self.data, indent=4, separators=(',', ': '), sort_keys=True)
        with open(self.filename, 'w') as f:
            f.write(json_pretty)
    
    def update_checksums( self, collection ):
        """Returns file info in sorted list.
        """
        logger.debug('    CollectionJSON.update_files({})'.format(collection))
        
        fdict = {}
        for entity in collection.entities():
            fdict[entity.uid] = {'eid':entity.uid,}
        
        # has to be sorted list so can meaningfully version
        files = []
        fkeys = fdict.keys()
        fkeys.sort()
        for key in fkeys:
            files.append(fdict[key])
        
        data = self.data
        
        # add files if absent
        present = False
        for field in self.data:
            for key in field.keys():
                if key == 'files':
                    present = True
        if not present:
            self.data.append( {'files':[]} )
        
        for field in self.data:
            for key in field.keys():
                if key == 'files':
                    field[key] = files



class EntityJSON():
    path = None
    path_rel = None
    entity_path = None
    filename = None
    data = None
    
    def __init__( self, entity ):
        self.entity_path = entity.path
        self.filename = entity.json_path
        self.path = entity.json_path
        self.path_rel = os.path.basename(self.path)
        self.read()
    
#    @staticmethod
#    def create( path ):
#        logger.debug('    EntityJSON.create({})'.format(path))
#        tpl = load_template(ENTITY_JSON_TEMPLATE)
#        with open(path, 'w') as f:
#            f.write(tpl)
    
    def read( self ):
        #logger.debug('    EntityJSON.read({})'.format(self.filename))
        with open(self.filename, 'r') as f:
            self.data = json.loads(f.read())
     
    def write( self ):
        logger.debug('    EntityJSON.write({})'.format(self.filename))
        json_pretty = json.dumps(self.data, indent=4, separators=(',', ': '), sort_keys=True)
        with open(self.filename, 'w') as f:
            f.write(json_pretty)
    
    CHECKSUMS = ['sha1', 'sha256', 'files']
    def update_checksums( self, entity ):
        """Returns file info in sorted list.
        """
        logger.debug('    EntityJSON.update_checksums({})'.format(entity))
        
        def relative_path(entity_path, payload_file):
            # relative path to payload
            if entity_path[-1] != '/':
                entity_path = '{}/'.format(entity_path)
            return payload_file.replace(entity_path, '')
        
        fdict = {}
        for sha1,path in entity.checksums('sha1'):
            relpath = relative_path(entity.path, path)
            size = os.path.getsize(path)
            fdict[relpath] = {'path':relpath,
                              'basename':os.path.basename(path),
                              'sha1':sha1,
                              'size':size,}
        for sha256,path in entity.checksums('sha256'):
            relpath = relative_path(entity.path, path)
            fdict[relpath]['sha256'] = sha256
        for md5,path in entity.checksums('md5'):
            relpath = relative_path(entity.path, path)
            fdict[relpath]['md5'] = md5
        
        # has to be sorted list so can meaningfully version
        files = []
        fkeys = fdict.keys()
        fkeys.sort()
        for key in fkeys:
            files.append(fdict[key])

        data = self.data

        # add files if absent
        present = False
        for field in self.data:
            for key in field.keys():
                if key == 'files':
                    present = True
        if not present:
            self.data.append( {'files':[]} )
        
        for field in self.data:
            for key in field.keys():
                if key == 'files':
                    field[key] = files

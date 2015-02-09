import json

from ddrlocal import models
from ddrlocal.models import test as testmodule


TEST_DOCUMENT = """[
    {
        "application": "https://github.com/densho/ddr-local.git",
        "commit": "52155f819ccfccf72f80a11e1cc53d006888e283  (HEAD, repo-models) 2014-09-16 16:30:42 -0700",
        "git": "git version 1.7.10.4; git-annex version: 3.20120629",
        "models": "",
        "release": "0.10"
    },
    {"id": "ddr-test-123"},
    {"timestamp": "2014-09-19T03:14:59"},
    {"status": 1},
    {"title": "TITLE"},
    {"description": "DESCRIPTION"}
]"""

class Document(object):
    pass

class Form(object):
    pass


def test_labels_values():
    document = Document()
    models.load_json(document, testmodule, TEST_DOCUMENT)
    expected = [
        {'value': u'ddr-test-123', 'label': 'ID'},
        {'value': u'2014-09-19T03:14:59', 'label': 'Timestamp'},
        {'value': 1, 'label': 'Status'},
        {'value': u'TITLE', 'label': 'Title'},
        {'value': u'DESCRIPTION', 'label': 'Description'}
    ]
    assert models.labels_values(document, testmodule) == expected

def test_form_prep():
    document = Document()
    models.load_json(document, testmodule, TEST_DOCUMENT)
    expected = {
        'id': u'ddr-test-123',
        'timestamp': u'2014-09-19T03:14:59',
        'status': 1,
        'title': u'TITLE',
        'description': u'DESCRIPTION',
    }
    assert models.form_prep(document, testmodule) == expected

def test_form_post():
    document = Document()
    form = Form()
    form.cleaned_data = {
        'id': 'ddr-test-123',
        'timestamp': '2014-09-19T12:34:56',
        'status': 0,
        'title': 'NEW TITLE',
        'description': 'NEW DESCRIPTION',
    }
    models.load_json(document, testmodule, TEST_DOCUMENT)
    models.form_post(document, testmodule, form)
    assert document.id == "ddr-test-123"
    assert document.timestamp == "2014-09-19T12:34:56"
    assert document.status == 0
    assert document.title == "NEW TITLE"
    assert document.description == "NEW DESCRIPTION"    



#DDRLocalCollection
#DDRLocalCollection.__init__
#DDRLocalCollection.__repr__
#DDRLocalCollection.entities
#DDRLocalCollection.inheritable_fields
#DDRLocalCollection.form_prep
#DDRLocalCollection.form_post
#DDRLocalCollection.json
#DDRLocalCollection.from_json
#DDRLocalCollection.load_json
#DDRLocalCollection.dump_json
#DDRLocalCollection.ead
#DDRLocalCollection.dump_ead

#DDRLocalEntity
#DDRLocalEntity.__init__
#DDRLocalEntity.__repr__
#DDRLocalEntity.files_master
#DDRLocalEntity.files_mezzanine
#DDRLocalEntity.detect_file_duplicates
#DDRLocalEntity.rm_file_duplicates
#DDRLocalEntity.file
#DDRLocalEntity._addfile_log_path
#DDRLocalEntity.files_log
#DDRLocalEntity.inherit
#DDRLocalEntity.inheritable_fields
#DDRLocalEntity.labels_values
#DDRLocalEntity.form_prep
#DDRLocalEntity.form_post
#DDRLocalEntity.json
#DDRLocalEntity.from_json
#DDRLocalEntity._load_file_objects
#DDRLocalEntity.load_json
#DDRLocalEntity.prep_file_metadata
#DDRLocalEntity.dump_json
#DDRLocalEntity.mets
#DDRLocalEntity.dump_mets
#DDRLocalEntity.add_file
#DDRLocalEntity.add_access
#DDRLocalEntity.checksums

# DDRLocalFile
# DDRLocalFile.__init__
# DDRLocalFile.__repr__
# DDRLocalFile.files_rel
# DDRLocalFile.present
# DDRLocalFile.access_present
# DDRLocalFile.inherit
# DDRLocalFile.labels_values
# DDRLocalFile.form_prep
# DDRLocalFile.form_post
# DDRLocalFile.from_json
# DDRLocalFile.load_json
# DDRLocalFile.dump_json
# DDRLocalFile.file_name
# DDRLocalFile.set_path
# DDRLocalFile.set_access
# DDRLocalFile.file
# DDRLocalFile.dict
# DDRLocalFile.access_filename
# DDRLocalFile.links_incoming
# DDRLocalFile.links_outgoing
# DDRLocalFile.links_all

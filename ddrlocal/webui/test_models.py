import json

from webui import models


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


def test_git_version():
    out = models.git_version()
    assert 'git version' in out
    assert 'git-annex version' in out
    assert 'local repository version' in out

# TODO repo_models_valid
# TODO model_def_commits
# TODO model_def_fields

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

# TODO post_json
# TODO _child_jsons
# TODO _selected_inheritables
# TODO _selected_field_values
# TODO _load_object
# TODO _update_inheritables

# TODO Collection.__repr__
# TODO Collection.collection_path
# TODO Collection.gitstatus_path
# TODO Collection.url
# TODO Collection.cgit_url
# TODO Collection.cache_delete
# TODO Collection.from_json
# TODO Collection.repo_fetch
# TODO Collection.repo_status
# TODO Collection.repo_annex_status
# TODO Collection._repo_state
# TODO Collection.repo_synced
# TODO Collection.repo_ahead
# TODO Collection.repo_behind
# TODO Collection.repo_diverged
# TODO Collection.repo_conflicted
# TODO Collection.sync_status
# TODO Collection.sync_status_url
# TODO Collection.gitstatus
# TODO Collection.selected_inheritables
# TODO Collection.update_inheritables
# TODO Collection.model_def_commits
# TODO Collection.model_def_fields
# TODO Collection.form_prep
# TODO Collection.form_post
# TODO Collection.post_json

# TODO Entity.__repr__
# TODO Entity.entity_path
# TODO Entity.url
# TODO Entity.from_json
# TODO Entity.selected_inheritables
# TODO Entity.update_inheritables
# TODO Entity.model_def_commits
# TODO Entity.model_def_fields
# TODO Entity.form_prep
# TODO Entity.form_post
# TODO Entity.post_json
# TODO Entity.load_file_objects

# TODO DDRFile.__repr__
# TODO DDRFile.url
# TODO DDRFile.media_url
# TODO DDRFile.access_url
# TODO DDRFile.file_path
# TODO DDRFile.model_def_commits
# TODO DDRFile.model_def_fields
# TODO DDRFile.form_prep
# TODO DDRFile.form_post
# TODO DDRFile.post_json

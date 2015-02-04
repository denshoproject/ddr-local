from ddrlocal import models


def test_git_version():
    out = models.git_version()
    assert 'git version' in out
    assert 'git-annex version' in out
    assert 'local repository version' in out

# TODO module_function
# TODO module_xml_function
# TODO write_json
# TODO _inheritable_fields
# TODO _inherit
# TODO hash

# TODO DDRLocalCollection.__init__
# TODO DDRLocalCollection.__repr__
# TODO DDRLocalCollection.url
# TODO DDRLocalCollection.cgit_url
# TODO DDRLocalCollection.collection_path
# TODO DDRLocalCollection.repo_fetch
# TODO DDRLocalCollection.repo_status
# TODO DDRLocalCollection.repo_synced
# TODO DDRLocalCollection.repo_ahead
# TODO DDRLocalCollection.repo_behind
# TODO DDRLocalCollection.repo_diverged
# TODO DDRLocalCollection.repo_conflicted
# TODO DDRLocalCollection.repo_annex_status
# TODO DDRLocalCollection._lockfile
# TODO DDRLocalCollection.lock
# TODO DDRLocalCollection.unlock
# TODO DDRLocalCollection.locked
# TODO DDRLocalCollection.create
# TODO DDRLocalCollection.entities
# TODO DDRLocalCollection.inheritable_fields
# TODO DDRLocalCollection.labels_values
# TODO DDRLocalCollection.form_prep
# TODO DDRLocalCollection.form_post
# TODO DDRLocalCollection.json
# TODO DDRLocalCollection.from_json
# TODO DDRLocalCollection.load_json
# TODO DDRLocalCollection.dump_json
# TODO DDRLocalCollection.write_json
# TODO DDRLocalCollection.ead
# TODO DDRLocalCollection.dump_ead

# TODO DDRLocalEntity.__init__
# TODO DDRLocalEntity.__repr__
# TODO DDRLocalEntity.url
# TODO DDRLocalEntity.entity_path
# TODO DDRLocalEntity._lockfile
# TODO DDRLocalEntity.lock
# TODO DDRLocalEntity.unlock
# TODO DDRLocalEntity.locked
# TODO DDRLocalEntity.files_master
# TODO DDRLocalEntity.files_mezzanine
# TODO DDRLocalEntity.detect_file_duplicates
# TODO DDRLocalEntity.rm_file_duplicates
# TODO DDRLocalEntity.file
# TODO DDRLocalEntity.files_log
# TODO DDRLocalEntity.create
# TODO DDRLocalEntity.inherit
# TODO DDRLocalEntity.inheritable_fields
# TODO DDRLocalEntity.labels_values
# TODO DDRLocalEntity.form_prep
# TODO DDRLocalEntity.form_post
# TODO DDRLocalEntity.json
# TODO DDRLocalEntity.from_json
# TODO DDRLocalEntity._load_file_objects
# TODO DDRLocalEntity.load_json
# TODO DDRLocalEntity.dump_json
# TODO DDRLocalEntity.write_json
# TODO DDRLocalEntity.mets
# TODO DDRLocalEntity.dump_mets
# TODO DDRLocalEntity.add_file
# TODO DDRLocalEntity.add_access

# TODO DDRLocalFile.__init__
# TODO DDRLocalFile.__repr__
# TODO DDRLocalFile.url
# TODO DDRLocalFile.media_url
# TODO DDRLocalFile.access_url
# TODO DDRLocalFile.file_path
# TODO DDRLocalFile.files_rel
# TODO DDRLocalFile.present
# TODO DDRLocalFile.access_present
# TODO DDRLocalFile.inherit
# TODO DDRLocalFile.labels_values
# TODO DDRLocalFile.form_prep
# TODO DDRLocalFile.form_post
# TODO DDRLocalFile.from_json
# TODO DDRLocalFile.load_json
# TODO DDRLocalFile.dump_json
# TODO DDRLocalFile.write_json
# TODO DDRLocalFile.file_name
# TODO DDRLocalFile.set_path
# TODO DDRLocalFile.set_access
# TODO DDRLocalFile.file
# TODO DDRLocalFile.dict
# TODO DDRLocalFile.extract_xmp
# TODO DDRLocalFile.access_file_name
# TODO DDRLocalFile.make_access_file
# TODO DDRLocalFile.make_thumbnail
# TODO DDRLocalFile.links_incoming
# TODO DDRLocalFile.links_outgoing
# TODO DDRLocalFile.links_all

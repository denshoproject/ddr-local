from celery import task

@task
def extract_exif(src_path):
    """Look for EXIF data in specified file, extract if present.
    
    @param src_path Absolute path to source file.
    """
    pass

@task
def copy_to_entity(src_path, dest_path):
    """Copy src file to dest file.
    
    @param src_path Absolute path to source file.
    @param dest_path Absolute path to destination file, including basename.
    """
    pass

@task
def make_access_copy(dest_path):
    """Create an access copy from the dest file.
    
    Note: Access copy is made from the destination file, which is the same
    as the source file, but in a new place and with a new filename.
    
    @param dest_path Absolute path to destination file, including basename.
    """
    pass

@task
def make_thumbnail(dest_path):
    """Attempt to make a sorl-thumbnail.
    
    @param dest_path Absolute path to destination file, including basename.
    """
    pass

@task
def add_filemeta(entity, dest_path):
    """Add filemeta entry for src file.
    
    @param entity DDRLocalEntity object
    @param dest_path Absolute path to destination file, including basename.
    """
    pass

@task
def entity_annex_add(git_name, git_mail, entity, files):
    """Add and annex-add the file to the collection repo.
    
    @param git_name
    @param git_mail
    @param entity DDRLocalEntity object
    @param files List of DDRFile objects(?)
    """
    pass

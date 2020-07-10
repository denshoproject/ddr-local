import csv
import logging
logger = logging.getLogger(__name__)
from pathlib import Path

from django.conf import settings
from django.urls import reverse

from DDR.batch import Exporter, Importer
from DDR import commands
from DDR import dvcs
from DDR import fileio
from DDR import util

CSV_MODELS = {'entity':'objects', 'file':'files'}

CSV_IMPORT_FILE = '/tmp/import-{cid}-{model}.csv'


def export_to_csv(collection, model, logger=logger):
    """Write collection to CSV, then read
    """
    logger.info('All paths in %s' % collection.path_abs)
    paths = util.find_meta_files(
        basedir=collection.path_abs, model=model, recursive=1, force_read=1
    )
    logger.info('Exporting %s paths' % len(paths))
    path = csv_path(collection, model)
    result = Exporter.export(
        paths, model, path, required_only=False
    )
    logger.info(result)
    return path

def csv_rows(path):
    """Read CSV from filesystem and write to HttpResponse
    
    See https://docs.djangoproject.com/en/3.0/howto/outputting-csv/
    
    @param path: str
    @param response: HttpResponse
    @returns: HttpResponse
    """
    return fileio.read_csv(path)

def import_from_csv(csv_path, collection, model, git_name, git_mail):
    if model == 'entity':
        return import_entities(csv_path, collection, git_name, git_mail)
    elif model == 'file':
        return import_files(csv_path, collection, git_name, git_mail)

def import_entities(csv_path, collection, git_name, git_mail):
    imported = Importer.import_entities(
        csv_path=csv_path,
        cidentifier=collection.identifier,
        vocabs_url=settings.VOCABS_URL,
        git_name=git_name,
        git_mail=git_mail,
        agent='ddrlocal-csv-import-entity',
        dryrun=False,
    )
    imported_rel = sorted([o.identifier.path_rel() for o in imported])
    result = commands.commit_files(
        repo=dvcs.repository(collection.identifier.path_abs()),
        message='Imported by ddr-local from file "%s"' % csv_path,
        git_files=imported_rel,
        annex_files=[]
    )
    return result,imported_rel

def import_files(csv_path, collection, git_name, git_mail):
    imported = Importer.import_files(
        csv_path=csv_path,
        cidentifier=collection.identifier,
        vocabs_url=settings.VOCABS_URL,
        git_name=git_name,
        git_mail=git_mail,
        agent='ddrlocal-csv-import-file',
        row_start=0,
        row_end=9999999,
        dryrun=False
    )
    # flatten: import_files returns a list of file,entity lists
    imported_flat = [i for imprtd in imported for i in imprtd]
    # import_files returns absolute paths but we need relative
    imported_rel = [
        os.path.relpath(
            file_path_abs,
            collection.identifier.path_abs()
        )
        for file_path_abs in imported_flat
    ]
    result = commands.commit_files(
        repo=dvcs.repository(collection.identifier.path_abs()),
        message='Imported by ddr-local from file "%s"' % csv_path,
        git_files=imported_rel,
        annex_files=[],
    )
    return result

def models(model):
    return CSV_MODELS[model]

def csv_path(collection, model):
    return Path(settings.CSV_EXPORT_PATH[model] % collection.id)

def csv_filename(collection, model):
    return csv_path(collection, model).name

def csv_url(collection, model):
    if model == 'entity':
        return reverse('webui-collection-csv-entities', args=[collection.id])
    elif model == 'file':
        return reverse('webui-collection-csv-files', args=[collection.id])

def csv_import_path(cid, model):
    return Path(CSV_IMPORT_FILE.format(cid=cid, model=model))

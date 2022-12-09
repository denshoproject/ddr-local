from pathlib import Path

from django.conf import settings

from DDR.batch import Checker, Importer, InvalidCSVException
from DDR import csvfile
from DDR import fileio
from DDR import signatures
from DDR import util


def load_csv_run_checks(collection, model, csv_path, log_errors=False):
    """Load CSV and run validation checks
    TODO move to webui.batch?
    """
    # load csv
    try:
        headers,rowds,csv_errs = csvfile.make_rowds(fileio.read_csv(csv_path))
    except Exception as err:
        log.error(err)
    log = util.FileLogger(get_log_path(csv_path))
    errors = []
    # csv
    csv_errs,id_errs,validation_errs = Checker.check_csv(
        model, csv_path, rowds, headers, csv_errs,
        collection.identifier, settings.VOCABS_URL
    )
    header_errs,rowds_errs,file_errs = validation_errs
    for err in csv_errs: errors.append(f'CSV: {err}')
    for err in id_errs: errors.append(f'Identifier: {err}')
    for key,val in header_errs.items():
        errors.append(f"CSV header: {key}: {','.join(val)}")
    for err,items in rowds_errs.items():
        for item in items:
            errors.append(f'{err} {item}')
    for err in file_errs:
        for key,val in err.items():
            errors.append(f"{key}: {val}")
    # repository
    staged,modified = Checker.check_repository(collection.identifier)
    for f in staged: errors.append(f'STAGED: {f}')
    for f in modified: errors.append(f'MODIFIED: {f}')
    if model in ['file']:
        # files with missing parent entities
        entities,missing_entities = Importer._existing_bad_entities(
            Importer._eidentifiers(
                Importer._fid_parents(
                    Importer._fidentifiers(rowds, collection.identifier),
                    rowds,
                    collection.identifier)))
        if missing_entities:
            for e in missing_entities:
                errors.append(f'Entity {e} missing')
    if (model == 'entity') and idservice_client:
        chkeids = batch.Checker.check_eids(rowds, ci, idservice_client)
        for err in chkeids:
            errors.append(f'entity ID?: {err}')
    for err in errors:
        log.error(err)
    return rowds,errors

#def report_errors(results, csv_path):
#    log_path = get_log_path(csv_path)
#    # csv
#    for err in results.get('csv_errs', []}:
#        log.error(f'CSV: {err}')
#    for err in results.get('id_errs', []}:
#        log.error(f'Identifier: {err}')
#    for key,val in results.get('header_errs', {}).items():
#        log.error(f"CSV header: {key}: {','.join(val)}")
#    for err in results.get('rowds_errs', []}:
#        log.error(f'CSV row: {err}')
#    for err in results.get('file_errs', []}:
#        for key,val in err.items():
#            log.error(f"{key}: {val}")
#    # repository
#    for f in results.get('staged', []}:
#        log.error(f'staged: {f}')
#    for f in results.get('modified', []}:
#        log.error(f'modified: {f}')
#    # eids
#    if (model == 'entity'): # and idservice_client:
#        for err in results.get('chkeids', []}:
#            log.error(f'entity ID?: {err}')

def get_log_path(csv_path):
    if isinstance(csv_path, str):
        csv_path = Path(csv_path)
    return csv_path.parent / f'log/{csv_path.stem}.log'

def get_log_url(log_path):
    path_rel = str(log_path.relative_to(settings.VIRTUALBOX_SHARED_FOLDER))
    return f'/ddrshared/{path_rel}'

def csv_update_signatures(collection, rowds, user, mail, agent, log):
    """Choose signature File for each parent Entity in rowds
    
    This must be run *after* a CSV is imported and committed
    """
    log.info('Updating signatures')
    eidentifiers = Importer._eidentifiers(
        Importer._fid_parents(
            Importer._fidentifiers(rowds, collection.identifier),
            rowds,
            collection.identifier
        )
    )
    log.debug(f'{len(eidentifiers)} entities in {len(rowds)} rowds')
    files_written = []
    for ei in eidentifiers:
        entity_paths = util.find_meta_files(ei.path_abs(), recursive=True)
        updates = signatures.find_updates(signatures.choose(entity_paths))
        written = signatures.write_updates(updates)
        for path in written:
            log.debug(f'| {path}')
        files_written = files_written + written
    log.debug(f'Committing {len(files_written)} modified files')
    status,msg = signatures.commit_updates(
        collection, files_written, user, mail, agent, commit=True
    )
    log.debug(f'{status=} {msg=}')
    return status,msg

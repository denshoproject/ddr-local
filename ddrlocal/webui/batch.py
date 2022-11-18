from pathlib import Path

from django.conf import settings

from DDR.batch import Checker, Importer, InvalidCSVException
from DDR import csvfile
from DDR import fileio
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
    # check csv
    csv_errs,id_errs,validation_errs = Checker.check_csv(
        model, csv_path, rowds, headers, csv_errs, collection.identifier,
        settings.VOCABS_URL
    )
    header_errs,rowds_errs,file_errs = validation_errs
    # check repository
    staged,modified = Checker.check_repository(collection.identifier)
    # check eids
    if (model == 'entity'): # and idservice_client:
        raise Exception('TODO Checker.check_eids')
        chkeids = Checker.check_eids(rowds, collection.identifier, idservice_client)
        for err in chkeids:
            logging.error(f'entity ID?: {err}')
        if chkeids:
            assert False
    errors = {
        'csv_errs': csv_errs,
        'header_errs': header_errs,
        'rowds_errs': rowds_errs,
        'id_errs': id_errs,
        'file_errs': file_errs,
        'staged': staged,
        'modified': modified,
    }
    # write errors to log
    log = util.FileLogger(get_log_path(csv_path))
    log.info(f'Checking CSV {csv_path}')
    for title,errs in errors.items():
        if isinstance(errs, list):
            for err in errs:
                log.error(err)
        elif isinstance(errs, dict):
            for key,err in errs.items():
                log.error(f'{key} {err}')
    log.info('ok')
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

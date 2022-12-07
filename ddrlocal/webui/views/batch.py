from datetime import datetime
import logging
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from DDR import util
from storage.decorators import storage_required
from webui import batch
from webui.identifier import Identifier, InvalidIdentifierException
from webui.models import Collection
from webui.tasks import collection as collection_tasks
from webui.views.decorators import login_required
    

# views ----------------------------------------------------------------

@login_required
@storage_required
def import_files_browse(request, cid, dir=None):
    """Lists files/dirs in VIRTUALBOX_SHARED_FOLDER or subdirectory
    click on .csv and redirect to webui-import-files-confirm
    """
    try:
        collection = Collection.from_identifier(Identifier(cid))
    except:
        raise Http404
    path = request.GET.get('path')
    home = None
    parent = None
    if path:
        path_abs = Path(settings.VIRTUALBOX_SHARED_FOLDER) / path
        parent = path_abs.parent.relative_to(settings.VIRTUALBOX_SHARED_FOLDER)
        home = settings.VIRTUALBOX_SHARED_FOLDER
    else:
        path_abs = Path(settings.VIRTUALBOX_SHARED_FOLDER)
    listdir = []
    if not path_abs.exists():
        assert False
    elif path_abs.is_file() and path_abs.suffix == '.csv':
        return HttpResponseRedirect(
            f"{reverse('webui-import-files-confirm', args=[cid])}?path={path}"
        )
    elif path_abs.is_dir():
        for path in sorted(path_abs.iterdir()):
            xabs = Path(path)
            if xabs.is_dir():
                path = f'{path}/'  # append slash to dirnames
            rel = xabs.relative_to(settings.VIRTUALBOX_SHARED_FOLDER)
            size = None
            if not xabs.is_dir():
                size = xabs.lstat().st_size
            attribs = {
                'path': xabs,
                'isdir': xabs.is_dir(),
                'iscsv': xabs.suffix == '.csv',
                'rel': rel,
                'basename': xabs.name,
                'size': size,
                'mtime': datetime.fromtimestamp(xabs.stat().st_mtime)
            }
            if xabs.exists():
                listdir.append(attribs)
    return render(request, 'webui/batch/browse.html', {
        'collection': collection,
        'shared_folder': settings.VIRTUALBOX_SHARED_FOLDER,
        'listdir': listdir,
        'parent': parent,
        'home': home,
    })


class ImportFiles(View):
    
    @method_decorator(login_required)
    @method_decorator(storage_required)
    def get(self, request, cid, dir=None):
        """Run checks, confirm user really wants to import
        """
        try:
            collection = Collection.from_identifier(Identifier(cid))
        except:
            raise Http404
        model = 'file'
        if not request.GET.get('path'):
            return HttpResponseRedirect(
                reverse('webui-import-files-browse', args=[cid])
            )
        csv_path = get_csv_path(request)
        log_path = batch.get_log_path(csv_path)
        log = util.FileLogger(log_path=log_path)
        u = urlparse(request.META['HTTP_REFERER'])
        referer = f'{u.path}?{u.query}'
        #
        log.info(f'Running checks on {csv_path}')
        rowds,errors = batch.load_csv_run_checks(collection, model, csv_path)
        log.blank()
        log.blank()
        #
        clean = False
        if not errors:
            clean = True
        return render(request, 'webui/batch/confirm.html', {
            'referer': referer,
            'collection': collection,
            'clean': clean,
            'errors': errors,
            'log_url': batch.get_log_url(log_path),
        })
    
    @method_decorator(login_required)
    @method_decorator(storage_required)
    def post(self, request, cid, dir=None):
        try:
            collection = Collection.from_identifier(Identifier(cid))
        except:
            raise Http404
        model = 'file'
        if not request.GET.get('path'):
            return HttpResponseRedirect(
                reverse('webui-import-files-browse', args=[cid])
            )
        csv_path = get_csv_path(request)
        #
        collection_tasks.csv_import(request, collection, model, csv_path)
        #
        return HttpResponseRedirect(collection.absolute_url())


def get_csv_path(request):
    """Make an absolute to the CSV inside VIRTUALBOX_SHARED_FOLDER
    """
    return Path(settings.VIRTUALBOX_SHARED_FOLDER) / request.GET.get('path')

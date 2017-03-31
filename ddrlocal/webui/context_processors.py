from datetime import datetime
import logging
logger = logging.getLogger(__name__)
import os

from django.conf import settings
from django.core.urlresolvers import reverse

from webui.models import repo_models_valid
from webui import tasks


def sitewide(request):
    """Variables that need to be inserted into all templates.
    """
    # logout redirect - chop off edit/new/batch URLs if present
    logout_next = '?'.join([request.META['PATH_INFO'], request.META['QUERY_STRING']])
    if logout_next.find('edit') > -1:    logout_next = logout_next.split('edit')[0]
    elif logout_next.find('new') > -1:   logout_next = logout_next.split('new')[0]
    elif logout_next.find('batch') > -1: logout_next = logout_next.split('batch')[0]
    
    elasticsearch_url = 'http://%s:%s' % (
        request.META['HTTP_HOST'], settings.DOCSTORE_HOSTS[0]['port']
    )
    return {
        'request': request,
        # ddr-local info
        'time': datetime.now(settings.TZ).isoformat(),
        'pid': os.getpid(),
        'host': os.uname()[1],
        'commits': settings.COMMITS_TEXT,
        'models_valid': repo_models_valid(request),
        # user info
        'username': request.session.get('idservice_username', None),
        'git_name': request.session.get('git_name', None),
        'git_mail': request.session.get('git_mail', None),
        'celery_tasks': tasks.session_tasks_list(request),
        'celery_status_url': reverse("webui-task-status"),
        'celery_status_update': request.session.get('celery_status_update', False),
        'supervisord_url': settings.SUPERVISORD_URL,
        'elasticsearch_url': elasticsearch_url,
        'munin_url': settings.MUNIN_URL,
        'logout_next': logout_next,
        'idservice_url': settings.IDSERVICE_API_BASE,
        'manual_url': settings.MANUAL_URL,
    }

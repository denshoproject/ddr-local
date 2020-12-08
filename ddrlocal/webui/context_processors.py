from datetime import datetime
import logging
logger = logging.getLogger(__name__)
import os

from django.conf import settings
from django.urls import reverse

from webui.models import repo_models_valid
from webui.tasks import common as tasks_common


def sitewide(request):
    """Variables that need to be inserted into all templates.
    """
    # logout redirect - chop off edit/new/batch URLs if present
    logout_next = '?'.join([request.META['PATH_INFO'], request.META['QUERY_STRING']])
    if logout_next.find('edit') > -1:    logout_next = logout_next.split('edit')[0]
    elif logout_next.find('new') > -1:   logout_next = logout_next.split('new')[0]
    elif logout_next.find('batch') > -1: logout_next = logout_next.split('batch')[0]
    
    elasticsearch_url = 'http://%s' % (settings.DOCSTORE_HOST)
    return {
        'request': request,
        # ddr-local info
        'time': datetime.now(settings.TZ).isoformat(),
        'pid': os.getpid(),
        'host': os.uname()[1],
        'commits': settings.APP_COMMITS_HTML,
        'models_valid': repo_models_valid(request),
        # user info
        'username': request.session.get('idservice_username', None),
        'git_name': request.session.get('git_name', None),
        'git_mail': request.session.get('git_mail', None),
        'celery_tasks': tasks_common.session_tasks_list(request),
        'celery_status_url': reverse("webui-task-status"),
        'celery_status_update': request.session.get('celery_status_update', True),
        'STATIC_URL': settings.STATIC_URL,
        'supervisord_url': settings.SUPERVISORD_URL,
        'docstore_enabled': settings.DOCSTORE_ENABLED,
        'elasticsearch_url': elasticsearch_url,
        'logout_next': logout_next,
        'cgit_url': settings.CGIT_URL,
        'idservice_url': settings.IDSERVICE_API_BASE,
        'manual_url': settings.MANUAL_URL,
    }

from datetime import datetime
import logging
logger = logging.getLogger(__name__)
import os

import envoy

from django.conf import settings
from django.core.urlresolvers import reverse

from webui.tasks import session_tasks_list


def git_commit():
    """Returns the ddr-local repo's most recent Git commit.
    """
    try:
        commit = envoy.run('git log --pretty=format:"%H" -1').std_out
    except:
        commit = 'unknown'
    return commit

def sitewide(request):
    """Variables that need to be inserted into all templates.
    """
    # logout redirect - chop off edit/new/batch URLs if present
    logout_next = '?'.join([request.META['PATH_INFO'], request.META['QUERY_STRING']])
    
    if logout_next.find('edit') > -1:    logout_next = logout_next.split('edit')[0]
    elif logout_next.find('new') > -1:   logout_next = logout_next.split('new')[0]
    elif logout_next.find('batch') > -1: logout_next = logout_next.split('batch')[0]
    return {
        'request': request,
        # ddr-local info
        'time': datetime.now().isoformat(),
        'pid': os.getpid(),
        'host': os.uname()[1],
        'commit': git_commit()[:7],
        # user info
        'username': request.session.get('username', None),
        'git_name': request.session.get('git_name', None),
        'git_mail': request.session.get('git_mail', None),
        'celery_tasks': session_tasks_list(request),
        'celery_status_url': reverse("webui-task-status"),
        'logout_next': logout_next,
        'workbench_url': settings.WORKBENCH_URL,
    }

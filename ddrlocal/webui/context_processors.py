"""
See http://www.b-list.org/weblog/2006/jun/14/django-tips-template-context-processors/
"""
import requests

from django.conf import settings
from django.core.urlresolvers import reverse


def task_statuses(task_ids):
    tasks = []
    for task_id in task_ids:
        url = 'http://127.0.0.1/%s' % reverse('celery-task_status', args=[task_id])
        r = requests.get(url)
        try:
            data = r.json()
            task = data['task']
        except:
            task = None
        if task:
            tasks.append(task)
    return tasks

def sitewide(request):
    """Variables that need to be inserted into all templates.
    """
    task_ids = request.session.get('celery-tasks', [])
    # this clause can be thrown away once tasks in session is not just list of task_ids
    if type(task_ids) != type({}):
        task_ids = {}
    tasks = task_statuses(task_ids)
    # logout redirect - chop off edit/new/batch URLs if present
    logout_next = request.META['RAW_URI']
    if logout_next.find('edit') > -1:    logout_next = logout_next.split('edit')[0]
    elif logout_next.find('new') > -1:   logout_next = logout_next.split('new')[0]
    elif logout_next.find('batch') > -1: logout_next = logout_next.split('batch')[0]
    return {
        # user info
        'username': request.session.get('username', None),
        'git_name': request.session.get('git_name', None),
        'git_mail': request.session.get('git_mail', None),
        'celery_tasks': tasks,
        'logout_next': logout_next,
    }

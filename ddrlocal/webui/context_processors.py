"""
See http://www.b-list.org/weblog/2006/jun/14/django-tips-template-context-processors/
"""
import requests

from django.conf import settings
from django.core.urlresolvers import reverse


def task_statuses(celery_tasks):
    tasks = []
    for task_id in celery_tasks.keys():
        url = 'http://127.0.0.1/%s' % reverse('celery-task_status', args=[task_id])
        r = requests.get(url)
        try:
            data = r.json()
        except:
            task = None
        #assert False
        if task:
            tasks.append(task)
    return tasks



def sitewide(request):
    """Variables that need to be inserted into all templates.
    """
    
    # reset tasks
    del request.session[settings.CELERY_TASKS_SESSION_KEY]
    assert False
    
    celery_tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, [])
    # this clause can be thrown away once tasks in session is not just list of task_ids
    #if type(celery_tasks) != type({}):
    #    celery_tasks = {}
    tasks = task_statuses(celery_tasks)
    #assert False
    
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
        'celery_tasks': celery_tasks,
        'logout_next': logout_next,
    }

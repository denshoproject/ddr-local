from datetime import datetime
import logging
logger = logging.getLogger(__name__)

from django.conf import settings
from django.contrib import messages
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext

from DDR import commands

from webui import WEBUI_MESSAGES
from webui import api
from webui.decorators import ddrview
from webui.forms import LoginForm, TaskDismissForm
from webui.tasks import dismiss_session_task, session_tasks_list

# helpers --------------------------------------------------------------


# views ----------------------------------------------------------------

"""
local takes username/passwd
in background makes request to mits using that username/password
gets the response
figures out if successful/not
if successful:
    stores in memcached session

what do we need to store?
- username
- user name  (for git logs)
- user email (for git logs)
- repo
- orgs the user belongs to
"""

@ddrview
def login( request ):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            redirect_uri = form.cleaned_data['next']
            if not redirect_uri:
                redirect_uri = reverse('webui-index')
            s = api.login(request,
                          form.cleaned_data['username'],
                          form.cleaned_data['password'])
            if s and (type(s) != type('')) and s.cookies.get('sessionid', None):
                messages.success(
                    request,
                    WEBUI_MESSAGES['LOGIN_SUCCESS'].format(form.cleaned_data['username']))
                return HttpResponseRedirect(redirect_uri)
            else:
                messages.warning(request, WEBUI_MESSAGES['LOGIN_FAIL'])
    else:
        form = LoginForm(initial={'next':request.GET.get('next',''),})
        # Using "initial" rather than passing in data dict lets form include
        # redirect link without complaining about blank username/password fields.
    return render_to_response(
        'webui/login.html',
        {'form': form,},
        context_instance=RequestContext(request, processors=[])
    )

@ddrview
def logout( request ):
    redirect_uri = request.GET.get('redirect',None)
    if not redirect_uri:
        redirect_uri = reverse('webui-index')
    status = api.logout()
    if status == 'ok':
        username = request.session.get('username')
        # remove user info from session
        request.session['workbench_sessionid'] = None
        request.session['username'] = None
        request.session['git_name'] = None
        request.session['git_mail'] = None
        # feedback
        messages.success(request, WEBUI_MESSAGES['LOGOUT_SUCCESS'].format(username))
    else:
        messages.warning(request, WEBUI_MESSAGES['LOGOUT_FAIL'].format(status))
    return HttpResponseRedirect(redirect_uri)



def tasks( request ):
    """Show pending/successful/failed tasks; UI for dismissing tasks.
    """
    # add start datetime to tasks list
    celery_tasks = session_tasks_list(request)
    for task in celery_tasks:
        task['startd'] = datetime.strptime(task['start'], settings.TIMESTAMP_FORMAT)

    if request.method == 'POST':
        form = TaskDismissForm(request.POST, celery_tasks=celery_tasks)
        if form.is_valid():
            for task in celery_tasks:
                fieldname = 'dismiss_%s' % task['task_id']
                if (fieldname in form.cleaned_data.keys()) and form.cleaned_data[fieldname]:
                    dismiss_session_task(request, task['task_id'])
            # redirect
            redirect_uri = form.cleaned_data['next']
            if not redirect_uri:
                redirect_uri = reverse('webui-index')
            return HttpResponseRedirect(redirect_uri)
    else:
        data = {
            'next': request.GET.get('next',None),
        }
        form = TaskDismissForm(data, celery_tasks=celery_tasks)
        dismissable_tasks = [1 for task in celery_tasks if task['dismissable']]
    return render_to_response(
        'webui/tasks.html',
        {'form': form,
         'celery_tasks': celery_tasks,
         'dismissable_tasks': dismissable_tasks,
         'hide_celery_tasks': True,},
        context_instance=RequestContext(request, processors=[])
    )

def task_status( request ):
    """
    Gets celery task status, generates HTML for display in alert box in base template.
    """
    return render_to_response(
        'webui/task-include.html',
        {'dismiss_next': request.GET.get('this', reverse('webui-index'))},
        context_instance=RequestContext(request, processors=[])
    )

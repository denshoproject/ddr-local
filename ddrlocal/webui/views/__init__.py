from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import os

from django.conf import settings
from django.contrib import messages
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext

from DDR import idservice

from webui import WEBUI_MESSAGES
from webui import gitstatus
from webui.decorators import ddrview
from webui.forms import LoginForm, TaskDismissForm
from webui.tasks import dismiss_session_task, session_tasks_list
from webui.views.decorators import login_required

# helpers --------------------------------------------------------------


# views ----------------------------------------------------------------

@ddrview
def login( request ):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            redirect_uri = form.cleaned_data['next']
            if not redirect_uri:
                redirect_uri = reverse('webui-index')

            ic = idservice.IDServiceClient()
            status1,reason1 = ic.login(
                form.cleaned_data['username'],
                form.cleaned_data['password'],
            )
            if status1 == 200:
                request.session['idservice_username'] = ic.username
                request.session['idservice_token'] = ic.token
            else:
                messages.warning(
                    request,
                    'Login failed[1]: %s %s' % (status1,reason1)
                )
                return HttpResponseRedirect(redirect_uri)
            
            status2,reason2,userinfo = ic.user_info()
            if not (userinfo['email'] and userinfo['first_name'] and userinfo['last_name']):
                messages.warning(
                    request,
                    'Login failed[2]: ID service missing required user info (email, first_name, last_name).'
                )
                return HttpResponseRedirect(redirect_uri)
            request.session['git_mail'] = userinfo['email']
            request.session['git_name'] = ' '.join([
                userinfo['first_name'],
                userinfo['last_name']
            ])
            
            if (status1 == 200) and (status2 == 200) and request.session['idservice_token']:
                messages.success(
                    request,
                    WEBUI_MESSAGES['LOGIN_SUCCESS'].format(form.cleaned_data['username']))
                return HttpResponseRedirect(redirect_uri)
            else:
                messages.warning(
                    request,
                    'Login failed[3]: Could not get user information: %s %s' % (status2,reason2)
                )
                return HttpResponseRedirect(redirect_uri)
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
    status = idservice.logout()
    if status == 'ok':
        username = request.session.get('idservice_username')
        # remove user info from session
        request.session['idservice_username'] = None
        request.session['idservice_token'] = None
        request.session['git_name'] = None
        request.session['git_mail'] = None
        # feedback
        messages.success(request, WEBUI_MESSAGES['LOGOUT_SUCCESS'].format(username))
    else:
        messages.warning(request, WEBUI_MESSAGES['LOGOUT_FAIL'].format(status))
    return HttpResponseRedirect(redirect_uri)


def gitstatus_queue(request):
    text = None
    try:
        path = gitstatus.queue_path(settings.MEDIA_BASE)
        assert os.path.exists(path)
        with open(path, 'r') as f:
            text = f.read()
    except AssertionError:
        text = None
    return render_to_response(
        'webui/gitstatus-queue.html',
        {
            'text': text,
        },
        context_instance=RequestContext(request, processors=[])
    )

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

@login_required
def task_dismiss( request, task_id ):
    dismiss_session_task(request, task_id)
    data = {'status':'ok'}
    return HttpResponse(json.dumps(data), content_type="application/json")

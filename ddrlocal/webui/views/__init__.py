import json
import logging
logger = logging.getLogger(__name__)
import os

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from DDR import converters
from DDR import idservice

from webui import cache
from webui import WEBUI_MESSAGES
from webui import gitstatus
from webui.decorators import ddrview
from webui import forms
from webui import identifier
from webui.tasks import common as common_tasks
from webui.views.decorators import login_required

# helpers --------------------------------------------------------------


# views ----------------------------------------------------------------

def detail(request, oid):
    """Generic function for handling IDs without models
    """
    oi = identifier.Identifier(oid)
    if not oi:
        raise Exception('"%s" is not a valid object ID' % oid)
    return HttpResponseRedirect(
        reverse(
            'webui-%s' % oi.model,
            args=([oid]),
        )
    )

def repository(request, oid):
    assert False

def organization(request, oid):
    assert False

@ddrview
def login( request ):
    if request.method == 'POST':
        form = forms.LoginForm(request.POST)
        if form.is_valid():
            redirect_uri = form.cleaned_data['next']
            if not redirect_uri:
                redirect_uri = reverse('webui-index')

            ic = idservice.IDServiceClient()
            status1,reason1 = ic.login(
                form.cleaned_data['username'],
                form.cleaned_data['password'],
            )
            if status1 != 200:
                messages.warning(
                    request,
                    'Login failed: %s %s (%s) [login]' % (
                        status1,reason1,settings.IDSERVICE_API_BASE
                    )
                )
                return HttpResponseRedirect(redirect_uri)
            status2,reason2,userinfo = ic.user_info()
            if status2 != 200:
                messages.warning(
                    request,
                    'Login failed: %s %s (%s) [user_info]' % (
                        status2,reason2,settings.IDSERVICE_API_BASE
                    )
                )
                return HttpResponseRedirect(redirect_uri)
            if not (userinfo['email'] \
                    and userinfo['first_name'] and userinfo['last_name']):
                messages.warning(
                    request,
                    'Login failed: ID service missing required user info '
                    '(email, first_name, last_name). (%s) [3]' % (
                        settings.IDSERVICE_API_BASE
                    )
                )
                return HttpResponseRedirect(redirect_uri)

            # everything looks kosher
            request.session['idservice_username'] = ic.username
            request.session['idservice_token'] = ic.token
            request.session['git_mail'] = userinfo['email']
            request.session['git_name'] = ' '.join([
                userinfo['first_name'],
                userinfo['last_name']
            ])
            messages.success(
                request,
                WEBUI_MESSAGES['LOGIN_SUCCESS'].format(form.cleaned_data['username']))
            return HttpResponseRedirect(redirect_uri)
        
    else:
        form = forms.LoginForm(initial={'next':request.GET.get('next',''),})
        # Using "initial" rather than passing in data dict lets form include
        # redirect link without complaining about blank username/password fields.
    return render(request, 'webui/login.html', {
        'form': form,
    })


class LoginOffline(View):
    """Just take the username and email and put it in session.
    """
    
    def get(self, request):
        form = forms.LoginOfflineForm(initial={'next':request.GET.get('next',''),})
        # Using "initial" rather than passing in data dict lets form include
        # redirect link without complaining about blank username/password fields.
        return render(request, 'webui/login-offline.html', {
            'form': form,
        })
    
    def post(self, request):
        form = forms.LoginOfflineForm(request.POST)
        if form.is_valid():
            redirect_uri = form.cleaned_data['next']
            if not redirect_uri:
                redirect_uri = reverse('webui-index')
            request.session['idservice_username'] = form.cleaned_data['username']
            #request.session['idservice_token'] = ic.token
            request.session['git_mail'] = form.cleaned_data['email']
            request.session['git_name'] = form.cleaned_data['git_name']
            messages.success(
                request,
                WEBUI_MESSAGES['LOGIN_SUCCESS'].format(
                    form.cleaned_data['username']
                )
            )
            return HttpResponseRedirect(redirect_uri)
        return render(request, 'webui/login-offline.html', {
            'form': form,
        })


@ddrview
def logout( request ):
    redirect_uri = request.GET.get('redirect',None)
    if not redirect_uri:
        redirect_uri = reverse('webui-index')
    
    ic = idservice.IDServiceClient()
    # resume session
    auth_status,auth_reason = ic.resume(request.session['idservice_token'])
    if auth_status != 200:
        request.session['idservice_username'] = None
        request.session['idservice_token'] = None
        messages.warning(
            request,
            'Session resume failed: %s %s (%s)' % (
                auth_status,auth_reason,settings.IDSERVICE_API_BASE
            )
        )
        return HttpResponseRedirect(redirect_uri)
    # log out
    logout_status,logout_reason = ic.logout()
    if logout_status == 200:
        username = request.session['idservice_username']
        request.session['idservice_username'] = None
        request.session['idservice_token'] = None
        # feedback
        messages.success(
            request,
            WEBUI_MESSAGES['LOGOUT_SUCCESS'].format(username)
        )
    else:
        messages.warning(
            request,
            'Logout failed: %s %s (%s)' % (
                logout_status,logout_reason,settings.IDSERVICE_API_BASE
            )
        )
    cache.redis_flush_all()
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
    return render(request, 'webui/gitstatus-queue.html', {
        'text': text,
    })

def task_list( request ):
    """Show pending/successful/failed tasks; UI for dismissing tasks.
    """
    # add start datetime to tasks list
    celery_tasks = common_tasks.session_tasks_list(
        request
    )
    for task in celery_tasks:
        task['startd'] = converters.text_to_datetime(task['start'])

    if request.method == 'POST':
        form = forms.TaskDismissForm(request.POST, celery_tasks=celery_tasks)
        if form.is_valid():
            for task in celery_tasks:
                fieldname = 'dismiss_%s' % task['task_id']
                if (fieldname in list(form.cleaned_data.keys())) and form.cleaned_data[fieldname]:
                    common_tasks.dismiss_session_task(
                        request,
                        task['task_id']
                    )
            # redirect
            redirect_uri = form.cleaned_data['next']
            if not redirect_uri:
                redirect_uri = reverse('webui-index')
            return HttpResponseRedirect(redirect_uri)
    else:
        data = {
            'next': request.GET.get('next',None),
        }
        form = forms.TaskDismissForm(data, celery_tasks=celery_tasks)
        dismissable_tasks = [1 for task in celery_tasks if task['dismissable']]
    return render(request, 'webui/tasks.html', {
        'form': form,
        'celery_tasks': celery_tasks,
        'dismissable_tasks': dismissable_tasks,
        'hide_celery_tasks': True,
    })

def task_status( request ):
    """
    Gets celery task status, generates HTML for display in alert box in base template.
    """
    return render(request, 'webui/task-include.html', {
        'dismiss_next': request.GET.get('this', reverse('webui-index'))
    })

@login_required
def task_dismiss( request, task_id ):
    common_tasks.dismiss_session_task(
        request,
        task_id
    )
    data = {'status':'ok'}
    return HttpResponse(json.dumps(data), content_type="application/json")

@ddrview
def gitstatus_toggle(request):
    """Toggle the Celery status update that runs every N seconds; remember for session.
    """
    if request.session.get('celery_status_update', False):
        request.session['celery_status_update'] = False
        messages.success(request, 'Celery status updates DISABLED for the duration of this session.')
    else:
        request.session['celery_status_update'] = True
        messages.success(request, 'Celery status updates ENABLED for the duration of this session.')
    return HttpResponseRedirect(
        request.META.get('HTTP_REFERER', reverse('webui-index'))
    )

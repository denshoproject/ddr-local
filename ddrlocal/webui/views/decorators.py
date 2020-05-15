from functools import wraps
import logging
logger = logging.getLogger(__name__)

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import available_attrs

def login_required(func):
    """Checks for git_name,git_main in session; redirects to login if absent
    """
    @wraps(func, assigned=available_attrs(func))
    def inner(request, *args, **kwargs):
        git_name = request.session.get('git_name')
        git_mail = request.session.get('git_mail')
        if not (git_name and git_mail):
            url = '{}?next={}'.format(reverse('webui-login'), request.META['PATH_INFO'])
            return HttpResponseRedirect(url)
        return func(request, *args, **kwargs)
    return inner

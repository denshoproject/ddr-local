"""
See http://www.b-list.org/weblog/2006/jun/14/django-tips-template-context-processors/
"""
from django.conf import settings

from webui.storage import storage_root, storage_status, storage_type

def sitewide(request):
    """Variables that need to be inserted into all templates.
    """
    return {
        # user info
        'username': request.session.get('username', None),
        'git_name': request.session.get('git_name', None),
        'git_mail': request.session.get('git_mail', None),
        # storage info
        'storage_root': storage_root(request),
        'storage_type': storage_type(request),
        'storage_status': storage_status(request),
    }

"""
See http://www.b-list.org/weblog/2006/jun/14/django-tips-template-context-processors/
"""
from django.conf import settings

def sitewide(request):
    """Variables that need to be inserted into all templates.
    """
    return {
        # user info
        'username': request.session.get('username', None),
        'git_name': request.session.get('git_name', None),
        'git_mail': request.session.get('git_mail', None),
    }

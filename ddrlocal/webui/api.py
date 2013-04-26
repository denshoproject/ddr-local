import logging
logger = logging.getLogger(__name__)

from bs4 import BeautifulSoup
import requests

from django.conf import settings


def logout():
    """Logs out of the workbench server.
    @returns string: 'ok' or error message
    """
    s = requests.Session()
    r = s.get(settings.WORKBENCH_LOGOUT_URL)
    if r.status_code == 200:
        return 'ok'
    return 'error: unspecified'

def login( request, username, password ):
    """Logs in to the workbench server.
    @returns requests.Session object or string error message (starting with 'error:')
    """
    if not (username or password):
        return 'error: missing username or password'
    s = requests.Session()
    # load test page to see if already logged in
    r = s.get(settings.WORKBENCH_LOGIN_TEST)
    soup = BeautifulSoup(r.text)
    titletag = soup.find('title')
    if (r.status_code == 200) and not ('Log in' in titletag.string):
        return s
    # get CSRF token from cookie
    csrf_token = r.cookies['csrftoken']
    # log in
    headers = {'X-CSRFToken': csrf_token}
    cookies = {'csrftoken': csrf_token}
    data = {'csrftoken': csrf_token,
            'username': username,
            'password': password,}
    r1 = s.post(settings.WORKBENCH_LOGIN_URL,
                headers=headers,
                cookies=cookies,
                data=data,)
    if r1.status_code != 200:
        return 'error: status code {} on POST'.format(r1.status_code)
    # it would be better to look for a success message...
    error_msg = 'Please enter a correct username and password.'
    if r1.text:
        if (error_msg not in r1.text):
            request.session['workbench_sessionid'] = s.cookies.get('sessionid')
            request.session['workbench_csrftoken'] = s.cookies.get('csrftoken')
            request.session['username'] = username
            return s
        else:
            return 'error: bad username or password'
    return 'error: unspecified'

def session( request ):
    s = requests.Session()
    if request.session.get('workbench_sessionid',None) \
           and request.session.get('workbench_csrftoken',None):
        s.cookies.set('sessionid', request.session['workbench_sessionid'])
        s.cookies.set('csrftoken', request.session['workbench_csrftoken'])
    return s

def collections_latest( request, repo, org, num_collections=1 ):
    """Get the most recent N collection IDs for the logged-in user.
    
    <table id="collections" class="table table-striped table-bordered table-condensed">
      <tr><td><a class="collection" href="/workbench/kiroku/ddr-densho-1/">ddr-densho-1</a></td></tr>
      <tr><td><a class="collection" href="/workbench/kiroku/ddr-densho-2/">ddr-densho-2</a></td></tr>
    ...
    
    We're screenscraping when we should be using the API.
    """
    collections = []
    s = session(request)
    url = '{}/kiroku/{}-{}/'.format(settings.WORKBENCH_URL, repo, org)
    r = s.get(url)
    soup = BeautifulSoup(r.text)
    cids = []
    for c in soup.find_all('a','collection'):
        cids.append(c.string)
    collections = cids[-num_collections:]
    return collections

def collections_next( request, repo, org, num_collections=1 ):
    """Generate the next N collection IDs for the logged-in user.
    
    <table id="collections" class="table table-striped table-bordered table-condensed">
      <tr><td><a class="collection" href="/workbench/kiroku/ddr-densho-1/">ddr-densho-1</a></td></tr>
      <tr><td><a class="collection" href="/workbench/kiroku/ddr-densho-2/">ddr-densho-2</a></td></tr>
    ...
    
    We're screenscraping when we should be using the API.
    Also, we're using a GET to change state.
    """
    collections = []
    s = session(request)
    #url = '{}/kiroku/{}-{}/'.format(settings.WORKBENCH_URL, repo, org)
    url = settings.WORKBENCH_NEWCOL_URL.replace('REPO',repo).replace('ORG',org)
    r = s.get(url)
    soup = BeautifulSoup(r.text)
    cids = []
    for c in soup.find_all('a','collection'):
        cids.append(c.string)
    collections = cids[-num_collections:]
    return collections

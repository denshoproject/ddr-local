import json
import logging
logger = logging.getLogger(__name__)

from bs4 import BeautifulSoup
import requests

from django.conf import settings
from django.contrib import messages

from webui import WEBUI_MESSAGES



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
        return WEBUI_MESSAGES['API_LOGIN_NOT_200'].format(r1.status_code)
    # it would be better to look for a success message...
    error_msg = 'Please enter a correct username and password.'
    if r1.text:
        if (error_msg not in r1.text):
            request.session['workbench_sessionid'] = s.cookies.get('sessionid')
            request.session['workbench_csrftoken'] = s.cookies.get('csrftoken')
            request.session['username'] = username
            # get user first/last name and email from workbench profile (via API)
            url = settings.WORKBENCH_USERINFO
            r2 = s.get(url)
            if r2.status_code == 200:
                data = json.loads(r2.text)
                email = data.get('email', None)
                if not email:
                    messages.error(request, WEBUI_MESSAGES['API_LOGIN_INVALID_EMAIL'])
                firstname = data.get('firstname', '')
                lastname = data.get('lastname', '')
                user_name = '{} {}'.format(firstname, lastname).strip()
                if email and (not user_name):
                    user_name = email
                    messages.error(request, WEBUI_MESSAGES['API_LOGIN_INVALID_NAME'])
                request.session['git_name'] = user_name
                request.session['git_mail'] = email
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
    
    TODO We're screenscraping when we should be using the API.
    """
    collections = []
    s = session(request)
    # get CSRF token
    r0 = s.get('{}/kiroku/{}-{}/'.format(settings.WORKBENCH_URL, repo, org))
    if r0.status_code == 200:
        # get CSRF token from cookie
        csrf_token = None
        for c in r0.cookies:
            if c.name == 'csrftoken':
                csrf_token = c.value
        if csrf_token:
            # request new CID
            r1 = s.post(settings.WORKBENCH_NEWCOL_URL.replace('REPO',repo).replace('ORG',org),
                        headers={'X-CSRFToken': csrf_token},
                        cookies={'csrftoken': csrf_token},
                        data={'csrftoken': csrf_token},)
            soup = BeautifulSoup(r1.text)
            cids = [c.string for c in soup.find_all('a','collection')]
            collections = cids[-num_collections:]
        else:
            logger.error('No CSRF token')
    else:
        logger.error('Request did not work! (status code: %s)' % r0.status_code)
    logger.debug('collections: %s' % collections)
    return collections

def entities_next( request, repo, org, cid, num=1 ):
    """Generate the next N entity IDs for the logged-in user.
    
    <table id="entities" class="table table-striped table-bordered table-condensed">
    ...
      <tr class="entity">
        <td class="eid">ddr-testing-28-1</td>
        <td class="timestamp">2013-05-17T18:25:12.431504-07:00</td>
      </tr>
      <tr class="entity">
        <td class="eid">ddr-testing-28-2</td>
        <td class="timestamp">2013-05-17T18:25:12.436942-07:00</td>
      </tr>
    ...
    
    TODO We're screenscraping when we should be using the API.
    """
    entities = []
    s = session(request)
    # get CSRF token
    url_get = '{}/kiroku/{}-{}-{}/'.format(settings.WORKBENCH_URL, repo, org, cid)
    r0 = s.get(url_get)
    if r0.status_code == 200:
        # get CSRF token from cookie
        csrf_token = None
        for c in r0.cookies:
            if c.name == 'csrftoken':
                csrf_token = c.value
        if csrf_token:
            # request new CID
            newent_url = settings.WORKBENCH_NEWENT_URL
            url_post = newent_url.replace('REPO',repo).replace('ORG',org).replace('CID',cid)
            r1 = s.post(url_post,
                        headers={'X-CSRFToken': csrf_token},
                        cookies={'csrftoken': csrf_token},
                        data={'csrftoken': csrf_token, 'num': num,},)
            soup = BeautifulSoup(r1.text)
            eids = [e.string.strip() for e in soup.find_all('td','eid')]
            entities = eids[-num:]
        else:
            logger.error('No CSRF token')
    else:
        logger.error('Request did not work! (status code: %s)' % r0.status_code)
    logger.debug('entities: %s' % entities)
    return entities

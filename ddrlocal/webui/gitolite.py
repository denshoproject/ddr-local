"""
gitolite

Local systems connect to settings.GITOLITE to list the repositories
to which they have access.  On systems with slow network connections
this takes too long to do during a page request.
"""

from datetime import datetime, timedelta
import logging
logger = logging.getLogger(__name__)

from django.conf import settings
from django.core.cache import cache

from DDR import converters
from DDR import dvcs

from webui import GITOLITE_INFO_CACHE_KEY


def get_repos_orgs():
    """Returns list of repo-orgs that the current SSH key gives access to.
    
    This function helps to manage 
    - cache
    - Gitolite server, with short timeout
    - the list of collections on the mounted Store.

    This function often runs in the context of a page request/reponse,
    but we don't want to have to wait for the Gitolite server.
    Cached value is kept up to date by a periodic background task.
    
    Cached gitolite info is prepended with a timestamp:
        hello ddr, this is git@mits running gitolite3 v3.2-19-gb9bbb78 on git 1.7.2.5
        
         R W C ddr-test-[0-9]+
         R W C ddr-test-[0-9]+-[0-9]+
         R W   ddr-test
         R W   ddr-test-1
    
    The cached value expires after GITOLITE_INFO_CACHE_TIMEOUT seconds.
    A background process checks every GITOLITE_INFO_CHECK_PERIOD seconds.
    If the timestamp is more than GITOLITE_INFO_CACHE_CUTOFF seconds old
    the cached value is refreshed.

    It is refreshed after GITOLITE_INFO_CACHE_CUTOFF seconds.
    The gitolite info should (almost) always be available to the webapp
    even if it's a bit stale.
    
    IMPORTANT: cached value of gitolite_info is in the following format:
        timestamp + '\n' + gitolite_info

    @returns: list of org IDs (e.g. ['ddr-densho', 'ddr-janm']).
    """
    gitolite = dvcs.Gitolite()
    repos_orgs = []
    cached = cache.get(GITOLITE_INFO_CACHE_KEY)
    if not cached:
        # cache miss!  This should not happen very often
        # Same code as webui.tasks.gitolite_info_refresh(),
        # but copied to prevent import loop.
        gitolite.initialize()
        info = gitolite.info
        cached = dumps(info, settings.GITOLITE)
        cache.set(
            GITOLITE_INFO_CACHE_KEY,
            cached,
            settings.GITOLITE_INFO_CACHE_TIMEOUT
        )
    if cached:
        try:
            timestamp,source,info = loads(cached)
        except ValueError:
            timestamp,source,info = None,None,None
        if info:
            gitolite.info = info
            repos_orgs = gitolite.orgs()
    return repos_orgs

def refresh():
    """
    Check the cached value of DDR.dvcs.gitolite_info().
    If it is stale (e.g. timestamp is older than cutoff)
    then hit the Gitolite server for an update and re-cache.
    """
    logger.debug('gitolite_info_check')
    gitolite = dvcs.Gitolite()
    feedback = []
    needs_update = None
    cached = cache.get(GITOLITE_INFO_CACHE_KEY)
    if cached:
        feedback.append('cached')
        try:
            timestamp,source,info = loads(cached)
            feedback.append(converters.datetime_to_text(timestamp))
            feedback.append(source)
        except ValueError:
            timestamp,source,info = None,None,None
            feedback.append('malformed')
            needs_update = True
        if timestamp:
            elapsed = datetime.now(settings.TZ) - timestamp
            cutoff = timedelta(seconds=settings.GITOLITE_INFO_CACHE_CUTOFF)
            if elapsed > cutoff:
                needs_update = True
                feedback.append('stale')
    else:
        needs_update = True
        feedback.append('missing')
    if needs_update:
        gitolite.initialize()
        if gitolite.info:
            cached = dumps(gitolite.info, settings.GITOLITE)
            cache.set(
                GITOLITE_INFO_CACHE_KEY,
                cached,
                settings.GITOLITE_INFO_CACHE_TIMEOUT
            )
            feedback.append('refreshed')
    else:
        feedback.append('ok')
    return ' '.join(feedback)

def dumps(info, source):
    """Dump raw gitolite info and source to cache value with timestamp
    Response from Gitolite looks like this:
        hello ddr, this is git@mits running gitolite3 v3.2-19-gb9bbb78 on git 1.7.2.5
        
         R W C ddr-test-[0-9]+
         R W C ddr-test-[0-9]+-[0-9]+
         R W   ddr-test
         R W   ddr-test-1
        ...
    
    Timestamp and source are prepended to the cached value:
        2014-08-20T09:39:28:386187 git@mits.densho.org
        hello ddr, this is git@mits running gitolite3 v3.2-19-gb9bbb78 on git 1.7.2.5
        
         R W C ddr-test-[0-9]+
        ...
    
    @param info: str
    @param source: str
    @returns: str
    """
    timestamp = converters.datetime_to_text(datetime.now(settings.TZ))
    text = '%s %s\n%s' % (timestamp, source, info)
    return text

def loads(text):
    """Load timestamp, source, and raw gitolite info from cached value
    
    @param text
    @returns: timestamp,source,info (datetime,str,str)
    """
    line0,info = text.split('\n', 1)
    ts,source = line0.split(' ')
    timestamp = converters.text_to_datetime(ts)
    return timestamp,source,info

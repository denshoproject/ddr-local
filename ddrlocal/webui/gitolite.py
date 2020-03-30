"""
gitolite

Local systems connect to settings.GITOLITE to list the repositories
to which they have access.  On systems with slow network connections
this takes too long to do during a page request.

To support systems with no internet access for extended periods of
time, responses from settings.GITOLITE are cached to a file in the
same tmp dir as gitstatus files, queue, and lockfiles.
"""

from datetime import datetime, timedelta
import json
import logging
logger = logging.getLogger(__name__)
from pathlib import Path
import os

from django.conf import settings

from DDR import dvcs

# TODO hard-coded
DEFAULT_REPOS_ORGS = ['ddr-testing']


def get_repos_orgs(force=False):
    """Returns list of repo-orgs that the current SSH key gives access to.
    
    This function helps to manage 
    - cache
    - Gitolite server, with short timeout
    - the list of collections on the mounted Store.

    This function often runs in the context of a page request/reponse,
    but we don't want to have to wait for the Gitolite server.

    It is refreshed after GITOLITE_INFO_CACHE_CUTOFF seconds.
    The gitolite info should (almost) always be available to the webapp
    even if it's a bit stale.
    
    @param force: bool
    @returns: list of org IDs (e.g. ['ddr-densho', 'ddr-janm']).
    """
    state = _get_state()
    action = DECISION_TABLE[state]
    if force or (action == 'refresh'):
        return _refresh()
    return _read()

def cache_path(base_dir=settings.MEDIA_BASE):
    """Path to gitolite repos-orgs cache file
    """
    return Path(settings.MEDIA_BASE) / 'tmp' / 'gitolite-repos-orgs'

DECISION_TABLE = {
    'missing:missing': 'refresh',
    'present:stale': 'refresh',
    'present:fresh': 'read',
}

def _get_state():
    """Check cache file and decide what to do. See DECISION_TABLE.
    """
    states = ['missing','missing']
    path = cache_path()
    if path.exists():
        states = ['present']
        cutoff = timedelta(seconds=settings.GITOLITE_INFO_CACHE_CUTOFF)
        age = None
        if path.exists():
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            age = datetime.now() - mtime
        if age and (age < cutoff):
            states.append('fresh')
        else:
            states.append('stale')
    return ':'.join(states)

def _refresh():
    """Try to contact Gitolite server, write file only if successful.
    
    @return: list of repo-org strs
    """
    gitolite = dvcs.Gitolite()
    gitolite.initialize()
    repos_orgs = gitolite.orgs()
    if repos_orgs:
        with cache_path().open('w') as f:
            f.write(json.dumps(repos_orgs))
        return repos_orgs
    else:
        repos_orgs = _read()
        if repos_orgs:
            return repos_orgs
    return DEFAULT_REPOS_ORGS

def _read():
    """Read file. If missing use DEFAULT, if JSON error try refresh.
    """
    try:
        with cache_path().open('r') as f:
            raw = f.read()
    except FileNotFoundError:
        raw = str(DEFAULT_REPOS_ORGS)
    try:
        repos_orgs = json.loads(raw)
    except json.decoder.JSONDecodeError:
        repos_orgs = _refresh()
    return repos_orgs

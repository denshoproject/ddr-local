VERSION = '0.20130711'

import subprocess

def git_commit():
    """Returns the ddr-local repo's most recent Git commit and timestamp.
    
    sample:
    '8ad396324cc4a9ce6b9c0bce1cc8b78cc8e82859 (HEAD, master) 2013-07-11 11:03:19 -0700'
    """
    cmd = ['git', 'log', '--pretty=format:%H %d %ad', '--date=iso', '-1']
    return subprocess.check_output(cmd).replace('  ', ' ')

"""Returns git branch or "release" if "-rc" is present in VERSION string

Used to populate DEB_BRANCH in Makefile.  Adding '-rcN' to VERSION will name
the package "ddrlocal-release" instead of "ddrlocal-BRANCH".  This lets us have
a release package without requiring a separate release branch in the Git repo.

VERSION: "2.9.10"     -> "master"  -> ddrlocal-master_2.8.11-rc1~deb9_amd64.deb
VERSION: "2.9.10-rc1" -> "release" -> ddrlocal-release_2.8.11-rc1~deb9_amd64.deb
"""

import os
import subprocess
import sys

def app_version():
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, '..', 'VERSION')
    with open(path, 'r') as f:
        return f.read().strip()

def git_branch():
    return subprocess.check_output([
        'git','rev-parse','--abbrev-ref','HEAD'
    ]).strip()

def decide(version, branch):
    if '-rc' in version:
        return 'release'
    else:
        return branch

def main():
    sys.stdout.write(
        decide(app_version(), git_branch())
    )

if __name__ == '__main__':
    main()

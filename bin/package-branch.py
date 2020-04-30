"""Returns git branch or "release" if "-rc" is present in VERSION string

Used to populate DEB_BRANCH in Makefile.  Adding '-rcN' to VERSION will name
the package "ddrlocal-release" instead of "ddrlocal-BRANCH".  This lets us have
a release package without requiring a separate release branch in the Git repo.

VERSION: "2.9.10"     -> "master"  -> ddrlocal-master_2.8.11-rc1~deb9_amd64.deb
VERSION: "2.9.10-rc1" -> "release" -> ddrlocal-release_2.8.11-rc1~deb9_amd64.deb
"""

import pathlib
import subprocess
import sys

RELEASE_STR = 'rc'

def app_version():
    script_path = pathlib.Path(__file__).resolve()
    path = script_path.parent.parent / 'VERSION'
    with path.open('r') as f:
        return f.read().strip()

def git_branch():
    return subprocess.check_output([
        'git','rev-parse','--abbrev-ref','HEAD'
    ]).strip()

def decide(version, branch):
    if '-rc' in version:
        return RELEASE_STR
    else:
        return branch

def main():
    str(sys.stdout.write(
        decide(str(app_version()), str(git_branch()))
    ))

if __name__ == '__main__':
    main()

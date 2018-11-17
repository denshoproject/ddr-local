#!/usr/bin/env python

#
# deb-prep-post.py
#

description = """
In git worktrees, .git is a pointer file rather than a directory.
Wnen making a .deb package from a worktree, the result is an install
with no .git/ directory.

Makefile now runs bin/deb-prep-post.py before and after running
the FPM packager.

Before FPM it moves the .git pointer file aside, copies the .git/
directory from the master worktree, and makes sure the current
branch is checked out.

After FPM it deletes the copied .git/ dir and puts the worktree
pointer file back in place.
"""

epilog = """
"""


import argparse
import logging
import os
import shutil
import subprocess
import sys

    
def before():
    print('Checking for git-worktree')
    
    # Look at .git in project directory
    dotgit = os.path.join(os.getcwd(), '.git')
    dotgitref = os.path.join(os.getcwd(), '.gitref')
    dotgitcommit = os.path.join(os.getcwd(), '.gitcommit')
    
    if os.path.isdir(dotgit):
        # Don't touch the .git dir!
        print('{} is the git-dir. Nothing to do here.'.format(dotgit))
        sys.exit(0)
    
    elif os.path.isfile(dotgit):
        print('Moving git-worktree aside, copying git-dir')
        print('{} is a file'.format(dotgit))
        gitdir = gitdir_path(dotgit)
        print('{} is the git-dir'.format(gitdir))
        
        # note latest ref and commit
        current_ref(dotgitref)
        current_commit(dotgitcommit)
        
        # Move .git file aside
        dotgitwt = '{}wt'.format(dotgit)
        print('Moving git-worktree file: {} {}'.format(dotgit, dotgitwt))
        os.rename(dotgit, dotgitwt)
        if os.path.exists(dotgitwt) and os.path.isfile(dotgitwt):
            print('ok')
        else:
            print('ERR: {} not moved to {}.'.format(dotgit, dotgitwt))
        
        # Copy .git dir
        print('Copying git-dir from {}.'.format(gitdir))
        shutil.copytree(gitdir, dotgit, symlinks=False, ignore=None)
        if os.path.exists(dotgit) and os.path.isdir(dotgit):
            print('ok')
        else:
            print('ERR: {} not copied to {}.'.format(gitdir, dotgit))
        
        # checkout latest commit
        checkout_current(dotgitref, dotgitcommit)
        
    print('Done handling git-worktree')
    sys.exit(0)

def current_ref(dotgitref):
    # git symbolic-ref HEAD
    ref = subprocess.check_output(['git','symbolic-ref','HEAD'])
    with open(dotgitref, 'w') as f:
        f.write(ref)
    return ref

def current_commit(dotgitcommit):
    out = subprocess.check_output([
        'git','log','--pretty=format:"%H %d %ad"','--date=iso','-1'
    ])
    commit = out.replace('"','').strip().split(' ')[0]
    with open(dotgitcommit, 'w') as f:
        f.write(commit)
    return commit

def checkout_current(dotgitref, dotgitcommit):
    """Manually set to worktree's current branch
    
    When copying the .git/ dir, it will think it's on a different branch
    Run the following to point it to the right branch and commit
    see: https://git-scm.com/book/en/v1/Git-Internals-Git-References
    """
    # git symbolic-ref HEAD refs/heads/BRANCH
    with open(dotgitref, 'r') as f:
        ref = f.read().strip()
    print('Manually setting branch to {}'.format(
        ref.split('/')[-1]
    ))
    cmd = 'git symbolic-ref HEAD {}'.format(ref)
    print(cmd)
    out = subprocess.check_output(cmd.split())
    # git reset HEAD
    cmd = 'git reset HEAD'
    print(cmd)
    out = subprocess.check_output(cmd.split())
    print('ok')
    
    # clean up
    print('Cleaning up')
    os.remove(dotgitref)
    os.remove(dotgitcommit)
    print('ok')

def gitdir_path(worktree_file_path):
    with open(worktree_file_path, 'r') as f:
        text = f.read().strip()
        # "gitdir: /opt/ddr-local-master/.git/worktrees/ddr-local-develop"
        
        # is it legit?
        if ('gitdir' not in text) or ('worktrees' not in text):
            print("ERR: {} doesn't look like a git-worktree file.".format(
                worktree_file_path))
            print(text)
            sys.exit(1)
        
        # Find actual git-dir
        label,path = text.split(': ')
        gitdir = os.path.normpath(
            path[:path.index('worktrees')]
        )
        return gitdir
    print('ERR: Could not extract path from worktree!')
    sys.exit(1)

def after():
    """
    if there's NOT a .git/ and a .gitwt in project dir:
        quit
    read .gitwt
    if .git points elsewhere, and that .git exists:
        rmdir the .git
        mv .gitwt back to .git.
    """
    
    dotgit = os.path.join(os.getcwd(), '.git')
    dotgitwt = '{}wt'.format(dotgit)
    
    if os.path.exists(dotgit) and os.path.isdir(dotgit) \
    and (not os.path.exists(dotgitwt)):
        print("This is the master worktree or is not a worktree. Nothing to do here.")
        sys.exit(0)
    
    print('Restoring git-worktree')
    if not (os.path.exists(dotgit) and os.path.isdir(dotgit) \
    and os.path.exists(dotgitwt) and os.path.isfile(dotgitwt)):
        print('Something is not right: .git or .gitwt are missing!')
        sys.exit(1)
    
    if os.path.exists(dotgit) and os.path.isdir(dotgit) \
    and os.path.exists(dotgitwt) and os.path.isfile(dotgitwt):
        print('.git/ and .gitwt present.'.format(dotgit, dotgitwt))
        
        gitdir = gitdir_path(dotgitwt)
        print('.gitwt gitdir {}'.format(gitdir))
        if os.path.exists(gitdir) and os.path.isdir(gitdir) \
        and (os.getcwd() not in gitdir):
            print('gitdir exists and is not in this directory')
            
            print('Removing temporary copy of .git')
            shutil.rmtree(dotgit)
            print('ok')
            
            print('Putting worktree pointer back in place')
            os.rename(dotgitwt, dotgit)
            if os.path.exists(dotgit) and os.path.isfile(dotgit):
                print('ok')
            else:
                print('ERR: Something is not right!')
                sys.exit(1)
    
    print('Done restoring git-worktree')
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('action', help='"before" or "after.')
    args = parser.parse_args()
    if args.action == 'before':
        before()
    elif args.action == 'after':
        after()

if __name__ == '__main__':
    main()

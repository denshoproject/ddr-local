#!/usr/bin/env python
#

description = """Switch ddr-local and ddr-cmdln to a different branch; checkout from origin if not present"""

epilog = """
"""

import argparse
import os

import envoy



def branch_exists(branch):
    exists = False
    r = envoy.run('git branch')
    branches = r.std_out.split('\n')
    for b in branches:
        if b[2:] == branch:
            exists = True
    return exists

def branch_exists_in_both(local_path, cmdln_path, branch):
    os.chdir(local_path)
    local_exists = branch_exists(branch)
    os.chdir(cmdln_path)
    cmdln_exists = branch_exists(branch)
    return local_exists,cmdln_exists

def fetch():
    r = envoy.run('git fetch')
    print(r.std_out)

def pull():
    r = envoy.run('git pull')
    print(r.std_out)

def checkout_existing_local(branch):
    print('checking out existing branch...')
    cmd = 'git checkout %s' % branch
    print(cmd)
    r = envoy.run(cmd)
    print(r.std_out)
    print(r.std_err)

def checkout_new_local(branch):
    cmd = 'git checkout -b %s origin/%s' % (branch,branch)
    print(cmd)
    r = envoy.run(cmd)
    print(r.std_out)
    print(r.std_err)

def setup_install_cmdln(cmdln_path):
    os.chdir(cmdln_path)
    r = envoy.run('sudo python setup.py install')
    print(r.std_out)
    print(r.std_err)


def main():

    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('branch')
    args = parser.parse_args()
    
    ddrlocal_dir = os.getcwd()
    os.chdir('../../ddr-cmdln/ddr')
    ddrcmdln_dir = os.getcwd()
    os.chdir(ddrlocal_dir)
    
    os.chdir(ddrlocal_dir)
    print(os.getcwd())
    local_exists = branch_exists(args.branch)
    if not local_exists:
        print('fetching...')
        fetch()
        local_exists = branch_exists(args.branch)
        print('local_exists %s' % local_exists)
    if local_exists:
        checkout_existing_local(args.branch)
    else:
        checkout_new_local(args.branch)
    
    os.chdir(ddrcmdln_dir)
    print(os.getcwd())
    cmdln_exists = branch_exists(args.branch)
    if not cmdln_exists:
        print('fetching...')
        fetch()
        cmdln_exists = branch_exists(args.branch)
        print('cmdln_exists %s' % cmdln_exists)
    if cmdln_exists:
        checkout_existing_local(args.branch)
    else:
        checkout_new_local(args.branch)
    setup_install_cmdln(ddrcmdln_dir)
    
    os.chdir(ddrlocal_dir)
    

if __name__ == '__main__':
    main()

import os
import json
import re

import envoy
import git



MARKER_START = '<<<<<<<'
MARKER_MID   = '======='
MARKER_END   = '>>>>>>>'



"""FINDING UNMERGED FILES"""

"""
$ git status
hello: needs merge
# On branch master
# Changed but not updated:
#
(use "git add <file>..." to update what will be committed)
#
#
unmerged:
hello
#
no changes added to commit (use "git add" and/or "git commit -a")
$
"""

"""
$ git ls-files -u
100644 ce013625030ba8dba906f756967f9e9ca394464a 1
100644 e63164d9518b1e6caf28f455ac86c8246f78ab70 2
100644 562080a4c6518e1bf67a9f58a32a67bff72d4f00 3
hello
hello
hello
$
"""



def list_unmerged( path ):
    """Lists unmerged files in path.
    
    @param path: Absolute path to a Git repository
    @returns list of filenames.
    """
    files = []
    #r = envoy.run('git ls-files -u')
    #print(r.status_code)
    #print(r.std_out)
    #for line in r.std_out.strip().split('\n'):
    #    print(line)
    repo = git.Repo(path)
    for line in repo.git.ls_files('-u').strip().split('\n'):
        if line:
            f = line.strip().split('\t')[1]
            if f not in files:
                files.append(f)
    return files

def merge_add( repo_path, file_path_rel ):
    """
    will refuse to add a file that contains conflict markers
    """
    # check for merge conflict markers
    file_path_abs = os.path.join(repo_path, file_path_rel)
    with open(file_path_abs, 'r') as f:
        txt = f.read()
    if (MARKER_START in txt) or (MARKER_MID in txt) or (MARKER_END in txt):
        return 'ERROR: file still contains merge conflict markers'
    # add file
    repo = git.Repo(repo_path)
    repo.git.add(file_path_rel)
    return 'ok'
    
def merge_commit( path ):
    """Performs the final commit on a merge.
    
    Assumes files have already been added; will quit if it finds unmerged files.
    
    @param path: Absolute path to a Git repository
    """
    unmerged = list_unmerged(path)
    if unmerged:
        return 'ERROR: unmerged files exist!'
    repo = git.Repo(path)
    commit = repo.git.commit()



# REGEX

# # <<<<<<< ([a-zA-Z0-9]*)\n(.*)(\n=======\n)(.*)>>>>>>> ([a-zA-Z0-9]*)\n
# #pattern = '%s ([a-zA-Z0-9]*)(.*)(%s)(.*)%s ([a-zA-Z0-9]*)' % (MARKER_START, MARKER_MID, MARKER_END)
# #pattern = '%s (?P<left_commit>[a-zA-Z0-9]*)(?P<left>.*)%s(?P<right>.*)%s (?P<right_commit>[a-zA-Z0-9]*)' % (MARKER_START, MARKER_MID, MARKER_END)
# pattern = '%s (?P<left_commit>[a-zA-Z0-9]*)(?P<left>.*)%s(?P<right>.*)%s (?P<right_commit>[a-zA-Z0-9]*)' % (MARKER_START, MARKER_MID, MARKER_END)
#  
# #print(pattern)
#  
# match = re.search(pattern, raw, flags=re.DOTALL)
# if match:
#     #print(match.groupdict())
#     for name,group in match.groupdict().iteritems():
#         print('%s: %s' % (name,group))
#     #for group in match.groups():
#     #    print(group)






# SPLIT

#def load_conflicted_json(text):
#    """Reads DDR JSON file, extracts conflicting fields; arranges in left-right pairs.
#    
#    Takes JSON like this:
#    ...
#        {
#            "record_created": "2013-09-30T12:43:11"
#        },
#        {
#    <<<<<<< HEAD
#            "record_lastmod": "2013-10-02T12:59:30"
#    =======
#            "record_lastmod": "2013-10-02T12:59:30"
#    >>>>>>> 0b9d669da8295fc05e092d7abdce22d4ffb50f45
#        },
#        {
#            "status": "completed"
#        },
#    ...
# 
#    Outputs like this:
#    [
#    {'name':'record_lastmod', 'left':'...', 'right':'...'}
#    {'name':'description', 'left':'...', 'right':'...'}
#    {'name':'notes', 'left':'...', 'right':'...'}
#    ]
#    """
#    left = []; right = []
#    l = 0; r = 0
#    for line in text.split('\n'):
#        if MARKER_START in line:
#            l = 1; r = 0
#        elif MARKER_MID in line:
#            l = 0; r = 1
#        elif MARKER_END in line:
#            l = 0; r = 0
#        keyval_sep = '": "'  # only keep lines with keyval pairs
#        if l and (keyval_sep in line):
#            # NOTE: we're assuming each line can be made into a valid JSON string.
#            left.append(json.loads('{%s}' % line))
#        elif r and (keyval_sep in line):
#            right.append(json.loads('{%s}' % line))
#    # make side-by-side
#    # NOTE: we're assuming that left and right will match up.
#    fields = []
#    if len(left) == len(right):
#        for n in range(0, len(left)):
#            field = {'name': left[n].keys()[0],
#                     'left': left[n].values()[0],
#                     'right': right[n].values()[0],}
#            fields.append(field)
#    return fields

def load_conflicted_json(text):
    """Reads DDR JSON file, extracts conflicting fields; arranges in left-right pairs.
    
    Takes JSON like this:
        ...
            {
                "record_created": "2013-09-30T12:43:11"
            },
            {
        <<<<<<< HEAD
                "record_lastmod": "2013-10-02T12:59:30"
        =======
                "record_lastmod": "2013-10-02T12:59:30"
        >>>>>>> 0b9d669da8295fc05e092d7abdce22d4ffb50f45
            },
            {
                "status": "completed"
            },
        ...

    Outputs like this:
        ...
        {u'record_created': u'2013-09-30T12:43:11'}
        {u'record_lastmod': {'right': u'2013-10-02T12:59:30', 'left': u'2013-10-02T12:59:30'}}
        {u'status': u'completed'}
        ...
    """
    
    def make_dict(line):
        """
        Sample inputs:
            '    "application": "https://github.com/densho/ddr-local.git",'
            '    "release": "0.20130711"'
        Sample outputs:
            {"application": "https://github.com/densho/ddr-local.git"}
            {"release": "0.20130711"}
        """
        txt = line.strip()
        if txt[-1] == ',':
            txt = txt[:-1]
        txt = '{%s}' % txt
        return json.loads(txt)
    
    fieldlines = []
    l = ' '; r = ' '
    for line in text.split('\n'):
        KEYVAL_SEP = '": "'  # only keep lines with keyval pairs
        mrk = ' ';  sep = ' '
        if MARKER_START in line: mrk='M'; l='L'; r=' ' # <<<<<<<<
        elif MARKER_MID in line: mrk='M'; l=' '; r='R' # ========
        elif MARKER_END in line: mrk='M'; l=' '; r=' ' # >>>>>>>>
        elif KEYVAL_SEP in line: sep='S'               # normal field
        flags = '%s%s%s%s' % (sep, mrk, l, r)
        fieldlines.append((flags, line))
    
    fields = []
    for flags,line in fieldlines:
        if   flags == 'S   ': fields.append(make_dict(line)) # normal field
        elif flags == ' ML ': left = []; right = []          # <<<<<<<<
        elif flags == 'S L ': left.append(make_dict(line))   # left
        elif flags == 'S  R': right.append(make_dict(line))  # right
        elif flags == ' M  ':                                # >>>>>>>>
            if len(left) == len(right):
                for n in range(0, len(left)):
                    key = left[n].keys()[0]
                    val = {'left': left[n].values()[0],
                           'right': right[n].values()[0],}
                    fields.append( {key:val} )
    return fields



def automerge_conflicted(text, which='left'):
    """Automatically accept left or right conflicted changes in a file.
    
    Works on any kind of file.
    Does not actually understand the file contents!
    
    Used for files like ead.xml, mets.xml that are autogenerated
    We'll just accept whatever change and then it'll get fixed
    next time the file is edited.
    These really shouldn't be in Git anyway...
    """
    lines = []
    l = 0; r = 0
    for line in text.split('\n'):
        marker = 0
        if MARKER_START in line: l = 1; r = 0; marker = 1
        elif MARKER_MID in line: l = 0; r = 1; marker = 1
        elif MARKER_END in line: l = 0; r = 0; marker = 1
        flags = '%s%s%s' % (l, r, marker)
        add = 0
        if ( flags == '000'): add = 1
        if ((flags == '100') and (which == 'left')): add = 1
        if ((flags == '010') and (which == 'right')): add = 1
        if add:
            lines.append(line)
    return '\n'.join(lines)



if __name__ == '__main__':
    pass
    #print('========================================================================')
    #conflicted = '/usr/local/src/ddr-local/ddrlocal/collection.json-mergeconflict'
    #with open(conflicted, 'r') as f:
    #    raw = f.read()
    #print(raw)
    #print('------------------------------------------------------------------------')
    #fields = load_conflicted_json1(raw)
    #for f in fields:
    #    print(f)
    ##    print('')
    
    #conflicted = '/var/www/media/base/ddr-testing-160/ead.xml'
    #with open(conflicted, 'r') as f:
    #    text = f.read()
    #merged = automerge_conflicted(text, 'left')
    #print(merged)
    #pass

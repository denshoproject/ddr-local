from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from celery import states
from celery.result import AsyncResult
from celery.utils.encoding import safe_repr
from celery.utils import get_full_cls_name

from django.conf import settings
from django.urls import reverse

from webui import identifier


TASK_STATUSES = ['STARTED', 'PENDING', 'SUCCESS', 'FAILURE', 'RETRY', 'REVOKED',]
TASK_STATUSES_DISMISSABLE = ['STARTED', 'SUCCESS', 'FAILURE', 'RETRY', 'REVOKED',]

# Background task status messages.
# IMPORTANT: These are templates.  Arguments (words in {parentheses}) MUST match keys in the task dict. 
# See "Accessing arguments by name" section on http://docs.python.org/2.7/library/string.html#format-examples
TASK_STATUS_MESSAGES = {

    'collection-check': {
        #'STARTED': '',
        'PENDING': 'Checking <b><a href="{collection_url}">{collection_id}</a></b> files.',
        'SUCCESS': 'Checked <b><a href="{collection_url}">{collection_id}</a></b> files. See Background Tasks for results.',
        'FAILURE': 'Could not check <b><a href="{collection_url}">{collection_id}</a></b> files.',
        #'RETRY': '',
        #'REVOKED': '',
    },

    'collection-new-manual': {
        #'STARTED': '',
        'PENDING': 'Manually creating collection <b><a href="{collection_url}">{collection_id}</a></b>...',
        'SUCCESS': 'Manually created collection <b><a href="{collection_url}">{collection_id}</a></b>.',
        'FAILURE': 'Could not manually create collection <b><a href="{collection_url}">{collection_id}</a></b>.',
        #'RETRY': '',
        #'REVOKED': '',
    },

    'collection-new-idservice': {
        #'STARTED': '',
        'PENDING': 'Creating new <b>{organization_id}</b> collection...',
        'SUCCESS': 'Created collection <b><a href="{result[collection_url]}">{result[collection_id]}</a></b>.',
        'FAILURE': 'Could not create collection <b>{organization_id}</b> collection.',
        #'RETRY': '',
        #'REVOKED': '',
    },

    'collection-edit': {
        #'STARTED': '',
        'PENDING': 'Saving changes to collection <b><a href="{collection_url}">{collection_id}</a></b>...',
        'SUCCESS': 'Saved changes to collection <b><a href="{collection_url}">{collection_id}</a></b>.',
        'FAILURE': 'Could not save changes to collection <b><a href="{collection_url}">{collection_id}</a></b>.',
        #'RETRY': '',
        #'REVOKED': '',
    },

    'collection-sync': {
        #'STARTED': '',
        'PENDING': 'Syncing <b><a href="{collection_url}">{collection_id}</a></b> with the workbench server.',
        'SUCCESS': 'Synced <b><a href="{collection_url}">{collection_id}</a></b> with the workbench server.',
        'FAILURE': 'Could not sync <b><a href="{collection_url}">{collection_id}</a></b> with the workbench server.',
        #'RETRY': '',
        #'REVOKED': '',
    },

    'collection-signatures': {
        #'STARTED': '',
        'PENDING': 'Choosing signatures for <b><a href="{collection_url}">{collection_id}</a></b>.',
        'SUCCESS': 'Signatures chosen for <b><a href="{collection_url}">{collection_id}</a></b>.',
        'FAILURE': 'Could not choose signatures for <b><a href="{collection_url}">{collection_id}</a></b>.',
        #'RETRY': '',
        #'REVOKED': '',
    },

    'csv-export-model': {
        #'STARTED': '',
        'PENDING': 'Exporting {collection_id} {things} to CSV.',
        'SUCCESS': 'CSV file ready for download: <a href="{file_url}">{file_name}</a>.',
        'FAILURE': 'Could not export {collection_id} {things} to CSV.',
        #'RETRY': '',
        #'REVOKED': '',
    },

    'collection-reindex': {
        #'STARTED': '',
        'PENDING': 'Reindexing collection <b><a href="{collection_url}">{collection_id}</a></b>.',
        'SUCCESS': 'Reindexing <b><a href="{collection_url}">{collection_id}</a></b> completed.',
        'FAILURE': 'Reindexing <b><a href="{collection_url}">{collection_id}</a></b> failed!',
        #'RETRY': '',
        #'REVOKED': '',
    },

    'entity-edit': {
        #'STARTED': '',
        'PENDING': 'Saving changes to object <b><a href="{entity_url}">{entity_id}</a></b>...',
        'SUCCESS': 'Saved changes to object <b><a href="{entity_url}">{entity_id}</a></b>.',
        'FAILURE': 'Could not save changes to object <b><a href="{entity_url}">{entity_id}</a></b>.',
        #'RETRY': '',
        #'REVOKED': '',
    },

    'entity-delete': {
        #'STARTED': '',
        'PENDING': 'Deleting object <b>{entity_id}</b> from <a href="{collection_url}">{collection_id}</a>.',
        'SUCCESS': 'Deleted object <b>{entity_id}</b> from <a href="{collection_url}">{collection_id}</a>.',
        'FAILURE': 'Could not delete object <a href="{entity_url}">{entity_id}</a> from <a href="{collection_url}">{collection_id}</a>.',
        #'RETRY': '',
        #'REVOKED': '',
    },

    'entity-reload-files': {},

    'entity-add-external': {},

    'entity-add-access': {},
    
    'file-edit': {
        #'STARTED': '',
        'PENDING': 'Saving changes to file <b><a href="{file_url}">{file_id}</a></b>...',
        'SUCCESS': 'Saved changes to file <b><a href="{file_url}">{file_id}</a></b>.',
        'FAILURE': 'Could not save changes to file <b><a href="{file_url}">{file_id}</a></b>.',
        #'RETRY': '',
        #'REVOKED': '',
    },

    'file-delete': {
        #'STARTED': '',
        'PENDING': 'Deleting file <b>{filename}</b> from <a href="{entity_url}">{entity_id}</a>.',
        'SUCCESS': 'Deleted file <b>{filename}</b> from <a href="{entity_url}">{entity_id}</a>.',
        'FAILURE': 'Could not delete file <a href="{file_url}">{filename}</a> from <a href="{entity_url}">{entity_id}</a>.',
        #'RETRY': '',
        #'REVOKED': '',
    },

    'set-signature': {
        #'STARTED': '',
        'PENDING': 'Setting signature for <b><a href="{parent_url}">{parent_id}</a></b>...',
        'SUCCESS': 'Set signature for <b><a href="{parent_url}">{parent_id}</a></b>.',
        'FAILURE': 'Could not set signature for <b><a href="{parent_url}">{parent_id}</a></b>.',
        #'RETRY': '',
        #'REVOKED': '',
    },

    'webui-file-new-local': {
        #'STARTED': '',
        'PENDING': 'Uploading <b>{filename}</b> to <a href="{entity_url}">{entity_id}</a>.',
        'SUCCESS': 'Uploaded <a href="{file_url}">{filename}</a> to <a href="{entity_url}">{entity_id}</a>.',
        'FAILURE': 'Could not upload <b>{filename}</b> to <a href="{entity_url}">{entity_id}</a>.<br/>{result}',
        #'RETRY': '',
        #'REVOKED': '',
    },
    'webui-file-new-external': {
        #'STARTED': '',
        'PENDING': 'Adding <b>{filename}</b> to <a href="{entity_url}">{entity_id}</a>.',
        'SUCCESS': 'Added <a href="{file_url}">{filename}</a> to <a href="{entity_url}">{entity_id}</a>.',
        'FAILURE': 'Could not add <b>{filename}</b> to <a href="{entity_url}">{entity_id}</a>.<br/>{result}',
        #'RETRY': '',
        #'REVOKED': '',
    },
    'webui-file-new-access': {
        #'STARTED': '',
        'PENDING': 'Generating new access file for <b>{filename}</b> (<a href="{entity_url}">{entity_id}</a>).',
        'SUCCESS': 'Generated new access file for <a href="{file_url}">{filename}</a> (<a href="{entity_url}">{entity_id}</a>).',
        'FAILURE': 'Could not generate new access file for <a href="{file_url}">{filename}</a> (<a href="{entity_url}">{entity_id}</a>).',
        #'RETRY': '',
        #'REVOKED': '',
    },

}


def session_tasks( request ):
    """Gets task statuses from Celery API, appends to task dicts from session.
    
    This function is used to generate the list of pending/successful/failed tasks
    in the webapp page notification area.
    
    @param request: A Django request object
    @return tasks: a dict with task_id for key
    """
    # basic tasks info from session:
    # task_id, action ('name' argument of @task), start time, args
    tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    # add entity URLs
    for task_id in list(tasks.keys()):
        task = tasks.get(task_id, None)
        if task and task['action'] in ['webui-file-new-local',
                                       'webui-file-new-external',
                                       'webui-file-new-access']:
                # Add entity_url to task for newly-created file
                task['entity_url'] = reverse('webui-entity', args=[task['entity_id']])
    # Hit the celery-task_status view for status updates on each task.
    # get status, retval from celery
    # TODO Don't create a new ctask/task dict here!!! >:-O
    traceback = None
    for task_id in list(tasks.keys()):
        # Skip the HTTP and get directly from Celery API
        # djcelery.views.task_status
        result = AsyncResult(task_id)
        state, retval = result.state, result.result
        response_data = {'id': task_id, 'status': state, 'result': retval}
        if state in states.EXCEPTION_STATES:
            traceback = result.traceback
            response_data.update({'result': safe_repr(retval),
                                  'exc': get_full_cls_name(retval.__class__),
                                  'traceback': traceback})
        # end djcelery.views.task_status
        task = response_data
        # construct collection/entity/file urls if possible
        if task:
            ctask = tasks[task['id']]
            ctask['status'] = task.get('status', None)
            ctask['result'] = task.get('result', None)
            # try to convert 'result' into a collection/entity/file URL
            if (ctask['status'] != 'FAILURE') and ctask['result']:
                r = ctask['result']
                if type(r) == type({}):
                    if r.get('id', None):
                        oid = identifier.Identifier(r['id'])
                        object_url = reverse('webui-%s' % oid.model, args=[oid.id])
                        ctask['%s_url' % oid.model] = object_url
            tasks[task['id']] = ctask
    # pretty status messages
    for task_id in list(tasks.keys()):
        task = tasks[task_id]
        action = task.get('action', None)
        if action:
            messages = TASK_STATUS_MESSAGES.get(action, None)
        status = task.get('status', None)
        template = None
        if messages and status:
            template = messages.get(status, None)
        if template:
            msg = template.format(**task)
            task['message'] = msg
    # indicate if task is dismiss or not
    for task_id in list(tasks.keys()):
        task = tasks[task_id]
        if task.get('status', None):
            task['dismissable'] = (task['status'] in TASK_STATUSES_DISMISSABLE)
    # include traceback in task if present
    if traceback:
        task['traceback'] = traceback
    # done
    return tasks

def session_tasks_list( request ):
    """session_tasks as a list, sorted in reverse chronological order.
    
    NOTE: This function adds task['startd'], a datetime based on the str task['start'].
    
    @param request: A Django request object
    @return tasks: A list of task dicts.
    """
    return sorted(list(session_tasks(request).values()),
                  key=lambda t: t['start'],
                  reverse=True)

def dismiss_session_task( request, task_id ):
    """Dismiss a task from session_tasks.
    
    Removes 'startd' fields bc datetime objects not serializable to JSON.
    """
    newtasks = {}
    tasks = request.session.get(settings.CELERY_TASKS_SESSION_KEY, {})
    for tid in list(tasks.keys()):
        if tid != task_id:
            task = tasks[tid]
            if task.get('startd',None):
                task.pop('startd')
            newtasks[tid] = task
    request.session[settings.CELERY_TASKS_SESSION_KEY] = newtasks

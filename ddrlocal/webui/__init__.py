WEBUI_MESSAGES = {
    
    # webui.api
    'API_LOGIN_NOT_200': 'Error: status code {} on POST', # status code
    'API_LOGIN_INVALID_EMAIL': 'Your email is invalid! Please log in to workbench and enter a valid email!',
    'API_LOGIN_INVALID_NAME': 'Please log in to workbench and enter your first/last name(s).',
    
    # webui.views
    'ERROR': 'Error: {}', # error code
    'LOGIN_REQUIRED': 'Login is required',
    'LOGIN_SUCCESS': 'Logged in as <strong>{}</strong>.', # username
    'LOGIN_FAIL': "Couldn't log in. Please enter a valid username and password.", # status code
    'LOGOUT_SUCCESS': 'Logged out <strong>{}</strong>.', # username
    'LOGOUT_FAIL': "Couldn't log out ({}).", # status code
    
    # webui.views.collections
    'VIEWS_COLL_SYNCED': 'Collection synced with server: {}', # collection id
    'VIEWS_COLL_CREATED': 'New collection created: {}',
    'VIEWS_COLL_ERR_NO_IDS': 'Error: Could not get new collection IDs from workbench.',
    'VIEWS_COLL_ERR_CREATE': 'Error: Could not create new collection.',
    'VIEWS_COLL_UPDATED': 'Collection updated',
    'VIEWS_COLL_LOCKED': 'Collection is locked: <strong>{}</strong>', # collection_id
    
    # webui.views.entities
    'VIEWS_ENT_CREATED': 'New object created: {}', # entity id
    'VIEWS_ENT_ERR_NO_IDS': 'Error: Could not get new object IDs from workbench.',
    'VIEWS_ENT_ERR_CREATE': 'Error: Could not create new object.',
    'VIEWS_ENT_UPDATED': 'Object updated',
    'VIEWS_ENT_LOCKED': 'This object is locked.',
    
    # webui.views.files
    'VIEWS_FILES_UPLOADING': 'Uploading <b>%s</b> (%s)', # filename, original filename
    'VIEWS_FILES_PARENT_LOCKED': "This file's parent object is locked.",
    'VIEWS_FILES_UPDATED': 'File metadata updated',
    'VIEWS_FILES_NEWACCESS': 'Generating access file for <strong>%s</strong>.' # filename
    
}

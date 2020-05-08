from django import template

from webui.models import MODEL_PLURALS

register = template.Library()

def collection( obj ):
    """list-view collection template
    """
    t = template.loader.get_template('webui/collections/list-object.html')
    return t.render({'object':obj})

def entity( obj ):
    """list-view entity template
    """
    t = template.loader.get_template('webui/entities/list-object.html')
    return t.render({'object':obj})

def file( obj ):
    """list-view file template
    """
    t = template.loader.get_template('webui/files/list-object.html')
    return t.render({'object':obj})

def breadcrumbs(obj, endpoint=''):
    identifier = obj.identifier
    breadcrumbs = identifier.breadcrumbs(endpoint)
    t = template.loader.get_template('webui/breadcrumbs.html')
    return t.render({'breadcrumbs': breadcrumbs})

@register.filter(name='formaticon')
def formaticon( code ):
    """returns fa icon for the given entity.format code
    """
    icon = 'fa-file-text-o'
    if code == 'img':
        icon = 'fa-file-image-o'
    elif code == 'vh' or code == 'av':
        icon = 'fa-film'
    return icon

GALLERYITEM_DIV = """<div class="media " style="border:2px dashed red;">{}</div>"""

def galleryitem( obj ):
    """gallery-view item template
    """
    try:
        model_plural = MODEL_PLURALS[obj['model']]
    except:
        return GALLERYITEM_DIV.format(str(obj))
    template_path = 'webui/%s/gallery-object.html' % model_plural
    t = template.loader.get_template(template_path)
    return t.render({'object':obj})

LISTITEM_DIV = """<div class="media " style="border:2px dashed red;">{}</div>"""

def listitem( obj ):
    """list-view item template
    """
    try:
        model_plural = MODEL_PLURALS[obj['model']]
    except:
        return LISTITEM_DIV.format(str(obj))
    template_path = 'webui/%s/list-object.html' % model_plural
    t = template.loader.get_template(template_path)
    return t.render({'object':obj})

register.simple_tag(collection)
register.simple_tag(entity)
register.simple_tag(file)
register.simple_tag(breadcrumbs)
register.simple_tag(galleryitem)
register.simple_tag(listitem)

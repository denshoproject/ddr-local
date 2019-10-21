from django import template

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

def galleryitem( obj ):
    """gallery-view item template
    """
    try:
        model_plural = MODEL_PLURALS[obj['model']]
    except:
        return """<div class="media " style="border:2px dashed red;">%s</div>""" % str(obj)
    template_path = 'ui/%s/gallery-object.html' % model_plural
    t = template.loader.get_template(template_path)
    return t.render({'object':obj})

def listitem( obj ):
    """list-view item template
    """
    try:
        model_plural = MODEL_PLURALS[obj['model']]
    except:
        return """<div class="media " style="border:2px dashed red;">%s</div>""" % str(obj)
    template_path = 'ui/%s/list-object.html' % model_plural
    t = template.loader.get_template(template_path)
    return t.render({'object':obj})

register.simple_tag(collection)
register.simple_tag(entity)
register.simple_tag(file)
register.simple_tag(breadcrumbs)
register.simple_tag(galleryitem)
register.simple_tag(listitem)

import datetime
from django import template

register = template.Library()

def collection( obj ):
    """list-view collection template
    """
    t = template.loader.get_template('webui/collections/list-object.html')
    return t.render(template.Context({'object':obj}))

def entity( obj ):
    """list-view entity template
    """
    t = template.loader.get_template('webui/entities/list-object.html')
    return t.render(template.Context({'object':obj}))

def file( obj ):
    """list-view file template
    """
    t = template.loader.get_template('webui/files/list-object.html')
    return t.render(template.Context({'object':obj}))

register.simple_tag(collection)
register.simple_tag(entity)
register.simple_tag(file)

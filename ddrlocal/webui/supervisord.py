from datetime import datetime
import xmlrpc.client

from django.conf import settings

def process_info():
    """Supervisord process info for ddr-local apps with fields for UI.
    
    http://supervisord.org/subprocess.html#process-states
    """
    data = {'procs': settings.SUPERVISORD_PROCS}
    for name in settings.SUPERVISORD_PROCS:
        data[name] = {
            'name': name,
            'alert_class': 'danger',
            'timestamp': datetime.now(settings.TZ),
            'statename': 'restarting...',
        }
    server = xmlrpc.client.Server(settings.SUPERVISORD_URL)
    for name in settings.SUPERVISORD_PROCS:
        data[name] = server.supervisor.getProcessInfo(name)
    return data

def restart():
    server = xmlrpc.client.Server(settings.SUPERVISORD_URL)
    restarted = server.supervisor.restart()

def state():
    server = xmlrpc.client.Server(settings.SUPERVISORD_URL)
    return server.supervisor.getState()

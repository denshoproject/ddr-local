from django import forms

class MountForm(forms.Form):
    which = forms.CharField(max_length=10, required=True, initial='mount', widget=forms.HiddenInput)
    device = forms.ChoiceField(label='Removable Devices', required=True, choices=[], widget=forms.RadioSelect)
    
    def __init__(self, *args, **kwargs):
        """Initializes form object; adds list of devices to form.
        @param devices
        """
        if kwargs.has_key('devices'):
            devices = kwargs.pop('devices')
        else:
            devices = []
        super(MountForm, self).__init__(*args, **kwargs)
        choices = []
        for devicefile,label in devices:
            c = '{} {}'.format(devicefile,label)
            choices.append( (c,c) )
        self.fields['device'].choices = choices


class UmountForm(forms.Form):
    which = forms.CharField(max_length=10, required=True, initial='umount', widget=forms.HiddenInput)
    device = forms.ChoiceField(label='Removable Devices', required=True, choices=[], widget=forms.RadioSelect)
    
    def __init__(self, *args, **kwargs):
        """Initializes form object; adds list of devices to form.
        @param devices
        """
        if kwargs.has_key('devices'):
            devices = kwargs.pop('devices')
        else:
            devices = []
        super(UmountForm, self).__init__(*args, **kwargs)
        choices = []
        for mountpoint,devicefile in devices:
            c = '{} {}'.format(mountpoint,devicefile)
            choices.append( (c,c) )
        self.fields['device'].choices = choices

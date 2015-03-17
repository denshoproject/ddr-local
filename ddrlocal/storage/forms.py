import os

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


class ActiveForm(forms.Form):
    """Indicates which device is the target of the MEDIA_BASE symlink.
    
    Symlinks set using ManualSymlinkForm are listed here if present.
    """
    which = forms.CharField(max_length=10, required=True, initial='active', widget=forms.HiddenInput)
    device = forms.ChoiceField(label='Active Device', required=True, choices=[], widget=forms.RadioSelect)
    
    def __init__(self, *args, **kwargs):
        """Initializes form object; adds list of devices to form.
        @param devices
        """
        if kwargs.has_key('devices'):
            devices = kwargs.pop('devices')
        else:
            devices = []
        super(ActiveForm, self).__init__(*args, **kwargs)
        choices = []
        for mountpoint,devicefile in devices:
            # removable devices (i.e. "/media/TS1TB2013") have devicefile values
            # non-removables (i.e. "/tmp/ddr") do not
            # see storage.views.local_mount().
            if devicefile:
                choices.append( (mountpoint, os.path.basename(mountpoint)) )
            else:
                choices.append( (mountpoint, mountpoint) )
        self.fields['device'].choices = choices


class ManualSymlinkForm(forms.Form):
    """Form for setting the active-device symlink manually.
    
    See storage.views.manual_symlink.
    """
    path = forms.CharField(label='Path', max_length=255, required=True)
    label = forms.CharField(label='Label', max_length=255, required=True)
    
    def clean_path(self):
        data = self.cleaned_data['path']
        if not os.path.exists(data):
            raise forms.ValidationError("Path does not exist.")
        elif not os.access(data, os.W_OK):
            raise forms.ValidationError("Path is not writable.")
        return data

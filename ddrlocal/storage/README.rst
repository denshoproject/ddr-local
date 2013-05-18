==============
django-storage
==============

An app for managing local USB storage for Django apps running in VirtualBox VMs.




TODO (someday) Handle case where USB HDD is removed from host while VM is paused.
To reproduce:
- Pause VM (save state, etc).
- Unmount USB HDD from host OS.
- Resume the VM.
You'll see some really weird behavior:
- df -h shows that the drive is still mounted.
- It's possible to ls recently-used directories and even cd into them.
- Collections and entities that were recently visited can still be visited (these did not appear to be in the browser cache).
- Attempting to browse collections that had not recently been visited return some strange "Improperly configured Git Repo" error (should have copied or screenshotted it).
- Eventually, ddr.DDR.commands.removables_mounted() showed the device but it listed it as unmounted, with no label, causing a KeyError in a lookup function.

Sample output from DDR.commands.removables():
    {'devicefile': '/dev/sdc1',
     'ismounted': '0',
     'isreadonly': '0',
     'type': '0x07'}

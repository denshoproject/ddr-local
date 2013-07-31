==============
django-storage
==============

This app exists to address the problem of mounting and unmounting the USB device without making the user have to touch the command-line, and to provide helpful error messages and guidance for same.

In the current use case for DDR, we have a bunch of files on a Windows host.
We want to copy ingest them into Git/git-annex repositories on a USB hard drive attached to the host.
The DDR application will run in a Linux virtual machine on the host.

This app does not address the problem of shared folders.

The actual mounting and unmounting is performed by `ddr-cmdln`.  `ddr-cmdln`  makes use of `ulink` to gather information about USB devices, and `pmount` to do the actual mounting and unmounting.

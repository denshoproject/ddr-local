#!/bin/bash

# This is a general-purpose script to install ddr-local
# on a Debian netinstall base. (See README for more details.)
# This install script is intended to be run on a newly installed
# system. No attempts will be made to backup any existing data!

# USAGE
# This script should come in a folder called bunsen-?-netinstall,
# along with a collection of other necessary files.
# Change directory (cd) into that folder and run
# ./install
# to start the installation process.
# A folder called .bunsen-netinstall-logs will be added to your home folder.
# This may safely be removed if the installation was successful.
# A folder /backup (or other name) on your root file system will hold
# backups of system files replaced during the install.

################################################

set -o nounset # do not accept unset variables
# If not running in terminal, exit with message
[[ -t 0 && -t 1 && -t 2 ]] || { echo "$0: This script must be run from a terminal" >&2; exit 1; }

log_dir=.
logfile=error.log # temporary logfile in installer directory
exec > >( tee -a "$logfile" ) 2>&1

user=$USER


msg() {
    echo "
$1
"
}


bigmsg() {
    tput bold
    echo "
$1
------------------------------------------------"
    tput sgr0
    sleep 2
}


errmsg() {
    tput bold
    echo "######## ERROR ########
$1
------------------------------------------------"
    tput sgr0
    sleep 4
}


log() {
    echo "
$1
" >> "$logfile"
}


warnlog() {
    echo "######## WARNING ########
$1
------------------------------------------------" >> "$logfile"
}


confirm() { # $1 is message, $2 is desired return value: 0 or 1 (passed to 'giveup')
    echo "
$1
(press ENTER to continue, any other key to exit)
"
    read -srn1
    [[ $REPLY ]] && giveup "Goodbye!" $2
    log "Continuing"
}


option() {
    echo "
$1
(press ENTER to agree, any other key to pass)
"
    read -srn1
    [[ $REPLY ]] && { log "$user did not agree"; return 1; }
    log "$user agreed"
    return 0
}


giveup() { # $1 is message, $2 is desired return value: 0 or 1
    if [[ ${2:-1} = 0 ]]
    then
        bigmsg "$1"
    else
        errmsg "$1"
    fi
    [[ ${replaced_dirs[0]} != "none" ]] && {
        for i in "${replaced_dirs[@]}"
        do
            sudo test -d "$i" || { # if dir has not been replaced by new version, put back the original backup
                if sudo test -d  "${i%/*}"
                then
                    sudo test -d "${backup_dir}/$i" && sudo mv "${backup_dir}/$i" "${i%/*}"  || errmsg "Unable to restore missing folder $i ."
                else
                    errmsg "Cannot move $i to ${i%/*} : no such directory."
                fi
            }
        done
    }
    echo "now exiting..."
    exit ${2:-1}
}


net_test() {
    tries=4
    printf 'checking network connection... '
    while [[ $tries -gt 0 ]]
    do
        wget -O - 'http://ftp.debian.org/debian/README' >/dev/null 2>&1 && {
            msg '[OK]'
            return 0
        }
        ((tries--))
        sleep 1
    done
    msg '[FAILED]'
    return 1
}


trap 'giveup "Script terminated." 1' 1 2 3 15
[[ $user = root ]] && giveup "This script should be run by a normal user, not root" 1


log "
########################################################################
Starting ddr-local netinstall script for $user at $(date)"


clear
tput bold
echo "Welcome to the DDR-LOCAL netinstall script!"
tput sgr0
echo "
This script is expected to be run just after completing a netinstall
installation of the Debian Jessie CORE SYSTEM ONLY.
(See \"Debian Netinstall Hints\" in the README file.)"
confirm "Would you like to start the install now?" 0


# ----------------------------------------------------------------------

net_test || giveup "You do not seem to have a working network connection.
Please fix this issue and run the script again." 1


# ----------------------------------------------------------------------

# setup logfile
[[ -d "$log_dir" ]] || {
    mkdir -p "$log_dir" || giveup "failed to create $log_dir in $HOME" 1
    cp bunsen-netinstall-logs-templates/* "$log_dir" || giveup "failed to copy logfiles directory contents into $log_dir" 1
}
cat "$logfile" >> "$log_dir"/install.log
rm "$logfile" # finished with temporary logfile
logfile="$log_dir"/install.log # this logfile will remain after the install
exec > >( tee -a "$logfile" ) 2>&1
bigmsg "Messages are being saved to $logfile"
cp -f pkgs-recs pkgs-norecs config "$log_dir"


# ----------------------------------------------------------------------

# check debian version FIXME Is /etc/debian_version the best way?
grep -q '\(jessie\|\(^\|[^a-zA-Z0-9.]\)8\($\|[^a-zA-Z0-9]\)\)' /etc/debian_version && msg "Debian version: OK"|| { warnlog "/etc/debian_version reads: $(cat /etc/debian_version)"
    confirm "Debian Jessie does not appear to be installed. If you think this is incorrect,
you may wish to continue with the installation, but it would be safer to stop.
Would you like to continue anyway?" 1; }


# ----------------------------------------------------------------------

# can use sudo?
echo "
You will need your password to perform certain system tasks.
Please enter it now and it will be stored for a while.
(You may need to enter it again later.)"
sudo -v || giveup "You do not appear to have permission to use sudo,
which is needed in this script.
Please make the necessary adjustments to your system and try again." 1


# ----------------------------------------------------------------------

option "Package update and upgrade?" && {
    bigmsg "[Press 'y' if prompted at some point.]"

    msg "Updating package database..."
    sudo apt-get --quiet update  || giveup "Problem with 'apt-get update'. See ${logfile}." 1

    msg "Upgrading packages..."
    sudo apt-get --quiet upgrade  || giveup "Problem with 'apt-get upgrade'. See ${logfile}." 1
}


# ----------------------------------------------------------------------

bigmsg "Network configuration"
option 'Install standard ddr-local VM networking config (192.168.56.101)?' && {
    sudo cp debian/conf/network-interfaces /etc/network/interfaces.copied
}
option 'Install openssh and ufw?' && {
    sudo apt-get --quiet install openssh-server ufw || giveup "Couldn't install openssh-server or ufw. See ${logfile}." 1
    sudo ufw allow 22/tcp   || giveup "Could not set port 22. See ${logfile}." 1 
    sudo ufw allow 80/tcp   || giveup "Could not set port 80. See ${logfile}." 1 
    sudo ufw allow 9001/tcp || giveup "Could not set port 9001. See ${logfile}." 1 
    sudo ufw enable         || giveup "Could not enable ufw. See ${logfile}." 1 
    sudo ufw status         || giveup "Could not check ufw status. See ${logfile}." 1 
}


# ----------------------------------------------------------------------

bigmsg "VirtualBox Guest Additions"
option 'Install VirtualBox guest additions?' && {
    sudo apt-get --quiet install build-essential module-assistant
    sudo m-a prepare
    confirm "In the VM window, click on \"Devices > Install Guest Additions\"." 0
    sudo mount /media/cdrom
    sudo sh /media/cdrom/VBoxLinuxAdditions.run
}


# ----------------------------------------------------------------------

DDR_USER=ddr

bigmsg "ddr user"
option 'Add ddr user?' && {
    sudo adduser $DDR_USER
}


# ----------------------------------------------------------------------

INSTALL_SRC=gjost@bonanza.dreamhost.com:~/densho/releases/*.tgz
INSTALL_DIR=/usr/local/src
INSTALL_FILE=ddr-local-201703171500.tgz

bigmsg "Download ddr-local."
option 'Download $INSTALL_FILE?' && {
    cd $INSTALL_DIR
    sudo scp $INSTALL_SRC .
    sudo tar xzf $INSTALL_FILE
}

bigmsg "Install ddr-local."
option 'Install $INSTALL_FILE?' && {
    cd $INSTALL_DIR/ddr-local
    sudo make install-packaged
}

bigmsg "Enable background processes?"
option '' && {
    cd $INSTALL_DIR/ddr-local
    sudo make enable-bkgnd
}

bigmsg "Restart app"
option '' && {
    cd $INSTALL_DIR/ddr-local
    sudo make restart
    sudo make status
}


# ----------------------------------------------------------------------

bigmsg "INSTALL FINISHED!"
option 'Reboot system?' && {
    bigmsg "REBOOTING..."
    sudo shutdown -r now
}
exit

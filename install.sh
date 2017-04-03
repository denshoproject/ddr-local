#!/bin/bash

# ddr-local/install.sh
#  
# This script bootstraps a new instance of the DDR Editor starting with
# a basic instance of Debian 8.* (Jessie) netinst.  Download this file
# and then
#  
# Install `sudo` and `wget` if you have not already:
#  
#     # apt-get install sudo wget
#  
# Then download this file and run it:
#  
#     $ wget https://raw.githubusercontent.com/densho/ddr-local/BRANCH/install.sh
#     $ sh install.sh


DDR_USER=ddr
PROJECT=ddr-local
BRANCH=master
INSTALL_DIR=/usr/local/src
INSTALL_FILE=ddrlocal_debian8.7_amd64.tgz

MLINE="========================================================================"
LINE="------------------------------------------------------------------------"

MENU_MSG=""


message() {
    MENU_MSG="\n[$1]\n"
}

msg() {
    echo "
$1
"
}


bigmsg() {
    echo ""
    echo ""
    echo $MLINE
    tput bold
    echo "$1"
    tput sgr0
    echo $LINE
    echo ""
    sleep 1
}


errmsg() {
    tput bold
    echo "######## ERROR ########
$1
------------------------------------------------"
    tput sgr0
    sleep 1
}


confirm() { # $1 is message, $2 is desired return value: 0 or 1 (passed to 'giveup')
    echo "
$1
(press ENTER to continue, any other key to exit)
"
    read -srn1
    [[ $REPLY ]] && giveup "Goodbye!" $2
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
    echo "now exiting..."
    exit ${2:-1}
}


print_error()
{
    echo "ERROR"
}


# ----------------------------------------------------------
apt_get()
{
    bigmsg "Updating package database..."
    UPDATE_STATUS="OK"
    UPGRADE_STATUS="OK"
    sudo apt-get --quiet update  || UPDATE_STATUS="ERROR"
    bigmsg "Upgrading packages..."
    sudo apt-get --quiet upgrade  || UPGRADE_STATUS="ERROR"
    sleep 2
    message "Update $UPDATE_STATUS, upgrade $UPGRADE_STATUS"
}


# ----------------------------------------------------------
net_config()
{
    bigmsg "Configuring Network..."
    option 'Install standard ddr-local VM networking config (192.168.56.101)?' && {
        sudo cp $INSTALL_DIR/$PROJECT/debian/conf/network-interfaces /etc/network/interfaces
    }
    option 'Install openssh and ufw?' && {
        sudo apt-get --quiet install openssh-server ufw || giveup "Couldn't install openssh-server or ufw. See ${logfile}." 1
        sudo ufw allow 22/tcp   || giveup "Could not set port 22. See ${logfile}." 1 
        sudo ufw allow 80/tcp   || giveup "Could not set port 80. See ${logfile}." 1 
        sudo ufw allow 9001/tcp || giveup "Could not set port 9001. See ${logfile}." 1 
        sudo ufw enable         || giveup "Could not enable ufw. See ${logfile}." 1 
        sudo ufw status         || giveup "Could not check ufw status. See ${logfile}." 1 
    }
    sleep 2
    message "Network config file installed."
}


# ----------------------------------------------------------
vbox_guest()
{
    bigmsg "Installing VirtualBox Guest Additions"
    echo "Installing prerequisites..."
    sudo apt-get --quiet install build-essential module-assistant
    sudo m-a prepare
    confirm "In the VM window, click on \"Devices > Install Guest Additions\"." 0
    sudo mount /media/cdrom
    sudo sh /media/cdrom/VBoxLinuxAdditions.run
    sleep 2
    message "VirtualBox Guest Additions installed."
}


# ----------------------------------------------------------
add_user()
{
    sudo adduser $DDR_USER
    sleep 2
    message "Added '$DDR_USER' user."
}


# ----------------------------------------------------------
setbranch()
{
    BRANCH=$(
        whiptail \
            --inputbox "Install branch:" \
            8 78 $BRANCH \
            --title "Set branch" \
            3>&1 1>&2 2>&3
    )
    message "Branch set to $BRANCH."
}


# ----------------------------------------------------------
setinstalldir()
{
    INSTALL_DIR=$(
        whiptail \
            --inputbox "Install in directory:" \
            8 78 $INSTALL_DIR \
            --title "Install dir" \
            3>&1 1>&2 2>&3
    )
    message "Install directory set to $INSTALL_DIR."
}


# ----------------------------------------------------------
download()
{
    INSTALL_SRC=https://ddr.densho.org/static/ddrlocal/ddrlocal-$BRANCH.tgz
    INSTALL_URL=$(
        whiptail \
            --inputbox "Download release tarball." \
            8 78 $INSTALL_SRC \
            --title "Download" \
            3>&1 1>&2 2>&3
    )
    cd $INSTALL_DIR
    sudo wget $INSTALL_URL
    INSTALL_FILE=`basename $INSTALL_URL`
    message "Downloaded $INSTALL_FILE."
    sleep 1
}


# ----------------------------------------------------------
install()
{
    bigmsg "Installing ddr-local"

    cd $INSTALL_DIR
    sudo tar xzf $INSTALL_FILE
    cd $INSTALL_DIR/$PROJECT
    sudo make install-packaged
    sleep 2
    message "Installed ddr-local."
}


# ----------------------------------------------------------
enable_bkgnd()
{
    bigmsg "Enabling background processes"
    cd $INSTALL_DIR/$PROJECT
    sudo make enable-bkgnd
    sleep 2
    message "Background processes enabled."
}


# ----------------------------------------------------------
restart()
{
    bigmsg "Restart ddr-local application"
    cd $INSTALL_DIR/$PROJECT
    sudo make restart
    sudo make status
    sleep 2
}


# ----------------------------------------------------------
reboot_vm()
{
    if (whiptail --title "Confirm Reboot" --yesno "You do really want to reboot?" 8 78) then
       sudo shutdown -r now
    else
       message "Reboot cancelled by user."
    fi
}


# ----------------------------------------------------------
main_menu()
{
        
    OPTION=$(whiptail \
        --title "DDR-LOCAL Installer" \
        --menu "$MENU_MSG\nInstalls ddr-local on VM running Debian 8.7 'Jessie' netinstall.\n\n" \
        22 72 10 \
        "vbox"       "Install VirtualBox Guest Additions." \
        "user"       "Set up the 'ddr' user." \
        "branch"     "Set branch ($BRANCH)" \
        "installdir" "Set install directory ($INSTALL_DIR)" \
        "download"   "Download to install directory." \
        "network"    "Install ddr-local network configs." \
        "install"    "Run install scripts." \
        "bkgnd"      "Enable background processes (e.g. repo status)." \
        "restart"    "Restart ddr-local daemons and application." \
        "reboot"     "Reboot the machine." \
        3>&1 1>&2 2>&3)

    MENU_MSG=""
    repeat=false
    case $OPTION in
        packages)
            apt_get
            repeat=true
            ;;
        network)
            net_config
            repeat=true
            ;;
        vbox)
            vbox_guest
            repeat=true
            ;;
        user)
            add_user
            repeat=true
            ;;
        branch)
            setbranch
            repeat=true
            ;;
        installdir)
            setinstalldir
            repeat=true
            ;;
        download)
            download
            repeat=true
            ;;
        install)
            install
            repeat=true
            ;;
        bkgnd)
            enable_bkgnd
            repeat=true
            ;;
        restart)
            restart
            repeat=true
            ;;
        reboot)
            reboot_vm
            repeat=true
            ;;
    esac
    break
    if [ "$repeat" = true ];then
        main_menu
    fi
}

main_menu
exit 0

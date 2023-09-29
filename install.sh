#!/usr/bin/bash

# Copyright 2023 iiPython

# Ensure we have sudo
if [ "$EUID" -ne 0 ]
then
    echo "The ISM install script requires root privileges."
    exit 1
fi

# Helper functions
init_setup() {
    rm -rf /tmp/ism  # In case of multiple wizard installs (maybe a crash?)
    mkdir -p /tmp/ism /opt/ism
    if ! id ism >/dev/null 2>&1; then
        useradd -M -K MAIL_DIR=/dev/null ism
        usermod -L ism
    fi

    # Download repository
    cd /tmp/ism && wget https://github.com/iiPythonx/ism/archive/refs/heads/main.zip

    # Install unzip
    echo "Installing zip ..."
    if [ -x "$(command -v apk)" ];       then sudo apk add --no-cache unzip
    elif [ -x "$(command -v apt-get)" ]; then sudo apt-get install unzip -y
    elif [ -x "$(command -v dnf)" ];     then sudo dnf install unzip -y
    elif [ -x "$(command -v zypper)" ];  then sudo zypper install unzip
    else
        echo "FAILED TO INSTALL the zip package, please install it manually and restart the installation.">&2
        exit 1
    fi

    # Head to repo
    unzip main.zip
    cd ism-main
} 
clean() {
    cd && rm -rf /tmp/ism
}
install_client() {
    init_setup
    echo "Installing ISM client requirements ..."
    python3 -m pip install -r client/requirements.txt
    echo "Copying ISM client files ..."
    cp -r client/ /opt/ism/
    echo "Installing systemd unit ..."
    cp systemd/ism_client.service /lib/systemd/system/
    systemctl daemon-reload
    systemctl enable ism_client
    echo "Cleaning up ..."
    clean
    printf "\n\n\n"
    echo "ISM client installed!"
    echo "Now, edit /lib/systemd/system/ism_client.service and add in your configuration details."
    echo "Afterwards, the client can be started with `systemctl start ism_client`!"
    exit 0
}
install_server() {
    init_setup
    echo "Installing ISM server ..."
    ls
}
uninstall() {
    echo "Uninstalling ISM ..."

    # Remove systemd units
    systemctl stop ism_server
    systemctl stop ism_client
    rm -rf /lib/systemd/system/ism_*
    systemctl daemon-reload

    # Handle purging the ISM user/group
    userdel ism && groupdel ism
    rm -rf /opt/ism

    # Done!
    echo "ISM has been uninstalled."
}

# Ask what operation we're performing
while true; do
    clear
    echo "ISM Install Script"
    echo "=================================="
    echo "1) Install ISM client"
    echo "2) Install ISM server"
    echo "3) Uninstall ISM"
    echo

    # Check option
    read -p "Select option: " opt
    clear
    case $opt in
        1) install_client; exit;;
        2) install_server; exit;;
        3) uninstall; exit;;
        *) continue;;
    esac
done
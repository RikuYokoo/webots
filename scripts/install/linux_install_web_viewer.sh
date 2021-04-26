#!/bin/bash

if [[ $EUID -ne 0 ]]; then
       echo "This script must be run as root"
       exit 1
fi

apt install python3-pip -y
pip3 install --upgrade pip
pip3 install pyclibrary


git clone https://github.com/emscripten-core/emsdk.git dependencies/emsdk

user=$(env | grep SUDO_USER | cut -d '=' -f 2-) 
chown $user dependencies/emsdk

git pull
./dependencies/emsdk/emsdk install latest
./dependencies/emsdk/emsdk activate latest

echo 'source "/home/benjamin/webots/dependencies/emsdk/emsdk_env.sh"' >> /home/$user/.bashrc

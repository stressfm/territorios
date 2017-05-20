#!/bin/bash

# Get Instructions here: 
# https://www.raspberrypi.org/documentation/installation/installing-images/README.md
# Download latest rapbian image and write it to sdcard
# wget https://downloads.raspberrypi.org/raspbian_lite/images/raspbian_lite-2017-04-10/2017-04-10-raspbian-jessie-lite.zip
# 


# Boot the raspberry pi with the sdcard with the installed image

# Copy the script with:
# scp build_pi.sh pi@<ip address of pi>:.

# Ssh into pi:
# ssh pi@<ip address of pi>

# Execute script with:
# sudo sh ./build_pi.sh

echo "deb http://matriz.stress.fm/deb_repo jessie main" > /etc/apt/sources.list.d/matriz.list
wget -O - http://matriz.stress.fm/deb_repo/matriz_deb.gpg.asc | apt-key add -

apt-get update
apt-get install debconf-utils -y --force-yes
debconf-set-selections <<< "jackd2    jackd/tweak_rt_limits   boolean true"
sed -i 's/# en_GB.UTF-8 UTF-8/en_GB.UTF-8 UTF-8/' /etc/locale.gen
sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
locale-gen
update-locale LC_ALL=en_US.UTF-8
debconf-set-selections <<< "locales locales/default_environment_locale select en_US.UTF-8"
dpkg-reconfigure  -f noninteractive locales

apt-get upgrade -y --force-yes
apt-get install -y --force-yes jackd2 \
   moc python-gst-1.0 libgstrtspserver-1.0 \
   python-gst-1.0 gstreamer1.0-plugins-bad libgstreamer-plugins-bad1.0 \
   python-dev libffi-dev libssl-dev curl git

curl -LO https://bootstrap.pypa.io/get-pip.py
python get-pip.py


GITREPO="/home/pi/territorios"
if [ -d "$GITREPO" ]; then
  cd "$GITREPO"
  sudo -u git pull
else
  cd /home/pi
  sudo -u pi git clone https://github.com/stressfm/territorios.git
  cd "$GITREPO"
  sudo -u pi git checkout no_rtspserver
fi

pip install supervisor
"${GITREPO}/configs/installer/client.sh"

if [ ! -e /dpkgdivert ]; then
  sudo -u pi supervisord
fi

# Cleanup
apt-get --yes --force-yes autoremove
apt-get clean


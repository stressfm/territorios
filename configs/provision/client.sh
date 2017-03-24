#!/bin/bash

INSTALL_USER="vagrant"

echo "deb http://matriz.stress.fm/deb_repo jessie main" > /etc/apt/sources.list.d/matriz.list
wget -O - http://matriz.stress.fm/deb_repo/matriz_deb.gpg.asc | apt-key add -

apt-get update
apt-get dist-upgrade
apt-get install debconf-utils -y
debconf-set-selections <<< "jackd2    jackd/tweak_rt_limits   boolean true"
apt-get install -y jackd2 \
   moc libgstrtspserver-1.0 \
   python-gst-1.0 gstreamer1.0-plugins-bad libgstreamer-plugins-bad1.0 \
   python-dev libffi-dev libssl-dev curl

curl -LO https://bootstrap.pypa.io/get-pip.py
python get-pip.py
pip install supervisor

pip install matriz

apt-get install -y rsync
sudo -u $INSTALL_USER mkdir /home/$INSTALL_USER/territorios

cp /vagrant/configs/provision/client.d/{rc.local,supervisord.conf} /etc
sudo -u $INSTALL_USER cp /vagrant/configs/provision/client.d/client.json /home/$INSTALL_USER/client.json
sudo -u $INSTALL_USER cp /vagrant/configs/provision/common.d/_.jackdrc /home/$INSTALL_USER/.jackdrc
sudo -u $INSTALL_USER cp /vagrant/configs/provision/client.d/update_code.sh /home/$INSTALL_USER
sudo -u $INSTALL_USER cp /vagrant/scripts/start_jackd.sh /home/$INSTALL_USER
chmod +x /home/$INSTALL_USER/{update_code.sh,start_jackd.sh}

rsync -rv /vagrant/{scripts,src} /home/$INSTALL_USER/territorios/
/etc/rc.local

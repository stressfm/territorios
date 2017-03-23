echo "deb http://matriz.stress.fm/deb_repo jessie main" > /etc/apt/sources.list.d/matriz.list
wget -O - http://matriz.stress.fm/deb_repo/matriz_deb.gpg.asc | apt-key add -

apt-get update
apt-get install debconf-utils -y
debconf-set-selections <<< "jackd2    jackd/tweak_rt_limits   boolean true"
apt-get install -y jackd2 \
   moc libgstrtspserver-1.0 \
   python-gst-1.0 gstreamer1.0-plugins-bad libgstreamer-plugins-bad1.0 \
   python-dev libffi-dev curl

curl -LO https://bootstrap.pypa.io/get-pip.py
python get-pip.py
pip install supervisor

pip install matriz

apt-get install -y rsync
sudo -u vagrant mkdir /home/vagrant/territorios
sudo -u vagrant rsync -rv /vagrant/{scripts,src} /home/vagrant/territorios/

cp /vagrant/configs/provision/client.d/{rc.local,supervisord.conf} /etc
cp /vagrant/configs/provision/client.d/client.json /home/vagrant/client.json


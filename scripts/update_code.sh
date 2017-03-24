#!/bin/bash
rsync -rv /vagrant/{scripts,src} /home/vagrant/territorios/
supervisorctl -c /etc/supervisord/supervisord.conf restart server


#!/bin/bash
rsync -rv /vagrant/{scripts,src} /home/vagrant/territorios/
supervisorctl -c /etc/supervisord.conf restart client


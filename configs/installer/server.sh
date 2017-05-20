#!/bin/bash

INSTALLERDIR="$(basedir $0)"

SERVERDIR="/home/saturno"
SERVERDIR="saturno"

CLIENTDIR="/home/pi"
CLIENTUSER="pi"
# Installer/Updater for matriz server



# Client
sed "s|BASEDIR|$CLIENTDIR|g" $INSTALLERDIR/spvr.client.conf.template  | sed "s|USER|$CLIENTUSER|g" | sudo tee /etc/supervisord.conf >/dev/null


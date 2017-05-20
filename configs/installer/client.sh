#!/bin/bash

INSTALLERDIR="$(dirname $(readlink -f $0))"
GITREPODIR="$(readlink -f $INSTALLERDIR/../..)"
SCRIPTSDIR="$GITREPODIR/scripts"

CLIENTDIR="/home/pi"
CLIENTUSER="pi"


# Installer/Updater for matriz server

cd "$GITREPODIR"
git pull

# Client
sed "s|BASEDIR|$CLIENTDIR|g" $INSTALLERDIR/spvr.client.conf.template  | sed "s|USER|$CLIENTUSER|g" | sudo tee /etc/supervisord.conf >/dev/null
cp -v "$SCRIPTSDIR/start_jackd.sh" "$SCRIPTSDIR/shutdown_pi.py" "$CLIENTDIR"
sudo sed -i "$(wc -l /etc/rc.local | cut -d' ' -f1)i sudo -u pi supervisord -c /etc/supervisord.conf" /etc/rc.local
## Restart services
#sudo -u pi supervisorctl reload

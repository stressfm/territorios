import socket
import json
import logging
import re
from gevent import subprocess


def config_liq():
    """
    Change IPs for lisboa, porto, montemor
    Restart Liquidsoap if necessary
    """

    liq_file = "/etc/liquidsoap/matriz.liq"
    info = {}

    for i in get_clients():
        info[i["name"]] = i["ip"]

    seds = []
    for k, v in info.iteritems():
        seds += ['-e', 's/^%s .*/%s = "%s"/' % (k, k, v)]

    cmd = ['sed', '-i'] + seds + [liq_file]
    p = subprocess.Popen(cmd)
    p.wait()
    # TODO: Check if uptime is less then 10 sec - do not restart
    cmd = ['sudo', '/usr/local/bin/supervisorctl', 'restart', 'liquidsoap']
    p = Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, err = p.communicate()
    logging.debug("[Func liq_restart]: %s" % cmd)
    logging.debug("[stdout] '%s'" % out)
    # logging.debug("[stderr] '%s'" % err)
    return True

def check_rtsp_port(address="127.0.0.1", port=8554):
    """
    Checks if a given port is open and accepting coonections.
    """
    s = socket.socket()
    try:
        s.connect((address, int(port)))
    except socket.error as e:
        return False, "{}".format(e)
    return True, ""

def sanitize_to_json(s):
    """
    Convert the string that come through the websockets to json
    We get it an escaped string
    """
    return json.loads(s.decode('string-escape').strip('"'))

def get_local_ip():
    out,err = subprocess.Popen(["ip","addr","show"],stdout=subprocess.PIPE).communicate()
    #return [ x for x in re.findall("\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", out.decode()) if not (x.startswith('127') or x.endswith('255'))][0]
    return "172.28.128.3"

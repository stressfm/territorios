import socket
import json
import logging

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

def check_rtsp_port(address=None, port=8554):
    """
    Checks if a given port is open and accepting coonections.
    """
    s = socket.socket()
    s.settimeout(5.0)
    connected = True
    message = "Hello. How are you today?"
    try:
        s.connect((address, int(port)))
        messsage = "Port %d at %s is open" % (int(port), address,)
    except socket.error as e:
        conected = False
        message = "%s" % e
    return connected, message

def sanitize_to_json(s):
    """
    Convert the string that come through the websockets to json
    We get it an escaped string
    """
    return json.loads(s.decode('string-escape').strip('"'))


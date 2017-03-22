#!/usr/bin/env python3
"""
Helper script to find raspberrys in local network

System Dependencies: nmap


sudo nmap -p 22 192.168.2.0/24 | grep -B4 "Raspberry Pi Foundation"
"""

import re
from subprocess import Popen, PIPE

import os
import json
import argparse
import sys
import logging

MACS_FILE = "find_network.json"

LOGGER_FORMAT_DEBUG = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOGGER_FORMAT_INFO = '%(message)s'
logger = logging.getLogger(__name__)

def _create_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-d', '--debug', action="store_true", default=False)

    return parser

def main(arguments=sys.argv[1:]):
    with open(MACS_FILE, "r") as f:
        j = json.loads(f.read())
        MACHINE_NAMES = j["MACHINE_NAMES"]
        WIRELESS_CARDS = j["WIRELESS_CARDS"]

    MACHINE_NAMES.update(WIRELESS_CARDS)
    MAC_ADDRESSES = [k for k in MACHINE_NAMES]

    #OUTFILE = "TEMPFILE_NMAP_TEST.txt"

    parser = _create_parser()
    args = parser.parse_args(arguments)
    if args.debug:
        logging.basicConfig(
            format=LOGGER_FORMAT_DEBUG,
            level=logging.DEBUG
        )
    else:
        logging.basicConfig(
            format=LOGGER_FORMAT_INFO,
            level=logging.INFO
        )

    logging.debug("Starting program")
    logging.info("Starting program")

    nmap = check_nmap()

    cmd1 = nmap + " -sP --host-timeout 40s --max-retries 16 {}".format(get_network_address())
    cmd2 = "grep -e {}".format(" -e ".join(MAC_ADDRESSES))
    #fd = open(OUTFILE, "w")
    #p1 = Popen(cmd1.split(" "), stdout=PIPE)
    #p2 = Popen(cmd2.split(" "), stdout=fd, stdin=p1.stdout)
    #p2.wait()
    logging.debug("{}".format(cmd1.split(" ")))

    FOUND={}
    tries = 0
    while not FOUND:
        tries += 1
        p1 = Popen(cmd1.split(" "), stdout=PIPE)
        p1.wait()
        LINES = p1.stdout.read().decode('utf-8').split("\n")
        for line in range(len(LINES)):
            for a in MAC_ADDRESSES:
                if a.lower() in LINES[line].lower():
                    if a not in FOUND:
                        FOUND[a] = LINES[line-2][21:]
        if tries > 5:
            break

    logging.debug("Had to pass {} times\n{}".format(tries, FOUND))
    logging.debug("had to hosts file >> ")
    print_hosts(FOUND)

def get_network_address():
    cmd_iproute = "ip route"
    out, err = Popen(cmd_iproute.split(" "), stdout=PIPE).communicate()
    pattern = re.compile("\d{1,3}\.\d{1,3}\.\d{1,3}\.0\/\d{1,2}")
    return pattern.findall(out.decode('utf-8'))[0]

def get_actual_server_ip():
    # get the server ip and set it in /home/pi/client.json
    pass

def restart_matriz():
    #restart matriz after the server ip is set
    pass

def check_nmap():
    if os.path.exists("/usr/bin/nmap"):
        return "sudo /usr/bin/nmap"
    if os.path.exists("/usr/sbin/nmap"):
        return "sudo /usr/sbin/nmap"
    Popen(["sudo", "apt-get", "update"]).wait()
    p1 = Popen(["sudo", "apt-get", "install", "-y", "nmap"])
    out = p1.wait()
    if not out:
        return check_nmap()
    return None

def print_hosts(mydict):
    text_to_replace = "s/^[0-9].*\\b{0}\\b/{1} {0}/"
    for mac in mydict:
        logging.debug("replacing /etc/hosts lines... {} {}".format(mydict[mac], MACHINE_NAMES[mac]))
        #cmd = ["sudo", "sed", "-i.bak", text_to_replace.format(MACHINE_NAMES[mac], mydict[mac]), "/etc/hosts"]
        #Popen(cmd).wait()

if __name__ == "__main__":
    main()

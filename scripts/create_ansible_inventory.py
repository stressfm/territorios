#!/usr/bin/env python
"""
Create an inventory file for ansible after doing vagrant up
"""

import os

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INVENTORY_PATH = os.path.join(BASE_PATH, "ansible/hosts")

HOSTS = [
    {"name": "server", "port": "2222", "key": os.path.join(BASE_PATH, ".vagrant/machines/server/virtualbox/private_key")},
    {"name": "client", "port": "2200", "key": os.path.join(BASE_PATH, ".vagrant/machines/client/virtualbox/private_key")},
]
INVENTORY_CONTENT = ""
for i in HOSTS:
    INVENTORY_CONTENT += "{name} ansible_host=localhost ansible_ssh_private_key_file={key} ansible_port={port} ansible_user=vagrant\n".format(**i)

f = open(INVENTORY_PATH, "w")
f.write(INVENTORY_CONTENT)
f.close()






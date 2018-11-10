#-------------------------------------------------------------------------------
# Name:        heat_inventory
# Purpose:
#
# Author:      Daniel Watrous
#
# Created:     10/07/2015
# Copyright:   (c) HP 2015
#-------------------------------------------------------------------------------
#!/usr/bin/python

import argparse
from os.path import join
from simplejson import loads
from string import Template
from textwrap import dedent
import subprocess



class heat_inventory:
    # default values
    default_stack_name = "dask-stack"
    ansible_ssh_user = "cloud-user"
    ansible_ssh_private_key_file = "/home/calba/.ssh/ISUZUid_rsa"

    # templates
    host_entry_disk = Template('$ipaddress   systemname=$hostname  intip=$intipaddress ansible_connection=ssh  ansible_ssh_user=$ssh_user   ansible_ssh_private_key_file=$private_key_file device=$deviceid')
    host_entry_nodisk = Template('$ipaddress   systemname=$hostname  intip=$intipaddress ansible_connection=ssh  ansible_ssh_user=$ssh_user   ansible_ssh_private_key_file=$private_key_file')

    hostsInv_output = Template("""
[$blockAnsGroup]
$blockData
$blockVar
""")

    var_part = Template("""

[$blockAnsGroup:vars]
schedulerIP=$scheduler

""")

    node_entry = Template("""  - hostname: $hostname
    ip: $ipaddress""")

    nodes_section = Template("""---
$key:
$nodes
""")
    nodes_sshkeyscan = Template('ssh-keyscan -t rsa $ipaddress >> ~/.ssh/known_hosts')

    def __init__(self, **kwargs):
        self.stack = kwargs.get('stack', self.default_stack_name)
        self.ssh_user = kwargs.get('ssh_user', self.ansible_ssh_user)
        self.ssh_key = kwargs.get('ssh_key', self.ansible_ssh_private_key_file)
        self.load_heat_output()

    def __add__(self,other):
        for item in other.heat_output:
            self.heat_output[item] = other.heat_output[item]
        return self

    def load_heat_output(self):
        # stack_cmd = "heat output-show %s --all" % self.default_stack_name
        stack_cmd = 'openstack stack output show %s --all -f json | sed -e \'s/"{/{/g\' -e \'s/}"/}/g\' -e \'s/\\\\n/ /g\' -e \'s/\\\\"/"/g\' ' % self.stack
        # self.heat_output = json.loads(subprocess.Popen(stack_cmd, shell=True, stdout=subprocess.PIPE).stdout.read())
        stack_output = subprocess.Popen(stack_cmd, shell=True, stdout=subprocess.PIPE).stdout.read()
        
        aux = loads(stack_output)
        self.heat_output = dict()
        for item in aux:
            self.heat_output[item] = aux[item]

    def get_output_data(self, key):
        if key not in self.heat_output:
            return []
        return self.heat_output[key]['output_value']

    def get_host_entry(self, ipaddress, intipaddress, device, name):
        if device:
            return self.host_entry_disk.substitute(hostname=name,
                                                   ipaddress=ipaddress,
                                                   intipaddress=intipaddress,
                                                   ssh_user=self.ssh_user,
                                                   private_key_file=self.ssh_key,
                                                   deviceid=device)
        else:
            return self.host_entry_nodisk.substitute(hostname=name,
                                                     ipaddress=ipaddress,
                                                     intipaddress=intipaddress,
                                                     ssh_user=self.ssh_user,
                                                     private_key_file=self.ssh_key)

    def get_host_entries(self, key):
        datanode_hosts = []
        for datanode_host in self.get_output_data(key):
            if len(datanode_host) == 4:
                device = datanode_host[3]
            else:
                device = ""
            datanode_hosts.append(self.get_host_entry(datanode_host[1], datanode_host[2], device, datanode_host[0]))
        return "\n".join(datanode_hosts)

    def get_hosts_InvOutput(self, stackKey, ansGroup, schedulerAdd=None):
        hostsList = self.get_host_entries(stackKey)
        blockVarStr = "" if schedulerAdd is None else self.var_part.substitute(blockAnsGroup=ansGroup, scheduler=schedulerAdd)

        if not hostsList:
            return ""
        return dedent(self.hostsInv_output.substitute(blockAnsGroup=ansGroup, blockData=hostsList, blockVar=blockVarStr))

    # Ansible group_vars nodes

    def get_node_entry(self, hostname, ipaddress):
        return self.node_entry.substitute(hostname=hostname, ipaddress=ipaddress)

    def get_nodes_entries(self, *args):
        nodes = []
        for key in args:
            for node in self.get_output_data(key):
                nodes.append(self.get_node_entry(node[0], node[2]))
        return "\n".join(nodes)

    def get_nodes_output(self, *args):
        key = args[0]
        return self.nodes_section.substitute(key=key, nodes=self.get_nodes_entries(*(args[1:])))

    def get_node_keyscan_script(self, *args):
        nodes = []
        for key in args:
            for node in self.get_output_data(key):
                nodes.append(self.nodes_sshkeyscan.substitute(ipaddress=node[1]))
        return "\n".join(nodes)


def getParameters():
    parser = argparse.ArgumentParser(description='Prepare stack inventory')
    parser.add_argument("-s", "--stack", default=argparse.SUPPRESS)

    parser.add_argument("-u", "--ssh_user", default=argparse.SUPPRESS)
    parser.add_argument("-k", "--ssh_key", default=argparse.SUPPRESS)

    parser.add_argument("-d", "--output-dir", default=".", dest="outputdir", type=str)

    opts = vars(parser.parse_args())

    return opts

def composeFich(opts, fichname):
    return join(opts['outputdir'], fichname)

def main():

    stack_opts = getParameters()

    stack_inv = heat_inventory(**stack_opts)

    schedulerIP = None
    schedulerList = stack_inv.get_output_data('dask_scheduler_data')
    if schedulerList:
        schedulerIP = schedulerList[0][2]

    inventory_file = open(composeFich(stack_opts,'%s-inventory.txt' % stack_opts['stack']), 'w')
    inventory_file.write(stack_inv.get_hosts_InvOutput('dask_nodes_data', 'dask-workers', schedulerAdd=schedulerIP))
    inventory_file.write(stack_inv.get_hosts_InvOutput('dask_scheduler_data', 'dask-scheduler'))
    inventory_file.close()

    nodes_file = open(composeFich(stack_opts,'dask-workers'), 'w')
    nodes_file.write(stack_inv.get_nodes_output('nodes', 'dask_nodes_data', 'workers'))
    nodes_file.close()

    keyscan_script_file = open(composeFich(stack_opts,'scan-node-keys.sh'), 'w')
    keyscan_script_file.write(stack_inv.get_node_keyscan_script('self.heat_output', 'dask_nodes_data', 'dask_scheduler_data'))
    keyscan_script_file.write('\n')
    keyscan_script_file.close()

if __name__ == '__main__':
    main()


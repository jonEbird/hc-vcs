#!/usr/bin/env python

import subprocess, re, sys

try:
    import paramiko
except ImportError:
    raise Exception, "Please install the paramiko module. Required for connecting to remote servers."

def command(cmd, filter='^[^\n]*', nparts=0):
    """
    Execute cmd and filter the output before the data is returned.
    cmd should be a string with arguments (if needed) and filter is a regex
    Return is a list of lines matched
    """
    try:
        filter_re = re.compile(filter, re.M)
        # We're combining stderr with stdout
        proc = subprocess.Popen(cmd.split(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        if proc.returncode == 0:
            flist = filter_re.findall(stdout)
            if nparts:
                # means you want the data split on each line and in at least nparts length
                flist = [(parts + [''] * (nparts - len(parts))) for parts in [ i.split(None, nparts-1) for i in flist ]]
            return flist
    except (OSError), e:
        pass
    # Empty list means something went wrong
    return []

def remote_command(server, cmd, username='root', password='cangetin', filter='^[^\n]*'):

    try:
        filter_re = re.compile(filter, re.M)
        ssh = paramiko.SSHClient()

        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server, username=username, password=password)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read()
        ssh.close()
        
        return filter_re.findall(output)

    except (Exception), e:
        print 'Remote_command error: %s' % (str(e))
        raise #pass
    # Empty list means something went wrong
    return []

def make_pyfriendly(x):
    """ VCS often uses '1' for True and '0' for False.
    You can use this fun in a map() to make it more python friendly.
    E.g. map(make_pyfriendly, hares_display())
    """
    if x[-1] == '1':
        x[-1] = True
    elif x[-1] == '0':
        x[-1] = False
    return x

class VCS:
    """ Veritas Cluster Server (VCS) class for making many inquiries on a cluster server.
    Can be used for querying a local cluster or a remote cluster.
    If remote, you will need to pass a username and password which is allowed to make VCS inquiries (see 'hauser')

    Upon instantiation, take a look at:
      self.info    = dictionary of useful cluster attributes
      self.groups  = list of service groups in the cluster
      self.status  = dict of dict; See self.get_cluster_status() for more on the data structure.
    """
    def __init__(self, server='local', username='root', password='cangetin'):
        self.__ssh = None
        self.server   = server
        self.username = username
        self.password = password
        self.PATH = '/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin:/usr/local/bin:/opt/VRTS/bin:/opt/VRTSvcs/bin'
        # Get some information on your cluster
        self.info   = dict(self.run('haclus -display', filter='^[^#].*', ncol=2))
        self.groups = [] # get_cluster_status() populates this for us
        self.status = self.get_cluster_status()

    def __del__(self):
        # clean up ssh connections, if used
        if self.__ssh:
            self.__ssh.close()

    def __isremote(self):
        return self.server != 'local'

    def run(self, cmd, filter='^[^\n]*', ncol=0):
        """ Execute a command on the server and returning list of results.
        filter := regex for, obviously, filtering the results
        ncol   := When specified, each line will be split into this many columns of data.
                  Results is now list of lists.
        """
        # get the output for the command
        output = ''
        if self.__isremote():
            try:
                if not self.__ssh:
                    self.__ssh = paramiko.SSHClient()
                    self.__ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    self.__ssh.connect(self.server, username=self.username, password=self.password, timeout=5)
                stdin, stdout, stderr = self.__ssh.exec_command('PATH="%s" %s' % (self.PATH, cmd.strip()))
                output = stdout.read()
            except (Exception), e: # FIXME: Need to use more specific Paramiko exceptions.
                #print 'VCS.run ssh Error: %s' % (str(e))
                #raise
                pass
        else:
            try:
                proc = subprocess.Popen(cmd.split(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                stdout, stderr = proc.communicate()
                if proc.returncode == 0:
                    output = stdout
            except (OSError), e:
                pass

        # Now, how about filtering the results?
        filter_re = re.compile(filter, re.M)
        results = filter_re.findall(output)

        # Does the caller want each line split into N parts?
        if ncol:
            results = [(parts + [''] * (ncol - len(parts))) for parts in [ i.split(None, ncol-1) for i in results ]]

        # return results
        return results

    def get_cluster_status(self):
        """ Basic data on a cluster. Same data as running a 'hastatus -sum'
        This function is used to populate self.status at initialization time.
        Data returned is a dict of dicts, with cluster members as first keys
          server1:
            frozen - False | True
            state  - 'RUNNNING' | ...
            servicegrp1:
              autodisabled - False | True
              probed - True | False
              state  - ONLINE | OFFLINE | ...
            servicegrp2:
              ...
          server2:
            ...
        """
        status = {}
        groups = {}
        for line in self.run("/opt/VRTS/bin/hastatus -sum", filter='^\w.*'):
            parts = line.split()
            # 'A' lines are the systems. Output fields are: "A" System State Frozen
            if parts[0] == 'A':
                status[parts[1]] = {'state': parts[2], 'frozen': parts[3] != '0'}
            # 'B' lines are the group states. Output fields are: "B" Group System Probed AutoDisabled State
            elif parts[0] == 'B':
                #status[parts[2]]['groups'].append({'name': parts[1], 'probed': parts[3] == 'Y', 'autodisabled': parts[4] == 'Y', 'state': parts[5]})
                status[parts[2]][parts[1]] = {'probed': parts[3] == 'Y', 'autodisabled': parts[4] == 'Y', 'state': parts[5]}
                groups[parts[1]] = ''
        # update the group list. easier this way
        self.groups = groups.keys()
        return status

    def resource_list(self, group=''):
        """ Get a list of the resources defined on a cluster.
        Optionally pass a specific group and only see resources for that group.
        Results is a list of [Resource System]
        """
        # hares -list Group=myS1oraSG
        cmd = '/opt/VRTS/bin/hares -list'
        if group:
            cmd += ' Group=%s' % group
        return self.run(cmd, filter='^\w.*', ncol=2)

    def resource_display(self, res='', system=''):
        """ Get a detailed list of attributes on resource(s)
        Specifying 'res' will filter the results as well as 'system' (note: 'global' system is included)
        Results is a list of [Resource Attribute System Value]
        """
        results = self.run('/opt/VRTS/bin/hares -display', filter='^[^#].*', ncol=4)
        if res:
            results = filter(lambda x: x[0] == res, results)
        if system:
            results = filter(lambda x: x[2] in [system, 'global'], results)
        return results

    def group_list(self):
        """ Get a list of groups and associated systems.
        If a group is defined to run on two systems, you will see the group twice with both systems.
        Results is a list of [ServiceGroup System]
        """
        cmd = '/opt/VRTS/bin/hagrp -list'
        return self.run(cmd, filter='^\w.*', ncol=2)
    
    def group_display(self, group='', system=''):
        """ Get a list of group attributes. Optionally limited to a single group.
        Specifying 'system' will filter the results. (note: 'global' system is included)
        Results is a list of [Group Attribute System Value]
        """
        cmd = '/opt/VRTS/bin/hagrp -display %s' % group # If blank, will be just all groups
        results = self.run(cmd, filter='^[^#].*', ncol=4)
        if system:
            results = filter(lambda x: x[2] in [system, 'global'], results)
        return results

if __name__ == '__main__':

    """
    Possible future commands to support:
      hagrp -dep myS1oraSG  # lists dependencies between SGs
    """

    import sys

    # ./vcs.py delta "uname -a"
    print '\n'.join(remote_command(sys.argv[1], sys.argv[2], filter=sys.argv[3]))
    sys.exit(0)

    print '\n'.join(fdisk_list())

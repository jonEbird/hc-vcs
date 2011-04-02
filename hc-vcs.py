#!/usr/bin/env python

import hcvcs, time, os

"""
Health Check script:
1. Dump / report cluster configuration data.
   a. How many nodes do you need to start the cluster? (/etc/gabtab)
   b. How is LLT configured? (lltconfig -T query)
   c. What are the members of the cluster and their status?
   d. Is the cluster in jeopardy?
   e. Is the cluster config open or closed? (haclus -display | grep ReadOnly)
   f. When was the last edit done on the cluster? (haclus -display | grep ClusterTime # is a epoch value)
   g. What users are enabled to log into the cluster?
2. Query service groups and check:
   a. Are all members, in the cluster, valid targets for a SG?
   b. Do you have all of the proper attributes set? (SG values)
   c. Are all resouces in the SG marked critical?
   d. Are there unlinked resources in the SG in terms of dependencies? (graph theory here)
3. Specific resource validations
   a. Does your Mount resource's MountPoint value exist on all failover nodes? (or do you have CreateMntPt == 1?)
   b. Does the NIC resource have 'bond0' as the 'Device'?

   On group attributes:
        E.g. Need to have 'ManageFaults' set to 'ALL': myS1oraSG ManageFaults global NONE
             To fix: hagrp -modify myS1oraSG ManageFaults ALL
             AutoStart := 1
             AutoStartList := charlie delta # all members?
             AutoFailOver := 1
"""

#--------------------------------------------------
# Service Group Attributes
#--------------------------------------------------
# Standard / expected attributes to be set for a failover service group
failover_group_attr = {
     'ManageFaults': 'ALL',
     'AutoStart': '1',
     'AutoFailOver': '1',
     'OnlineRetryLimit': '0',
     'AutoStartPolicy': 'Order',
     'FailOverPolicy': 'Priority', # 'RoundRobin'
     'ClusterFailOverPolicy': 'Manual',
     }
# 'ClusterList', '' # if non-empty, list of clusters for which this group is a global failover
# 'FaultPropagation', '1' # should fail resources
# 'NumRetries', '0' # useful number to know if you are using OnlineRetryLimit

# Standard / expected attributes to be set for a parallel service group
parallel_group_attr = failover_group_attr.copy() # Most are the same as failover groups
parallel_group_attr['AutoFailOver'] = '0' # Set to False for parallel groups

#--------------------------------------------------
# Resource Attributes
#--------------------------------------------------
# Standard / expected attributes for a resource
std_resource_attr = {
     'Probed': '1',
     'Enabled': '1',
     'Critical': '1',
     }

#--------------------------------------------------
# General Cluster Attributes
#--------------------------------------------------
# Standard / expected cluster attributes
std_cluser_attr = {
     'BackupInterval': '3',
     'Administrators': 'admin',
     'Guests': '',
     'Operators': '',
     }

def health_check(system=''):
     """ Perform a health check on the cluster.
     """
     if not system:
          system = os.uname()[1]

     print 'Checking system: %s' % (system)
     c = hcvcs.VCS(server=system)
     if not c.status:
          print '  Error: Problem communicating with cluster. Moving on.'
          return

     # 0. Status information
     t1 = time.localtime(int(c.info['ClusterTime']))
     print '  Cluster "%s" was last updated %s (%s)' % (c.info['ClusterName'], time.strftime('%F %T', t1), c.info['ClusterTime'])
     # VCSFeatures == 'NONE' means non-global. WACPort is the port which a global cluster connect to.
     print '  VCSFeatures: %s, WACPort: %s' % (c.info['VCSFeatures'], c.info['WACPort'])

     # 1. General cluster status health
     c_info = c.status[system]
     if c.info['ReadOnly'] != '1':
          print '  Warn: Cluster is Writable. (haconf -dump -makero)'
     if c_info['frozen']:
          print '  Warn: system %s is frozen.' % system
     if c_info['state'] != 'RUNNING':
          print '  Warn: system %s state is "%s".' % (system, c_info['state'])

     attr_list = std_cluser_attr
     for k, v in attr_list.iteritems():
               if c.info[k] != v:
                    print '  Warn: Expecting cluster "%s" value "%s" to be "%s": Currently "%s".' % (system, k, v, c.info[k])
                    
     # 2. Service group health
     for group in c.groups:
          g_state = c_info[group]
          #print '  Checking group: %s - "%s" on "%s"' % (group, g_state['state'], system)
          if not g_state['probed']:
               print '    Warn: group "%s" is not probed on system "%s".' % (group, system)
          if g_state['autodisabled']:
               print '    Warn: group "%s" is currently autodisabled.' % (group)
               
          g_list = c.group_display(group) #, c.group_display(group, system)

          g_info = hcvcs.quad2dict(g_list)
          # Check values that should be set. Some attributes are different for parallel vs. failover groups.
          if g_info.get('Parallel', '0') == '1':
               attr_list = parallel_group_attr
          else:
               attr_list = failover_group_attr
          for k, v in attr_list.iteritems():
               try:
                    if g_info[k] != v:
                         print '    Warn: Expecting group %s "%s" to be "%s": Currently "%s".' % (group, k, v, g_info[k])
               except (KeyError), e:
                    pass

          # Is the group configured to run on all systems?
          syslist = g_info.get('SystemList', '').split('\t')
          group_nodes   = set([ syslist[i] for i in range(len(syslist)) if not i % 2 ])
          cluster_nodes = set(c.status.keys())
          group_nodes_off = cluster_nodes.difference(group_nodes)
          if group_nodes_off:
               print '    Warn: group %s is not configured to run on cluster nodes: %s' % (group, ', '.join(group_nodes_off))
               
          # 3. Attributes on a group
          for resource in [ x[0] for x in c.resource_list(group) if x[1] == system ]:
               r_list = c.resource_display(resource, system)
               r_info = hcvcs.quad2dict(r_list)
               attr_list = std_resource_attr
               for k, v in attr_list.iteritems():
                    try:
                         if r_info[k] != v:
                              print '    Warn: Resource "%s", in group "%s", attr "%s" should be "%s": Currently "%s".' % (resource, group, k, v, r_info[k])
                    except (KeyError), e:
                         pass

if __name__ == '__main__':
     
     print 'Performing a health check on the local cluster.'
     health_check()

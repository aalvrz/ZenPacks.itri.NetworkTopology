import Globals
import sys, os
import logging
log = logging.getLogger('zen.NetworkTopology.lldp')

from pynetsnmp.SnmpSession import *
from pynetsnmp.netsnmp import *

# Error codes
ERR_DEVICE_TYPE_ERROR = 51101
ERR_SNMP_CONNECTION_FAILED = 51102
ERR_PARTIAL_SNMP_CONNECTION_FAILED = 51105

# OIDs
MIB_LLDP_REM_MAN_ADDR_IF_SUBTYPE = '.1.0.8802.1.1.2.1.4.2.1.3'
MIB_LLDP_REM_PORT_DESC = '.1.0.8802.1.1.2.1.4.1.1.8'
MIB_LLDP_REM_SYS_DESC = '.1.0.8802.1.1.2.1.4.1.1.10'
MIB_RFC1213_SYS_DESC = '.1.3.6.1.2.1.1.1'


class Link():
    """Class to represent links between a local and remote devices."""

    def __init__(self, local_type='Unknown', local_ip='Unknown', 
                 local_port='Unknown', remote_type='Unknown', 
                 remote_ip='Unknown', remote_port='Unknown'):
        self.local_type = local_type
        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_type = remote_type
        self.remote_ip = remote_ip
        self.remote_port = remote_port

    def __repr__(self):
        return '{0}\t{1}\t{2}\t{3}\t{4}\t{5}'.format(self.local_type, self.local_ip, 
            self.local_port, self.remote_type, self.remote_ip, self.remote_port)

class LLDPSession(SnmpSession):
    """A SNMP Session to gather switch network topology information."""

    def get_remote_ip_and_local_port(self):
        """ Returns a list of tuples. Each tuple consists of a local port and a remote mgmIP."""
        ret = []

        remManAddrTable = self._walk(MIB_LLDP_REM_MAN_ADDR_IF_SUBTYPE)
        
        for address in remManAddrTable:
            ip = ''
            for key in address.keys()[0][16:20]:
                ip = ip + '.' + str(key)
            ret.append((address.keys()[0][12], ip[1:]))
        
        return ret

    def get_remote_port_description(self):
        """ return a dictionary with an index of local port and a value of remote port """
        ret = {}

        remote_ports_table = self._walk(MIB_LLDP_REM_PORT_DESC)

        for i in remote_ports_table:
            port = i.values()[0].split(' ')
            if len(port) == 1:   # server
                ret[i.keys()[0][12]] = i.values()[0]
            else:                # switch
                for x in range(0, len(port)-1):
                    if port[x] == 'port' or port[x] == 'Port':
                        ret[i.keys()[0][12]] = 'port' + port[x+1]
        return ret

    def get_remote_device_type(self):
        """ return a dictionary with an index of local port and a value of remote device type """
        ret = {}

        remDeviceTable = self._walk(MIB_LLDP_REM_SYS_DESC)
        for device in remDeviceTable:
            type = device.values()[0].split(' ')
            if type[0] == 'Linux':
                ret[device.keys()[0][-2]] = 'Server'
            else:
                ret[device.keys()[0][-2]] = 'Switch'

        return ret

    def get_local_device_type(self):
        """ Returns the device type of this session."""
        snmp_result = self.get(MIB_RFC1213_SYS_DESC + '.0')
        device_type = snmp_result.values()[0].split(' ')

        if device_type[0] == 'Linux':
            return 'Server'

        return 'Switch'

    def _walk(self, root_oid):
        table_result = []
        
        current_tuple = self._getNext(root_oid)
        base_oid = tuple(map(int, (root_oid).strip('.').split('.')))
        
        while True:
            if current_tuple.keys()[0][:len(base_oid)] == base_oid:
                table_result.append(current_tuple)
                oid = ''
                
                for key in current_tuple.keys()[0]:
                    oid = oid + '.' + str(key)
                current_tuple = self._getNext(oid)
            else:
                break
                
        return table_result

    def _getNext(self, oid):
        self.session = netsnmp.Session(
            version = self._version,
            timeout = int(self.timeout*1e6),
             retries=int(self.retries-1),
            peername= '%s:%d' % (self.ip, self.port),
            community=self.community,
            community_len=len(self.community),
            cmdLineArgs=self.cmdLineArgs
            )

        oid = tuple(map(int, oid.strip('.').split('.')))
        self.session.open()
        try:
            return self._sgetnext([oid])
        finally:
            self.session.close()


    def _sgetnext(self, oids):
        req = self.session._create_request(SNMP_MSG_GETNEXT)

        for oid in oids:
            oid = mkoid(oid)
            lib.snmp_add_null_var(req, oid, len(oid))

        response = netsnmp_pdu_p()

        if lib.snmp_synch_response(self.session.sess, req, byref(response)) == 0:
            result = dict(getResult(response.contents))
            lib.snmp_free_pdu(response)
            return result

def get_switch_links(switch_ip):
    session = LLDPSession(switch_ip, timeout=1.5, port=161)
    session.community = 'public'
    
    try:
        if session.get_local_device_type() == 'Server':
            return ERR_DEVICE_TYPE_ERROR, [], [switch_ip]
    except AttributeError:
        log.error("Error: SNMP connection failed.")
        return ERR_SNMP_CONNECTION_FAILED, [], [switch_ip]
    except Exception as e:
        log.error("Unknown Error: {0}".format(e.message))
        return ERR_UNKNOWN_ERROR, [], [switch_ip]
        
    todo_switches = [switch_ip]
    processed_switches = []
    failed_switches = []

    links = []    
    for switch in todo_switches:
        if switch not in processed_switches:
            session = LLDPSession(switch, timeout=1.5, port=161)
            session.community = 'public'
        
            try:
                processed_switches.append(switch)
                
                remote_ips_table = session.get_remote_ip_and_local_port()                
                remote_ports_table = session.get_remote_port_description()
                remote_device_types = session.get_remote_device_type()
                
                for remote_ip in remote_ips_table:
                    link = Link(local_type='Switch', local_ip=switch, local_port=('port' + str(remote_ip[0])))
                    
                    # Assign the remote device's type to the link
                    if remote_device_types[remote_ip[0]]:
                        link.remote_type = remote_device_types[remote_ip[0]]
                        
                    link.remote_ip = remote_ip[1]
                    
                    if remote_ports_table[remote_ip[0]]:
                        link.remote_port = remote_ports_table[remote_ip[0]]
                        
                    links.append(link)
                    
                    if link.remote_type == 'Switch':
                        todo_switches.append(link.remote_ip)
            except Exception as e:
                log.error("Error obtaining switch links for {0}: {1}".format(switch_ip, e.message))
                failed_switches.append(switch)

    return links

if __name__ == '__main__':
    links = get_switch_links("100.67.0.21")
    for link in links:
        print link

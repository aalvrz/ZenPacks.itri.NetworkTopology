"""Models the network links for a switch device using LLDP."""

# Twisted imports
from twisted.internet.defer import inlineCallbacks, returnValue

# Zenoss imports
from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin

# ZenPack imports
from ZenPacks.itri.NetworkTopology import lldp

class NetworkLinks(PythonPlugin):
    relname = 'networkLinks'
    modname = 'ZenPacks.itri.NetworkTopology.NetworkLink'

    requiredProperties = ()

    deviceProperties = PythonPlugin.deviceProperties + requiredProperties
    
    @inlineCallbacks
    def collect(self, device, log):
        log.info('Collecting network link data for switch device {0}'.format(device.id))
        
        switch_links = yield lldp.get_switch_links(device.id)

        rm = self.relMap()
        
        for link in switch_links:
            rm.append(self.objectMap({
                'id': self.prepId(link.local_ip + '_' + link.local_port),
                'local_ip': link.local_ip,
                'local_type': link.local_type,
                'local_port': link.local_port,
                'remote_ip':  link.remote_ip,
                'remote_type': link.remote_type,
                'remote_port': link.remote_port,
                }))
        
        returnValue(rm)
    
    def process(self, device, results, log):
        log.info('Processing network link data for switch device {0}'.format(device.id))
        log.debug(results)
        return results

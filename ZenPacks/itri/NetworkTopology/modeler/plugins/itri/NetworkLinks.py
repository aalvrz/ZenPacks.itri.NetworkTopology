"""Models the network links for a switch device using LLDP."""

from twisted.internet.defer import inlineCallbacks, returnValue

from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin

from ZenPacks.itri.NetworkTopology.lib import lldp


class NetworkLinks(PythonPlugin):
    relname = 'networkLinks'
    modname = 'ZenPacks.itri.NetworkTopology.NetworkLink'

    requiredProperties = ()

    deviceProperties = PythonPlugin.deviceProperties + requiredProperties
    
    @inlineCallbacks
    def collect(self, device, log):
        log.info('Collecting network link data for switch device {0}'.format(
            device.id))

        try:
            switch_links = yield lldp.get_switch_links(device.id)
        except Exception as e:
            log.error('{0}: {1}'.format(device.id, e))

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
        log.info('Processing network link data for switch device {0}'.format(
            device.id))
        log.debug(results)
        
        return results

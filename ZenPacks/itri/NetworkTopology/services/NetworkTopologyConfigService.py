"""
NetworkTopologyConfigService
Zenhub service for providing configuration to the nmapper collector daemon.
"""

import logging
log = logging.getLogger('zen.nmapper')

import Globals
from Products.ZenUtils.Utils import unused
from Products.ZenCollector.services.config import CollectorConfigService

unused(Globals)

class NetworkTopologyConfigService(CollectorConfigService):
    """ Zenhub service for nmapper daemon."""
    
    def _filterDevice(self, device):
        filter = CollectorConfigService._filterDevice(self, device)
        
        has_flag = False
        if filter:
            try:
                if '/Network/Switch' in device.getDeviceClassName():
                    has_flag = True
            except Exception as e:
                log.error(e.message)
        
        return CollectorConfigService._filterDevice(self, device) and has_flag
        
    def _createDeviceProxy(self, device):
        proxy = CollectorConfigService._createDeviceProxy(self, device)
        
        proxy.configCycleInterval = 5 * 60
        proxy.datapoints = []
        
        perfServer = device.getPerformanceServer()
        
        return proxy
        
if __name__ == '__main__':
    from Products.ZenHub.ServiceTester import ServiceTester
    
    tester = ServiceTester(NetworkTopologyConfigService)
    
    def printer(config):
        print config.datapoints
    
    tester.printDeviceProxy = printer
    tester.showDeviceInfo()

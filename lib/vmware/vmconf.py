#!/usr/bin/env python

# TODO: Description
###

from __future__ import print_function

#__all__     = ['']
__author__  = 'aume'
__version__ = '0.5.0'


################################################################################
### Required Modules
################################################################################
import atexit
import ssl
import sys
import time

try:
    from pyVim.connect import SmartConnect, Disconnect
    from pyVmomi import vim
except Exception as e:
    print(e)
    sys.exit(-1)


################################################################################
### Error Codes
################################################################################


################################################################################
### Setup Logger
################################################################################


################################################################################
### External Functions - Connection
################################################################################
def Connect(protocol='https', host='localhost', port=443, user='root', password=''):
    ssl_context = None
    if hasattr(ssl, '_create_unverified_context'):
        ssl_context = ssl._create_unverified_context()
    try:
        si = SmartConnect(protocol=protocol, host=host, port=int(port), user=user, pwd=password, sslContext=ssl_context)
    except Exception as e:
        return None
    #
    if not si:
        return None
    #
    atexit.register(Disconnect, si)
    content = si.RetrieveContent()
    return content


def GetDatacenterList(content):
    dclist = []
    for datacenter in content.rootFolder.childEntity:
        dclist.append(datacenter.name)
    dclist.sort()
    return dclist


def GetDatacenter(content, name):
    for datacenter in content.rootFolder.childEntity:
        if datacenter.name == name:
            return datacenter
    return None


def GetHostList(content):
    hostlist = []
    for datacenter in content.rootFolder.childEntity:
        folders = [datacenter.hostFolder]
        while folders:
            folder = folders.pop(0)
            for node in folder.childEntity:
                if type(node) is vim.ComputeResource and type(node.host[0]) is vim.HostSystem:
                    hostlist.append(node.host[0].name)
                if type(node) is vim.Folder:
                    folders.append(node)
    hostlist.sort()
    return hostlist


def GetHost(content, name):
    for datacenter in content.rootFolder.childEntity:
        folders = [datacenter.hostFolder]
        while folders:
            folder = folders.pop(0)
            for node in folder.childEntity:
                if type(node) is vim.ComputeResource and type(node.host[0]) is vim.HostSystem:
                    if node.host[0].name == name:
                        return node.host[0]
                if type(node) is vim.Folder:
                    folders.append(node)
    return None


def GetDatastoreList(content):
    dslist = []
    for dcname in GetDatacenterList(content):
        for datastore in GetDatacenter(content, dcname).datastore:
            dslist.append(datastore.name)
    dslist.sort()
    return dslist


def GetDatastore(content=None, host=None, name=None):
    if content is not None and name is not None:
        for dcname in GetDatacenterList(content):
            for datastore in GetDatacenter(content, dcname).datastore:
                if datastore.name == name:
                    return datastore
    if host is not None and name is not None:
        for datastore in host.datastore:
            if datastore.name == name:
                return datastore
    return None


def GetNetworkList(content):
    nwlist = []
    for dcname in GetDatacenterList(content):
        for network in GetDatacenter(content, dcname).network:
            nwlist.append(network.name)
    nwlist.sort()
    return nwlist


def GetNetwork(content=None, host=None, name=None):
    if content is not None and name is not None:
        for dcname in GetDatacenterList(content):
            for network in GetDatacenter(content, dcname).network:
                if network.name == name:
                    return network
    if host is not None and name is not None:
        for network in host.network:
            if network.name == name:
                return network
    return None


def GetVmList(content):
    vmlist = []
    for datacenter in content.rootFolder.childEntity:
        folders = [datacenter.vmFolder]
        while folders:
            folder = folders.pop(0)
            for node in folder.childEntity:
                if type(node) is vim.VirtualMachine:
                    vmlist.append(node.name)
                if type(node) is vim.Folder:
                    folders.append(node)
    vmlist.sort()
    return vmlist


def GetVm(content, name):
    for datacenter in content.rootFolder.childEntity:
        folders = [datacenter.vmFolder]
        while folders:
            folder = folders.pop(0)
            for node in folder.childEntity:
                if type(node) is vim.VirtualMachine:
                    if node.name == name:
                        return node
                if type(node) is vim.Folder:
                    folders.append(node)
    return None


################################################################################
### External Functions - System
################################################################################
def GetEsxVersion(host):
    return host.config.product.version


def GetEsxBuildNumber(host):
    return host.config.product.build


################################################################################
### External Functions - Kernel Option
################################################################################
def GetKernelOption(host, name):
    for option in host.configManager.advancedOption.QueryOptions():
        if option.key == name:
            return {
                'key'   : option.key,
                'value' : option.value
            }
    return None


def UpdateKernelOption(host, name, value):
    option = GetKernelOption(host, name)
    if option is None:
        return None
    if option['value'] == value:
        return True
    #
    try:
        reconfigOption = vim.option.OptionValue()
        reconfigOption.key = name
        reconfigOption.value = value
        host.configManager.advancedOption.UpdateOptions([reconfigOption])
    except Exception as e:
        return False
    #
    return True


################################################################################
### External Functions - Kernel Module
################################################################################
def GetKernelModuleVersion(host, name):
    for module in host.configManager.imageConfigManager.FetchSoftwarePackages():
        if module.name == name:
            return module.version
    return None


def GetKernelModuleOption(host, name):
    for module in host.configManager.kernelModuleSystem.QueryModules():
        if module.name == name:
            return {
                'name'      : module.name,
                'enabled'   : module.enabled,
                'loaded'    : module.loaded,
                'version'   : module.version,
                'option'    : module.optionString
            }
    return None


def UpdateKernelModuleOption(host, name, value):
    module = GetKernelModuleOption(host, name)
    if module is None:
        return None
    if module['option'] == value:
        return True
    #
    try:
        host.configManager.kernelModuleSystem.UpdateModuleOptionString(name=name, options=value)
    except Exception as e:
        return False
    #
    return True


################################################################################
### External Functions - Power Policy
################################################################################
def GetPowerPolicyCapability(host):
    policies = []
    for policy in host.configManager.powerSystem.capability.availablePolicy:
        policies.append({
            'name'  : policy.shortName,
            'key'   : policy.key
        })
    policies.sort(key=lambda x: x['key'])
    return policies


def GetPowerPolicyConfig(host):
    policy = host.configManager.powerSystem.info.currentPolicy
    return {
        'name'  : policy.shortName,
        'key'   : policy.key
    }


def UpdatePowerPolicyConfig(host, name=None, key=None):
    policy = GetPowerPolicyConfig(host)
    if policy is None:
        return None
    if name is None and key is None:
        return False
    if policy['name'] == name or policy['key'] == key:
        return True
    #
    policies = GetPowerPolicyCapability(host)
    for policy in policies:
        if policy['name'] == name or policy['key'] == key:
            try:
                host.configManager.powerSystem.ConfigurePowerPolicy(key=policy['key'])
                return True
            except Exception as e:
                return False
    #
    return False


################################################################################
### External Functions - PCI Passthru
################################################################################
def GetPciPassthruList(host):
    devices = []
    for passthru in host.configManager.pciPassthruSystem.pciPassthruInfo:
        if type(passthru) is vim.host.PciPassthruInfo:
            if passthru.passthruCapable:
                devices.append(passthru.id.lower())
    devices.sort()
    return devices


def GetPciPassthruInfo(host, sbdf):
    for passthru in host.parent.environmentBrowser.QueryConfigTarget(host=host).pciPassthrough:
        if passthru.pciDevice.id.lower() == sbdf.lower():
            return {
                'systemId'      : passthru.systemId,
                'id'            : passthru.pciDevice.id.lower(),
                'vendorId'      : passthru.pciDevice.vendorId,
                'deviceId'      : passthru.pciDevice.deviceId,
                'subVendorId'   : passthru.pciDevice.subVendorId,
                'subDeviceId'   : passthru.pciDevice.subDeviceId,
                'vendorName'    : passthru.pciDevice.vendorName,
                'deviceName'    : passthru.pciDevice.deviceName
            }
    return None


def GetPciPassthruConfig(host, sbdf):
    for passthru in host.configManager.pciPassthruSystem.pciPassthruInfo:
        if type(passthru) is vim.host.PciPassthruInfo:
            if passthru.id.lower() == sbdf.lower():
                return passthru.passthruActive
    return None


def UpdatePciPassthruConfig(host, sbdf, value):
    config = GetPciPassthruConfig(host, sbdf)
    if config is None:
        return None
    if config == value:
        return True
    #
    try:
        reconfigDevice = vim.host.PciPassthruConfig()
        reconfigDevice.id = sbdf.lower()
        reconfigDevice.passthruEnabled = value
        host.configManager.pciPassthruSystem.UpdatePassthruConfig([reconfigDevice])
        host.configManager.pciPassthruSystem.Refresh()
    except Exception as e:
        return False
    #
    return True


################################################################################
### External Functions - SR-IOV
################################################################################
def GetPciSriovList(host):
    devices = []
    for sriov in host.configManager.pciPassthruSystem.pciPassthruInfo:
        if type(sriov) is vim.host.SriovInfo:
            if sriov.sriovCapable:
                devices.append(sriov.id.lower())
    devices.sort()
    return devices


def GetPciSriovInfo(host, sbdf):
    for sriov in host.parent.environmentBrowser.QueryConfigTarget(host=host).sriov:
        if sriov.pciDevice.id.lower() == sbdf.lower():
            return {
                'systemId'      : sriov.systemId,
                'id'            : sriov.pciDevice.id.lower(),
                'vendorId'      : sriov.pciDevice.vendorId,
                'deviceId'      : sriov.pciDevice.deviceId,
                'subVendorId'   : sriov.pciDevice.subVendorId,
                'subDeviceId'   : sriov.pciDevice.subDeviceId,
                'vendorName'    : sriov.pciDevice.vendorName,
                'deviceName'    : sriov.pciDevice.deviceName
            }
    return None


def GetPciSriovConfig(host, sbdf):
    for sriov in host.configManager.pciPassthruSystem.pciPassthruInfo:
        if type(sriov) is vim.host.SriovInfo:
            if sriov.id.lower() == sbdf.lower():
                return {
                    'enabled'   : sriov.sriovEnabled,
                    'numVfs'    : sriov.numVirtualFunction,
                    "numMaxVfs" : sriov.maxVirtualFunctionSupported
                }
    return None


def UpdatePciSriovConfig(host, sbdf, enable, numVfs):
    config = GetPciSriovConfig(host, sbdf)
    if config is None:
        return None
    if numVfs > config['numMaxVfs']:
        return False
    if enable == config['enabled'] and numVfs == config['numVfs']:
        return True
    #
    try:
        reconfigDevice = vim.host.SriovConfig()
        reconfigDevice.id = sbdf.lower()
        reconfigDevice.passthruEnabled = False
        reconfigDevice.sriovEnabled = enable
        reconfigDevice.numVirtualFunction = numVfs
        host.configManager.pciPassthruSystem.UpdatePassthruConfig([reconfigDevice])
        host.configManager.pciPassthruSystem.Refresh()
    except Exception as e:
        return False
    #
    return True


################################################################################
### External Functions - Network
################################################################################
def GetPhysicalNicList(host):
    nics = []
    for nic in host.configManager.networkSystem.networkInfo.pnic:
        nics.append(nic.device)
    nics.sort()
    return nics


def GetPhysicalNicInfo(host, name):
    for nic in host.configManager.networkSystem.networkInfo.pnic:
        if nic.device == name:
            return {
                'name'      : name,
                'link'      : nic.linkSpeed.speedMb if nic.linkSpeed is not None else None,
                'mac'       : nic.mac,
                'pci'       : nic.pci,
                'sbdf'      : nic.pci,
                'driver'    : nic.driver
            }
    return None


def GetVirtualSwitchList(host):
    switches = []
    for switch in host.configManager.networkSystem.networkInfo.vswitch:
        switches.append(switch.name)
    switches.sort()
    return switches


def GetVirtualSwitchConfig(host, name):
    for switch in host.configManager.networkSystem.networkInfo.vswitch:
        if switch.name == name:
            nics = [nic for nic in switch.spec.bridge.nicDevice]
            nics.sort()
            return {
                'name'      : switch.name,
                'pnics'     : nics,
                'mtu'       : switch.mtu
            }
    return None


def UpdateVirtualSwitchConfig(host, name, pnics=None, mtu=None):
    spec = None
    for switch in host.configManager.networkSystem.networkConfig.vswitch:
        if switch.name == name:
            spec = switch.spec
    if spec is None:
        return False
    #
    if pnics is not None:
        while len(spec.bridge.nicDevice):
            spec.bridge.nicDevice.pop()
        while len(spec.policy.nicTeaming.nicOrder.activeNic):
            spec.policy.nicTeaming.nicOrder.activeNic.pop()
        while len(spec.policy.nicTeaming.nicOrder.standbyNic):
            spec.policy.nicTeaming.nicOrder.standbyNic.pop()
        for nic in pnics:
            spec.bridge.nicDevice.append(nic)
            spec.policy.nicTeaming.nicOrder.activeNic.append(nic)
    if mtu is not None:
        spec.mtu = int(mtu)
    #
    try:
        host.configManager.networkSystem.UpdateVirtualSwitch(name, spec)
    except Exception as e:
        return False
    #
    return True


def CreateVirtualSwitch(host, name, pnics, mtu=None):
    if name in GetVirtualSwitchList(host):
        return False
    #
    spec = vim.host.VirtualSwitch.Specification()
    spec.numPorts = 128
    spec.bridge = vim.host.VirtualSwitch.BondBridge()
    for nic in pnics:
        spec.bridge.nicDevice.append(nic)
    spec.bridge.beacon = vim.host.VirtualSwitch.BeaconConfig()
    spec.bridge.beacon.interval = 1
    spec.bridge.linkDiscoveryProtocolConfig = vim.host.LinkDiscoveryProtocolConfig()
    spec.bridge.linkDiscoveryProtocolConfig.protocol = 'cdp'
    spec.bridge.linkDiscoveryProtocolConfig.operation = 'listen'
    if mtu is not None:
        spec.mtu = int(mtu)
    #
    try:
        host.configManager.networkSystem.AddVirtualSwitch(name, spec)
    except Exception as e:
        return False
    #
    return True


def DeleteVirtualSwitch(host, name):
    if name not in GetVirtualSwitchList(host):
        return False
    #
    try:
        host.configManager.networkSystem.RemoveVirtualSwitch(name)
    except Exception as e:
        return False
    #
    return True


def GetPortGroupList(host):
    portgroups = []
    for portgroup in host.configManager.networkSystem.networkInfo.portgroup:
        portgroups.append(portgroup.spec.name)
    portgroups.sort()
    return portgroups


def GetPortGroupConfig(host, name):
    for portgroup in host.configManager.networkSystem.networkInfo.portgroup:
        if portgroup.spec.name == name:
            return {
                'name'      : portgroup.spec.name,
                'vswitch'   : portgroup.spec.vswitchName,
                'vlan'      : portgroup.spec.vlanId
            }
    return None


def UpdatePortGroupConfig(host, name, vswitch=None, vlan=None, pnics=None):
    spec = None
    for portgroup in host.configManager.networkSystem.networkConfig.portgroup:
        if portgroup.spec.name == name:
            spec = portgroup.spec
    if spec is None:
        return False
    #
    if vswitch is not None:
        spec.vswitchName = vswitch
    if vlan is not None:
        spec.vlanId = int(vlan)
    if pnics is not None:
        while len(spec.policy.nicTeaming.nicOrder.activeNic):
            spec.policy.nicTeaming.nicOrder.activeNic.pop()
        while len(spec.policy.nicTeaming.nicOrder.standbyNic):
            spec.policy.nicTeaming.nicOrder.standbyNic.pop()
        for nic in pnics:
            spec.policy.nicTeaming.nicOrder.activeNic.append(nic)
    #
    try:
        host.configManager.networkSystem.UpdatePortGroup(name, spec)
    except Exception as e:
        return False
    #
    return True


def CreatePortGroup(host, name, vswitch, vlan=0):
    if name in GetPortGroupList(host):
        return False
    #
    spec = vim.host.PortGroup.Specification()
    spec.name = name
    spec.vlanId = vlan
    spec.vswitchName = vswitch
    spec.policy = vim.host.NetworkPolicy()
    spec.policy.security = vim.host.NetworkPolicy.SecurityPolicy()
    spec.policy.nicTeaming = vim.host.NetworkPolicy.NicTeamingPolicy()
    spec.policy.nicTeaming.failureCriteria = vim.host.NetworkPolicy.NicFailureCriteria()
    spec.policy.offloadPolicy = vim.host.NetOffloadCapabilities()
    spec.policy.shapingPolicy = vim.host.NetworkPolicy.TrafficShapingPolicy()
    #
    try:
        host.configManager.networkSystem.AddPortGroup(spec)
    except Exception as e:
        return False
    #
    return True


def DeletePortGroup(host, name):
    if name not in GetPortGroupList(host):
        return False
    #
    try:
        host.configManager.networkSystem.RemovePortGroup(name)
    except Exception as e:
        return False
    #
    return True


################################################################################
### External Functions - Storage
################################################################################
def GetHostBusAdapterList(host):
    hbas = []
    for hba in host.configManager.storageSystem.storageDeviceInfo.hostBusAdapter:
        hbas.append(hba.device)
    hbas.sort()
    return hbas


def GetHostBusAdapterInfo(host, name):
    for hba in host.configManager.storageSystem.storageDeviceInfo.hostBusAdapter:
        if hba.device == name:
            return {
                'device'    : hba.device,
                'status'    : hba.status,
                'speed'     : hba.speed                             if hasattr(hba, 'speed')                else None,
                'wwn'       : format(hba.portWorldWideName, '016x') if hasattr(hba, 'portWorldWideName')    else None,
                'pci'       : hba.pci                               if hasattr(hba, 'pci')                  else None,
                'driver'    : hba.driver                            if hasattr(hba, 'driver')               else None
            }
    return None


def GetPhysicalDiskList(host, mode='naa'):
    disks = []
    for disk in host.configManager.storageSystem.storageDeviceInfo.scsiLun:
        if disk.deviceType == 'disk':
            if mode == 'naa':
                disks.append(disk.canonicalName)
            elif mode == 'uuid':
                disks.append(disk.uuid)
            elif mode == 'vml':
                disks.append('vml.' + disk.uuid)
            elif mode == 'both':
                disks.append(disk.canonicalName + ' : vml.' + disk.uuid)
            else:
                disks.append(disk.canonicalName)
    disks.sort()
    return disks


def GetPhysicalDiskInfo(host, naa=None, uuid=None):
    for disk in host.configManager.storageSystem.storageDeviceInfo.scsiLun:
        if (naa == disk.canonicalName) or (uuid == disk.uuid):
            return {
                'name'      : disk.displayName,
                'device'    : disk.deviceName,
                'naa'       : disk.canonicalName,
                'uuid'      : disk.uuid
            }
    return None


def GetHostDatastoreList(host):
    datastores = []
    for datastore in host.configManager.datastoreSystem.datastore:
        datastores.append(datastore.info.name)
    datastores.sort()
    return datastores


def GetHostDatastoreInfo(host, name):
    for datastore in host.configManager.datastoreSystem.datastore:
        if datastore.info.name == name:
            return {
                'name'      : datastore.info.vmfs.name,
                'version'   : datastore.info.vmfs.majorVersion,
                'capacity'  : datastore.info.vmfs.capacity,
                'blockSize' : datastore.info.vmfs.blockSize,
                'disk'      : datastore.info.vmfs.extent[0].diskName
            }
    return None


################################################################################
### External Functions - Other Device
################################################################################
def GetPhysicalCdromList(host):
    cdroms = []
    for lun in host.config.storageDevice.scsiLun:
        if lun.deviceType == 'cdrom':
            cdroms.append(lun.deviceName)
    #cdroms.sort()
    return cdroms


################################################################################
### External Functions - Virtual Machine
################################################################################
def GetVirtualMachineInfo(vm):
    vscsis = []
    for vscsi in GetVirtualScsiList(vm):
        vscsis.append(GetVirtualScsiInfo(vm, vscsi))
    vdisks = []
    for vdisk in GetVirtualDiskList(vm):
        vdisks.append(GetVirtualDiskInfo(vm, vdisk))
    vnics = []
    for vnic in GetVirtualNicList(vm):
        vnics.append(GetVirtualNicInfo(vm, vnic))
    passthrus = []
    for passthru in GetVirtualPciPassthruList(vm):
        passthrus.append(GetVirtualPciPassthruInfo(vm, passthru))
    cdrom = True if GetVirtualCdRom(vm) is not None else False
    return {
        'name'                          : vm.config.name,
        'version'                       : vm.config.version,
        'firmware'                      : vm.config.firmware,
        'secureBoot'                    : vm.config.bootOptions.efiSecureBootEnabled,
        'datastore'                     : vm.datastore[0].name,
        'guestId'                       : vm.config.guestId,
        'numCpus'                       : vm.config.hardware.numCPU,
        'numCoresPerSocket'             : vm.config.hardware.numCoresPerSocket,
        'cpuAffinity'                   : vm.config.cpuAffinity.affinitySet if vm.config.cpuAffinity is not None else None,
        'cpuReservation'                : vm.config.cpuAllocation.reservation,
        'memoryMB'                      : vm.config.hardware.memoryMB,
        'memoryAffinity'                : vm.config.memoryAffinity.affinitySet if vm.config.memoryAffinity is not None else None,
        'memoryReservation'             : vm.config.memoryAllocation.reservation,
        'latencySensitivity'            : vm.config.latencySensitivity.level,
        'vscsis'                        : vscsis,
        'vdisks'                        : vdisks,
        'vnics'                         : vnics,
        'passthrus'                     : passthrus,
        'cdrom'                         : cdrom,
        'latency.enforceCpuMin'         : GetVirtualMachineOption(vm, 'latency.enforceCpuMin'),
        'numa.nodeAffinity'             : GetVirtualMachineOption(vm, 'numa.nodeAffinity'),
        'numa.autosize'                 : GetVirtualMachineOption(vm, 'numa.autosize'),
        'numa.vcpu.maxPerMachineNode'   : GetVirtualMachineOption(vm, 'numa.vcpu.maxPerMachineNode'),
        'numa.vcpu.maxPerVirtualNode'   : GetVirtualMachineOption(vm, 'numa.vcpu.maxPerVirtualNode')
    }


def GetVirtualMachineOption(vm, name):
    for config in vm.config.extraConfig:
        if config.key == name:
            return config.value
    return None


def GetVirtualScsiList(vm):
    scsis = []
    for device in vm.config.hardware.device:
        if type(device) in [vim.vm.device.ParaVirtualSCSIController, vim.vm.device.VirtualLsiLogicSASController]:
            scsis.append(device.deviceInfo.label)
    scsis.sort()
    return scsis


def GetVirtualScsiInfo(vm, name):
    for device in vm.config.hardware.device:
        if type(device) in [vim.vm.device.ParaVirtualSCSIController, vim.vm.device.VirtualLsiLogicSASController]:
            if device.deviceInfo.label == name:
                scsiType = 'Unknown'
                if type(device) is vim.vm.device.ParaVirtualSCSIController:
                    scsiType = 'PVSCSI'
                if type(device) is vim.vm.device.VirtualLsiLogicSASController:
                    scsiType = 'LSI'
                #
                return {
                    'name'      : device.deviceInfo.label,
                    'type'      : scsiType,
                    'key'       : device.key,
                    'controller': device.controllerKey,
                    'slot'      : device.slotInfo.pciSlotNumber if device.slotInfo is not None else None,
                    'sharing'   : device.sharedBus
                }
    return None


def GetVirtualDiskList(vm):
    disks = []
    for device in vm.config.hardware.device:
        if type(device) is vim.vm.device.VirtualDisk:
            disks.append((device.deviceInfo.label, device.controllerKey, device.key))
    disks.sort(key=lambda x: x[1])
    disks.sort(key=lambda x: x[2])
    return map(lambda x: x[0], disks)


def GetVirtualDiskInfo(vm, name):
    for device in vm.config.hardware.device:
        if type(device) is vim.vm.device.VirtualDisk:
            if device.deviceInfo.label == name:
                diskType = 'Unknown'
                diskUuid = None
                diskNaa = None
                if type(device.backing) is vim.vm.device.VirtualDisk.RawDiskMappingVer1BackingInfo:
                    diskType = 'rdm'
                    diskUuid = device.backing.lunUuid
                    host = vm.resourcePool.owner.host[0]
                    diskInfo = GetPhysicalDiskInfo(host, uuid=diskUuid)
                    if diskInfo is not None:
                        diskNaa = diskInfo['naa']
                if type(device.backing) is vim.vm.device.VirtualDisk.FlatVer2BackingInfo:
                    if device.backing.thinProvisioned:
                        diskType = 'thin'
                    else:
                        if device.backing.eagerlyScrub:
                            diskType = 'thick_eager0'
                        else:
                            diskType = 'thick_lazy0'
                #
                return {
                    'name'      : device.deviceInfo.label,
                    'file'      : device.backing.fileName,
                    'type'      : diskType,
                    'key'       : device.key,
                    'controller': device.controllerKey,
                    'size'      : device.capacityInBytes,
                    'sizeGB'    : device.capacityInBytes // 1024 // 1024 // 1024,
                    'uuid'      : diskUuid,
                    'naa'       : diskNaa,
                    'mode'      : device.backing.diskMode,
                    'sharing'   : device.backing.sharing
                }
    return None


def GetVirtualNicList(vm):
    nics = []
    for device in vm.config.hardware.device:
        if type(device) in [vim.vm.device.VirtualVmxnet3, vim.vm.device.VirtualE1000e, vim.vm.device.VirtualSriovEthernetCard]:
            nics.append(device.deviceInfo.label)
    nics.sort()
    return nics


def GetVirtualNicInfo(vm, name):
    for device in vm.config.hardware.device:
        if type(device) in [vim.vm.device.VirtualVmxnet3, vim.vm.device.VirtualE1000e, vim.vm.device.VirtualSriovEthernetCard]:
            if device.deviceInfo.label == name:
                nicType = 'Unknown'
                if type(device) is vim.vm.device.VirtualVmxnet3:
                    nicType = 'vmxnet3'
                if type(device) is vim.vm.device.VirtualE1000e:
                    nicType = 'e1000e'
                if type(device) is vim.vm.device.VirtualSriovEthernetCard:
                    nicType = 'sriov'
                return {
                    'name'      : device.deviceInfo.label,
                    'type'      : nicType,
                    'key'       : device.key,
                    'controller': device.controllerKey,
                    'slot'      : device.slotInfo.pciSlotNumber if device.slotInfo is not None else None,
                    'mac'       : device.macAddress,
                    'portgroup' : device.backing.deviceName,
                    'pfId'      : device.sriovBacking.physicalFunctionBacking.id if type(device) is vim.vm.device.VirtualSriovEthernetCard else None,
                    'sbdf'      : device.sriovBacking.physicalFunctionBacking.id if type(device) is vim.vm.device.VirtualSriovEthernetCard else None,
                    'pf'        : device.sriovBacking.physicalFunctionBacking.id if type(device) is vim.vm.device.VirtualSriovEthernetCard else None,
                    'id'        : device.sriovBacking.virtualFunctionBacking.id  if type(device) is vim.vm.device.VirtualSriovEthernetCard and device.sriovBacking.virtualFunctionBacking is not None else None,
                    'vf'        : device.sriovBacking.virtualFunctionBacking.id  if type(device) is vim.vm.device.VirtualSriovEthernetCard and device.sriovBacking.virtualFunctionBacking is not None else None
                }
    return None


def GetVirtualPciPassthruList(vm):
    passthru = []
    for device in vm.config.hardware.device:
        if type(device) is vim.vm.device.VirtualPCIPassthrough:
            passthru.append(device.deviceInfo.label)
    passthru.sort()
    return passthru


def GetVirtualPciPassthruInfo(vm, name):
    for device in vm.config.hardware.device:
        if type(device) is vim.vm.device.VirtualPCIPassthrough:
            if device.deviceInfo.label == name:
                return {
                    'name'      : device.deviceInfo.label,
                    'type'      : 'passthru',
                    'key'       : device.key,
                    'controller': device.controllerKey,
                    'slot'      : device.slotInfo.pciSlotNumber if device.slotInfo is not None else None,
                    'id'        : device.backing.id,
                    'sbdf'      : device.backing.id
                }
    return None


def GetVirtualCdRom(vm):
    for device in vm.config.hardware.device:
        if type(device) is vim.vm.device.VirtualCdrom:
            return {
                'name'      : device.deviceInfo.label,
                'type'      : 'cdrom',
                'key'       : device.key,
                'controller': device.controllerKey
            }
    return None


VM_GUEST_SUPPORTED  = ['rhel7_64Guest', 'rhel8_64Guest', 'rhel9_64Guest', 'windows2019srv_64Guest']
VM_GUEST_WINDOWS    = [                                                   'windows2019srv_64Guest']
VM_FIRMWARE_EFI     = [                 'rhel8_64Guest', 'rhel9_64Guest', 'windows2019srv_64Guest']
def CreateVirtualMachineSpec(host, name, datastore, guestId, version=None, firmware=None, secureBoot=None, numCpus=1, numCoresPerSocket=1, memoryMB=2048, cdrom=True, scsis=[{'type': None, 'sharing': None, 'slot': None}], disks=[{'size': 16, 'type': 'thick_lazy0', 'scsi': 0, 'sharing': None}], nics=[{'type': None, 'portgroup': 'VM Network', 'slot': None}]):
    if datastore not in GetHostDatastoreList(host):
        return None
    if guestId not in VM_GUEST_SUPPORTED:
        return None
    #
    spec = vim.vm.ConfigSpec()
    spec.name = name
    if version is not None:
        spec.version = 'vmx-' + str(version)
    spec.guestId = guestId
    #
    spec.numCPUs = numCpus
    spec.numCoresPerSocket = numCoresPerSocket
    #
    spec.memoryMB = memoryMB
    #
    spec.files = vim.vm.FileInfo()
    spec.files.vmPathName = '[' + datastore + ']'
    #
    spec.powerOpInfo = vim.vm.DefaultPowerOpInfo()
    spec.powerOpInfo.suspendType = 'soft'
    #
    spec.extraConfig = []
    if firmware == 'efi' or (firmware != 'bios' and guestId in VM_FIRMWARE_EFI):
        spec.firmware = 'efi'
        spec.extraConfig.append(vim.option.OptionValue(key='firmware', value='efi'))
    spec.extraConfig.append(vim.option.OptionValue(key='RemoteDisplay.maxConnections', value='-1'))
    spec.extraConfig.append(vim.option.OptionValue(key='vmware.tools.internalversion', value='0'))
    spec.extraConfig.append(vim.option.OptionValue(key='sched.cpu.latencySensitivity', value='normal'))
    #
    spec.bootOptions = vim.vm.BootOptions()
    spec.bootOptions.bootRetryDelay = 10
    if secureBoot is not None:
        spec.bootOptions.efiSecureBootEnabled = secureBoot
    elif firmware == 'efi' or (firmware != 'bios' and guestId in VM_FIRMWARE_EFI):
        spec.bootOptions.efiSecureBootEnabled = True
    #
    spec.maxMksConnections = -1
    #
    spec.deviceChange = []
    #
    videoSpec = vim.vm.device.VirtualDeviceSpec()
    videoSpec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    videoSpec.device = vim.vm.device.VirtualVideoCard()
    videoSpec.device.key = 500
    videoSpec.device.useAutoDetect = True
    spec.deviceChange.append(videoSpec)
    #
    usbSpec = vim.vm.device.VirtualDeviceSpec()
    usbSpec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    if guestId in VM_GUEST_WINDOWS:
        usbSpec.device = vim.vm.device.VirtualUSBXHCIController()
        usbSpec.device.key = 14000
        usbSpec.device.controllerKey = 100
        usbSpec.device.unitNumber = 23
        usbSpec.device.busNumber = 0
        usbSpec.device.autoConnectDevices = False
    else:
        usbSpec.device = vim.vm.device.VirtualUSBController()
        usbSpec.device.key = 7000
        usbSpec.device.controllerKey = 100
        usbSpec.device.unitNumber = 22
        usbSpec.device.busNumber = 0
        usbSpec.device.autoConnectDevices = False
    spec.deviceChange.append(usbSpec)
    #
    if scsis is not None:
        index = 0
        for scsi in scsis:
            if index >= 4:
                continue
            scsiSpec = vim.vm.device.VirtualDeviceSpec()
            scsiSpec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
            if scsi['type'] == 'PVSCSI':
                scsiSpec.device = vim.vm.device.ParaVirtualSCSIController()
            elif scsi['type'] == 'LSI':
                scsiSpec.device = vim.vm.device.VirtualLsiLogicSASController()
            elif guestId in VM_GUEST_WINDOWS:
                scsiSpec.device = vim.vm.device.VirtualLsiLogicSASController()
            else:
                scsiSpec.device = vim.vm.device.ParaVirtualSCSIController()
            scsiSpec.device.key = 1000 + index
            if scsi['slot'] is not None:
                scsiSpec.device.slotInfo = vim.vm.device.VirtualDevice.PciBusSlotInfo()
                scsiSpec.device.slotInfo.pciSlotNumber = int(scsi['slot'])
            scsiSpec.device.controllerKey = 100
            scsiSpec.device.unitNumber = 3 + index
            scsiSpec.device.busNumber = 0 + index
            if scsi['sharing'] == 'physicalSharing':
                scsiSpec.device.sharedBus = 'physicalSharing'
            else:
                scsiSpec.device.sharedBus = 'noSharing'
            scsiSpec.device.scsiCtlrUnitNumber = 7
            spec.deviceChange.append(scsiSpec)
            index = index + 1
    #
    ahciSpec = vim.vm.device.VirtualDeviceSpec()
    ahciSpec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    ahciSpec.device = vim.vm.device.VirtualAHCIController()
    ahciSpec.device.key = 15000
    ahciSpec.device.controllerKey = 100
    ahciSpec.device.unitNumber = 24
    ahciSpec.device.busNumber = 0
    spec.deviceChange.append(ahciSpec)
    #
    if cdrom is not None:
        phyCdroms = GetPhysicalCdromList(host)
        cdromSpec = vim.vm.device.VirtualDeviceSpec()
        cdromSpec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        cdromSpec.device = vim.vm.device.VirtualCdrom()
        cdromSpec.device.key = 16000
        cdromSpec.device.controllerKey = 15000
        cdromSpec.device.unitNumber = 0
        cdromSpec.device.backing = vim.vm.device.VirtualCdrom.AtapiBackingInfo()
        if len(phyCdroms) > 0:
            cdromSpec.device.backing.deviceName = phyCdroms[0]
            cdromSpec.device.backing.useAutoDetect = False
        else:
            cdromSpec.device.backing.deviceName = ''
            cdromSpec.device.backing.useAutoDetect = True
        cdromSpec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        cdromSpec.device.connectable.allowGuestControl = True
        spec.deviceChange.append(cdromSpec)
    #
    if disks is not None:
        indexes = {'0': 0, '1': 0, '2': 0, '3': 0}
        for disk in disks:
            if int(disk['scsi']) >= 4 or indexes[str(disk['scsi'])] >= 33:
                continue
            index = indexes[str(disk['scsi'])]
            diskSpec = vim.vm.device.VirtualDeviceSpec()
            diskSpec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
            diskSpec.fileOperation = 'create'
            diskSpec.device = vim.vm.device.VirtualDisk()
            if (index < 16):
                diskSpec.device.key = 2000 + index + 16 * int(disk['scsi'])
            else:
                diskSpec.device.key = 131088 + (index - 16) + 256 * int(disk['scsi'])
            if disk['type'] == 'rdm':
                lunInfo = GetPhysicalDiskInfo(host, naa=disk['naa'])
                if lunInfo is None:
                    continue
                diskSpec.device.backing = vim.vm.device.VirtualDisk.RawDiskMappingVer1BackingInfo()
                diskSpec.device.backing.datastore = GetDatastore(host=host, name=datastore)
                diskSpec.device.backing.lunUuid = lunInfo['uuid']
                diskSpec.device.backing.deviceName = lunInfo['device']
                diskSpec.device.backing.compatibilityMode = 'physicalMode'
                diskSpec.device.backing.diskMode = 'independent_persistent'
                if disk['sharing'] == 'sharingMultiWriter':
                    diskSpec.device.backing.sharing = 'sharingMultiWriter'
                else:
                    diskSpec.device.backing.sharing = 'sharingNone'
            else:
                diskSpec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
                diskSpec.device.backing.datastore = GetDatastore(host=host, name=datastore)
                diskSpec.device.backing.diskMode = 'persistent'
                if disk['type'] == 'thin':
                    diskSpec.device.backing.thinProvisioned = True
                    diskSpec.device.backing.eagerlyScrub = False
                elif disk['type'] == 'thick_lazy0':
                    diskSpec.device.backing.thinProvisioned = False
                    diskSpec.device.backing.eagerlyScrub = False
                elif disk['type'] == 'thick_eager0':
                    diskSpec.device.backing.thinProvisioned = False
                    diskSpec.device.backing.eagerlyScrub = True
                diskSpec.device.capacityInKB = int(disk['size']) * 1024 * 1024
            diskSpec.device.controllerKey = 1000 + int(disk['scsi'])
            diskSpec.device.unitNumber = 0 + index
            spec.deviceChange.append(diskSpec)
            if (index + 1) == 7:
                indexes[str(disk['scsi'])] = index + 2
            else:
                indexes[str(disk['scsi'])] = index + 1
    #
    if nics is not None:
        index = 0
        for nic in nics:
            networkInfo = GetNetwork(host=host, name=nic['portgroup'])
            if networkInfo is not None:
                nicSpec = vim.vm.device.VirtualDeviceSpec()
                nicSpec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
                if nic['type'] == 'vmxnet3':
                    nicSpec.device = vim.vm.device.VirtualVmxnet3()
                elif nic['type'] == 'e1000e':
                    nicSpec.device = vim.vm.device.VirtualE1000e()
                elif guestId in VM_GUEST_WINDOWS:
                    nicSpec.device = vim.vm.device.VirtualE1000e()
                else:
                    nicSpec.device = vim.vm.device.VirtualVmxnet3()
                nicSpec.device.key = 4000 + index
                nicSpec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                nicSpec.device.backing.deviceName = nic['portgroup']
                nicSpec.device.backing.network = networkInfo
                if nic['slot'] is not None:
                    nicSpec.device.slotInfo = vim.vm.device.VirtualDevice.PciBusSlotInfo()
                    nicSpec.device.slotInfo.pciSlotNumber = int(nic['slot'])
                nicSpec.device.controllerKey = 100
                nicSpec.device.unitNumber = 7 + index
                nicSpec.device.addressType = 'generated'
                nicSpec.device.wakeOnLanEnabled = False
                spec.deviceChange.append(nicSpec)
                index = index + 1
    #
    return spec


def CustomizeVirtualMachineSpec(spec, host, highLS=False, cpuPin=False, memPin=False, nodeAffinity=None):
    if highLS:
        memPin = True
        spec.extraConfig.append(vim.option.OptionValue(key='latency.enforceCpuMin', value='FALSE'))
        for option in spec.extraConfig:
            if option.key == 'sched.cpu.latencySensitivity':
                option.value = 'high'
    #
    if cpuPin:
        spec.cpuAllocation = vim.ResourceAllocationInfo()
        spec.cpuAllocation.reservation = host.hardware.cpuInfo.hz // 1000000 * spec.numCPUs
    #
    if memPin:
        spec.memoryReservationLockedToMax = True
        spec.memoryAllocation = vim.ResourceAllocationInfo()
        spec.memoryAllocation.reservation = spec.memoryMB
        spec.extraConfig.append(vim.option.OptionValue(key='sched.mem.pin', value='TRUE'))
    #
    if nodeAffinity is not None:
        nodeNum = len(str(nodeAffinity).split(','))
        if nodeNum > 1:
            spec.extraConfig.append(vim.option.OptionValue(key='numa.vcpu.maxPerMachineNode', value=str(-(-spec.numCPUs // nodeNum)))) ## Rounded up
            spec.extraConfig.append(vim.option.OptionValue(key='numa.vcpu.maxPerVirtualNode', value=str(-(-spec.numCPUs // nodeNum)))) ## Rounded up
            spec.extraConfig.append(vim.option.OptionValue(key='numa.autosize', value='TRUE'))
        spec.extraConfig.append(vim.option.OptionValue(key='numa.nodeAffinity', value=str(nodeAffinity)))
    #
    return spec


def AddVirtualPciPassthruDevice(spec, host, sbdf, slot=None):
    keyBase = 13000
    numOfPassthru = 0
    for devSpec in spec.deviceChange:
        if type(devSpec.device) is vim.vm.device.VirtualPCIPassthrough:
            numOfPassthru = numOfPassthru + 1
    #
    ptInfo = GetPciPassthruInfo(host, sbdf)
    if ptInfo is not None:
        passthruSpec = vim.vm.device.VirtualDeviceSpec()
        passthruSpec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        passthruSpec.device = vim.vm.device.VirtualPCIPassthrough()
        passthruSpec.device.key = keyBase + numOfPassthru
        passthruSpec.device.backing = vim.vm.device.VirtualPCIPassthrough.DeviceBackingInfo()
        passthruSpec.device.backing.deviceName = ''
        passthruSpec.device.backing.id = sbdf
        passthruSpec.device.backing.deviceId = "%x" % ptInfo['deviceId']
        passthruSpec.device.backing.systemId = ptInfo['systemId']
        passthruSpec.device.backing.vendorId = ptInfo['vendorId']
        if slot:
            passthruSpec.device.slotInfo = vim.vm.device.VirtualDevice.PciBusSlotInfo()
            passthruSpec.device.slotInfo.pciSlotNumber = slot
        passthruSpec.device.controllerKey = 100
        spec.deviceChange.append(passthruSpec)
    return spec


def AddIntelSriovVirtualNicDevice(spec, host, sbdf, portgroup, slot=None):
    maxId = 15
    keyBase = 13000
    numOfSriov = 0
    for devSpec in spec.deviceChange:
        if type(devSpec.device) is vim.vm.device.VirtualSriovEthernetCard:
            numOfSriov = numOfSriov + 1
    #
    networkInfo = GetNetwork(host=host, name=portgroup)
    if networkInfo is not None:
        sriovSpec = vim.vm.device.VirtualDeviceSpec()
        sriovSpec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        sriovSpec.device = vim.vm.device.VirtualSriovEthernetCard()
        sriovSpec.device.key = keyBase + maxId - numOfSriov
        sriovSpec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
        sriovSpec.device.backing.deviceName = portgroup
        sriovSpec.device.backing.network = networkInfo
        if slot is not None:
            sriovSpec.device.slotInfo = vim.vm.device.VirtualDevice.PciBusSlotInfo()
            sriovSpec.device.slotInfo.pciSlotNumber = slot
        sriovSpec.device.controllerKey = 100
        sriovSpec.device.addressType = 'generated'
        sriovSpec.device.sriovBacking = vim.vm.device.VirtualSriovEthernetCard.SriovBackingInfo()
        sriovSpec.device.sriovBacking.physicalFunctionBacking = vim.vm.device.VirtualPCIPassthrough.DeviceBackingInfo()
        sriovSpec.device.sriovBacking.physicalFunctionBacking.deviceName = ''
        sriovSpec.device.sriovBacking.physicalFunctionBacking.id = sbdf
        sriovSpec.device.sriovBacking.physicalFunctionBacking.deviceId = '0'
        sriovSpec.device.sriovBacking.physicalFunctionBacking.systemId = 'BYPASS'
        sriovSpec.device.sriovBacking.physicalFunctionBacking.vendorId = 0
        spec.deviceChange.append(sriovSpec)
    return spec


def CreateVirtualMachine(spec, host):
    datacenter = host.parent.parent.parent
    pool = host.parent.resourcePool
    try:
        result = datacenter.vmFolder.CreateVM_Task(spec, pool)
        while result.info.state == 'running':
            time.sleep(1)
        if result.info.state != 'success':
            return False
    except Exception as e:
        return False
    time.sleep(1)
    return True


def DeleteVirtualMachine(vm):
    try:
        result = vm.Destroy_Task()
        while result.info.state == 'running':
            time.sleep(1)
        if result.info.state != 'success':
            return False
    except Exception as e:
        return False
    time.sleep(1)
    return True

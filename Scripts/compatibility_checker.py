from Scripts.datasets import chipset_data
from Scripts.datasets import gpu_data
from Scripts.datasets import os_data
from Scripts.datasets import pci_data
from Scripts.datasets import codec_layouts
from Scripts import utils
import time

class CompatibilityChecker:
    def __init__(self):
        self.utils = utils.Utils()

    def show_macos_compatibility(self, device_compatibility):
        if not device_compatibility:
            return "\033[90mUnchecked\033[0m"
        
        if not device_compatibility[0]:
            return "\033[0;31mUnsupported\033[0m"
        
        max_compatibility = self.utils.parse_darwin_version(device_compatibility[0])[0]
        min_compatibility = self.utils.parse_darwin_version(device_compatibility[-1])[0]
        max_version = self.utils.parse_darwin_version(os_data.get_latest_darwin_version())[0]
        min_version = self.utils.parse_darwin_version(os_data.get_lowest_darwin_version())[0]

        if min_version < min_compatibility and max_compatibility < max_version:
            return "\033[1;32m{} - {}\033[0m".format(
                os_data.get_macos_name_by_darwin(device_compatibility[0]), 
                os_data.get_macos_name_by_darwin(device_compatibility[-1])
            )
        
        if max_compatibility == min_version:
            return "\033[1;36mMaximum support up to {}\033[0m".format(
                os_data.get_macos_name_by_darwin(device_compatibility[-1])
            )
        
        return "\033[1;36mUp to {}\033[0m".format(
            os_data.get_macos_name_by_darwin(device_compatibility[0])
        )
        
    def is_low_end_intel_cpu(self, processor_name):
        return any(cpu_branding in processor_name for cpu_branding in ("Celeron", "Pentium"))

    def check_cpu_compatibility(self):
        max_version = os_data.get_latest_darwin_version()
        min_version = os_data.get_lowest_darwin_version()

        if "SSE4" not in self.hardware_report.get("CPU").get("SIMD Features"):
            max_version = min_version = None
        else:
            if "SSE4.2" not in self.hardware_report.get("CPU").get("SIMD Features"):
                min_version = "18.0.0"
                if "SSE4.1" in self.hardware_report.get("CPU").get("SIMD Features"):
                    max_version = "21.99.99"

        self.hardware_report["CPU"]["Compatibility"] = (max_version, min_version)
        print("{}- {}: {}".format(" "*3, self.hardware_report.get("CPU").get("Processor Name"), self.show_macos_compatibility(self.hardware_report["CPU"].get("Compatibility"))))

        if max_version == min_version and max_version == None:
            self.utils.request_input("\n\nThe CPU is not compatible with macOS!")
            self.utils.exit_program()

        self.max_native_macos_version = max_version
        self.min_native_macos_version = min_version

    def check_gpu_compatibility(self):
        gpu_compatibility = []

        for gpu_name, gpu_props in self.hardware_report.get("GPU").items():
            gpu_manufacturer = gpu_props.get("Manufacturer")
            gpu_codename = gpu_props.get("Codename")
            device_id = gpu_props.get("Device ID")[5:]

            max_version = os_data.get_latest_darwin_version()
            min_version = os_data.get_lowest_darwin_version()
            ocl_patched_max_version = max_version
            ocl_patched_min_version = "20.0.0"

            if "Intel" in gpu_manufacturer:
                if device_id.startswith(("0042", "0046")) and self.hardware_report.get("Motherboard").get("Platform") != "Desktop":
                    max_version = "17.99.99"
                elif device_id.startswith("01") and not device_id[-2] in ("5", "6") and not device_id in ("0102", "0106", "010A"):
                    max_version = "17.99.99"
                elif device_id.startswith("01") and not device_id in ("0152", "0156"):
                    max_version = "20.99.99"
                elif device_id.startswith(("04", "0A", "0C", "0D", "0B", "16")):
                    max_version = "21.99.99"
                elif device_id.startswith(("09", "19", "59", "59", "3E", "87", "9B")) and not device_id in ("3E90", "3E93", "3E99", "3E9C", "3EA1", "3EA4", "9B21", "9BA0", "9BA2", "9BA4", "9BA5", "9BA8", "9BAA", "9BAB", "9BAC"):
                    pass
                elif device_id.startswith("8A"):
                    min_version = "19.4.0"
                else:
                    max_version = min_version = None

                if self.is_low_end_intel_cpu(self.hardware_report.get("CPU").get("Processor Name")) or self.hardware_report.get("Motherboard").get("Chipset") in chipset_data.IntelChipsets[127:141]:
                    max_version = min_version = None
            elif "AMD" in gpu_manufacturer:
                if "Navi 2" in gpu_codename:
                    if not "AVX2" in self.hardware_report.get("CPU").get("SIMD Features"):
                        max_version = "21.99.99"
                        ocl_patched_max_version = max_version
                    else:
                        if gpu_codename in ("Navi 23", "Navi 22"):
                            min_version = "21.2.0"
                        elif "Navi 21" in gpu_codename:
                            min_version = "20.5.0"
                        else:
                            max_version = min_version = None
                elif "Navi 1" in gpu_codename:
                    if not "AVX2" in self.hardware_report.get("CPU").get("SIMD Features"):
                        max_version = "21.99.99"
                        ocl_patched_min_version = "22.0.0"
                    min_version = "19.0.0"
                elif "Vega 20" in gpu_codename:
                    if not "AVX2" in self.hardware_report.get("CPU").get("SIMD Features"):
                        max_version = "21.99.99"
                        ocl_patched_min_version = "22.0.0"
                    min_version = "18.6.0"
                elif gpu_codename in ("Vega 10", "Polaris 22", "Polaris 20", "Baffin", "Ellesmere") or device_id in ("6995", "699F"):
                    if not "AVX2" in self.hardware_report.get("CPU").get("SIMD Features"):
                        max_version = "21.99.99"
                        ocl_patched_min_version = "22.0.0"
                    min_version = "17.0.0"
                elif self.utils.contains_any(gpu_data.AMDCodenames, gpu_codename):
                    max_version = "21.99.99"
                elif device_id in ("15D8", "15DD", "15E7", "1636", "1638", "164C"):
                    min_version = "19.0.0"
                else:
                    max_version = min_version = None
            elif "NVIDIA" in gpu_manufacturer:
                if "Kepler" in gpu_codename:
                    max_version = "20.99.99"
                elif gpu_codename in ("Pascal", "Maxwell", "Fermi", "Tesla"):
                    max_version = "17.99.99"
                    min_version = "17.0.0"
                else:
                    max_version = min_version = None

            if (max_version == min_version and max_version == None) or \
                ( "Intel" in gpu_manufacturer and device_id.startswith(("01", "04", "0A", "0C", "0D")) and \
                  all(monitor_info.get("Connector Type") == "VGA" and monitor_info.get("Connected GPU", gpu_name) == gpu_name for monitor_name, monitor_info in self.hardware_report.get("Monitor", {}).items())):
                gpu_props["Compatibility"] = (None, None)
            else:
                gpu_props["Compatibility"] = (max_version, min_version)
                if max_version != ocl_patched_max_version:
                    gpu_props["OCLP Compatibility"] = (ocl_patched_max_version, ocl_patched_min_version if self.utils.parse_darwin_version(ocl_patched_min_version) > self.utils.parse_darwin_version("{}.{}.{}".format(int(max_version[:2]) + 1, 0, 0)) else "{}.{}.{}".format(int(max_version[:2]) + 1, 0, 0))

            print("{}- {}: {}{}".format(
                " "*3, 
                gpu_name, 
                self.show_macos_compatibility(gpu_props.get("Compatibility")),
                " \033[1;36m(requires monitor)\033[0m" 
                if  max_version and \
                    not "Intel" in gpu_manufacturer and \
                    not any(monitor_info.get("Connected GPU", gpu_name) == gpu_name for monitor_name, monitor_info in self.hardware_report.get("Monitor", {}).items()) else ""
            ))
            connected_monitors = []
            for monitor_name, monitor_info in self.hardware_report.get("Monitor", {}).items(): 
                if monitor_info.get("Connected GPU") == gpu_name:
                    connected_monitors.append("{} ({})".format(monitor_name, monitor_info.get("Connector Type")))
                    if "Intel" in gpu_manufacturer and device_id.startswith(("01", "04", "0A", "0C", "0D")):
                        if monitor_info.get("Connector Type") == "VGA":
                            connected_monitors[-1] = "\033[0;31m{}{}\033[0m".format(connected_monitors[-1][:-1], ", unsupported)")
            if connected_monitors:
                print("{}- Connected Monitor{}: {}".format(" "*6, "s" if len(connected_monitors) > 1 else "", ", ".join(connected_monitors)))

        max_supported_gpu_version = min_supported_gpu_version = None

        for gpu_name, gpu_props in self.hardware_report.get("GPU").items():
            if gpu_props.get("Compatibility") != (None, None):
                if all(other_gpu_props.get("Compatibility") == (None, None) for other_gpu_props in self.hardware_report.get("GPU").values() if other_gpu_props != gpu_props):
                    pass
                elif any(monitor_info.get("Connected GPU", gpu_name) != gpu_name for monitor_info in self.hardware_report.get("Monitor", {}).values() if monitor_info.get("Connector Type") == "Internal"):
                    gpu_props["Compatibility"] = (None, None)
                    if gpu_props.get("OCLP Compatibility"):
                        del gpu_props["OCLP Compatibility"]

                max_version, min_version = gpu_props.get("Compatibility")
                max_supported_gpu_version = max_version if not max_supported_gpu_version else max_version if self.utils.parse_darwin_version(max_version) > self.utils.parse_darwin_version(max_supported_gpu_version) else max_supported_gpu_version
                min_supported_gpu_version = min_version if not min_supported_gpu_version else min_version if self.utils.parse_darwin_version(min_version) < self.utils.parse_darwin_version(min_supported_gpu_version) else min_supported_gpu_version

            if gpu_props.get("OCLP Compatibility"):
                self.ocl_patched_macos_version = (gpu_props.get("OCLP Compatibility")[0], self.ocl_patched_macos_version[-1] if self.ocl_patched_macos_version and self.utils.parse_darwin_version(self.ocl_patched_macos_version[-1]) < self.utils.parse_darwin_version(gpu_props.get("OCLP Compatibility")[-1]) else gpu_props.get("OCLP Compatibility")[-1])
        
        if max_supported_gpu_version == min_supported_gpu_version and max_supported_gpu_version == None:
            self.utils.request_input("\n\nNo compatible GPU card for macOS was found!")
            self.utils.exit_program()

        self.max_native_macos_version = max_supported_gpu_version if self.utils.parse_darwin_version(max_supported_gpu_version) < self.utils.parse_darwin_version(self.max_native_macos_version) else self.max_native_macos_version
        self.min_native_macos_version = min_supported_gpu_version if self.utils.parse_darwin_version(min_supported_gpu_version) > self.utils.parse_darwin_version(self.min_native_macos_version) else self.min_native_macos_version

        return gpu_compatibility

    def check_sound_compatibility(self):
        sound_info = {}

        for audio_device, audio_props in self.hardware_report.get("Sound", {}).items():
            codec_id = audio_props.get("Device ID")
            if "USB" in audio_props.get("Bus Type") or \
                codec_id.startswith("1002") or \
                codec_id.startswith("8086") and not codec_id in pci_data.IntelSSTIDs or \
                codec_id in codec_layouts.data:
                audio_props["Compatibility"] = (os_data.get_latest_darwin_version(), os_data.get_lowest_darwin_version())
                if codec_id in codec_layouts.data:
                    sound_info = {**{audio_device: audio_props}, **sound_info}
                else:
                    sound_info[audio_device] = audio_props
            else:
                audio_props["Compatibility"] = (None, None)
                sound_info[audio_device] = audio_props
            print("{}- {}: {}".format(" "*3, audio_device, self.show_macos_compatibility(audio_props.get("Compatibility"))))
            audio_endpoints = audio_props.get("Audio Endpoints")
            if audio_endpoints:
                print("{}- Audio Endpoint{}: {}".format(" "*6, "s" if len(audio_endpoints) > 1 else "", ", ".join(audio_endpoints)))

        self.hardware_report["Sound"] = sound_info
        
    def check_biometric_compatibility(self):
        for biometric_device, biometric_props in self.hardware_report.get("Biometric", {}).items():
            biometric_props["Compatibility"] = (None, None)
            print("{}- {}: {}".format(" "*3, biometric_device, self.show_macos_compatibility(biometric_props.get("Compatibility"))))

    def check_network_compatibility(self):
        primary_wifi_device = next((device_props.get("Device ID") for device_name, device_props in self.hardware_report.get("Network", {}).items() if device_props.get("Device ID") in pci_data.BroadcomWiFiIDs), None)
        if not primary_wifi_device:
            primary_wifi_device = next((device_props.get("Device ID") for device_name, device_props in self.hardware_report.get("Network", {}).items() if device_props.get("Device ID") in pci_data.IntelWiFiIDs), None)
            if not primary_wifi_device:
                primary_wifi_device = next((device_props.get("Device ID") for device_name, device_props in self.hardware_report.get("Network", {}).items() if device_props.get("Device ID") in pci_data.AtherosWiFiIDs), None)

        for device_name, device_props in self.hardware_report.get("Network", {}).items():
            bus_type = device_props.get("Bus Type")
            device_id = device_props.get("Device ID")
            
            max_version = os_data.get_latest_darwin_version()
            min_version = os_data.get_lowest_darwin_version()
            ocl_patched_max_version = max_version
            ocl_patched_min_version = "20.0.0"

            if device_id in pci_data.BroadcomWiFiIDs:
                device_index = pci_data.BroadcomWiFiIDs.index(device_id)

                if device_index == 13 or 17 < device_index < 21:
                    max_version = "22.99.99"
                    ocl_patched_min_version = "23.0.0"
                elif device_index < 12:
                    max_version = "17.99.99"
            elif device_id in pci_data.AtherosWiFiIDs[:8]:
                max_version = "17.99.99"
            elif device_id in pci_data.AtherosWiFiIDs[8:]:
                max_version = "20.99.99"
            elif device_id in pci_data.IntelI22XIDs:
                min_version = "19.0.0"
            elif device_id in pci_data.AquantiaAqtionIDs:
                min_version = "21.0.0"

            if device_id in pci_data.WirelessCardIDs:
                if device_id == primary_wifi_device:
                    if not device_id in pci_data.IntelWiFiIDs and not device_id in pci_data.AtherosWiFiIDs[8:]:
                        device_props["OCLP Compatibility"] = (ocl_patched_max_version, ocl_patched_min_version)
                        self.ocl_patched_macos_version = (ocl_patched_max_version, self.ocl_patched_macos_version[-1] if self.ocl_patched_macos_version and self.utils.parse_darwin_version(self.ocl_patched_macos_version[-1]) < self.utils.parse_darwin_version(device_props.get("OCLP Compatibility")[-1]) else device_props.get("OCLP Compatibility")[-1])
                    device_props["Compatibility"] = (max_version, min_version)
                    primary_wifi_device = None
            elif device_id in pci_data.EthernetIDs + pci_data.WirelessUSBIDs:
                device_props["Compatibility"] = (max_version, min_version)

            if bus_type.startswith("PCI") and not device_props.get("Compatibility"):
                device_props["Compatibility"] = (None, None)

            print("{}- {}: {}".format(" "*3, device_name, self.show_macos_compatibility(device_props.get("Compatibility"))))

    def check_storage_compatibility(self):
        for controller_name, controller_props in self.hardware_report.get("Storage Controllers", {}).items():
            if "PCI" not in controller_props.get("Bus Type"):
                continue

            device_id = controller_props.get("Device ID")
            subsystem_id = controller_props.get("Subsystem ID", "0"*8)

            max_version = os_data.get_latest_darwin_version()
            min_version = os_data.get_lowest_darwin_version()

            if device_id in pci_data.IntelVMDIDs:
                self.utils.request_input("\n\nDisable Intel RST VMD in the BIOS before exporting the hardware report and try again with the new report")
                self.utils.exit_program()

            controller_props["Compatibility"] = (max_version, min_version)

            if next((device for device in pci_data.UnsupportedNVMeSSDIDs if device_id == device[0] and subsystem_id in device[1]), None):
                controller_props["Compatibility"] = (None, None)
                
            print("{}- {}: {}".format(" "*3, controller_name, self.show_macos_compatibility(controller_props.get("Compatibility"))))

        if all(controller_props.get("Compatibility") == (None, None) for controller_name, controller_props in self.hardware_report.get("Storage Controllers", {}).items()):
            self.utils.request_input("\n\nNo compatible storage for macOS was found!")
            self.utils.exit_program()

    def check_bluetooth_compatibility(self):
        for bluetooth_name, bluetooth_props in self.hardware_report.get("Bluetooth", {}).items():
            device_id = bluetooth_props.get("Device ID")
            
            max_version = os_data.get_latest_darwin_version()
            min_version = os_data.get_lowest_darwin_version()

            if device_id in pci_data.AtherosBluetoothIDs:
                max_version = "20.99.99"
            elif device_id in pci_data.BluetoothIDs:
                pass
            else:
                max_version = min_version = None

            bluetooth_props["Compatibility"] = (max_version, min_version)
            print("{}- {}: {}".format(" "*3, bluetooth_name, self.show_macos_compatibility(bluetooth_props.get("Compatibility"))))
        
    def check_sd_controller_compatibility(self):
        for controller_name, controller_props in self.hardware_report.get("SD Controller", {}).items():
            if controller_props.get("Device ID") not in pci_data.RealtekCardReaderIDs:
                controller_props["Compatibility"] = (None, None)
            else:
                controller_props["Compatibility"] = (os_data.get_latest_darwin_version() if controller_props.get("Device ID") in pci_data.RealtekCardReaderIDs[5:] else "23.99.99", os_data.get_lowest_darwin_version())
            print("{}- {}: {}".format(" "*3, controller_name, self.show_macos_compatibility(controller_props.get("Compatibility"))))

    def get_unsupported_devices(self, macos_verison):
        new_hardware_report = {}
        unsupported_device = {}
        needs_oclp = False

        for device_type, devices in self.hardware_report.items():
            if device_type in ("Motherboard", "BIOS", "CPU", "USB Controllers", "Input", "System Devices"):
                new_hardware_report[device_type] = devices
                continue

            new_hardware_report[device_type] = {}

            for device_name in devices:
                device_props = devices[device_name].copy()
                if device_props.get("OCLP Compatibility") and self.utils.parse_darwin_version(device_props.get("OCLP Compatibility")[0]) >= self.utils.parse_darwin_version(macos_verison) >= self.utils.parse_darwin_version(device_props.get("OCLP Compatibility")[-1]):
                    new_hardware_report[device_type][device_name] = device_props
                    needs_oclp = True
                    continue

                device_compatibility = device_props.get("Compatibility")

                if device_compatibility:
                    if device_compatibility[0] is None or not self.utils.parse_darwin_version(device_compatibility[0]) >= self.utils.parse_darwin_version(macos_verison) >= self.utils.parse_darwin_version(device_compatibility[-1]):
                        unsupported_device["{}: {}{}".format(device_props.get("Device Type") or device_type, device_name, "" if not device_props.get("Audio Endpoints") else " ({})".format(", ".join(device_props.get("Audio Endpoints"))))] = device_props
                    else:
                        new_hardware_report[device_type][device_name] = device_props
                else:
                    new_hardware_report[device_type][device_name] = device_props

                if new_hardware_report[device_type].get(device_name) and new_hardware_report[device_type][device_name].get("OCLP Compatibility"):
                    del new_hardware_report[device_type][device_name]["OCLP Compatibility"]

            if not new_hardware_report[device_type]:
                del new_hardware_report[device_type]

        return new_hardware_report, unsupported_device, needs_oclp

    def check_compatibility(self, hardware_report):
        self.hardware_report = hardware_report
        self.ocl_patched_macos_version = None

        self.utils.head("Compatibility Checker")
        print()

        steps = [
            ('CPU', self.check_cpu_compatibility),
            ('GPU', self.check_gpu_compatibility),
            ('Sound', self.check_sound_compatibility),
            ('Biometric', self.check_biometric_compatibility),
            ('Network', self.check_network_compatibility),
            ('Storage Controllers', self.check_storage_compatibility),
            ('Bluetooth', self.check_bluetooth_compatibility),
            ('SD Controller', self.check_sd_controller_compatibility)
        ]

        index = 0
        for device_type, function in steps:
            if self.hardware_report.get(device_type):
                index += 1
                print("{}. {}:".format(index, device_type))
                time.sleep(0.5)
                function()

        print("")
        self.utils.request_input()

        return (self.min_native_macos_version, self.max_native_macos_version), *self.get_unsupported_devices(self.max_native_macos_version), self.ocl_patched_macos_version

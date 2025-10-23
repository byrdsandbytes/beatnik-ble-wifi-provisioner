from __future__ import annotations
import asyncio
import subprocess
import logging

from dbus_next.service import ServiceInterface, method, signal, dbus_property
from dbus_next.aio import MessageBus
from dbus_next.constants import PropertyAccess
from dbus_next import BusType, Variant

# --- Configuration ---
# These are the standard D-Bus paths and interfaces for BlueZ
BLUEZ_SERVICE = "org.bluez"
GATT_MANAGER_IFACE = "org.bluez.GattManager1"
LE_ADVERTISING_MANAGER_IFACE = "org.bluez.LEAdvertisingManager1"
AGENT_MANAGER_IFACE = "org.bluez.AgentManager1"
DBUS_OM_IFACE = "org.freedesktop.DBus.ObjectManager"
DBUS_PROP_IFACE = "org.freedesktop.DBus.Properties"

# --- Your Custom Settings ---
# Change these to customize your BLE device
DEVICE_NAME = "beatnik"  # <-- Change this to customize the device name visible during scanning

# --- Our Custom Application ---
# We define our own object paths for our app, service, and characteristics
# This is just a unique name on D-Bus, like a folder path.
APP_PATH = "/org/example/provisioning"
SERVICE_PATH = f"{APP_PATH}/service1"

# Bluetooth Base UUID: 00000000-0000-1000-8000-00805F9B34FB
# Our Service UUID (using a random base): 6E400001-B5A3-F393-E0A9-E50E24DCCA9E
SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
SSID_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
PASS_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
CONNECT_CHAR_UUID = "6E400004-B5A3-F393-E0A9-E50E24DCCA9E"
STATUS_CHAR_UUID = "6E400005-B5A3-F393-E0A9-E50E24DCCA9E"
SCAN_CHAR_UUID = "6E400006-B5A3-F393-E0A9-E50E24DCCA9E"

# We'll store our data in these global-like variables
class ProvisioningData:
    ssid = b""
    password = b""
    status = b"Ready"
    available_networks = b""  # Store scan results

data = ProvisioningData()
status_char_instance = None # Global instance for status updates
scan_char_instance = None  # Global instance for scan updates

# --- Helper: Wi-Fi Connection Logic ---

def update_status(message_str):
    """Updates the status and prepares it for D-Bus."""
    if status_char_instance:
        status_char_instance.update_status(message_str)

def update_scan_results(results_str):
    """Updates the scan results and prepares it for D-Bus."""
    if scan_char_instance:
        scan_char_instance.update_scan_results(results_str)

def scan_wifi_networks():
    """Scans for available Wi-Fi networks using nmcli."""
    logging.info("Scanning for available Wi-Fi networks...")
    update_scan_results("Scanning...")
    
    try:
        # Run nmcli to scan and list networks
        # Format: SSID:SIGNAL:SECURITY (e.g., "MyNetwork:85:WPA2")
        cmd = ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"]
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if process.returncode == 0:
            # Parse the output
            networks = []
            lines = process.stdout.strip().split('\n')
            
            for line in lines:
                if line.strip():
                    parts = line.split(':')
                    if len(parts) >= 2:
                        ssid = parts[0]
                        signal = parts[1] if len(parts) > 1 else "?"
                        security = parts[2] if len(parts) > 2 else "Open"
                        
                        # Skip empty SSIDs (hidden networks)
                        if ssid:
                            networks.append(f"{ssid}|{signal}|{security}")
            
            # Join networks with semicolon separator
            result = ";".join(networks) if networks else "No networks found"
            logging.info(f"Found {len(networks)} networks")
            update_scan_results(result)
        else:
            error_msg = "Scan failed"
            logging.error(f"Failed to scan: {process.stderr}")
            update_scan_results(error_msg)
    
    except subprocess.TimeoutExpired:
        update_scan_results("Scan timeout")
    except Exception as e:
        update_scan_results(f"Error: {str(e)}")
        logging.error(f"Scan error: {e}")

def attempt_connection():
    """Uses nmcli to connect to the Wi-Fi network."""
    ssid = data.ssid.decode("utf-8")
    password = data.password.decode("utf-8")

    if not ssid:
        update_status("Error: No SSID")
        return

    logging.info(f"Attempting connection to SSID: {ssid}")
    update_status(f"Connecting to {ssid}...")

    try:
        # Try connection with the standard command first
        cmd = ["nmcli", "device", "wifi", "connect", ssid, "password", password]
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if process.returncode == 0:
            update_status("Success! Connected.")
            logging.info("Successfully connected!")
            # In a real app, you might stop advertising here
        else:
            # If the first attempt fails, try with a connection profile
            logging.info("First connection attempt failed, trying with explicit connection profile...")
            
            # Create a new connection profile with explicit settings
            profile_name = f"wifi-{ssid}"
            cmd = [
                "nmcli", "connection", "add",
                "type", "wifi",
                "con-name", profile_name,
                "ifname", "wlan0",
                "ssid", ssid,
                "wifi-sec.key-mgmt", "wpa-psk",
                "wifi-sec.psk", password
            ]
            create_profile = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if create_profile.returncode == 0:
                # Try to activate the new connection
                cmd = ["nmcli", "connection", "up", profile_name]
                activate = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if activate.returncode == 0:
                    update_status("Success! Connected.")
                    logging.info("Successfully connected using connection profile!")
                else:
                    error_msg = "Failed: Bad Password?"
                    if "Error: No network with SSID" in activate.stderr:
                        error_msg = "Failed: SSID Not Found"
                    logging.error(f"Failed to activate connection: {activate.stderr}")
                    # Clean up the failed connection profile
                    subprocess.run(["nmcli", "connection", "delete", profile_name], 
                                capture_output=True, timeout=5)
                    update_status(error_msg)
            else:
                error_msg = "Failed: Could not create connection profile"
                logging.error(f"Failed to create connection profile: {create_profile.stderr}")
                update_status(error_msg)

    except subprocess.TimeoutExpired:
        update_status("Failed: Timeout")
    except Exception as e:
        update_status(f"Failed: {str(e)}")


# --- D-Bus GATT Interface Classes ---
# This is the boilerplate to make our Python classes look like
# standard BlueZ GATT services and characteristics.

class BaseGATTCharacteristic(ServiceInterface):
    """Base class for our characteristics."""
    IFACE = "org.bluez.GattCharacteristic1"
    _char_counter = 0  # Class variable to track characteristic count

    def __init__(self, service_path, uuid, flags, description):
        super().__init__(self.IFACE)
        BaseGATTCharacteristic._char_counter += 1
        self.path = f"{service_path}/char{BaseGATTCharacteristic._char_counter}"
        self._uuid = uuid
        self._flags = flags
        self._description = description
        self.service = service_path
        
    @method()
    def ReadValue(self, options: "a{sv}") -> "ay":  # 'ay' means 'array of bytes'
        """Default ReadValue method."""
        logging.warning(f"ReadValue called on non-readable char: {self._uuid}")
        return b""  # Return empty bytes instead of empty list

    @method()
    def WriteValue(self, value: "ay", options: "a{sv}"):
        """Default WriteValue method."""
        logging.warning(f"WriteValue called on non-writable char: {self._uuid}")

    @dbus_property(access=PropertyAccess.READ)
    def UUID(self) -> "s":  # 's' means 'string'
        return self._uuid

    @dbus_property(access=PropertyAccess.READ)
    def Service(self) -> "o":  # 'o' means 'object path'
        return self.service

    @dbus_property(access=PropertyAccess.READ)
    def Flags(self) -> "as":  # 'as' means 'array of strings'
        return self._flags
    
    @signal()
    def PropertiesChanged(self, interface: "s", changed: "a{sv}", invalidated: "as"):
        """Signal emitted when a property changes. Used for BLE notifications."""
        pass
        
    def add_descriptor(self, bus):
        """Adds the 'User Description' descriptor."""
        desc = Descriptor(
            bus=bus,
            index=0,
            uuid="2901",
            flags=["read"],
            characteristic=self,
            value=self._description.encode("utf-8")
        )
        bus.export(desc.path, desc)
        return desc.path

class Descriptor(ServiceInterface):
    """
    A simple GATT Descriptor implementation.
    """
    IFACE = "org.bluez.GattDescriptor1"

    def __init__(self, bus, index, uuid, flags, characteristic, value):
        self.path = f"{characteristic.path}/desc{index}"
        super().__init__(self.IFACE)
        self.bus = bus
        self._uuid = f"0000{uuid}-0000-1000-8000-00805f9b34fb"
        self._flags = flags
        self.characteristic = characteristic
        self._value = value

    @method()
    def ReadValue(self, options: "a{sv}") -> "ay":
        return list(self._value)

    @dbus_property(access=PropertyAccess.READ)
    def UUID(self) -> "s":
        return self._uuid

    @dbus_property(access=PropertyAccess.READ)
    def Characteristic(self) -> "o":
        return self.characteristic.path

    @dbus_property(access=PropertyAccess.READ)
    def Flags(self) -> "as":
        return self._flags

class SSIDCharacteristic(BaseGATTCharacteristic):
    def __init__(self, service_path):
        super().__init__(
            service_path,
            SSID_CHAR_UUID,
            ["write", "write-without-response"],
            "Wi-Fi SSID"
        )

    @method()
    def WriteValue(self, value: "ay", options: "a{sv}"):
        logging.info(f"WriteValue called with options: {options}")
        logging.info(f"SSID set to: {bytes(value).decode('utf-8', errors='replace')}")
        data.ssid = bytes(value)

class PasswordCharacteristic(BaseGATTCharacteristic):
    def __init__(self, service_path):
        super().__init__(
            service_path,
            PASS_CHAR_UUID,
            ["write", "write-without-response"],
            "Wi-Fi Password"
        )

    @method()
    def WriteValue(self, value: "ay", options: "a{sv}"):
        # Don't log the password!
        logging.info("Password set.")
        data.password = bytes(value)

class ConnectCharacteristic(BaseGATTCharacteristic):
    def __init__(self, service_path):
        super().__init__(
            service_path,
            CONNECT_CHAR_UUID,
            ["write", "write-without-response"],
            "Trigger Connection"
        )

    @method()
    def WriteValue(self, value: "ay", options: "a{sv}"):
        logging.info("Connect characteristic written to. Starting connection...")
        # Run connection logic in the background, don't block D-Bus
        asyncio.create_task(
            asyncio.to_thread(attempt_connection)
        )

class StatusCharacteristic(BaseGATTCharacteristic):
    def __init__(self, service_path):
        super().__init__(
            service_path,
            STATUS_CHAR_UUID,
            ["read", "notify"],
            "Connection Status"
        )
        self.value = b"Ready"
        self.notifying = False  # Track if notifications are enabled

    @method()
    def StartNotify(self):
        """Called when a client subscribes to notifications."""
        logging.info(f"Status notifications enabled on {self._uuid}")
        self.notifying = True
        # Send initial value immediately
        logging.info(f"Sending initial status value: {self.value.decode('utf-8', errors='replace')}")
        self.PropertiesChanged(DBUS_PROP_IFACE, {"Value": Variant("ay", self.value)}, [])

    @method()
    def StopNotify(self):
        """Called when a client unsubscribes from notifications."""
        logging.info(f"Status notifications disabled on {self._uuid}")
        self.notifying = False

    def update_status(self, message_str):
        """Updates the status and notifies subscribers."""
        logging.info(f"Updating status: {message_str}")
        self.value = message_str.encode("utf-8")
        if self.notifying:
            # Send actual BLE notification using the Properties interface
            logging.info(f"Sending status notification: {message_str}")
            self.PropertiesChanged(DBUS_PROP_IFACE, {"Value": Variant("ay", self.value)}, [])

    @method()
    def ReadValue(self, options: "a{sv}") -> "ay":
        logging.info(f"Status read: {self.value.decode('utf-8', errors='replace')}")
        return self.value

class ScanCharacteristic(BaseGATTCharacteristic):
    def __init__(self, service_path):
        super().__init__(
            service_path,
            SCAN_CHAR_UUID,
            ["read", "write", "notify"],
            "WiFi Network Scan"
        )
        self.value = b"Ready to scan"
        self.notifying = False  # Track if notifications are enabled

    @method()
    def StartNotify(self):
        """Called when a client subscribes to notifications."""
        logging.info(f"Scan notifications enabled on {self._uuid}")
        self.notifying = True
        # Send initial value immediately
        logging.info(f"Sending initial scan value: {self.value.decode('utf-8', errors='replace')}")
        self.PropertiesChanged(DBUS_PROP_IFACE, {"Value": Variant("ay", self.value)}, [])

    @method()
    def StopNotify(self):
        """Called when a client unsubscribes from notifications."""
        logging.info(f"Scan notifications disabled on {self._uuid}")
        self.notifying = False

    def update_scan_results(self, results_str):
        """Updates the scan results and notifies subscribers."""
        logging.info(f"Updating scan results: {results_str[:100]}...")  # Log first 100 chars
        self.value = results_str.encode("utf-8")
        if self.notifying:
            # Send actual BLE notification using the Properties interface
            logging.info(f"Sending scan notification with {len(self.value)} bytes")
            self.PropertiesChanged(DBUS_PROP_IFACE, {"Value": Variant("ay", self.value)}, [])

    @method()
    def ReadValue(self, options: "a{sv}") -> "ay":
        logging.info("Scan results read")
        return self.value
    
    @method()
    def WriteValue(self, value: "ay", options: "a{sv}"):
        # Writing any value triggers a scan
        logging.info("Scan characteristic written to. Starting Wi-Fi scan...")
        # Run scan in the background, don't block D-Bus
        asyncio.create_task(
            asyncio.to_thread(scan_wifi_networks)
        )

# This class will hold all our characteristics
class ProvisioningService(ServiceInterface):
    IFACE = "org.bluez.GattService1"

    def __init__(self):
        super().__init__(self.IFACE)
        self.path = SERVICE_PATH
        self._uuid = SERVICE_UUID
        self._primary = True
        self.characteristics = []

    @dbus_property(access=PropertyAccess.READ)
    def UUID(self) -> "s":
        return self._uuid

    @dbus_property(access=PropertyAccess.READ)
    def Primary(self) -> "b":
        return self._primary

    def add_characteristic(self, char):
        self.characteristics.append(char)

    def get_paths(self):
        """Gets all D-Bus paths for this service and its children."""
        paths = {self.path: [self.IFACE]}
        for char in self.characteristics:
            paths[char.path] = [char.IFACE, "org.freedesktop.DBus.Properties"]
            # Add descriptor path
            paths[f"{char.path}/desc0"] = [Descriptor.IFACE, "org.freedesktop.DBus.Properties"]
        return paths

    def get_properties(self):
        """Gets all D-Bus properties for this service."""
        return {
            self.IFACE: {
                "UUID": self._uuid,
                "Primary": self._primary,
                # This tells BlueZ which characteristics belong to this service
                "Characteristics": [char.path for char in self.characteristics],
            }
        }

# This class defines our BLE Advertisement
class Advertisement(ServiceInterface):
    IFACE = "org.bluez.LEAdvertisement1"

    def __init__(self):
        super().__init__(self.IFACE)
        self.path = "/org/example/advertisement1"
        self.ad_type = "peripheral"
        self.local_name = DEVICE_NAME  # Use the configurable device name
        self.service_uuids = [SERVICE_UUID]
        self.include_tx_power = True
        # iOS-friendly settings
        self.discoverable = True
        self.appearance = 0x0000  # Unknown appearance
        # Additional manufacturer data for better visibility
        self.manufacturer_data = {0xFFFF: [0x50, 0x69]}  # "Pi" in hex
        # Add flags for better service visibility
        self.flags = ["general-discoverable", "le-only"]
        # Explicitly include service data
        self.service_data = {SERVICE_UUID: [0x00]}  # Adding minimal service data

    @method()
    def Release(self):
        logging.info("Advertisement released.")

    def get_properties(self):
        props = {
            self.IFACE: {
                "Type": self.ad_type,
                "ServiceUUIDs": self.service_uuids,
                "LocalName": self.local_name,
                "IncludeTxPower": self.include_tx_power,
                "Discoverable": self.discoverable,
                "Appearance": self.appearance,
                "ManufacturerData": self.manufacturer_data,
                "Flags": self.flags,
                "ServiceData": self.service_data
            }
        }
        return props


# --- Simple Auto-Accept Agent ---

class SimpleAgent(ServiceInterface):
    """
    A minimal agent that auto-accepts everything.
    """
    IFACE = "org.bluez.Agent1"
    
    def __init__(self):
        super().__init__(self.IFACE)
        self.path = "/org/example/agent"
    
    @method()
    def Release(self):
        logging.info("Agent released")
    
    @method()
    def RequestPinCode(self, device: "o") -> "s":
        logging.info(f"Auto-accepting pin request for {device}")
        return "0000"
    
    @method()
    def DisplayPinCode(self, device: "o", pincode: "s"):
        logging.info(f"Display pin: {pincode}")
    
    @method()
    def RequestPasskey(self, device: "o") -> "u":
        logging.info(f"Auto-accepting passkey request for {device}")
        return 0
    
    @method()
    def DisplayPasskey(self, device: "o", passkey: "u", entered: "q"):
        logging.info(f"Display passkey: {passkey}")
    
    @method()
    def RequestConfirmation(self, device: "o", passkey: "u"):
        logging.info(f"Auto-confirming {passkey} for {device}")
        # Just return - no exception means accept
        return
    
    @method()
    def RequestAuthorization(self, device: "o"):
        logging.info(f"Auto-authorizing {device}")
        return
    
    @method()
    def AuthorizeService(self, device: "o", uuid: "s"):
        logging.info(f"Auto-authorizing service {uuid} for {device}")
        return
    
    @method()
    def Cancel(self):
        logging.info("Pairing canceled")


# --- Main Application Logic ---

async def main():
    logging.basicConfig(level=logging.INFO)
    global status_char_instance, scan_char_instance

    # Connect to the D-Bus system bus (where BlueZ lives)
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

    # --- 1. Define Service and Characteristics ---
    service = ProvisioningService()
    
    # Add characteristics to the service
    service.add_characteristic(SSIDCharacteristic(service.path))
    service.add_characteristic(PasswordCharacteristic(service.path))
    service.add_characteristic(ConnectCharacteristic(service.path))
    status_char_instance = StatusCharacteristic(service.path)
    service.add_characteristic(status_char_instance)
    scan_char_instance = ScanCharacteristic(service.path)
    service.add_characteristic(scan_char_instance)

    # --- 2. Publish everything on D-Bus ---
    # This makes our Python objects visible to other programs (like BlueZ)
    bus.export(service.path, service)
    for char in service.characteristics:
        bus.export(char.path, char)
        char.add_descriptor(bus)

    # We must also publish all our objects under the DBus.ObjectManager
    # This is how BlueZ discovers all the paths at once
    class ApplicationObjectManager(ServiceInterface):
        def __init__(self, service):
            super().__init__(DBUS_OM_IFACE)
            self.service = service
        
        @method()
        def GetManagedObjects(self) -> "a{oa{sa{sv}}}":
            return self.service.get_paths()
    
    obj_manager = ApplicationObjectManager(service)
    bus.export(APP_PATH, obj_manager)

    # --- 3. Find the Bluetooth adapter ---
    # First, get the ObjectManager to discover available adapters
    try:
        introspection = await bus.introspect(BLUEZ_SERVICE, "/")
    except Exception as e:
        logging.error(f"Failed to introspect BlueZ service. Is bluetoothd running? Error: {e}")
        logging.error("Try: sudo systemctl start bluetooth")
        return
    
    obj = bus.get_proxy_object(BLUEZ_SERVICE, "/", introspection)
    obj_manager = obj.get_interface(DBUS_OM_IFACE)
    objects = await obj_manager.call_get_managed_objects()
    
    adapter_path = None
    for path, interfaces in objects.items():
        if GATT_MANAGER_IFACE in interfaces:
            adapter_path = path
            break
    
    if not adapter_path:
        logging.error("No Bluetooth adapter with GATT support found")
        return
    
    logging.info(f"Using Bluetooth adapter: {adapter_path}")
    
    # --- 4. Power on and configure the adapter ---
    adapter_introspection = await bus.introspect(BLUEZ_SERVICE, adapter_path)
    adapter_obj = bus.get_proxy_object(BLUEZ_SERVICE, adapter_path, adapter_introspection)
    
    # Make sure the adapter is powered on and discoverable
    adapter_props = adapter_obj.get_interface(DBUS_PROP_IFACE)
    await adapter_props.call_set("org.bluez.Adapter1", "Powered", Variant("b", True))
    logging.info("Adapter powered on")
    
    # Set the adapter alias to match our desired device name
    # This overrides the hostname that BlueZ uses by default
    await adapter_props.call_set("org.bluez.Adapter1", "Alias", Variant("s", DEVICE_NAME))
    logging.info(f"Adapter alias set to: {DEVICE_NAME}")
    
    # Enable discoverable mode for BLE advertising (iOS requires this)
    await adapter_props.call_set("org.bluez.Adapter1", "Discoverable", Variant("b", True))
    await adapter_props.call_set("org.bluez.Adapter1", "DiscoverableTimeout", Variant("u", 0))
    logging.info("Adapter set to always discoverable")
    
    # Disable pairing completely - iOS will connect without bonding
    await adapter_props.call_set("org.bluez.Adapter1", "Pairable", Variant("b", False))
    logging.info("Pairing disabled - iOS connects without bonding")
    
    gatt_manager = adapter_obj.get_interface(GATT_MANAGER_IFACE)
    
    try:
        await gatt_manager.call_register_application(APP_PATH, {})
        logging.info("GATT application registered successfully.")
    except Exception as e:
        logging.error(f"Failed to register GATT application: {e}")
        return

    # --- 6. Register our Advertisement with BlueZ ---
    ad_manager = adapter_obj.get_interface(LE_ADVERTISING_MANAGER_IFACE)
    advertisement = Advertisement()    
    bus.export(advertisement.path, advertisement)
    
    try:
        await ad_manager.call_register_advertisement(advertisement.path, {})
        logging.info(f"✅ Advertising as '{advertisement.local_name}' - Device should now be visible in BLE scanners!")
        logging.info(f"   Service UUID: {SERVICE_UUID}")
    except Exception as e:
        logging.error(f"Failed to register advertisement: {e}")
        return

    # --- 5. Run forever ---
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        logging.info("Unregistering application and advertisement...")
        try:
            await gatt_manager.call_unregister_application(APP_PATH)
            await ad_manager.call_unregister_advertisement(advertisement.path)
        except:
            pass
        bus.unexport(advertisement.path)
        bus.unexport(APP_PATH)
        bus.disconnect()
        logging.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())
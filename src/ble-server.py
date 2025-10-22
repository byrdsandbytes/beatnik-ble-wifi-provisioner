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

# --- Our Custom Application ---
# We define our own object paths for our app, service, and characteristics
# This is just a unique name on D-Bus, like a folder path.
APP_PATH = "/org/example/provisioning"
SERVICE_PATH = f"{APP_PATH}/service1"

# Generate your own UUIDs!
SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
SSID_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef1"
PASS_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef2"
CONNECT_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef3"
STATUS_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef4"

# We'll store our data in these global-like variables
class ProvisioningData:
    ssid = b""
    password = b""
    status = b"Ready"

data = ProvisioningData()
status_char_instance = None # Global instance for status updates

# --- Helper: Wi-Fi Connection Logic ---

def update_status(message_str):
    """Updates the status and prepares it for D-Bus."""
    if status_char_instance:
        status_char_instance.update_status(message_str)

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
        cmd = ["nmcli", "device", "wifi", "connect", ssid, "password", password]
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if process.returncode == 0:
            update_status("Success! Connected.")
            logging.info("Successfully connected!")
            # In a real app, you might stop advertising here
        else:
            error_msg = "Failed: Bad Password?"
            if "Error: No network with SSID" in process.stderr:
                error_msg = "Failed: SSID Not Found"
            logging.error(f"Failed to connect: {process.stderr}")
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
        return []

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

    def update_status(self, message_str):
        """Updates the status and notifies subscribers."""
        logging.info(f"Updating status: {message_str}")
        self.value = message_str.encode("utf-8")
        self.emit_properties_changed({"Value": self.value})

    @method()
    def ReadValue(self, options: "a{sv}") -> "ay":
        logging.info(f"Status read: {self.value.decode('utf-8', errors='replace')}")
        return list(self.value)

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
        self.local_name = "Pi-Provisioner"
        self.service_uuids = [SERVICE_UUID]
        self.include_tx_power = True
        # iOS-friendly settings
        self.discoverable = True
        self.appearance = 0x0000  # Unknown appearance

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
    global status_char_instance

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
        logging.info(f"Advertising as '{advertisement.local_name}'...")
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
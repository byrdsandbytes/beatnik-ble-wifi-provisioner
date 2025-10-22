# beatnik-ble-wifi-provisioner

 Python script that allows you to configure Wi-Fi credentials on a Raspberry Pi via Bluetooth Low Energy (BLE) using GATT characteristics. Perfect for headless Raspberry Pi setups where you need to connect to Wi-Fi without a keyboard/monitor.

## Features

- ✅ Advertises as a BLE peripheral device
- ✅ No pairing required (completely open for easy access)
- ✅ Set Wi-Fi SSID and password via BLE
- ✅ Real-time connection status updates
- ✅ Works with iOS (nRF Connect, LightBlue), Android, macOS, and Linux
- ✅ Uses standard GATT characteristics

## Requirements

### Hardware
- Raspberry Pi with built-in Bluetooth (Pi 3, 4, 5, Zero W, etc.)
- Or USB Bluetooth dongle

### Software
- Python 3.7+
- BlueZ 5.50+
- NetworkManager (nmcli)
- dbus-next Python library

## Installation

### 1. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y bluetooth bluez python3-pip
```

### 2. Install Python Dependencies

```bash
pip3 install dbus-next
```

### 3. Download the Script

```bash
# Clone or download ble-test.py to your Raspberry Pi
wget https://your-repo/ble-test.py
# or
git clone https://your-repo/ble-provisioning.git
cd ble-provisioning
```

### 4. Enable Bluetooth Service

```bash
sudo systemctl enable bluetooth
sudo systemctl start bluetooth
```

## Usage

### Running the Script

```bash
# Run with sudo (required for Bluetooth access)
sudo python3 ble-test.py
```

You should see output like:
```
INFO:root:Auto-accept agent registered
INFO:root:Using Bluetooth adapter: /org/bluez/hci0
INFO:root:Adapter powered on
INFO:root:Adapter set to always discoverable
INFO:root:Pairing disabled - iOS connects without bonding
INFO:root:GATT application registered successfully.
INFO:root:Advertising as 'Pi-Provisioner'...
```

### Connecting from Your Device

#### iOS (iPhone/iPad)
1. **Download a BLE app** (required - iOS Settings won't work):
   - **nRF Connect** by Nordic Semiconductor (recommended)
   - **LightBlue** by Punch Through
   
2. Open the BLE app and scan for devices
3. Look for **"Pi-Provisioner"**
4. Tap to connect (no pairing needed)

#### Android
1. Download **nRF Connect** from Google Play
2. Scan and connect to **"Pi-Provisioner"**

#### macOS
1. Download **nRF Connect** or use `bluetoothctl`
2. Connect to **"Pi-Provisioner"**

### Setting Wi-Fi Credentials

Once connected, you'll see a service with 4 characteristics:

| Characteristic | UUID | Type | Description |
|---------------|------|------|-------------|
| **SSID** | `12345678-1234-5678-1234-56789abcdef1` | Write | Write your Wi-Fi network name |
| **Password** | `12345678-1234-5678-1234-56789abcdef2` | Write | Write your Wi-Fi password |
| **Connect** | `12345678-1234-5678-1234-56789abcdef3` | Write | Write any value to trigger connection |
| **Status** | `12345678-1234-5678-1234-56789abcdef4` | Read/Notify | Read connection status |

#### Step-by-Step in nRF Connect:

1. **Connect** to "Pi-Provisioner"
2. **Expand** the service (UUID: `12345678-1234-5678-1234-56789abcdef0`)
3. **Write SSID**: 
   - Tap the "Write" button on the SSID characteristic
   - Select "Text" format
   - Enter your Wi-Fi network name (e.g., "MyHomeWiFi")
   - Send
4. **Write Password**:
   - Tap "Write" on the Password characteristic
   - Select "Text" format
   - Enter your Wi-Fi password
   - Send
5. **Enable Notifications** on Status characteristic (optional but recommended)
6. **Trigger Connection**:
   - Tap "Write" on the Connect characteristic
   - Send any value (e.g., "1")
7. **Watch Status** characteristic for updates:
   - "Connecting to MyHomeWiFi..."
   - "Success! Connected." or "Failed: Bad Password?"

## How It Works

1. **BLE Advertisement**: The script advertises itself as "Pi-Provisioner"
2. **GATT Service**: Exposes a custom service with 4 characteristics
3. **Write Credentials**: Client writes SSID and password
4. **Connection Trigger**: Writing to Connect characteristic triggers `nmcli` to connect
5. **Status Updates**: Status characteristic updates in real-time with connection progress

## Configuration

### Customize Device Name

Edit line 293 in `ble-test.py`:
```python
self.local_name = "Pi-Provisioner"  # Change this to your preferred name
```

### Use Custom UUIDs

Edit lines 27-31:
```python
SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"  # Your custom service UUID
SSID_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef1"
PASS_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef2"
CONNECT_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef3"
STATUS_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef4"
```

### Run on Boot

Create a systemd service:

```bash
sudo nano /etc/systemd/system/ble-provisioning.service
```

Add:
```ini
[Unit]
Description=BLE Wi-Fi Provisioning Service
After=bluetooth.service
Requires=bluetooth.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/pi/ble-test.py
WorkingDirectory=/home/pi
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable ble-provisioning.service
sudo systemctl start ble-provisioning.service
```

Check status:
```bash
sudo systemctl status ble-provisioning.service
```

## Troubleshooting

### "Failed to introspect BlueZ service"
```bash
sudo systemctl start bluetooth
sudo systemctl status bluetooth
```

### Device not appearing in iOS/Android
- Make sure Bluetooth is enabled
- Use a BLE scanning app (not iOS Settings)
- Try restarting the script
- Check if advertising: `sudo hcitool lescan`

### Connection fails immediately
- On iOS: Forget the device in Settings → Bluetooth if it appears there
- Turn Bluetooth OFF and ON
- Restart the script

### "No Bluetooth adapter found"
```bash
# Check if Bluetooth hardware is detected
hciconfig
# Should show hci0 or similar

# If not, check if rfkill is blocking it
sudo rfkill list
sudo rfkill unblock bluetooth
```

### Cannot write characteristics
- Make sure you're using a BLE app (not iOS Settings)
- Check that the script is running with `sudo`
- Look at script logs for errors

## Important Notes

### iOS Limitations
- **iOS Settings → Bluetooth will NOT work** for accessing GATT services
- You **MUST** use a dedicated BLE app like nRF Connect or LightBlue
- This is a limitation of iOS, not this script
- Even after pairing, you need an app to read/write characteristics

### Security Considerations
- ⚠️ This implementation has **no security** - anyone nearby can connect
- Credentials are transmitted without encryption
- Suitable for initial setup in a controlled environment
- For production, consider adding:
  - BLE bonding/pairing
  - Encrypted characteristics
  - Authentication mechanisms
  - Time-limited operation (only allow provisioning for 5 minutes after boot)

### Network Requirements
- Uses NetworkManager (`nmcli`) for Wi-Fi configuration
- Most modern Raspberry Pi OS versions include this by default
- If using a different network manager, modify the `attempt_connection()` function

## Advanced Usage

### Stopping Advertising After Connection

Uncomment line 70 to stop advertising after successful connection:
```python
# In a real app, you might stop advertising here
# Add code to unregister advertisement
```

### Custom Connection Logic

Modify the `attempt_connection()` function (lines 48-78) to:
- Use different network managers (wpa_supplicant, etc.)
- Add VPN configuration
- Set static IP addresses
- Configure additional network settings

## Credits

Built with:
- [dbus-next](https://github.com/altdesktop/python-dbus-next) - Python D-Bus library
- [BlueZ](http://www.bluez.org/) - Linux Bluetooth stack
- NetworkManager - Network configuration

## License

MIT License - feel free to use and modify for your projects!

## Support

For issues and questions:
1. Check the Troubleshooting section above
2. Enable DEBUG logging: Change `logging.INFO` to `logging.DEBUG` on line 367
3. Check BlueZ version: `bluetoothctl --version` (requires 5.50+)
4. Test with nRF Connect first before trying other apps

---

**Pro Tip**: For production IoT devices, consider building a companion mobile app using:
- iOS: CoreBluetooth framework
- Android: Android BLE APIs

This provides a much better user experience than requiring users to install third-party BLE apps!

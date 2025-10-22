# beatnik-ble-wifi-provisioner

A Python script that allows you to configure Wi-Fi credentials on a Raspberry Pi via Bluetooth Low Energy (BLE) using GATT characteristics. Perfect for headless Raspberry Pi setups where you need to connect to Wi-Fi without a keyboard/monitor.

> 🚀 **Quick Start**: Want to get started in 5 minutes? Check out [QUICKSTART.md](QUICKSTART.md)

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

Follow these steps to install and set up the BLE Wi-Fi provisioner on your Raspberry Pi (or any Linux system with Bluetooth).

### Step 1: Install System Dependencies

First, make sure your system has the required Bluetooth packages and Python:

```bash
sudo apt-get update
sudo apt-get install -y bluetooth bluez python3-full python3-pip
```

**What this does:**
- `bluetooth` & `bluez` - The Linux Bluetooth stack
- `python3-full` - Complete Python installation (needed for venv on newer systems)
- `python3-pip` - Python package installer

### Step 2: Clone/Download This Repository

```bash
# Option A: Clone with git
git clone https://github.com/byrdsandbytes/beatnik-ble-wifi-provisioner.git
cd beatnik-ble-wifi-provisioner

# Option B: Download manually
# Download the repository as a ZIP and extract it, then:
cd beatnik-ble-wifi-provisioner
```

### Step 3: Set Up Python Virtual Environment

Now run the automated setup script:

```bash
# Make the setup script executable (only needed once)
chmod +x setup-venv.sh

# Run the setup script
./setup-venv.sh
```

**What this does:**
1. Creates a virtual environment in `venv/` directory
2. Activates the virtual environment
3. Upgrades pip to the latest version
4. Installs all Python dependencies from `requirements.txt` (currently just `dbus-next`)

You should see output like:
```
Creating Python virtual environment...
Activating virtual environment...
Installing dependencies...
...
✅ Setup complete!
```

### Step 4: Enable Bluetooth Service

Make sure the Bluetooth service is running:

```bash
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Verify it's running
sudo systemctl status bluetooth
```

You should see `active (running)` in green.

### Step 5: Test the Installation

Activate the virtual environment and run the script:

```bash
# Activate the virtual environment
source venv/bin/activate

# Run the BLE server (requires sudo for Bluetooth access)
sudo venv/bin/python3 src/ble-server.py
```

**Important:** Even when using `sudo`, you must specify the full path to the Python interpreter in the venv (`venv/bin/python3`), otherwise sudo will use the system Python which doesn't have the packages installed.

You should see output like:
```
INFO:root:Using Bluetooth adapter: /org/bluez/hci0
INFO:root:Adapter powered on
INFO:root:Adapter set to always discoverable
INFO:root:Pairing disabled - iOS connects without bonding
INFO:root:GATT application registered successfully.
INFO:root:Advertising as 'Pi-Provisioner'...
```

✅ **Success!** Your Raspberry Pi is now advertising as a BLE device.

### Step 6: Connect from Your Phone

See the [Connecting from Your Device](#connecting-from-your-device) section below for instructions on how to connect and provision Wi-Fi.

## Usage

### Running the Script

Every time you want to run the BLE provisioning server:

```bash
# 1. Navigate to the project directory
cd beatnik-ble-wifi-provisioner

# 2. Activate the virtual environment
source venv/bin/activate

# 3. Run the server with sudo
sudo venv/bin/python3 src/ble-server.py
```

**Why `sudo venv/bin/python3`?**
- `sudo` is required for Bluetooth low-level access
- `venv/bin/python3` ensures you're using the Python with installed packages
- Just `sudo python3` would use the system Python without your packages!

**To stop the server:**
Press `Ctrl+C` in the terminal.

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

**Easy Method** - Edit the constant at the top of `src/ble-server.py` (around line 17):

```python
DEVICE_NAME = "Pi-Provisioner"  # <-- Change this to your preferred name
```

This is the name that will appear when scanning for BLE devices in apps like nRF Connect.

**Examples:**
- `DEVICE_NAME = "MyPi"` → Shows as "MyPi" in scanners
- `DEVICE_NAME = "IoT-Device-001"` → Shows as "IoT-Device-001"
- `DEVICE_NAME = "WiFi Setup"` → Shows as "WiFi Setup"

After changing the name, restart the script for changes to take effect.

### Use Custom UUIDs

Edit lines 27-31 in `src/ble-server.py`:
```python
SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"  # Your custom service UUID
SSID_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef1"
PASS_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef2"
CONNECT_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef3"
STATUS_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef4"
```

### Run on Boot (Auto-start as a Service)

To make the BLE provisioner start automatically when your Raspberry Pi boots:

**Step 1:** Create a systemd service file:

```bash
sudo nano /etc/systemd/system/ble-provisioning.service
```

**Step 2:** Add this configuration (update paths if needed):

```ini
[Unit]
Description=BLE Wi-Fi Provisioning Service
After=bluetooth.service network.target
Requires=bluetooth.service

[Service]
Type=simple
# Update this path to match your installation location
ExecStart=/home/pi/beatnik-ble-wifi-provisioner/venv/bin/python3 /home/pi/beatnik-ble-wifi-provisioner/src/ble-server.py
WorkingDirectory=/home/pi/beatnik-ble-wifi-provisioner
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

**Step 3:** Enable and start the service:

```bash
# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable ble-provisioning.service

# Start the service now
sudo systemctl start ble-provisioning.service
```

**Step 4:** Check that it's running:

```bash
# Check service status
sudo systemctl status ble-provisioning.service

# View live logs
sudo journalctl -u ble-provisioning.service -f
```

**Managing the service:**
```bash
# Stop the service
sudo systemctl stop ble-provisioning.service

# Restart the service
sudo systemctl restart ble-provisioning.service

# Disable auto-start on boot
sudo systemctl disable ble-provisioning.service

# View recent logs
sudo journalctl -u ble-provisioning.service -n 50
```

## Troubleshooting

> 📖 **Detailed Troubleshooting**: For comprehensive troubleshooting steps, especially if you can't see your device when scanning, check out [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### Virtual Environment Issues

**"No module named 'dbus_next'" when running with sudo**
```bash
# Make sure you're using the venv Python, not system Python:
sudo venv/bin/python3 src/ble-server.py

# NOT just:
sudo python3 src/ble-server.py  # ❌ This uses system Python
```

**"venv/bin/python3: No such file or directory"**
```bash
# The virtual environment wasn't created. Run setup again:
./setup-venv.sh
```

**"Permission denied: ./setup-venv.sh"**
```bash
# Make the script executable:
chmod +x setup-venv.sh
./setup-venv.sh
```

**Want to recreate the virtual environment from scratch?**
```bash
# Delete the old venv
rm -rf venv

# Run setup again
./setup-venv.sh
```

### Bluetooth Issues

**"Failed to introspect BlueZ service"
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

## Quick Reference

### First-time Setup
```bash
# 1. Install system packages
sudo apt-get update
sudo apt-get install -y bluetooth bluez python3-full python3-pip

# 2. Clone the repository
git clone https://github.com/byrdsandbytes/beatnik-ble-wifi-provisioner.git
cd beatnik-ble-wifi-provisioner

# 3. Run setup script
chmod +x setup-venv.sh
./setup-venv.sh

# 4. Enable Bluetooth
sudo systemctl enable bluetooth
sudo systemctl start bluetooth
```

### Running the Server
```bash
cd beatnik-ble-wifi-provisioner
source venv/bin/activate
sudo venv/bin/python3 src/ble-server.py
```

### Common Commands
```bash
# Check Bluetooth status
sudo systemctl status bluetooth

# View Bluetooth devices
hciconfig

# Restart Bluetooth
sudo systemctl restart bluetooth

# Recreate virtual environment
rm -rf venv && ./setup-venv.sh

# Check if process is running
ps aux | grep ble-server
```

**Pro Tip**: For production IoT devices, consider building a companion mobile app using:
- iOS: CoreBluetooth framework
- Android: Android BLE APIs

This provides a much better user experience than requiring users to install third-party BLE apps!

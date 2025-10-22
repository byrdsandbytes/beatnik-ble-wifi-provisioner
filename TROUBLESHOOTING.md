# Troubleshooting Guide

## Can't See the Device When Scanning

If you're not seeing your "Pi-Provisioner" (or your custom device name) when scanning with nRF Connect or other BLE apps:

### 1. Check the Server is Running

```bash
# Make sure the script is running without errors
sudo venv/bin/python3 src/ble-server.py
```

Look for this message:
```
✅ Advertising as 'Pi-Provisioner' - Device should now be visible in BLE scanners!
```

### 2. Verify Bluetooth is Working

```bash
# Check Bluetooth adapter status
hciconfig

# Should show something like:
# hci0:   Type: Primary  Bus: USB
#         BD Address: XX:XX:XX:XX:XX:XX  ACL MTU: 1021:8  SCO MTU: 64:1
#         UP RUNNING
```

If it says "DOWN", enable it:
```bash
sudo hciconfig hci0 up
```

### 3. Check if Device is Advertising

```bash
# Use hcitool to scan for BLE devices
sudo hcitool lescan

# Or use bluetoothctl
bluetoothctl
[bluetooth]# scan on
```

You should see your device appear in the list.

### 4. Restart Bluetooth Service

Sometimes the Bluetooth service needs a restart:

```bash
# Restart Bluetooth
sudo systemctl restart bluetooth

# Wait a few seconds, then restart your script
sudo venv/bin/python3 src/ble-server.py
```

### 5. Check for Conflicting Processes

```bash
# Check if another process is using Bluetooth
ps aux | grep python | grep ble
ps aux | grep bluetoothd

# Kill any old instances
sudo pkill -f ble-server.py
```

### 6. Increase Bluetooth Visibility (Linux/Raspberry Pi)

```bash
# Make sure Bluetooth is discoverable
bluetoothctl
[bluetooth]# discoverable on
[bluetooth]# pairable on
[bluetooth]# quit
```

### 7. Phone/App Specific Issues

#### iOS (iPhone/iPad)
- **Use nRF Connect or LightBlue** - iOS Settings won't show BLE devices
- Go to **Settings → Bluetooth** and make sure it's ON
- Close and reopen the BLE scanning app
- Sometimes you need to turn Bluetooth OFF and back ON
- Make sure Location Services are enabled (iOS requires this for BLE scanning)

#### Android
- Make sure **Location Services** are enabled (required for BLE scanning)
- Grant location permissions to nRF Connect
- Try clearing the app cache: Settings → Apps → nRF Connect → Clear Cache

#### macOS
- Use nRF Connect from the App Store
- Or use command line: `blueutil` (install via Homebrew)

### 8. Check Signal Strength

BLE has limited range (typically 10-30 meters):
- **Move closer** to the Raspberry Pi
- Make sure there are **no metal objects** blocking the signal
- Avoid areas with lots of **Wi-Fi interference**

### 9. Verify the Device Name

Check what name is being advertised:

```bash
# In your src/ble-server.py, look for line ~17:
DEVICE_NAME = "Pi-Provisioner"  # <-- This is what appears in scanners
```

If you changed this, restart the script for changes to take effect.

### 10. Check BlueZ Version

```bash
bluetoothctl --version
```

You need BlueZ 5.50 or higher. If you have an older version:

```bash
# On Raspberry Pi OS / Debian / Ubuntu
sudo apt-get update
sudo apt-get install --upgrade bluez
```

### 11. View Detailed Logs

Run with debug logging to see what's happening:

```python
# Edit src/ble-server.py, change line ~373:
logging.basicConfig(level=logging.DEBUG)  # Changed from INFO to DEBUG
```

Then run the script and look for errors.

### 12. Test with Multiple Devices

Try scanning with different devices/apps:
- **iOS**: nRF Connect, LightBlue
- **Android**: nRF Connect
- **macOS**: nRF Connect, BluetoothExplorer
- **Linux**: `bluetoothctl`, `hcitool lescan`

If it works on one device but not another, the issue is likely with the device/app, not your Pi.

## Still Not Working?

### Hardware Issues

1. **Check if Bluetooth hardware exists:**
   ```bash
   lsusb  # For USB Bluetooth adapters
   dmesg | grep -i bluetooth
   ```

2. **Make sure it's not blocked:**
   ```bash
   sudo rfkill list
   # If blocked, unblock it:
   sudo rfkill unblock bluetooth
   ```

3. **Try a different Bluetooth adapter** (if using USB)

### Software Conflicts

Some software can interfere with Bluetooth:
- **PulseAudio** - Can conflict with Bluetooth audio (not relevant here, but good to know)
- **Other BLE services** - Make sure you're not running multiple BLE servers

### Reset Everything

When all else fails:

```bash
# Stop the script
# Ctrl+C

# Restart Bluetooth
sudo systemctl stop bluetooth
sudo systemctl start bluetooth

# Clear any old Bluetooth cache
sudo rm -rf /var/lib/bluetooth/*

# Restart Bluetooth again
sudo systemctl restart bluetooth

# Run your script
sudo venv/bin/python3 src/ble-server.py
```

## Common Error Messages

### "Failed to introspect BlueZ service"
```bash
sudo systemctl start bluetooth
```

### "No Bluetooth adapter with GATT support found"
- Your Bluetooth adapter doesn't support BLE
- Try a different adapter or check compatibility

### "Failed to register advertisement"
- Usually means another process is advertising
- Stop other BLE services and try again

### "dbus.exceptions.DBusException: org.bluez.Error.NotPermitted"
- Need to run with `sudo`
- Make sure bluetoothd is running

## Need More Help?

1. Check the logs: `sudo journalctl -u bluetooth -n 50`
2. Enable debug mode in the script
3. Try the script on a different Raspberry Pi to rule out hardware issues
4. Ask for help with **complete error messages** and your:
   - Raspberry Pi model
   - OS version: `cat /etc/os-release`
   - BlueZ version: `bluetoothctl --version`
   - Python version: `python3 --version`

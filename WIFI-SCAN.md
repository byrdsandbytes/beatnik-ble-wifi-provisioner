# WiFi Scan Feature

## Overview

The BLE WiFi provisioner now includes a **WiFi Scan** characteristic that allows you to scan for available WiFi networks before attempting to connect. This makes it easier to see what networks are in range and their signal strength.

## How to Use

### Using nRF Connect (iOS/Android)

1. **Connect** to your device (e.g., "beatnik-server")
2. **Find the WiFi Scan characteristic** (UUID: `12345678-1234-5678-1234-56789abcdef5`)
3. **Enable Notifications** (tap the 🔔 icon) - This lets you see results automatically
4. **Trigger Scan** - Tap "Write" and send any value (e.g., "1")
5. **Wait 3-5 seconds** for the scan to complete
6. **Read Results** - The characteristic will update with the scan results

### Result Format

Results are returned as a semicolon-separated list of networks:

```
NetworkName|SignalStrength|Security;NetworkName2|SignalStrength|Security
```

**Example:**
```
MyHomeWiFi|85|WPA2;GuestNetwork|72|Open;Office5G|65|WPA3;NeighborWiFi|45|WPA2
```

**Fields:**
- **Network Name** (SSID) - The name of the WiFi network
- **Signal Strength** - Number from 0-100 (higher is better)
- **Security** - Type of encryption (WPA2, WPA3, Open, etc.)

### Reading the Results

**Good Signal Strength:**
- 80-100: Excellent
- 60-79: Good
- 40-59: Fair
- Below 40: Poor

**Security Types:**
- `Open` - No password required (not secure!)
- `WPA2` - Standard modern security
- `WPA3` - Latest, most secure
- `WEP` - Old, insecure (avoid if possible)

## Example Workflow

```
1. Connect to device via BLE
2. Write "1" to WiFi Scan characteristic
3. Read result: "HomeWiFi|88|WPA2;GuestNet|70|Open"
4. Choose "HomeWiFi" (strong signal, secure)
5. Write "HomeWiFi" to SSID characteristic
6. Write password to Password characteristic
7. Write "1" to Connect characteristic
8. Monitor Status for "Success!"
```

## Technical Details

### Implementation

The scan uses `nmcli` (NetworkManager command-line tool):

```bash
nmcli -t -f SSID,SIGNAL,SECURITY device wifi list
```

This command:
- `-t` - Machine-readable output (colon-separated)
- `-f` - Select specific fields
- Lists all visible WiFi networks with their properties

### Scan Time

- **Typical**: 3-5 seconds
- **Maximum**: 15 seconds (timeout)
- During scan, the characteristic shows "Scanning..."

### Limitations

1. **Hidden Networks**: Networks with hidden SSIDs won't appear in the scan results
2. **Refresh Rate**: The scan uses cached results from the last few seconds (nmcli behavior)
3. **Requires NetworkManager**: This feature needs `nmcli` to be installed and working

### Error Messages

| Message | Meaning |
|---------|---------|
| `Scanning...` | Scan is in progress |
| `No networks found` | No WiFi networks detected (check adapter) |
| `Scan failed` | Error running nmcli |
| `Scan timeout` | Took longer than 15 seconds |
| `Error: [message]` | Specific error occurred |

## Troubleshooting

### "Scan failed" Error

```bash
# Check if nmcli is working
nmcli device wifi list

# If you get an error, try:
sudo systemctl restart NetworkManager
```

### "No networks found"

- Make sure you're in range of WiFi networks
- Check if the WiFi adapter is working: `nmcli radio wifi`
- Enable WiFi if disabled: `nmcli radio wifi on`

### Scan Never Completes

- Check the server logs for errors
- NetworkManager might be busy or not responding
- Try restarting the service: `sudo systemctl restart NetworkManager`

### Results Show Strange Characters

- Some network names contain special characters
- This is normal - the client app should handle UTF-8 encoding

## Code Reference

### Scan Function Location

`src/ble-server.py` - Line ~60-105

```python
def scan_wifi_networks():
    """Scans for available Wi-Fi networks using nmcli."""
    # ... implementation
```

### Characteristic Definition

`src/ble-server.py` - Line ~295-322

```python
class ScanCharacteristic(BaseGATTCharacteristic):
    def __init__(self, service_path):
        super().__init__(
            service_path,
            SCAN_CHAR_UUID,
            ["read", "write", "notify"],
            "WiFi Network Scan"
        )
```

## Future Enhancements

Possible improvements for this feature:

1. **JSON Format** - Return results as structured JSON instead of delimited string
2. **Filtering** - Only show networks above a certain signal strength
3. **Sorting** - Sort by signal strength (strongest first)
4. **Auto-Refresh** - Periodically update scan results
5. **Channel Info** - Include WiFi channel and frequency
6. **MAC Addresses** - Include BSSID for network identification

## API Reference

### UUID
```
SCAN_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef5"
```

### Properties
- **Read**: Get current scan results
- **Write**: Trigger a new scan (any value)
- **Notify**: Receive updates when scan completes

### Write Values
- Any value triggers a scan (commonly use "1" or "scan")
- The actual value is ignored

### Read Values
Returns a UTF-8 encoded string in this format:
```
SSID1|signal1|security1;SSID2|signal2|security2;...
```

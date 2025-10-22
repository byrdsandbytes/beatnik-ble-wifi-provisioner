# Quick Start Guide

## 5-Minute Setup

Follow these steps to get the BLE Wi-Fi provisioner running on your Raspberry Pi.

### 1️⃣ Install System Packages

```bash
sudo apt-get update
sudo apt-get install -y bluetooth bluez python3-full python3-pip
```

### 2️⃣ Clone the Repository

```bash
git clone https://github.com/byrdsandbytes/beatnik-ble-wifi-provisioner.git
cd beatnik-ble-wifi-provisioner
```

### 3️⃣ Run Setup Script

```bash
chmod +x setup-venv.sh
./setup-venv.sh
```

Wait for the setup to complete. You should see `✅ Setup complete!`

### 4️⃣ Enable Bluetooth

```bash
sudo systemctl enable bluetooth
sudo systemctl start bluetooth
```

### 5️⃣ Run the Server

```bash
source venv/bin/activate
sudo venv/bin/python3 src/ble-server.py
```

You should see:
```
INFO:root:Advertising as 'Pi-Provisioner'...
```

**✅ Done!** Your Pi is now advertising via BLE.

---

## Connect from Your Phone

### iOS/Android

1. **Download nRF Connect** app (from App Store or Google Play)
2. Open the app and tap **Scan**
3. Find **"Pi-Provisioner"** in the list
4. Tap to **Connect**
5. Expand the service (UUID: `12345678...`)
6. You'll see 4 characteristics:
   - **SSID** - Write your Wi-Fi network name
   - **Password** - Write your Wi-Fi password
   - **Connect** - Write any value to trigger connection
   - **Status** - Read/notify to see connection status

### Provisioning Steps

1. **Write SSID**: Tap Write → Select "Text" → Enter network name → Send
2. **Write Password**: Tap Write → Select "Text" → Enter password → Send
3. **Enable Notifications** on Status (tap the 🔔 icon)
4. **Trigger Connection**: Tap Write on Connect → Send any value
5. **Watch Status**: Should show "Connecting..." then "Success! Connected."

---

## Stop the Server

Press `Ctrl+C` in the terminal.

---

## Auto-Start on Boot (Optional)

Want it to start automatically? See the **Run on Boot** section in [README.md](README.md#run-on-boot-auto-start-as-a-service).

---

## Troubleshooting

**"No module named 'dbus_next'"**
```bash
# Use the venv Python, not system Python:
sudo venv/bin/python3 src/ble-server.py
```

**Can't see the device in nRF Connect?**
```bash
# Restart Bluetooth and try again:
sudo systemctl restart bluetooth
sudo venv/bin/python3 src/ble-server.py
```

**More help?** Check the full [README.md](README.md) for detailed troubleshooting.

---

## What's Next?

- **Customize the device name**: Edit `src/ble-server.py` line 293
- **Change UUIDs**: Edit lines 27-31 in `src/ble-server.py`
- **Set up auto-start**: See README.md for systemd service setup
- **Add security**: Consider adding pairing/bonding for production use

Happy provisioning! 🚀

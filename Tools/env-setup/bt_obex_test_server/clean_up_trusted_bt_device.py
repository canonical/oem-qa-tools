#!/usr/bin/env python3

import pydbus

# Connect to system bus
bus = pydbus.SystemBus()

# Try standard adapter path directly (most common on Ubuntu)
adapter_path = "/org/bluez/hci0"
try:
    adapter = bus.get("org.bluez", adapter_path)["org.bluez.Adapter1"]
    print("Adapter found at", adapter_path)
except Exception:
    # Fallback: list all adapters via bluetoothctl equivalent logic
    manager = bus.get("org.bluez", "/")["org.freedesktop.DBus.ObjectManager"]
    objects = manager.GetManagedObjects()
    adapter_path = None
    for path, interfaces in objects.items():
        if "org.bluez.Adapter1" in interfaces:
            adapter_path = path
            break

    if not adapter_path:
        print("Run: bluetoothctl show | grep Controller")
        raise Exception(
            "No adapter found. Check: hciconfig or bluetoothctl list"
        )

    adapter = bus.get("org.bluez", adapter_path)["org.bluez.Adapter1"]
    print("Adapter found at", adapter_path)

# Get and remove all devices
try:
    devices = adapter.GetDevices()
    print(f"Found {len(devices)} devices. Removing all...")

    for device_path in devices:
        try:
            bus.get("org.bluez", adapter_path)[
                "org.bluez.Adapter1"
            ].RemoveDevice(device_path)
            print(f"Removed: {device_path}")
        except Exception as e:
            print(f"Skip {device_path}: {e}")

except Exception as e:
    print(f"GetDevices failed: {e}. List directly from objects...")
    # Alternative: scan all objects for Device1 interfaces
    manager = bus.get("org.bluez", "/")["org.freedesktop.DBus.ObjectManager"]
    objects = manager.GetManagedObjects()
    for path, interfaces in objects.items():
        if "org.bluez.Device1" in interfaces and adapter_path in path:
            try:
                bus.get("org.bluez", adapter_path)[
                    "org.bluez.Adapter1"
                ].RemoveDevice(path)
                print(f"Removed: {path}")
            except Exception:
                pass

print("Cleanup complete.")

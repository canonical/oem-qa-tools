import gi
from pydbus import SessionBus, SystemBus
from gi.repository import GLib
import os

SAVE_PATH = os.path.expanduser("~/Downloads")

class BluetoothAutoTruster:
    def __init__(self):
        self.bus = SystemBus()

        # config bt device to make it work
        self.config_device("hci0")

        # The Object Manager allows us to see all devices
        self.manager = self.bus.get("org.bluez", "/")
        self.manager.onInterfacesAdded = self.on_interfaces_added
        
        print("[*] Monitoring for new devices to Auto-Trust...")
        self.check_existing_devices()

    def config_device(self, device: str):
        adapter = self.bus.get("org.bluez", f"/org/bluez/{device}")
        adapter.Discoverable = True
        print("[*] Discoverable:", adapter.Discoverable)

    def trust_device(self, path):
        """Helper to set Trusted=True on a device path"""
        try:
            device = self.bus.get("org.bluez", path)
            # Check if it's actually a device interface
            if hasattr(device, "Trusted"):
                device.Trusted = True
                device_name = getattr(device, "Name", "Unknown")
                print(f"[+] Successfully Trusted: {device_name} ({path})")
        except Exception as e:
            print(f"[!] Could not trust {path}: {e}")

    def on_interfaces_added(self, path, interfaces):
        """Triggered when a new device is found or paired"""
        if "org.bluez.Device1" in interfaces:
            print(f"[*] New device interface detected at {path}")
            self.trust_device(path)

    def check_existing_devices(self):
        """Trusts devices that are already known/paired"""
        objs = self.manager.GetManagedObjects()
        for path, interfaces in objs.items():
            if "org.bluez.Device1" in interfaces:
                self.trust_device(path)

class ObexReceiver:
    dbus = """
    <node>
        <interface name="org.bluez.obex.Agent1">
            <method name="AuthorizePush">
                <arg type="o" name="transfer" direction="in"/>
                <arg type="s" name="path" direction="out"/>
            </method>
            <method name="Cancel"></method>
            <method name="Release"></method>
        </interface>
    </node>
    """

    def AuthorizePush(self, transfer_path):
        print(f"[*] Incoming connection on D-Bus path: {transfer_path}")
        
        bus = SessionBus()
        try:
            # Get the transfer object properties
            transfer = bus.get("org.bluez.obex", transfer_path)
            # The property is usually 'Name', not 'Filename' in the Transfer1 interface
            props = transfer["org.bluez.obex.Transfer1"]
            filename = props.get("Name", "received_file")
            
            print(f"[+] Accepting file: {filename}")
            full_path = os.path.join(SAVE_PATH, filename)
            
            # Create directory if it doesn't exist
            os.makedirs(SAVE_PATH, exist_ok=True)
            
            return full_path
        except Exception as e:
            print(f"[!] Authorization error: {e}")
            # Fallback path if property lookup fails
            return os.path.join(SAVE_PATH, "incoming_file")

    def Cancel(self):
        print("[-] Transfer cancelled.")

    def Release(self):
        print("[!] Agent released.")

def main():
    # Auto Trust all connection
    BluetoothAutoTruster()

    bus = SessionBus()
    
    # 1. Publish the agent
    agent_path = "/test/obex/agent"
    bus.publish("org.bluez.obex.Agent1", ObexReceiver())
    
    # 2. Register the agent with the Manager
    try:
        manager = bus.get("org.bluez.obex", "/org/bluez/obex")
        manager.RegisterAgent(agent_path)
        print("[*] OBEX Agent Registered. Waiting for files...")
    except Exception as e:
        print(f"[!] Registration failed: {e}")
        print("Ensure 'obexd' is running (check systemctl --user status obex)")
        return

    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        loop.quit()

if __name__ == "__main__":
    main()

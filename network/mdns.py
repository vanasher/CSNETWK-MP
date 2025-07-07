from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser
import socket

# announcing and browsing services
zeroconf = Zeroconf()

hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)

service_info = ServiceInfo(
	"_lsnp._udp.local.",
    f"{hostname}._lsnp._udp.local.",
    addresses=[socket.inet_aton(ip_address)],
    port=54321,
    properties={},
    server=f"{hostname}.local."
)

# register service
zeroconf.register_service(service_info)
print(f"Service registered as {hostname} on {ip_address}:{54321}")


# to discover other services
class LSNPListener:
    def remove_service(self, zeroconf, type, name):
        print(f"Service removed: {name}")

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if info:
            addr = socket.inet_ntoa(info.addresses[0])
            print(f"Discovered {name} at {addr}:{info.port}")

zeroconf = Zeroconf()
listener = LSNPListener()
browser = ServiceBrowser(zeroconf, "_lsnp._udp.local.", listener)
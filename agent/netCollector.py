from scapy.all import sniff, IP, TCP, UDP, ICMP
import socket

import docker

client = docker.from_env()
containers = client.containers.list()

container_ips = []
for container in containers:
    ip = container.attrs['NetworkSettings']['IPAddress']
    container_ips.append(ip)
    print(f"Контейнер {container.name}: {ip}")

from scapy.all import sniff, IP



def container_traffic_filter(packet):
    if IP in packet:
        return (packet[IP].src in CONTAINER_IPS) and (packet[IP].dst in CONTAINER_IPS)
    return False

sniff(
    iface="docker0",
    lfilter=container_traffic_filter,
    prn=lambda p: p.show(),
    count=0
)

# Фильтр BPF для исходящего трафика
BPF_FILTER = f"src host {LOCAL_IP}"

def process_packet(packet):
    if IP in packet:
        ip_layer = packet[IP]
        dst_ip = ip_layer.dst
        protocol = ip_layer.proto
        
        # Вывод информации
        print(f"[+] Protocol: {protocol}")
        print(f"    Destination IP: {dst_ip}")
        print(f"    Destination Port: {protocol}")
        print("-" * 40)

# Запуск захвата трафика
print(f"[*] Starting sniffing on local IP: {LOCAL_IP}")
sniff(filter=BPF_FILTER, prn=process_packet, count=0)
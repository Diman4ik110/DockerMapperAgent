from scapy.all import sniff, IP, TCP, UDP
import docker

# Получаем IP контейнеров
def get_container_ips():
    client = docker.from_env()
    containers = client.containers.list()
    return [c.attrs['NetworkSettings']['IPAddress'] for c in containers]

# Фильтрация трафика между контейнерами
def process_packet(packet):
    if IP in packet:
        src_ip = packet[IP].src
        dst_ip = packet[IP].dst
        proto = "TCP" if TCP in packet else "UDP" if UDP in packet else "Other"
        print(f"[+] {proto} {src_ip} -> {dst_ip}")

# Основная функция
if __name__ == "__main__":
    container_ips = get_container_ips()
    print(f"IP контейнеров: {container_ips}")
    
    # Фильтр: только трафик между контейнерами
    sniff(
        iface="docker0",
        filter="ip",
        lfilter=lambda pkt: (
            IP in pkt and
            pkt[IP].src in container_ips and
            pkt[IP].dst in container_ips
        ),
        prn=process_packet,
        count=0
    )
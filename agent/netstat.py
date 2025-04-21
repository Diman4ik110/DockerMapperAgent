import aiodocker
import asyncio
from configparser import ConfigParser
from collections import defaultdict

previous_stats = defaultdict(dict)

async def getNetSpeed(interval):
    async with aiodocker.Docker() as docker:
        while True:
            async with aiohttp.ClientSession() as session:
                current_time = asyncio.get_event_loop().time()
                containers = await docker.containers.list()
                
                for container in containers:
                    container_id = container.id
                    
                    # Получаем статистику и обрабатываем возможный список
                    stats = await container.stats(stream=False)
                    stats_dict = stats[0] if isinstance(stats, list) else stats
                    
                    networks = stats_dict.get("networks", {})
                    if not networks:
                        continue
                    
                    for interface, data in networks.items():
                        rx_bytes = data['rx_bytes']
                        tx_bytes = data['tx_bytes']
                        print(networks.items())
                        prev_data = previous_stats[container_id].get(interface)
                        if prev_data:
                            prev_rx, prev_tx, prev_time = prev_data
                            time_diff = current_time - prev_time
                            
                            if time_diff > 0:
                                rx_speed = (rx_bytes - prev_rx) * 8 / time_diff / 1_000_000
                                tx_speed = (tx_bytes - prev_tx) * 8 / time_diff / 1_000_000
                                print(container_id, rx_speed, tx_speed, rx_bytes, tx_bytes)
                                
                        previous_stats[container_id][interface] = (rx_bytes, tx_bytes, current_time)
                        
                existing_ids = {c.id for c in containers}
                for cont_id in list(previous_stats.keys()):
                    if cont_id not in existing_ids:
                        del previous_stats[cont_id]

                await asyncio.sleep(interval)

if __name__ == "__main__":
    config = ConfigParser()
    config.read('/etc/DockerNetAgent/agent.conf')
    interval = config.getint('global', 'readinterval', fallback=2)
    
    try:
        asyncio.run(getNetSpeed(interval))
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
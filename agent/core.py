from agent.config import *
import asyncio
import logging
import datetime
import aiodocker
from aiodocker.exceptions import DockerError
from aiohttp.client_exceptions import ClientConnectorError
import os
import aiohttp  # Замена requests на асинхронный aiohttp
from agent.buffer import *
import time
from collections import defaultdict

class Agent:
    def __init__(self, config):
        self.previous_stats = defaultdict(dict)
        self.contStatBuffer = Buffer("containerStats.json")
        self.config = config
        self.headers = {'Content-Type': 'application/json', 'Accept-Charset': 'UTF-8'}  # Исправлено: словарь вместо строки
        self.logger = logging.getLogger(__name__)

    async def run(self):
        """Основной цикл работы агента."""
        self.logger.info("Агент запущен.")
        try:
            tasks = [
                asyncio.create_task(self.sendContainerList()),
                asyncio.create_task(self.sendNetList()),
                asyncio.create_task(self.sendNetConnection()),
                asyncio.create_task(self.writeContainerMetricsLoop()),
                asyncio.create_task(self.sendMetrics()),
                # asyncio.create_task(self.sendVolInfo()),
                asyncio.create_task(self.sendNetStat()),
            ]
            # Ждём завершения всех задач
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            self.logger.error(f"Ошибка в работе агента: {e}")

    async def chechRegister(self):
        url = f"{self.config['global']['entrypoint']}/api/v1/agents/checkRegister/"
        async with aiohttp.ClientSession() as session:
            agentData = {"authtoken": self.config['global']['authtoken']}
            print(self.config['global']['authtoken'])
            async with session.post(url, json=agentData, headers=self.headers, ssl=False) as response:
                if response.status == 200:
                    return True
                return False
            
    async def register(self):
        url = f"{self.config['global']['entrypoint']}/api/v1/agents/registerAgent/"
        async with aiohttp.ClientSession() as session:
            print(os.uname().nodename)
            agentData = {"token": self.config['global']['token'],"hostname": os.uname().nodename}
            async with session.post(url, json=agentData, headers=self.headers, ssl=False) as response:
                if response.status == 200:
                    # Получаем JSON из ответа
                    response_data = await response.json()
                    # Извлекаем токен (предположим, что ключ "token")
                    self.config.set_param("global","authtoken", response_data.get('authToken'))
                    print(self.config['global']['authtoken'])
                    return True
                return False

    async def sendNetStat(self):
        async with aiodocker.Docker() as docker:
            async with aiohttp.ClientSession() as session:
                while True:
                    containers = await docker.containers.list(all=True)
                    
                    for container in containers:
                        contID = container.id
                        
                        # Получаем статистику и обрабатываем возможный список
                        stats = await container.stats(stream=False)
                        stats_dict = stats[0] if isinstance(stats, list) else stats
                        
                        networks = stats_dict.get("networks", {})
                        
                        for interface, data in networks.items():
                            rx_bytes = data['rx_bytes']
                            tx_bytes = data['tx_bytes']
                            current_time = time.time()
                            prev_data = self.previous_stats[contID].get(interface)
                            if prev_data:
                                prev_rx, prev_tx, prev_time = prev_data
                                time_diff = current_time - prev_time
                                url = f"{self.config['global']['entrypoint']}/api/v1/netinfo/sendNetworkStat/"
                                if time_diff == 0:
                                    netStat = {
                                        "lastUpdate": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "contID": contID,
                                        "rxSpeed": 0,
                                        "txSpeed": 0,
                                        "rxBytes" : 0,
                                        "txBytes": 0
                                    }
                                if time_diff > 0:
                                    rx_speed = (rx_bytes - prev_rx) * 8 / time_diff / 1_000_000
                                    tx_speed = (tx_bytes - prev_tx) * 8 / time_diff / 1_000_000
                                    
                                    netStat = {
                                        "lastUpdate": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "contID": contID,
                                        "rxSpeed": rx_speed,
                                        "txSpeed": tx_speed,
                                        "rxBytes" : rx_bytes,
                                        "txBytes": tx_bytes
                                    }
                                await session.post(url, json=netStat, headers=self.headers, ssl=False)
                                        
                            self.previous_stats[contID][interface] = (rx_bytes, tx_bytes, current_time)
                                
                    existing_ids = {c.id for c in containers}
                    for cont_id in list(self.previous_stats.keys()):
                        if cont_id not in existing_ids:
                            del self.previous_stats[cont_id]
                    await asyncio.sleep(int(self.config['global']['readinterval']))

    async def sendContainerList(self):
        while True:
            await asyncio.sleep(int(self.config['global']['sendinterval']))
            async with aiodocker.Docker() as docker:
                try:
                    async with aiohttp.ClientSession() as session:
                        containers = await docker.containers.list(all=True)
                        containerList = []
                        for container in containers:
                            contInfo = await container.show()
                            containerList.append({
                                    'id': contInfo['Id'],
                                    'name': contInfo['Name'].strip('/'),
                                    'image': contInfo['Config']['Image'],
                                    'hostname': os.uname().nodename,
                                })
                        del containers
                        url = f"{self.config['global']['entrypoint']}/api/v1/containers/sendContList/"
                        await session.post(url, json=containerList, headers=self.headers, ssl=False)
                except DockerError as e:
                    print(f"Ошибка Docker: {e.message} (Код: {e.status})")
                except ClientConnectorError:
                    print("Не удалось подключиться к Docker API. Проверьте доступность Docker.")
                except asyncio.CancelledError:
                    print("Операция была отменена.")
                    raise
                except Exception as e:
                    print(f"Непредвиденная ошибка: {str(e)}")
                finally:
                    await docker.close()
    
    async def sendMetrics(self):
        while True:
            await asyncio.sleep(int(self.config['global']['sendinterval']))
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"{self.config['global']['entrypoint']}/api/v1/containers/sendContainerStats/"
                    await session.post(url, json=self.contStatBuffer.read(), headers=self.headers, ssl=False)
                    self.contStatBuffer.clear()
            except asyncio.CancelledError:
                print("Операция была отменена.")
                raise
            except Exception as e:
                print(f"Непредвиденная ошибка: {str(e)}")

    async def sendNetList(self):
        while True:
            await asyncio.sleep(int(self.config['global']['sendinterval']))
            async with aiodocker.Docker() as docker:
                try:
                    # Задержка из конфига (если нужно повторение)
                    networks = await docker.networks.list()
                    async with aiohttp.ClientSession() as session:
                        for network in networks:
                            network = {
                                    'netID': network['Id'],
                                    'name': network['Name']
                                }
                            url = f"{self.config['global']['entrypoint']}/api/v1/netinfo/sendNetList/"
                            await session.post(url, json=network, headers=self.headers, ssl=False)
                    del networks
                except DockerError as e:
                    print(f"Ошибка Docker: {e.message} (Код: {e.status})")
                except ClientConnectorError:
                    print("Не удалось подключиться к Docker API. Проверьте доступность Docker.")
                except asyncio.CancelledError:
                    print("Операция была отменена.")
                    raise
                except Exception as e:
                    print(f"Непредвиденная ошибка: {str(e)}")
                finally:
                    await docker.close()
            
    async def sendNetConnection(self):
        while True:
            await asyncio.sleep(int(self.config['global']['sendinterval']))
            async with aiodocker.Docker() as docker:
                try:
                    containers = await docker.containers.list(all=True)
                    
                    connList = []
                    async with aiohttp.ClientSession() as session:
                        for container in containers:
                            containerData = await container.show()
                            containerId = containerData['Id']
                            
                            networks = containerData.get('NetworkSettings', {}).get('Networks', {})
                            for netInfo in networks.values():
                                if 'NetworkID' in netInfo:
                                    connList.append({
                                        'contID': containerId,
                                        'netID': netInfo['NetworkID']
                                    })
                    
                            url = f"{self.config['global']['entrypoint']}/api/v1/netinfo/sendNetConnection/"
                            await session.post(url, json=connList, headers=self.headers, ssl=False)
                    del containers
                except DockerError as e:
                    print(f"Ошибка Docker: {e.message} (Код: {e.status})")
                except ClientConnectorError:
                    print("Не удалось подключиться к Docker API. Проверьте доступность Docker.")
                except asyncio.CancelledError:
                    print("Операция была отменена.")
                    raise
                except Exception as e:
                    print(f"Непредвиденная ошибка: {str(e)}")
                finally:
                    await docker.close()
            
    async def writeContainerMetricsLoop(self):
        """Отдельный цикл для записи метрик."""
        while True:
            await self.writeContainerMetrics()
            await self.sendContainerMetrics()
            await self.sendNetStat()
            self.contStatBuffer.clear()
            
    async def sendContainerMetrics(self):
        while True:
            await asyncio.sleep(int(self.config['global']['sendinterval']))
            async with aiohttp.ClientSession() as session:
                url = f"{self.config['global']['entrypoint']}/api/v1/netinfo/sendNetConnection/"
                await session.post(url, json=self.contStatBuffer.read(), headers=self.headers, ssl=False)
                
    async def writeContainerMetrics(self):
        while True:
            await asyncio.sleep(int(self.config['global']['readinterval']))
            async with aiodocker.Docker() as docker:
                try:
                    containers = await docker.containers.list(all=True)
                    # Основная информация о контейнере
                    for container in containers:
                        contInfo = await container.show()
                        contID = contInfo['Id']
                        status = contInfo['State']['Status']
                        # Получаем статистику (возвращает список!)
                        stats_list = await container.stats(stream=False)
                        # Если статус exited или stopped, добавляем в буфер пустое значение
                        if status != "running":
                            # Добавляем данные в буфер
                            self.contStatBuffer.add({
                                "contID": contID,
                                "lastUpdate": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "loadCPU": 0,
                                "loadRAM": 0,
                                "status": status
                            })
                            continue
                        # Проверяем, что список не пуст
                        if not stats_list:
                            continue
                        
                        # Берем первый элемент списка (последняя статистика)
                        stats = stats_list[0]
                        
                        # Вычисляем метрики CPU
                        CPUDelta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
                        SystemDelta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
                        loadCPU = (CPUDelta / SystemDelta) * stats['cpu_stats']['online_cpus'] * 100

                        # Вычисляем использование памяти
                        loadRAM = stats['memory_stats']['usage'] / 1024 / 1024  # Переводим в килобайты

                        # Добавляем данные в буфер
                        self.contStatBuffer.add({
                            "contID": contID,
                            "lastUpdate": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "loadCPU": loadCPU,
                            "loadRAM": loadRAM,
                            "status": status
                        })
                    del containers
                except DockerError as e:
                    print(f"Ошибка Docker: {e.message} (Код: {e.status})")
                except ClientConnectorError:
                    print("Не удалось подключиться к Docker API. Проверьте доступность Docker.")
                except asyncio.CancelledError:
                    print("Операция была отменена.")
                    raise
                except Exception as e:
                    print(f"Непредвиденная ошибка: {str(e)}")
                finally:
                    await docker.close()
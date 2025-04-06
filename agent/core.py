import asyncio
import logging
import datetime
import aiodocker
from aiodocker.exceptions import DockerError
from aiohttp.client_exceptions import ClientConnectorError
import os
import aiohttp  # Замена requests на асинхронный aiohttp
from agent.buffer import *

class Agent:
    def __init__(self, config):
        self.contStatBuffer = Buffer("containerStats.json")
        self.config = config
        self.headers = {'Content-Type': 'application/json', 'Accept-Charset': 'UTF-8'}  # Исправлено: словарь вместо строки
        self.logger = logging.getLogger(__name__)

    async def run(self):
        """Основной цикл работы агента."""
        self.logger.info("Агент запущен.")
        try:
            while True:
                tasks = [
                    asyncio.create_task(self.sendContainerList()),
                    asyncio.create_task(self.sendNetList()),
                    asyncio.create_task(self.sendNetConnection()),
                    asyncio.create_task(self.sendHostInfo()),
                    asyncio.create_task(self.writeContainerMetricsLoop()),
                    asyncio.create_task(self.sendMetrics())
                ]
                # Ждём завершения всех задач
                await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            self.logger.error(f"Ошибка в работе агента: {e}")

    async def registerAgent(self):
        regUrl = f"{self.config['global']['entrypoint']}/api/v1/agents/checkRegistration/"
        authToken = [{"authToken": self.config['global']['authtoken']}]
        async with aiohttp.ClientSession() as session:  # Используем aiohttp вместо requests
            async with session.post(regUrl, json=authToken, headers=self.headers) as response:
                if response.status == 200:
                    self.logger.info("Агент успешно зарегистрирован!")
                self.logger.error("Регистрация агента не удалась!")

    async def sendContainerList(self):
        while True:
            await asyncio.sleep(int(self.config['global']['sendinterval']))
            async with aiodocker.Docker() as docker:
                try:
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
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=containerList, headers=self.headers) as response:
                            if response.status == 200:
                                print("1")
                except DockerError as e:
                    print(f"Ошибка Docker: {e.message} (Код: {e.status})")
                except ClientConnectorError:
                    print("Не удалось подключиться к Docker API. Проверьте доступность Docker.")
                except asyncio.CancelledError:
                    print("Операция была отменена.")
                    raise
                except Exception as e:
                    print(f"Непредвиденная ошибка: {str(e)}")
    async def sendMetrics(self):
        while True:
            await asyncio.sleep(int(self.config['global']['sendinterval']))
            try:
                print("dfsdf")
                url = f"{self.config['global']['entrypoint']}/api/v1/containers/sendContainerStats/"
                async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=self.contStatBuffer.read(), headers=self.headers) as response:
                            if response.status == 200:
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
                    netList = []
                    for network in networks:
                        netList.append({
                                'netID': network['Id'],
                                'name': network['Name']
                            })
                        url = f"{self.config['global']['entrypoint']}/api/v1/netinfo/sendNetList/"
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=netList, headers=self.headers) as response:
                            if response.status == 200:
                                print("1")
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
            
    
    async def sendNetConnection(self):
        while True:
            await asyncio.sleep(int(self.config['global']['sendinterval']))
            async with aiodocker.Docker() as docker:
                try:
                    containers = await docker.containers.list(all=True)
                    
                    connList = []
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
                    del containers
                    url = f"{self.config['global']['entrypoint']}/api/v1/netinfo/sendNetConnection/"
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=connList, headers=self.headers) as response:
                            if response.status == 200:
                                print("1")
                except DockerError as e:
                    print(f"Ошибка Docker: {e.message} (Код: {e.status})")
                except ClientConnectorError:
                    print("Не удалось подключиться к Docker API. Проверьте доступность Docker.")
                except asyncio.CancelledError:
                    print("Операция была отменена.")
                    raise
                except Exception as e:
                    print(f"Непредвиденная ошибка: {str(e)}")
    async def sendHostInfo(self):
        while True:
            await asyncio.sleep(int(self.config['global']['sendinterval']))
            information = [{'hostname': os.uname().nodename, 'IPAddress': "1.1.1.1"}]
            url = f"{self.config['global']['entrypoint']}/api/v1/hosts/sendHostInfo/"
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=information, headers=self.headers) as response:
                    if response.status == 200:
                        print("1")
            
    async def writeContainerMetricsLoop(self):
        """Отдельный цикл для записи метрик."""
        while True:
            await self.writeContainerMetrics()
            await asyncio.sleep(int(self.config['global']['readinterval']))

    async def writeContainerMetrics(self):
        while True:
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
from aiohttp import JsonPayload
import docker
import time
import configparser
import os
from pathlib import Path
import json

def loadConfig(config_path='agent.conf'):
    """
    Функция для загрузки конфигурации из файла
    
    Параметры:
    config_path (str): путь к файлу конфигурации
    
    Возвращает:
    dict: словарь с настройками
    """
    
    # Проверяем существование файла
    if not Path(config_path).is_file():
        raise FileNotFoundError(f"Файл конфигурации {config_path} не найден")
    
    # Создаем объект конфигурации
    config = configparser.ConfigParser()
    
    try:
        # Читаем файл
        config.read(config_path)
        
        # Конвертируем в словарь
        config_dict = {}
        for section in config.sections():
            config_dict[section] = {}
            for option in config.options(section):
                config_dict[section][option] = config.get(section, option)
                
        return config_dict
        
    except configparser.Error as e:
        raise ValueError(f"Ошибка при чтении конфигурации: {e}")
# Функция получающая имя машины
def getHostInfo():
    """
    Получает информацию о хостовой системе.
    
    Возвращает:
    list: Список словарей с информацией о хостовой системе
    """
    information = []
    information += [{'hostname': os.uname().nodename}]
    return json.dumps(information)

# Получаем список контейнеров
def getContainers():
    # Инициализируем клиент Docker
    client = docker.DockerClient(base_url="unix://var/run/docker.sock")
    try:
        # Получаем список контейнеров
        containers = client.containers.list(all=True)
        containerList = []
        for container in containers:
            # Форматируем результат в читаемый вид
            containerList.append({
                'id' : container.id,
                'name': container.name,
                'hostname': os.uname().nodename,
            })
        return json.dumps(containerList)
    except docker.errors.APIError as e:
        print(f"Ошибка Docker API: {e}")
        return []
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return []
    
# Получаем список сетей
def getNetList():
    """
    Получает список сетей, к которым подключены контейнеры.
    
    Возвращает:
    list: Список словарей с информацией о сетях
    """
    client = docker.DockerClient(base_url="unix://var/run/docker.sock")
    try:
        networks = client.networks.list()
        result = []
        for network in networks:
            result.append({
                'netID' : network.id,
                'name': network.name
            })
        return json.dumps(result)
    except docker.errors.APIError as e:
        print(f"Ошибка Docker API: {e}")
        return []
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return []

# Получаем подключения между контейнерами
def getNetConnection():
    """
    Получает список сетей и ID контейнеров подключенных к ним.
    
    Возвращает:
    list: Список словарей с информацией о сетях и контейнерах
    """
    client = docker.DockerClient(base_url="unix://var/run/docker.sock")
    try:
        # Получаем список всех контейнеров (включая остановленные)
        containers = client.containers.list(all=True)
        result = []
        for container in containers:
            container.reload()  # Обновляем данные контейнера
            networks = container.attrs['NetworkSettings']['Networks']
            for net in networks.values():
                # Извлекаем NetworkID и NetworkName
                network_id = net['NetworkID']
                result.append({
                    'netID': network_id,
                    'contID': container.id,
                })
        return json.dumps(result, indent=4)
    except docker.errors.APIError as e:
        print(f"Ошибка Docker API: {e}")
        return []
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return []

# Запуск программы
if __name__ == '__main__':
    # Загружаем конфигурацию
    config = loadConfig('/etc/DockerNetAgent/agent.conf')
    # Запускаем главный цикл программы
    while True:
        # Отправляем на сервер данные о сетях
        os.system(f"curl -X POST http://{config['global']['server']}:{config['global']['port']}/api/v1/netinfo/sendNetList/ -H 'Content-Type: application/json' -d '{getNetList()}'")
        # Отправляем на сервер данные о виртуальной машине
        os.system(f"curl -X POST http://{config['global']['server']}:{config['global']['port']}/api/v1/hosts/sendHostInfo/ -H 'Content-Type: application/json' -d '{getHostInfo()}'")
        # Отправляем на сервер данные о контейнерах
        os.system(f"curl -X POST http://{config['global']['server']}:{config['global']['port']}/api/v1/containers/sendContList/ -H 'Content-Type: application/json' -d '{getContainers()}'")
        # Отправляем на сервер данные о сетях
        os.system(f"curl -X POST http://{config['global']['server']}:{config['global']['port']}/api/v1/netinfo/sendNetConnection/ -H 'Content-Type: application/json' -d '{getNetConnection()}'")
        # Задержка перед отправкой данных
        time.sleep(int(config['global']['sendinterval']))
        
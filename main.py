import time, requests, configparser, socket, os, docker, json

def loadConfig(config_path):
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
    information = [{'hostname': os.uname().nodename, 'IPAddress': getLocalIP()}]
    return json.dumps(information)

def getLocalIP():
    try:
        # Создаем временное соединение к публичному DNS
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google Public DNS
        localIP = s.getsockname()[0]
        s.close()
        return localIP
    except Exception:
        try:
            # Альтернативный способ
            return socket.gethostbyname(socket.gethostname())
        except:
            return "127.0.0.1"  # Возвращаем localhost если другие методы не сработали

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
    regUrl = f"http://{config['global']['server']}:{config['global']['port']}/api/v1/agents/checkRegistration/"
    authToken = [{"authToken": config['global']['authtoken']}]
    print()
    regReq = requests.post(regUrl, data=json.dumps(authToken))
    # Проверяем результат регистрации
    if regReq.status_code != 200:
        print('Не удалось авторизоваться на сервере')
        exit()
    # Запускаем главный цикл программы
    while True:
        headers = f"{'content-type': 'application/json', 'Accept-Charset': 'UTF-8'}"
        url1 = f"http://{config['global']['server']}:{config['global']['port']}/api/v1/netinfo/sendNetList/"
        url2 = f"http://{config['global']['server']}:{config['global']['port']}/api/v1/hosts/sendHostInfo/"
        url3 = f"http://{config['global']['server']}:{config['global']['port']}/api/v1/containers/sendContList/"
        url4 = f"http://{config['global']['server']}:{config['global']['port']}/api/v1/netinfo/sendNetConnection/"
        # Отправляем на сервер список сетей
        req1 = requests.post(url1, data=getNetList(), headers=headers)
        # Отправляем на сервер данные о хосте
        req2 = requests.post(url2, data=getHostInfo(), headers=headers)
        # Отправляем на сервер данные о контейнерах
        req3 = requests.post(url3, data=getContainers(), headers=headers)
        # Отправляем на сервер данные о подключениях
        req4 = requests.post(url4, data=getNetConnection(), headers=headers)
        # Очищаем память
        del url1, url2, url3, url4, headers, regReq, regUrl, req1, req2, req3, req4
        # Задержка перед отправкой данных
        time.sleep(int(config['global']['sendinterval']))
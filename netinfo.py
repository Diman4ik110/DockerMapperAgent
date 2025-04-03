# Класс для получения информации о сети контейнера
class Netinfo:
    def __init__(self, net, ip, mask):
        self.net = net
        self.ip = ip
        self.mask = mask
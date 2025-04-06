import configparser
class Config:
    def __init__(self, config_path):
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
                    
            self._data = config_dict
        except configparser.Error as e:
            raise ValueError(f"Ошибка при чтении конфигурации: {e}")
    # Метод для доступа к данным через квадратные скобки (например, config['global'])
    def __getitem__(self, key):
        return self._data[key]
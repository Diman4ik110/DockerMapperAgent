import configparser

class Config:
    def __init__(self, config_path):
        # Создаем объект конфигурации
        self.config = configparser.ConfigParser()
        self.configPath = config_path
        try:
            # Читаем файл
            self.config.read(config_path)
            
            # Конвертируем в словарь
            configDict = {}
            for section in self.config.sections():
                configDict[section] = {}
                for option in self.config.options(section):
                    configDict[section][option] = self.config.get(section, option)
                    
            self._data = configDict
        except configparser.Error as e:
            raise ValueError(f"Ошибка при чтении конфигурации: {e}")
            
    # Метод для доступа к данным через квадратные скобки
    def __getitem__(self, key):
        return self._data[key]

        
    def set_param(self, section: str, option: str, value: str) -> None:
        """Установка параметра с сохранением в файл"""
        try:
            # Обновляем словарь
            if section not in self._data:
                self._data[section] = {}
            self._data[section][option] = value
            
            # Обновляем ConfigParser
            if not self.config.has_section(section):
                self.config.add_section(section)
            self.config.set(section, option, value)
            
            # Перезаписываем файл
            with open(self.configPath, 'w') as f:
                self.config.write(f)
        except Exception as e:
            raise RuntimeError(f"Ошибка сохранения параметра: {e}")
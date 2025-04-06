import json
import os

class Buffer:
    def __init__(self, filename="buffer.json"):
        self.filename = filename

    def add(self, data):
        """Добавить данные в буфер."""
        with open(self.filename, 'a') as f:
            json.dump(data, f)
            f.write('\n')  # Каждая запись на новой строке

    def read(self):
        """Прочитать все данные из буфера."""
        if not os.path.exists(self.filename):
            return []
        with open(self.filename, 'r') as f:
            return [json.loads(line) for line in f]

    def clear(self):
        """Очистить буфер."""
        if os.path.exists(self.filename):
            os.remove(self.filename)
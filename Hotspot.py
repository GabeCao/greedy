import math


class Hotspot:
    def __init__(self, x, y, num):
        self.x = x
        self.y = y
        self.num = num

    def get_x(self):
        return self.x

    def get_y(self):
        return self.y

    def get_num(self):
        return self.num

    def get_distance_between_hotspot(self, hotspot):
        x = self.x - hotspot.get_x()
        y = self.y - hotspot.get_y()
        return math.sqrt((x ** 2) + (y ** 2))
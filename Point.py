import math


class Point:
    def __init__(self, x, y, time):
        self.x = x
        self.y = y
        self.time = time

    def get_x(self):
        return self.x

    def get_y(self):
        return self.y

    def get_time(self):
        return self.time

    def get_distance_between_point_and_hotspot(self, hotspot):
        x = self.x - hotspot.get_x()
        y = self.y - hotspot.get_y()
        return math.sqrt((x ** 2) + (y ** 2))
from sklearn.preprocessing import LabelBinarizer
import math
from Hotspot import Hotspot
from Point import Point
import numpy as np


class Env:
    def __init__(self):
        # 当前环境state
        self.state = []
        # mc移动花费的时间
        self.move_time = 0
        # 一个回合最大的时间，用秒来表示，早上八点到晚上10点，十四个小时，总共 14 * 3600 秒的时间
        # 如果self.get_evn_time() 得到的时间大于这个时间，则表示该回合结束
        self.one_episode_time = 14 * 3600
        # sensor 和 mc的能量信息
        self.sensors_mobile_charger = {}
        # 初始化所有的sensor,mc 的能量信息
        self.set_sensors_mobile_charger()
        # 初始化self.sensors_mobile_charger 和 self.sensors
        # self.set_sensors_mobile_charger()
        # 获得所有的hotspot
        self.hotspots = []
        # 初始化hotspots
        self.set_hotspots()
        # 记录当前时刻所在的hotspot，在环境初始化的时候设置为base_station
        self.current_hotspot = self.hotspots[0]

        # mc移动速度
        self.speed = 5
        # mc 移动消耗的能量
        self.mc_move_energy_consumption = 0
        # mc 给sensor充电消耗的能量
        self.mc_charging_energy_consumption = 0
        # 充电惩罚值
        self.charging_penalty = -1
        # 最近一次mc 移动和给sensor充电花费的能量，因为在charging trajectory 中，最后一次不能算作在 trajectory中
        self.last_time_mc_move_energy_consumption = 0
        self.last_time_mc_charging_energy_consumption = 0
        self.CS = []
        self.reward = 0
        self.current_reward = 0

    def set_sensors_mobile_charger(self):
        # [0.7 * 6 * 1000, 0.6, 0, True]  依次代表：上一次充电后的剩余能量，能量消耗的速率，上一次充电的时间，
        # 是否已经死掉(计算reward的惩罚值时候使用，避免将一个sensor计算死掉了多次)，
        # 最后一个标志位，表示senor在该hotpot，还没有被充过电，如果已经充过了为True，避免被多次充电
        self.sensors_mobile_charger['0'] = [0.7 * 6 * 1000, 0.5, 0, True, False]
        self.sensors_mobile_charger['1'] = [0.3 * 6 * 1000, 0.3, 0, True, False]
        self.sensors_mobile_charger['2'] = [0.9 * 6 * 1000, 0.5, 0, True, False]
        self.sensors_mobile_charger['3'] = [0.5 * 6 * 1000, 0.3, 0, True, False]
        self.sensors_mobile_charger['4'] = [0.2 * 6 * 1000, 0.2, 0, True, False]
        self.sensors_mobile_charger['5'] = [0.4 * 6 * 1000, 0.3, 0, True, False]
        self.sensors_mobile_charger['6'] = [1 * 6 * 1000, 0.6, 0, True, False]
        self.sensors_mobile_charger['7'] = [0.3 * 6 * 1000, 0.5, 0, True, False]
        self.sensors_mobile_charger['8'] = [1 * 6 * 1000, 0.3, 0, True, False]
        self.sensors_mobile_charger['9'] = [0.9 * 6 * 1000, 0.2, 0, True, False]
        self.sensors_mobile_charger['10'] = [0.8 * 6 * 1000, 0.2, 0, True, False]
        self.sensors_mobile_charger['11'] = [0.5 * 6 * 1000, 0.4, 0, True, False]
        self.sensors_mobile_charger['12'] = [0.4 * 6 * 1000, 0.2, 0, True, False]
        self.sensors_mobile_charger['13'] = [0.6 * 6 * 1000, 0.2, 0, True, False]
        self.sensors_mobile_charger['14'] = [0.3 * 6 * 1000, 0.2, 0, True, False]
        self.sensors_mobile_charger['15'] = [0.9 * 6 * 1000, 0.6, 0, True, False]
        self.sensors_mobile_charger['16'] = [0.8 * 6 * 1000, 0.4, 0, True, False]
        self.sensors_mobile_charger['MC'] = [1000 * 1000, 50]

    def set_hotspots(self):
        # 这是编号为0 的hotspot，也就是base_stattion,位于整个充电范围中心
        base_station = Hotspot((116.333 - 116.318) * 85000 / 2, (40.012 - 39.997) * 110000 / 2, 0)
        self.hotspots.append(base_station)
        # 读取hotspot.txt 的文件，获取所有的hotspot，放入self.hotspots中
        path = 'hotspot.txt'
        with open(path) as file:
            for line in file:
                data = line.strip().split(',')
                hotspot = Hotspot(float(data[0]), float(data[1]), int(data[2]))
                self.hotspots.append(hotspot)

    # 根据hotspot 的编号，在self.hotspots 中找到对应的hotpot
    def find_hotspot_by_num(self, num):
        for hotspot in self.hotspots:
            if hotspot.get_num() == num:
                return hotspot

    def initial_is_charged(self):
        for key, value in self.sensors_mobile_charger.items():
            if key != 'MC':
                value[4] = False

    # 传入一个action, 得到下一个state，reward，和 done(是否回合结束)的信息
    def one_step(self, action):
        # 记录执行当前action得到的reward
        self.current_reward = 0
        hotspot_num = int(action.split(',')[0])
        staying_time = int(action.split(',')[1])
        # 初始化是否充电
        self.initial_is_charged()
        # 距离当前hotspot的距离
        next_hotspot = self.find_hotspot_by_num(hotspot_num)
        distance = next_hotspot.get_distance_between_hotspot(self.current_hotspot)

        # 到达hotspot后，开始等待，mc减去移动消耗的能量，并更新当前属于的hotspot
        self.move_time += distance / self.speed
        start_seconds = self.get_evn_time()

        self.mc_move_energy_consumption += self.sensors_mobile_charger['MC'][1] * distance
        self.sensors_mobile_charger['MC'][0] = self.sensors_mobile_charger['MC'][0] \
                                               - self.sensors_mobile_charger['MC'][1] * distance

        self.current_hotspot = next_hotspot

        # 判断环境中的sensor 是否有死掉的
        for key, value in self.sensors_mobile_charger.items():
            if key == 'MC':
                break
            sensor_energy_after_last_time_charging = value[0]
            # 当前sensor 电量消耗的速率
            sensor_consumption_ratio = value[1]
            # 上一次的充电时间
            previous_charging_time = value[2]
            # 当前sensor 的剩余电量
            evn_time = self.get_evn_time()
            sensor_reserved_energy = sensor_energy_after_last_time_charging - \
                                     (evn_time - previous_charging_time) * sensor_consumption_ratio
            if (sensor_reserved_energy < 0) and (value[3] is True):
                value[3] = False
                self.reward += self.charging_penalty
                self.current_reward += self.charging_penalty
                print('sensor   ' + key + '  死了  ')

        # 结束等待的时间
        end_seconds = start_seconds + staying_time * 5 * 60
        # 将action 添加到 self.CS
        self.CS.append(action)
        # 获得所有的sensor 轨迹点
        for i in range(17):
            sensor_path = 'sensor数据五秒/' + str(i) + '.txt'
            with open(sensor_path) as sensor_file:
                for sensor_line in sensor_file:

                    # 检查当前sensor 是否在该hotspot 已经被充过电了，如果是，跳出循环
                    sensor_is_charged = self.sensors_mobile_charger[str(i)]
                    if sensor_is_charged[4] is True:
                        break
                    sensor_line = sensor_line.strip().split(',')
                    point = Point(float(sensor_line[0]), float(sensor_line[1]), sensor_line[2])
                    point_time = self.str_to_seconds(point.get_time())

                    if start_seconds <= point_time <= end_seconds and point.get_distance_between_point_and_hotspot(
                            self.current_hotspot) < 60:
                        # 取出sensor
                        sensor = self.sensors_mobile_charger[str(i)]
                        # 上一次充电后的电量
                        sensor_energy_after_last_time_charging = sensor[0]
                        # 当前sensor 电量消耗的速率
                        sensor_consumption_ratio = sensor[1]
                        # 上一次的充电时间
                        previous_charging_time = sensor[2]
                        # 当前sensor 的剩余电量
                        sensor_reserved_energy = sensor_energy_after_last_time_charging - \
                                                 (point_time - previous_charging_time) * sensor_consumption_ratio
                        # 当前sensor 的剩余寿命
                        rl = sensor_reserved_energy / sensor_consumption_ratio
                        # 如果剩余寿命大于两个小时
                        if rl >= 2 * 3600:
                            self.reward += 0
                            self.current_reward += 0
                        # 如果剩余寿命在0 到 两个小时
                        elif 0 < rl < 2 * 3600:
                            # mc 给该sensor充电， 充电后更新剩余能量
                            self.mc_charging_energy_consumption += 6 * 1000 - sensor_reserved_energy
                            self.sensors_mobile_charger['MC'][0] = self.sensors_mobile_charger['MC'][0] \
                                                                   - (6 * 1000 - sensor_reserved_energy)
                            # 设置sensor 充电后的剩余能量 是满能量
                            sensor[0] = 6 * 1000
                            # 更新被充电的时间
                            sensor[2] = point_time
                            # 在该hotspot 第一次被充电
                            sensor[4] = True
                            # 加上得到的奖励,需要先将 rl 的单位先转化成小时
                            rl = rl / 3600
                            self.reward += math.exp(-rl)
                            self.current_reward += math.exp(-rl)
                        else:
                            if sensor[3] is True:
                                self.reward += self.charging_penalty
                                self.current_reward += self.charging_penalty
                                sensor[3] = False
        return self.current_reward
    def step(self, action):
        self.current_reward = 0
        hotspot_num = int(action.split(',')[0])
        staying_time = int(action.split(',')[1])

        # 得到下一个hotspot
        hotspot = self.find_hotspot_by_num(hotspot_num)
        # 当前hotspot 和 下一个hotspot间的距离,得到移动花费的时间，添加到self.move_time 里
        distance = hotspot.get_distance_between_hotspot(self.current_hotspot)
        time = distance / self.speed
        self.move_time += time

        for key, value in self.sensors_mobile_charger.items():
            if key == 'MC':
                break
            sensor_energy_after_last_time_charging = value[0]
            # 当前sensor 电量消耗的速率
            sensor_consumption_ratio = value[1]
            # 上一次的充电时间
            previous_charging_time = value[2]
            # 当前sensor 的剩余电量
            evn_time = self.get_evn_time()
            sensor_reserved_energy = sensor_energy_after_last_time_charging - \
                                     (evn_time - previous_charging_time) * sensor_consumption_ratio
            # 如果剩余能量小于0，且value[3] is True，则sensor第一次死亡，reward 减去惩罚值
            if (sensor_reserved_energy < 0) and (value[3] is True):
                value[3] = False
                self.reward += self.charging_penalty
                with open('result.txt', 'a') as res:
                    res.write('sensor  ' + key + '  死了  ' + '\n')
                print('sensor   ' + key + '  死了  ')
        # 更新self.current_hotspot 为 action 中选择的 hotspot
        self.current_hotspot = hotspot
        # 更新mc 移动消耗的能量
        self.mc_move_energy_consumption += self.sensors_mobile_charger['MC'][1] * distance
        self.last_time_mc_move_energy_consumption = self.sensors_mobile_charger['MC'][1] * distance
        # 更新mc的剩余能量，减去移动消耗的能量
        self.sensors_mobile_charger['MC'][0] = self.sensors_mobile_charger['MC'][0] \
                                               - self.sensors_mobile_charger['MC'][1] * distance

        # 获取当前时间段,下面的path中使用，加8是因为从8点开始
        start_wait_seconds = self.get_evn_time()
        # hour = int(start_wait_seconds / 1200) + 1
        # 将在hotspot_num 等待的时间 添加到state中的CS
        self.state[2 * (hotspot_num - 1)] += 1
        self.state[2 * (hotspot_num - 1) + 1] += staying_time
        # self.CS.append(action)
        # mc 结束等待后环境的时间
        end_wait_seconds = self.get_evn_time()
        # 在一次执行action 的过程中，sensor只能被充电一次
        self.initial_is_charged()

        # if hour > 42:
        #     hour = 42
        # path = 'hotspot中sensor的访问情况/' + str(hour) + '时间段/' + str(hotspot_num) + '.txt'
        # # 读取文件，得到在当前时间段，hotspot_num 的访问情况，用字典保存。key: sensor 编号；value: 访问次数
        # hotspot_num_sensor_arrived_times = {}
        # with open(path) as f:
        #     for line in f:
        #         data = line.strip().split(',')
        #         hotspot_num_sensor_arrived_times[data[0]] = data[1]
        # 一共17个sensor，现在更新每个sensor 的信息

        for i in range(17):
            # 读取第i 个sensor 的轨迹点信息
            sensor_path = 'sensor数据五秒/' + str(i) + '.txt'
            with open(sensor_path) as f:
                for point_line in f:
                    # 检查当前sensor 是否在该hotspot 已经被充过电了，如果是，跳出循环
                    sensor_is_charged = self.sensors_mobile_charger[str(i)]
                    if sensor_is_charged[4] is True:
                        break

                    data = point_line.strip().split(',')
                    point_time = self.str_to_seconds(data[2])
                    point = Point(float(data[0]), float(data[1]), data[2])

                    # 如果第 i 个sensor的轨迹点的时间 小于end_wait_seconds且大于start_wait_seconds，
                    # 同时轨迹点和hotspot 的距离小于60，则到达该hotspot
                    if (start_wait_seconds <= point_time <= end_wait_seconds) and (point.get_distance_between_point_and_hotspot(self.current_hotspot) < 60):
                        # 取出sensor
                        sensor = self.sensors_mobile_charger[str(i)]
                        # 上一次充电后的电量
                        sensor_energy_after_last_time_charging = sensor[0]
                        # 当前sensor 电量消耗的速率
                        sensor_consumption_ratio = sensor[1]
                        # 上一次的充电时间
                        previous_charging_time = sensor[2]
                        # 当前sensor 的剩余电量
                        sensor_reserved_energy = sensor_energy_after_last_time_charging - \
                                                 (point_time - previous_charging_time) * sensor_consumption_ratio
                        # 当前sensor 的剩余寿命
                        rl = sensor_reserved_energy / sensor_consumption_ratio
                        # 如果剩余寿命大于两个小时
                        if rl >= 2 * 3600:
                            self.current_reward += 0
                            self.reward += 0
                        # 如果剩余寿命在0 到 两个小时
                        elif 0 < rl < 2 * 3600:
                            # 更新mc 的sensor充的电量
                            self.mc_charging_energy_consumption += 6 * 1000 - sensor_reserved_energy
                            self.last_time_mc_charging_energy_consumption = 6 * 1000 - sensor_reserved_energy
                            # mc 给该sensor充电， 充电后更新剩余能量
                            self.sensors_mobile_charger['MC'][0] = self.sensors_mobile_charger['MC'][0] \
                                                                   - (6 * 1000 - sensor_reserved_energy)
                            # 设置sensor 充电后的剩余能量 是满能量
                            sensor[0] = 6 * 1000
                            # 更新被充电的时间
                            sensor[2] = point_time
                            # sensor 被充电了
                            sensor[4] = True
                            # 加上得到的奖励,需要先将 rl 的单位先转化成小时
                            rl = rl / 3600
                            self.current_reward += math.exp(-rl)
                            self.reward += math.exp(-rl)
                        else:
                            # 如果是第一次死
                            if sensor[3] is True:
                                sensor[3] = False
                                self.reward += self.charging_penalty
                                self.current_reward += self.charging_penalty
                                with open('result.txt', 'a') as res:
                                    res.write('sensor   ' + str(i) + '  死了  ' + '\n')

    # 初始化整个环境
    def reset(self):
        # 前面0~83 都初始化为 0。记录CS的信息，每个hotspot占两位
        for i in range(42 * 2):
            self.state.append(0)
    # 传入时间字符串，如：09：02：03，转化成与 08:00:00 间的秒数差
    def str_to_seconds(self, input_str):
        data = input_str.split(':')
        hour = int(data[0]) - 8
        minute = int(data[1])
        second = int(data[2])
        return hour * 3600 + minute * 60 + second

    # 获得当前环境的秒
    def get_evn_time(self):
        total_t = 0
        for i in range(42 * 2):
            if i % 2 == 1:
                total_t += self.state[i]
        total_time = total_t * 5 * 60 + self.move_time
        return total_time
        # total_t = 0
        # # 获得CS中的所有等待时间
        # for action in self.CS:
        #     staying_time = int(action.split(',')[1])
        #     total_t += staying_time
        # #  CS中的时间加上移动的时间得到总共当前环境的时间
        # return total_t * 5 * 60 + self.move_time

if __name__ == '__main__':
    env = Env()
    env.reset()
    actions = []
    with open('rl actions.txt', 'r') as f:
        for line in f:
            line = line.strip()
            actions.append(line)

    for action in actions:
        env.step(action)
        print(action, '     ', env.current_reward)
    print(env.reward)

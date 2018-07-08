from Hotspot import Hotspot
import math
from Point import Point
import datetime
import sys


class Greedy:
    def __init__(self):
        # sensor 和 mc的能量信息
        self.sensors_mobile_charger = {}
        self.set_sensors_mobile_charger()
        # 获得所有的hotspot
        self.hotspots = []
        self.set_hotspots()
        # charging tour
        self.CS = []
        # charging reward
        self.reward = 0
        # 一个回合最大的时间，用秒来表示，早上8点到晚上10点，十四个小时，总共 14 * 3600 秒的时间
        # 如果self.get_evn_time() 得到的当前环境时间大于这个时间，则表示该回合结束
        self.one_episode_time = 14 * 3600
        # mc移动花费的时间
        self.move_time = 0
        # 当前时刻所在的hotspot，初始化为base_station
        self.current_hotspot = self.hotspots[0]
        # mc移动速度
        self.speed = 5
        # mc 移动消耗的能量
        self.mc_move_energy_consumption = 0
        # mc 给sensor充电消耗的能量
        self.mc_charging_energy_consumption = 0
        # 充电惩罚值
        self.charging_penalty = -100
        # 记录一次循环获得的reward，一次循环的mc 移动消耗的能量，mc给sensor充电的能量，用于最后一次减去这些数值
        self.current_reward = 0
        self.current_mc_move_energy_consumption = 0
        self.current_mc_charging_energy_consumption = 0
        # 输出文件的位置
        self.out_put_file = 'C:/Users/lv/Desktop/res(-100)2.txt'
        # 剩余寿命
        self.rl = 0

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

    def str_to_seconds(self, input_str):
        data = input_str.split(':')
        hour = int(data[0]) - 8
        minute = int(data[1])
        second = int(data[2])
        return hour * 3600 + minute * 60 + second

    def seconds_to_time_str(self, seconds):
        hour = int(seconds / 3600)
        minute = int((seconds - 3600 * hour) / 60)
        second = int(seconds - hour * 3600 - minute * 60)
        present_time = str(hour + 8) + ':' + str(minute) + ':' + str(second)
        return present_time

    # 获得当前环境时间，单位秒
    def get_evn_time(self):
        total_t = 0
        # 获得CS中的所有等待时间
        for action in self.CS:
            staying_time = int(action.split(',')[1])
            total_t += staying_time
        #  CS中的时间加上移动的时间得到总共当前环境的时间
        return total_t * 5 * 60 + self.move_time

    # 计算在hotspot_num 等待 stay_time 时间，碰到sensor_num 的概率
    def probability_T(self, current_slot, staying_time, sensor_num, hotspot_num):
        t = 5 / 60
        start_seconds = (current_slot - 1) * 3600
        end_seconds = start_seconds + 3600
        hotspot = self.find_hotspot_by_num(hotspot_num)

        # sensor 整个时间段到达 hotpsot 的次数
        arrived_times = 0
        path = 'sensor数据五秒/' + str(sensor_num) + '.txt'
        with open(path) as f:
            for line in f:
                line = line.strip().split(',')
                point = Point(float(line[0]), float(line[1]), line[2])
                point_time = self.str_to_seconds(point.get_time())

                if start_seconds <= point_time <= end_seconds and point.get_distance_between_point_and_hotspot(hotspot) < 60:
                    arrived_times += 1
        return 1 - (math.pow(arrived_times * staying_time * t, 0) * (math.exp(-arrived_times * staying_time * t))) / 1

    def initial_is_charged(self):
        for key, value in self.sensors_mobile_charger.items():
            if key != 'MC':
                value[4] = False


    def get_result(self):
        # 如果当前环境时间小于一个回合时间，并且 mc能量大于0
        with open(self.out_put_file, 'a') as res:
            res.write('程序开始时间       ' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n')
        while self.get_evn_time() < self.one_episode_time and self.sensors_mobile_charger['MC'][0] > 0:

            # 初始化这一次循环得到的reward 为0
            self.current_reward = 0
            self.current_mc_move_energy_consumption = 0
            self.current_mc_charging_energy_consumption = 0
            with open(self.out_put_file, 'a') as res:
                res.write('新一轮循环开始时间        ' + str(self.seconds_to_time_str(self.get_evn_time())) + '       ' + str(self.get_evn_time()) + '\n')

            with open(self.out_put_file, 'a') as res:
                res.write('residual energy of mc        ' + str(self.sensors_mobile_charger['MC'][0]) + '\n')
            # 获取当前时间段
            current_slot = int(self.get_evn_time() / 3600) + 1
            print('current_slot ', current_slot)
            print('residual energy of mc', self.sensors_mobile_charger['MC'][0])
            path = '1hour/' + str(current_slot) + '.txt'
            with open(path) as f:
                # 在当前时间段选择带来最大reward 的action
                # max_chose_reward 和 max_chose_action 暂存最大的reward 和 对应的 action
                print('choosing action ...........')
                max_chose_reward = -sys.maxsize - 1
                max_chose_action = None
                self.initial_is_charged()
                for line in f:
                    # 对于每一行就是一个action，我们依次迭代计算每一个action带来的reward，
                    chose_reward = 0
                    chose_action = line.strip()
                    hotspot_num_max_staying_time = line.strip().split(',')
                    # 选择的hotspot
                    hotspot = self.find_hotspot_by_num(int(hotspot_num_max_staying_time[0]))
                    # 最大等待时间
                    max_staying_time = int(hotspot_num_max_staying_time[1])
                    # 距离当前hotspot的距离
                    distance = hotspot.get_distance_between_hotspot(self.current_hotspot)
                    move_time = distance / self.speed
                    # 到达hotspot后，开始等待
                    start_seconds = self.get_evn_time() + move_time
                    # 结束等待的时间
                    end_seconds = start_seconds + max_staying_time * 5 * 60
                    # 获得所有的sensor 轨迹点
                    for i in range(17):
                        sensor_path = 'sensor数据五秒/' + str(i) + '.txt'
                        with open(sensor_path) as sensor_file:
                            for sensor_line in sensor_file:
                                sensor_line = sensor_line.strip().split(',')
                                point = Point(float(sensor_line[0]), float(sensor_line[1]), sensor_line[2])
                                point_time = self.str_to_seconds(point.get_time())

                                if start_seconds <= point_time <= end_seconds and point.get_distance_between_point_and_hotspot(hotspot) < 60:
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
                                        break
                                    # 如果剩余寿命在0 到 两个小时
                                    elif 0 < rl < 2 * 3600:
                                        # 加上得到的奖励,需要先将 rl 的单位先转化成小时
                                        rl = rl / 3600
                                        chose_reward += self.probability_T(current_slot, max_staying_time, str(i), hotspot.get_num()) \
                                                        * math.exp(-rl)
                                        sensor[4] = True
                                        break
                                    else:
                                        # if sensor[3] is True:
                                        #     chose_reward += self.charging_penalty
                                        #     break
                                        break
                    # 判断环境中的sensor 是否有死掉的
                    for key, value in self.sensors_mobile_charger.items():
                        if key != 'MC':
                            sensor_energy_after_last_time_charging = value[0]
                            # 当 前sensor 电量消耗的速率
                            sensor_consumption_ratio = value[1]
                            # 上一次的充电时间
                            previous_charging_time = value[2]
                            # 当前sensor 的剩余电量
                            sensor_reserved_energy = sensor_energy_after_last_time_charging - \
                                                     (end_seconds - previous_charging_time) * sensor_consumption_ratio
                            if (sensor_reserved_energy < 0) and (value[3] is True) and (value[4] is False):
                                chose_reward += self.charging_penalty
                                print('sensor   ' + key + '  死了  ')
                    print('test action reward ....  ', chose_action, '      ', chose_reward)
                    if chose_reward > max_chose_reward:
                        print('chose_action............................  ', chose_action)
                        max_chose_reward = chose_reward
                        max_chose_action = chose_action
            self.initial_is_charged()
            print('max_chose_action    ', max_chose_action)
            print('执行选择的action............')
            with open(self.out_put_file, 'a') as res:
                res.write(str(self.seconds_to_time_str(self.get_evn_time())) +
                          '        ' + max_chose_action + '\n')

            next_hotsopot_staying_time = max_chose_action.split(',')
            next_hotspot = self.find_hotspot_by_num(int(next_hotsopot_staying_time[0]))
            staying_time = int(next_hotsopot_staying_time[1])
            # 距离当前hotspot的距离
            distance = next_hotspot.get_distance_between_hotspot(self.current_hotspot)
            with open(self.out_put_file, 'a') as res:
                res.write('mc move distance             ' + str(distance) + '\n')
            self.move_time += distance / self.speed
            # 到达hotspot后，开始等待，mc减去移动消耗的能量，并更新当前属于的hotspot
            start_seconds = self.get_evn_time()
            # 当前这次循环mc消耗的移动能量
            self.current_mc_move_energy_consumption += self.sensors_mobile_charger['MC'][1] * distance
            # 更新总共的mc移动能量消耗
            self.mc_move_energy_consumption += self.sensors_mobile_charger['MC'][1] * distance
            # 更新mc的能量
            self.sensors_mobile_charger['MC'][0] = self.sensors_mobile_charger['MC'][0] \
                                                   - self.sensors_mobile_charger['MC'][1] * distance
            self.current_hotspot = next_hotspot
            # 结束等待的时间
            end_seconds = start_seconds + staying_time * 5 * 60
            # 将action 添加到 self.CS
            self.CS.append(max_chose_action)
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

                        if start_seconds <= point_time <= end_seconds and point.get_distance_between_point_and_hotspot(self.current_hotspot) < 60:
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
                                break
                            # 如果剩余寿命在0 到 两个小时
                            elif 0 < rl < 2 * 3600:
                                # mc 给该sensor充电， 充电后更新剩余能量
                                # 更新当前循环的能量充给sensor电的消耗
                                self.current_mc_charging_energy_consumption += 6 * 1000 - sensor_reserved_energy
                                # 更新总的能量充给sensor电的消耗
                                self.mc_charging_energy_consumption += 6 * 1000 - sensor_reserved_energy
                                # 更新mc的能量
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
                                # print('getting reward by executing chosen action ', math.exp(-rl))
                                with open(self.out_put_file, 'a') as res:
                                    res.write('charging sensor  ' + str(i) + '      the time is       ' + self.seconds_to_time_str(sensor[2]) + '\n')
                                    res.write('reward:  ' + str(math.exp(-rl)) + '\n')
                                self.reward += math.exp(-rl)
                                self.current_reward += math.exp(-rl)
                                break
                            else:
                                if sensor[3] is True:
                                    with open(self.out_put_file, 'a') as res:
                                        res.write(str(i) + 'sensor 死掉了' + '\n')
                                    print('sensor 死掉了')
                                    self.reward += self.charging_penalty
                                    self.current_reward += self.charging_penalty
                                    sensor[3] = False
                                    break

            # action结束，判断环境中的sensor 是否有死掉的
            for key, value in self.sensors_mobile_charger.items():
                if key != 'MC':
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
                        with open(self.out_put_file, 'a') as res:
                            res.write('sensor       ' + key + '         死掉了' + '\n')

        with open(self.out_put_file, 'a') as res:
            # 最后一次循环不能算在结果里面，得减去最后一次的结果
            res.write('\n' + '程序结束时间       ' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n')
            res.write('mc 移动消耗的能量           '
                      + str(self.mc_move_energy_consumption - self.current_mc_move_energy_consumption) + '\n')
            res.write('mc 给sensor充电消耗的能量           '
                      + str(self.mc_charging_energy_consumption - self.current_mc_charging_energy_consumption) + '\n')
            res.write('mc 剩余能量           '
                      + str(self.sensors_mobile_charger['MC'][0] + self.current_mc_move_energy_consumption
                            + self.current_mc_charging_energy_consumption) + '\n')
            res.write('所获得的奖励       ' + str(self.reward - self.current_reward) + '\n')

if __name__ == '__main__':
    greedy = Greedy()
    greedy.get_result()
    print(greedy.reward)
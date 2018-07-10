from Hotspot import Hotspot
import math
from Point import Point
import sys
import copy


class NewGreedy:
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
        # 记录一次循环的mc 移动消耗的能量，mc给sensor充电的能量，用于最后一次减去这些数值
        self.current_mc_move_energy_consumption = 0
        self.current_mc_charging_energy_consumption = 0

        self.current_hotspot_staying_time = 0
        self.actual_reward = 0
        self.expected_reward = 0
        self.current_charging_sensors = []
        self.current_dead_sensors = []

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

    # 获得当前环境时间，单位秒
    def get_evn_time(self):
        total_t = 0
        # 获得CS中的所有等待时间
        for action in self.CS:
            staying_time = int(action.split(',')[1])
            total_t += staying_time
        #  CS中的时间加上移动的时间得到总共当前环境的时间
        return total_t * 5 * 60 + self.move_time

    # 到达times 次，等待t 时间，等到的概率
    def get_probability(self, t, times):
        return 1 - math.pow((times * t), 0) * math.exp(-times * t) / 1

    # 在current_slot 时间段，hotspot_num上，sensor 的最大等待时间，需要输出到第3 个文件
    def get_max_staying_time(self):
        # 返回的结果
        res = {}
        current_slot = int(self.get_evn_time() / 3600) + 1
        for hotspot in self.hotspots:
            hotspot_num = hotspot.get_num()
            if hotspot_num == 0:
                continue
            path = 'hotspot中sensor的访问情况/' + str(current_slot) + '时间段/' + str(hotspot_num) + '.txt'
            with open(path) as f:
                for line in f:
                    line = line.strip().split(',')
                    sensor_num = int(line[0])
                    visite_times = int(line[1])
                    if visite_times == 0:
                        continue
                    else:
                        # 最小一个t，一个t 是 5 / 20
                        nunmber_of_t = 1
                        t = 5 / 60
                        # 等到的概率初始为 0
                        probability = 0
                        # 如果概率小于 0.9 就一直循环
                        while probability < 0.9:
                            probability = self.get_probability(nunmber_of_t * t, visite_times)
                            nunmber_of_t += 1
                        # 得到等到每个sensor 0.9概率所需要的时间
                        nunmber_of_t -= 1
                        res['h'+str(hotspot_num) + ':' + 's' + str(sensor_num)] = nunmber_of_t
                # 计算等到到达的所有sensor 0.9概率所需要的等待时间
            path_20minutes = '1hour/' + str(current_slot) + '.txt'
            with open(path_20minutes) as f:
                for line in f:
                    if int(line.strip().split(',')[0]) == hotspot_num:
                        res['h' + str(hotspot_num)] = line.strip().split(',')[1]
        if len(res) == 0:
            res['结果：'] = '没有senosr到达该hotspot'
        return res

    # 计算current_slot时间段，在hotspot_num 等待 stay_time 时间，碰到sensor_num 的概率
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

                if start_seconds <= point_time <= end_seconds and point.get_distance_between_point_and_hotspot(
                        hotspot) < 60:
                    arrived_times += 1
        return 1 - (math.pow(arrived_times * staying_time * t, 0) * (math.exp(-arrived_times * staying_time * t))) / 1

    def initial_is_charged(self):
        for key, value in self.sensors_mobile_charger.items():
            if key != 'MC':
                value[4] = False

    # 得到sensor的剩余能量信息(单位小时)，需要输出到第4 个文件
    def get_sensors_residual_energy(self):
        res = {}
        present_time = self.get_evn_time()
        for key, value in self.sensors_mobile_charger.items():
            if key != 'MC':
                res[key] = ((value[0] - value[1] * (present_time - value[2])) / value[1]) / 3600
        return res

    # 执行一步action ，需要输出到第 5 个文件
    def one_step(self, action):
        # 初始化当前这一步的所有信息
        self.actual_reward = 0
        self.expected_reward = 0
        self.current_charging_sensors = []
        self.current_dead_sensors = []

        hotspot_num = int(action.split(',')[0])
        staying_time = int(action.split(',')[1])
        # 初始化是否充电
        self.initial_is_charged()
        # 距离当前hotspot的距离
        next_hotspot = self.find_hotspot_by_num(hotspot_num)
        distance = next_hotspot.get_distance_between_hotspot(self.current_hotspot)

        # 计算得到期望奖励
        self.initial_is_charged()
        time = distance / self.speed
        start_seconds = self.get_evn_time() + time
        current_slot = int(start_seconds / 3600) + 1
        # 结束等待的时间
        end_seconds = start_seconds + staying_time * 5 * 60

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
                            next_hotspot) < 60:
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
                            self.expected_reward += 0
                            break
                        # 如果剩余寿命在0 到 两个小时
                        elif 0 < rl < 2 * 3600:
                            # 加上得到的奖励,需要先将 rl 的单位先转化成小时
                            rl = rl / 3600
                            probability = self.probability_T(current_slot, staying_time, str(i), next_hotspot.get_num())
                            self.expected_reward += probability * math.exp(-rl)
                            break
                        else:
                            # if sensor[3] is True:
                                # self.expected_reward += self.charging_penalty
                                # break
                            break
        # 判断环境中的sensor 是否有死掉的
        for key, value in self.sensors_mobile_charger.items():
            if key != 'MC':
                sensor_energy_after_last_time_charging = value[0]
                # 当前sensor 电量消耗的速率
                sensor_consumption_ratio = value[1]
                # 上一次的充电时间
                previous_charging_time = value[2]
                # 当前sensor 的剩余电量
                sensor_reserved_energy = sensor_energy_after_last_time_charging - \
                                         (end_seconds - previous_charging_time) * sensor_consumption_ratio
                if (sensor_reserved_energy < 0) and (value[3] is True):
                    self.expected_reward += self.charging_penalty
                    print('sensor   ' + key + '  死了  ')

        # 计算得到的真实奖励
        # 到达hotspot后，开始等待，mc减去移动消耗的能量，并更新当前属于的hotspot
        self.initial_is_charged()
        self.move_time += distance / self.speed
        start_seconds = self.get_evn_time()
        self.mc_move_energy_consumption += self.sensors_mobile_charger['MC'][1] * distance
        self.sensors_mobile_charger['MC'][0] = self.sensors_mobile_charger['MC'][0] \
                                               - self.sensors_mobile_charger['MC'][1] * distance

        self.current_hotspot = next_hotspot
        self.current_hotspot_staying_time = staying_time
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
                            self.actual_reward += 0
                            break
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
                            self.actual_reward += math.exp(-rl)
                            self.current_charging_sensors.append(str(i))
                            break
                        else:
                            if sensor[3] is True:
                                self.reward += self.charging_penalty
                                self.actual_reward += self.charging_penalty
                                sensor[3] = False
                                self.current_dead_sensors.append(str(i))
                                break

        # 判断环境中的sensor 是否有死掉的
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
                    self.actual_reward += self.charging_penalty
                    print('sensor   ' + key + '  死了  ')
                    self.current_dead_sensors.append(key)
    # 根据当前环境，返回得到最大reward的action，即得到greedy的action
    def get_an_action_after_steps(self):
        # 获取当前时间段
        current_slot = int(self.get_evn_time() / 3600) + 1
        path = '1hour/' + str(current_slot) + '.txt'
        with open(path) as f:
            # 在当前时间段选择带来最大reward 的action
            # max_chose_reward 和 max_chose_action 暂存最大的reward 和 对应的 action
            print('choosing action ...........')
            max_chose_reward = -sys.maxsize - 1
            max_chose_action = None
            for line in f:
                self.initial_is_charged()
                print('testing every action ............')
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
                            # 检查当前sensor 是否在该hotspot 已经被充过电了，如果是，跳出循环
                            sensor_is_charged = self.sensors_mobile_charger[str(i)]
                            if sensor_is_charged[4] is True:
                                break
                            sensor_line = sensor_line.strip().split(',')
                            point = Point(float(sensor_line[0]), float(sensor_line[1]), sensor_line[2])
                            point_time = self.str_to_seconds(point.get_time())

                            if start_seconds <= point_time <= end_seconds and point.get_distance_between_point_and_hotspot(
                                    hotspot) < 60:
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
                                                         (point_time - previous_charging_time) \
                                                         * sensor_consumption_ratio
                                # 当前sensor 的剩余寿命
                                rl = sensor_reserved_energy / sensor_consumption_ratio
                                # 如果剩余寿命大于两个小时
                                if rl >= 2 * 3600:
                                    chose_reward += 0
                                    break
                                # 如果剩余寿命在0 到 两个小时
                                elif 0 < rl < 2 * 3600:
                                    # 加上得到的奖励,需要先将 rl 的单位先转化成小时
                                    rl = rl / 3600
                                    chose_reward += self.probability_T(current_slot, max_staying_time, str(i),
                                                                       hotspot.get_num()) \
                                                    * math.exp(-rl)
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
                        # 当前sensor 电量消耗的速率
                        sensor_consumption_ratio = value[1]
                        # 上一次的充电时间
                        previous_charging_time = value[2]
                        # 当前sensor 的剩余电量
                        sensor_reserved_energy = sensor_energy_after_last_time_charging - \
                                                 (end_seconds - previous_charging_time) * sensor_consumption_ratio
                        if (sensor_reserved_energy < 0) and (value[3] is True):
                            chose_reward += self.charging_penalty
                            print('sensor   ' + key + '  死了  ')

                if chose_reward > max_chose_reward:
                    max_chose_reward = chose_reward
                    max_chose_action = chose_action
                    print('交换了一次,   ', chose_action)
            return max_chose_action

     # 传入一个action_list，执行所有的action，然后选择得到最大的reward的action执行，直到结束
    def execute_action_list(self, action_list):
        for action in action_list:
            self.one_step(action)
            print(action, '     ', self.actual_reward)

        # while self.get_evn_time() < self.one_episode_time and self.sensors_mobile_charger['MC'][0] > 0:
        #     # 获取当前时间段
        #     current_slot = int(self.get_evn_time() / 1200) + 1
        #     path = '20minutes/' + str(current_slot) + '.txt'
        #     with open(path) as f:
        #         # 在当前时间段选择带来最大reward 的action
        #         # max_chose_reward 和 max_chose_action 暂存最大的reward 和 对应的 action
        #         print('choosing action ...........')
        #         max_chose_reward = -sys.maxsize - 1
        #         max_chose_action = None
        #         for line in f:
        #             print('testing every action ............')
        #             # 对于每一行就是一个action，我们依次迭代计算每一个action带来的reward，
        #             chose_reward = 0
        #             chose_action = line.strip()
        #             hotspot_num_max_staying_time = line.strip().split(',')
        #             # 选择的hotspot
        #             hotspot = self.find_hotspot_by_num(int(hotspot_num_max_staying_time[0]))
        #             # 最大等待时间
        #             max_staying_time = int(hotspot_num_max_staying_time[1])
        #             # 距离当前hotspot的距离
        #             distance = hotspot.get_distance_between_hotspot(self.current_hotspot)
        #             move_time = distance / self.speed
        #             # 到达hotspot后，开始等待
        #             start_seconds = self.get_evn_time() + move_time
        #             # 结束等待的时间
        #             end_seconds = start_seconds + max_staying_time * 5 * 60
        #             # 获得所有的sensor 轨迹点
        #             for i in range(17):
        #                 sensor_path = 'sensor数据五秒/' + str(i) + '.txt'
        #                 with open(sensor_path) as sensor_file:
        #                     for sensor_line in sensor_file:
        #                         sensor_line = sensor_line.strip().split(',')
        #                         point = Point(float(sensor_line[0]), float(sensor_line[1]), sensor_line[2])
        #                         point_time = self.str_to_seconds(point.get_time())
        #
        #                         if start_seconds <= point_time <= end_seconds and point.get_distance_between_point_and_hotspot(
        #                                 hotspot) < 60:
        #                             # 取出sensor
        #                             sensor = self.sensors_mobile_charger[str(i)]
        #                             # 上一次充电后的电量
        #                             sensor_energy_after_last_time_charging = sensor[0]
        #                             # 当前sensor 电量消耗的速率
        #                             sensor_consumption_ratio = sensor[1]
        #                             # 上一次的充电时间
        #                             previous_charging_time = sensor[2]
        #                             # 当前sensor 的剩余电量
        #                             sensor_reserved_energy = sensor_energy_after_last_time_charging - \
        #                                                      (point_time - previous_charging_time) \
        #                                                      * sensor_consumption_ratio
        #                             # 当前sensor 的剩余寿命
        #                             rl = sensor_reserved_energy / sensor_consumption_ratio
        #                             # 如果剩余寿命大于两个小时
        #                             if rl >= 2 * 3600:
        #                                 break
        #                             # 如果剩余寿命在0 到 两个小时
        #                             elif 0 < rl < 2 * 3600:
        #                                 # 加上得到的奖励,需要先将 rl 的单位先转化成小时
        #                                 rl = rl / 3600
        #                                 chose_reward += self.probability_T(current_slot, max_staying_time, str(i),
        #                                                                    hotspot.get_num()) \
        #                                                 * math.exp(-rl)
        #                             else:
        #                                 if sensor[3] is True:
        #                                     chose_reward += self.charging_penalty
        #
        #             if chose_reward > max_chose_reward:
        #                 max_chose_reward = chose_reward
        #                 max_chose_action = chose_action
        #     print('执行  ', max_chose_action)
        #     self.one_step(max_chose_action)
        #     # self.res.append(max_chose_action)
        #     # self.res.append(self.current_sensors)
        #     # self.res.append(self.current_reward)
        #     print('得到的reward  ', self.rl_current_reward)
        # self.reward -= self.rl_current_reward


if __name__ == '__main__':
    rl_actions = []

    with open('rl_actions.txt', 'r') as f:
        for line in f:
            line = line.strip()
            rl_actions.append(line)
    # 建立一个rl_new_greedy 的环境，用于执行rl 的action
    rl_new_greedy = NewGreedy()
    i = 1
    total_reward = 0
    for action in rl_actions:
        rl_new_greedy.one_step(action)

        # 得到在当前环境下最大的reward 的action
        greedy_acttion = rl_new_greedy.get_an_action_after_steps()
        # 复制环境 rl_new_greedy 给 greedy_new_greedy，传入 greedy的action
        greedy_new_greedy = copy.deepcopy(rl_new_greedy)

        # 执行greedy 中的一步
        greedy_new_greedy.one_step(greedy_acttion)
        # 执行rl 中的一步
        rl_new_greedy.one_step(action)
        with open('C:/Users/lv/Desktop/res/3_每个sensor的独⽴最⼤等待时间及hotspot最⼤等待时间⽂件.txt', 'a') as f:
            f.write('########################' + '\n')
            f.write('action_' + str(i) + '    ' + action + '\n')

            res = rl_new_greedy.get_max_staying_time()
            for key, value in res.items():
                f.write(key + ',' + str(value) + '\n')
        with open('C:/Users/lv/Desktop/res/4_sensor的剩余能量.txt', 'a') as f:
            f.write('########################' + '\n')
            f.write('action_' + str(i) + '    ' + action + '\n')

            res = rl_new_greedy.get_sensors_residual_energy()
            for key, value in res.items():
                f.write(key + ',' + str(value) + '\n')

        with open('C:/Users/lv/Desktop/res/5_记录每⼀步的action.txt', 'a') as f:
            f.write('########################' + '\n')
            f.write('action_' + str(i) + '    ' + action + '\n')
            f.write('hotspot,' + str(rl_new_greedy.current_hotspot.get_num()) + ':'
                    + str(greedy_new_greedy.current_hotspot.get_num()) + '\n')

            f.write('time,' + str(rl_new_greedy.current_hotspot_staying_time) + ':'
                    + str(greedy_new_greedy.current_hotspot_staying_time) + '\n')

            f.write('reward,' + str(rl_new_greedy.actual_reward) + ':'
                    + str(greedy_new_greedy.actual_reward) +
                    ' , expected reward, ' + str(rl_new_greedy.expected_reward) + ':' +
                    str(greedy_new_greedy.expected_reward) + '\n')

            f.write('sensors,' + str(rl_new_greedy.current_charging_sensors) + ':'
                    + str(greedy_new_greedy.current_charging_sensors) + '\n')
            f.write('dead sensors,' + str(rl_new_greedy.current_dead_sensors) + ':'
                    + str(greedy_new_greedy.current_dead_sensors) + '\n')
            i += 1
            total_reward += rl_new_greedy.actual_reward
    print(rl_new_greedy.reward)
    print(total_reward)
import sys
max_reward = -sys.maxsize - 1
max_line = None
# with open('C:/Users/lv/Desktop/数据2018_07_18/2009-03-11/rl_2018_07_14_11/reward.txt', 'r') as f:
with open('C:/Users/lv/Desktop/数据2018_07_18/2009-03-15/rl_2018_07_15_15/reward.txt', 'r') as f:
    for line in f:
        reward = float(line.split(',')[1])
        if max_reward < reward:
            max_reward = reward
            max_line = line

print(max_reward)
print(max_line)

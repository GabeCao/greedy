import sys
max_reward = -sys.maxsize - 1
max_line = None
with open('C:/Users/lv/Desktop/reward.txt', 'r') as f:
    for line in f:
        reward = float(line.split(',')[1])
        if max_reward < reward:
            max_reward = reward
            max_line = line

print(max_reward)
print(max_line)
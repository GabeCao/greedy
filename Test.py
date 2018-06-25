max_reward = 0
max_line = None
with open('reward.txt', 'r') as f:
    for line in f:
        reward = float(line.split(',')[1])
        if reward > max_reward:
            max_reward = reward
            max_line = line

print(max_reward)
print(max_line)
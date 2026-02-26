"""
3. Intelligent Log "Anomalizer"
Instead of just searching for "Error," this script reads a log file and uses a dictionary to count occurrences of every unique word. It then flags lines that contain words that appear in less than 1% of the total log (finding the "needle in the haystack").

Key Libraries: collections.Counter, re.
"""

from collections import Counter

file = "log.txt"
word_cnt = 0

with open("log.txt", "r") as f:
    lines = f.readlines()

word_freq = Counter(lines)

for line in lines:
    words = line.split()
    word_cnt += len(words)

least_word_cnt = word_cnt * 0.01

for word, cnt in word_freq.items():
    if cnt < least_word_cnt:
        print(word)


    




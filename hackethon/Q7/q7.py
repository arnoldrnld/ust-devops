"""
7. System "Snapshot" Comparison Tool
This script takes a "snapshot" of the machine (installed packages, environment variables, and active users) and saves it to a file. Users can run it again later to see a "Diff" of exactly what changed on the system.

Key Libraries: subprocess, difflib.
"""

import subprocess
import os

# Installed packages
result = subprocess.check_output("pip freeze")
installed_packages = [r.decode().split('==')[0] for r in result.splitlines()]

# Environment variables
env_variables = os.environ

# Active Users
output = subprocess.check_output("quser", shell=True, text=True)

# Skip header, split each line, and grab the first part
usernames = [line.split()[0].replace('>', '') for line in output.strip().split('\n')[1:]]

with open("snap.txt", "w") as f:
    f.write("=====INSTALLED PACKAGES====\n")
    for p in installed_packages:
        f.write(f"{p}\n")

    f.write("\n=====ENV VARIABLES========\n")
    for key, value in os.environ.items():
        f.write(f"{key} - {value}\n")

    f.write("\n=====ACTIVE USERS=========\n")
    for user in usernames:
        f.write(f"{user}\n")


    







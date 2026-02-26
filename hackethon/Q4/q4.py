"""
4. The "Disk Space" Emergency Brake

A background daemon that monitors disk usage. If a specific partition hits 90%, it identifies the top 5 largest files and moves them to a compressed .zip archive on a different drive (or a /tmp folder) to prevent system a crash.

Key Libraries: os, zipfile, platform.
"""

import os
import shutil
import zipfile

def top_files(disk):
    """
    Search the top 5 largest files in the given disk and return the file paths as list
    """

def compress_top_files(disk, files):
    """
    Compress files and store it in tmp folder in the given disk
    """
    os.makedirs(f"{disk}tmp", exist_ok=True)

    with zipfile.ZipFile(f"{disk}tmp/archive.zip", "w") as zipf:
        
        for file in files:
            zipf.write(file)
            print(f"{file} moved to archive !!!")

            if os.path.exists(file):
                os.remove(file)


def check_usage():
    """
    Check if disk usage is above given 90%
    """
    disks = os.listdrives()

    for disk in disks:
        # Get storage info, Convert size to GB
        total, used, free = tuple(map(lambda x:x//(2**30), 
                                    shutil.disk_usage(disk)))
        # print(total, used, free)

        usage_limit = total * 0.9
        
        if used > usage_limit:
            print("Usage above 90% !!!")
            files = top_files(disk)
            compress_top_files(files)
        else:
            print("Usage is below 90%.")

if __name__ == "__main__":
    check_usage()








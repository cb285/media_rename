#!/usr/bin/env python3

import os
import shutil
import glob
from enum import Enum
import mimetypes
import hashlib

class FileType(Enum):
    VIDEO =   0
    AUDIO =   1
    CAPTION = 2
    UNKNOWN = 3

def makedirs(dir):
    os.makedirs(new, exist_ok=True)

def basename(filename):
    return os.path.basename(filename)

def move(src, dest, make_dirs = False):

    if make_dirs:
        makedirs(dest)

    shutil.move(src, dest)

def copy(src, dest, make_dirs = False):
    
    if make_dirs:
        makedirs(dest)
        
    shutil.copy(src, dest)

def checksum(filename):

    try:
        file = open(filename, "rb")
    except FileNotFoundError:
        return ""

    rv = hashlib.md5(file.read()).hexdigest()

    file.close()

    return rv

def extension(filename):
    return os.path.splitext(filename)[1].lower()

def type(filename):

    mimetypes.init()

    if (extension(filename) == ".srt") or (extension(filename) == ".sub"):
        return FileType.CAPTION
    elif extension(filename) == ".mkv":
        return FileType.VIDEO

    guess = mimetypes.guess_type(filename)[0]

    if not guess:
        return FileType.UNKNOWN

    if guess.startswith("video"):
        return FileType.VIDEO
    else:
        return FileType.UNKNOWN

def listdir(directory, recursive = False):

    if not recursive:
        files = glob.glob(directory)
        return [f for f in files if os.path.isfile(f)]

    rv = []

    for currentpath, folders, files in os.walk(directory):
        for file in files:
            rv.append(os.path.join(currentpath, file))

    return rv

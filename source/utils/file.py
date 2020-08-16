#!/usr/bin/env python3

import os
import shutil
import glob
from enum import Enum
import mimetypes

class FileType(Enum):
    VIDEO =   0
    AUDIO =   1
    CAPTION = 2
    UNKNOWN = 3

def makedirs(dir):
    os.makedirs(new, exist_ok=True)

def move(src, dest, makedirs = False):

    if makedirs:
        makedirs(new)

    shutil.move(src, dest)

def copy(src, dest, make_dirs = False):
    
    if makedirs:
        makedirs(new)
        
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

    if extension(filename) == ".srt":
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
    files = glob.glob(directory + "/**", recursive=recursive)
    return [f for f in files if os.path.isfile(f)]

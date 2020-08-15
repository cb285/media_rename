#!/usr/bin/env python3

import argparse
import re
from enum import Enum
import os.path
import hashlib
from utils import file
from utils.file import Filetype
from db_api import imdb
import colorama

HISTORY_FILENAME = "history"
past_show_info = dict()

class Action(Enum):
    TEST = 0
    MOVE = 1
    COPY = 2

class Format(Enum):
    SHOW_TITLE    = [ "%T", "show title" ]
    EPISODE_TITLE = [ "%t", "episode title" ]
    SEASON        = [ "%s", "season number" ]
    EPISODE       = [ "%e", "episode number" ]

def print_error(s):
    colorama.init()
    print(colorama.Fore.RED + str(s))
    print(colorama.Style.RESET_ALL)

def action_to_string(action):

    action = Action(action)

    if action == Action.TEST:
        return "test"
    elif action == Action.MOVE:
        return "move"
    elif action == Action.COPY:
        return "copy"
    else:
        return "invalid"

def get_new_filename(old_filename, format, show_title, season, episode, episode_title):

    extension = file.extension(old_filename)

    new = format

    new = new.replace(Format.SHOW_TITLE.value[0], show_title)
    new = new.replace(Format.EPISODE_TITLE.value[0], episode_title)
    new = new.replace(Format.SEASON.value[0], "{:02d}".format(season))
    new = new.replace(Format.EPISODE.value[0], "{:02d}".format(episode))

    return new + extension
    
def get_season_episode(filename):

    m = re.search("(?i)S(\d+)E(\d+)", filename)

    # no results
    if not m:
        return None, None

    groups = m.groups()

    if len(groups) >= 2:
        return int(groups[0]), int(groups[1])

    return None, None

def update_history(old, new, action):

    s = "{},{},\"{}\",\"{}\"".format(action_to_string(action), file.checksum(old), old, new)

    history_file = open(HISTORY_FILENAME, "a+")
    history_file.write(s + "\n")
    history_file.close()

def apply_action(old, new, action = Action.TEST, print_width = 0):

    print("[{}] \"{:<{width}}\" >> \"{}\"".format(action_to_string(action), old, new, width = print_width))

    if action != Action.TEST:

        # check if file exists
        if not os.path.exists(old):
            print_error("file doesn't exist \"{}\"".format(old))
            return False

        try:
            if action == Action.MOVE:
                file.move(old, new)
            elif action == Action.COPY:
                file.copy(old, new)
            else:
                return False

        except FileNotFoundError:
            print_error("file doesn't exist")
            return False

    # update history on success
    update_history(old, new, action)

    return True
        
def find_caption(season, episode, captions):

    for cap in captions:
        caption_season, caption_episode = get_season_episode(cap)

        if not caption_season:
            continue

        # check if matches
        if (season == caption_season) and (episode == caption_episode):
            return cap

    return None

def get_action(arg):

    if arg:
        action_str = arg.lower()
    else:
        return Action.TEST

    for action in [e.value for e in Action]:
        if action_to_string(action) == action_str:
            return Action(action)

    print_error("invalid action \"{}\"".format(arg))
    return None
    
def guess_title(filename):

    filename = os.path.basename(filename.strip())
    words = re.split('[^a-zA-Z]', filename)
    
    words = [word.lower() for word in words]
    
    title = ""
    
    for i in range(len(words)):
        if (i < (len(words) - 2)) and (words[i] == "s") and (words[i + 2] == "e"):
            break
        title += words[i] + " "
    
    return title.strip()

def process_file(filename, action, format, query = None):
    if not query:
        search = guess_title(filename)
    else:
        search = query
    
    print("input \"{}\"".format(filename))
    print("search \"{}\"".format(search))
    
    series_title, episode_info = imdb.search(search)
    
    if not series_title:
        print_error("not matches found")
        return False
    
    # get season and episode from filename
    season, episode = get_season_episode(filename)
    
    # check if have info for this episode
    if season not in episode_info:
        print_error("season {:>02} not found".format(season))
        return False
    
    if episode not in episode_info[season]:
        print_error("S{:>02}E{:>02} not found".format(season, episode))
        return False
    
    episode_title = episode_info[season][episode]["title"]
    new_episode_name = get_new_filename(filename, format, series_title, season, episode, episode_title)
    apply_action(filename, new_episode_name, action)

    print()
    return True
    
def format_help():

    s = ""
    for spec in [e.value for e in Format]:
        s += "\"%{}\" : {}\n".format(spec[0], spec[1])
    
    return s

def main():
    
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    
    # require input file/directory or list file
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", "-i", required = False, type=str, action="store", help="input directory")
    group.add_argument("--list", "-l", required = False, type=str, action="store", help="file containing list of filenames")
    
    parser.add_argument("--format", "-f", required = True, type=str, action="store", help=format_help())
    parser.add_argument("--action", "-a", required = False, type=str, action="store", help="test, copy, or move")
    parser.add_argument("--query", "-q", required = False, type=str, action="store", help="search query")
    
    args, args_unknown = parser.parse_known_args()
    
    input = args.input
    format = args.format
    action = get_action(args.action)
    query = args.query
    
    # check for valid action
    if not action:
        return False
    
    if not args.list:
        # find episode and caption files
        files = file.listdir(input, recursive = True)
    else:
        list_file = open(args.list, 'r')
        lines = list_file.readlines()
        files = [x.strip() for x in lines]
        list_file.close()
    
    # filter caption and episode files
    captions = list(filter(lambda ep: (file.type(ep) == Filetype.CAPTION), files))
    episodes = list(filter(lambda ep: (file.type(ep) == Filetype.VIDEO), files))
    
    if len(episodes) != 0:
        for ep in episodes:
            if not process_file(ep, action, format, query):
                return False
    
    if len(captions) != 0:
        for cap in captions:
            if not process_file(cap, action, format, query):
                return False
    
    return True
    
if __name__ == "__main__":
    main()
    

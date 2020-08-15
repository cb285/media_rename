#!/usr/bin/env python3

import argparse
import re
import glob
import mimetypes
from enum import Enum
import os.path
import imdb
import hashlib

HISTORY_FILENAME = "shows_history"

class Filetype(Enum):
    VIDEO =   0
    AUDIO =   1
    CAPTION = 2
    UNKNOWN = 3

class Action(Enum):
    TEST = 0
    MOVE = 1
    COPY = 2

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

def get_file_extension(filename):
    return os.path.splitext(filename)[1]

def get_filetype(filename):
    
    if get_file_extension(filename) == ".srt":
        return Filetype.CAPTION
    elif get_file_extension(filename) == ".mkv":
        return Filetype.VIDEO
    
    guess = mimetypes.guess_type(filename)[0]
    
    if not guess:
        return Filetype.UNKNOWN
    
    if guess.startswith("video"):
        return Filetype.VIDEO
    else:
        return Filetype.UNKNOWN
        
def get_new_filename(old_filename, show_title, season, episode, episode_title):

    extension = get_file_extension(old_filename)
    
    return show_title + " - S" + "{:02d}".format(season) + "E" + "{:02d}".format(episode) + " - " + episode_title + extension
    
def get_season_episode(filename):

    m = re.search("(?i)S(\d+)E(\d+)", filename)
    
    # no results
    if not m:
        return None, None
    
    groups = m.groups()
    
    if len(groups) >= 2:
        return int(groups[0]), int(groups[1])
        
    return None, None
    
def get_checksum(filename):

    try:
        file = open(filename, "rb")
    except FileNotFoundError:
        return ""

    rv = hashlib.md5(file.read()).hexdigest()
    file.close()

    return rv

def update_history(old, new, action):
    
    s = "{},{},\"{}\",\"{}\"".format(action_to_string(action), get_checksum(old), old, new)
    
    history_file = open(HISTORY_FILENAME, "a+")
    history_file.write(s + "\n")
    history_file.close()

def rename_file(old, new, output_dir, action = Action.TEST, print_width = 0):

    #new = new.replace("/", "")
    
    new = output_dir + "/" + new
    
    print("[{}] \"{:<{width}}\" >> \"{}\"".format(action_to_string(action), old, new, width = print_width))
    
    if action != Action.TEST:
        
        # check if file exists
        if not os.path.exists(old):
            print("file doesn't exist \"{}\"".format(old))
            return False
        
        try:
            os.mkdir(output_dir)
        except FileExistsError:
            pass
        
        try:
            if action == Action.MOVE:
                os.rename(old, new)
            elif action == Action.COPY:
                os.copy(old, new)
            else:
                return False

            # add to history
            update_history(old, new, action)

        except FileNotFoundError:
            print("file doesn't exist")
            return False
        
        finally:
            history_file.close()
    
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
    
past_show_info = dict()

def get_show_info(query):

    # check if already have info for this show
    if query in past_show_info:
        return past_show_info[query]

    imdb_api = imdb.IMDb()
    
    res = imdb_api.search_movie(query)
    
    if not res:
        return None, None
    
    series = imdb_api.get_movie(res[0].movieID)
    imdb_api.update(series, "episodes")
    num_seasons = series["number of seasons"]
    title = series["title"]
    
    episodes = dict()
    
    for season in range(1, num_seasons + 1):
    
        episodes[season] = dict()
        
        for episode in series["episodes"][season].keys():
            
            episodes[season][episode] = dict()
            episodes[season][episode]["title"] = series["episodes"][season][episode]["title"]
    
    # save to reuse
    past_show_info[query] = title, episodes
    
    return title, episodes

def listdir_fullpath(d):
    return [os.path.join(d, f) for f in os.listdir(d)]

def get_action(arg):
    
    if arg:
        action_str = arg.lower()
    else:
        return Action.TEST
    
    for action in [e.value for e in Action]:
        if action_to_string(action) == action_str:
            return action
    
    print("invalid action \"{}\"".format(arg))
    return None
    
def guess_title(filename):

    filename = filename.strip()
    words = re.split('[^a-zA-Z]', filename)
    
    words = [word.lower() for word in words]
    
    title = ""
    
    for i in range(len(words)):
        if (i < (len(words) - 2)) and (words[i] == "s") and (words[i + 2] == "e"):
            break
        title += words[i] + " "
    
    return title.strip()

def process_file(filename, action, output_dir, query = None):
    if not query:
        search = guess_title(filename)
    else:
        search = query
    
    print("input \"{}\"".format(filename))
    print("search \"{}\"".format(search))
    
    series_title, episode_info = get_show_info(search)
    
    if not series_title:
        print("not matches found")
        return False
    
    season, episode = get_season_episode(filename)
    episode_title = episode_info[season][episode]["title"]
    new_episode_name = get_new_filename(filename, series_title, season, episode, episode_title)
    rename_file(filename, new_episode_name, output_dir, action)

    print()
    return True

def main():
    
    mimetypes.init()
    parser = argparse.ArgumentParser()
    
    # require input file/directory or list file
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", "-i", required = False, type=str, action="store", help="input directory")
    group.add_argument("--list", "-l", required = False, type=str, action="store", help="file containing list of filenames")
    
    parser.add_argument("--output", "-o", required = False, action="store", help="output directory")
    parser.add_argument("--action", "-a", required = False, action="store", help="test, copy, or move")
    parser.add_argument("--query", "-q", required = False, type=str, action="store", help="search query")
    
    args, args_unknown = parser.parse_known_args()
    
    input = args.input
    output_dir = args.output
    action = get_action(args.action)
    query = args.query
    
    # check for valid action
    if not action:
        return False
    
    if not output_dir:
        output_dir = "output"
    
    if not args.list:
        # find episode and caption files
        files = listdir_fullpath(input)
    else:
        list_file = open(args.list, 'r')
        lines = list_file.readlines()
        files = [x.strip() for x in lines]
        list_file.close()
    
    # filter caption and episode files
    captions = list(filter(lambda ep: (get_filetype(ep) == Filetype.CAPTION), files))
    episodes = list(filter(lambda ep: (get_filetype(ep) == Filetype.VIDEO), files))
    
    if len(episodes) != 0:
        for ep in episodes:
            process_file(ep, action, output_dir, query)
    
    if len(captions) != 0:
        for cap in captions:
            process_file(cap, action, output_dir, query)
    
    return True
    
if __name__ == "__main__":
    main()
    

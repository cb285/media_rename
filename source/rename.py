#!/usr/bin/env python3

import argparse
import re
from enum import Enum
import os.path
import hashlib
from utils import file
from utils.file import FileType
from utils.language import LANGUAGE_MAP
from db_api import imdb
import colorama

HISTORY_FILENAME = "history"
past_show_info = dict()

NON_TITLE_WORDS = [ "bluray", "brrip", "webrip", "aac", "aac2", "h264", "480i", "576i", "480p", "576p", "720p", "1080i", "1080p", "x264", "x265" ]

class Action(Enum):
    TEST = 0
    MOVE = 1
    COPY = 2

class Format(Enum):
    TITLE         = [ "%T", "movie/show title" ]
    YEAR          = [ "%Y", "movie/show year" ]
    EPISODE_TITLE = [ "%t", "episode title" ]
    SEASON        = [ "%s", "season number" ]
    EPISODE       = [ "%e", "episode number" ]

class MediaType(Enum):
    UNKNOWN = 0
    MOVIE   = 1
    TV      = 2

class MediaFile():
    def __init__(self):
        self.file_type = FileType.UNKNOWN
        self.media_type = MediaType.UNKNOWN
        self.filename = None
        self.season = None
        self.episode = None

    def __str__(self):
        return self.filename

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

def format_movie(movie, format, old_filename, language = None):

    extension = file.extension(old_filename)

    if language:
        extension = "." + language + extension

    new = format
    
    new = new.replace(Format.TITLE.value[0], movie.title)
    new = new.replace(Format.YEAR.value[0], str(movie.year))
    
    return new + extension

def format_tv(show, format, season, episode, old_filename, language = None):

    episode_info = show.episodes[season][episode]

    extension = file.extension(old_filename)

    if language:
        extension = "." + language + extension

    new = format

    new = new.replace(Format.TITLE.value[0], show.title)
    new = new.replace(Format.YEAR.value[0], str(show.year))
    new = new.replace(Format.EPISODE_TITLE.value[0], episode_info["title"])
    new = new.replace(Format.SEASON.value[0], "{:02d}".format(season))
    new = new.replace(Format.EPISODE.value[0], "{:02d}".format(episode))

    return new + extension
    
def get_season_episode(s):
    matches = re.findall("(?i)S(\d+)(?:E(\d+))?", s)

    # no results
    if len(matches) == 0:
        return None, None

    # prefer matches later in string that have both season and episode
    matches.reverse()

    for match in matches:
        if match[1] != "":
            return int(match[0]), int(match[1])

    return int(matches[-1][0]), None

def get_language(filename):
    words = re.split('[^a-zA-Z0-9]', filename)
    words = [word.lower() for word in words]
    words.reverse()

    for word in words:
        for lang in LANGUAGE_MAP:
            if word in lang[0]:
                return lang[1]
    return None

def identify_media(filename, root_dir = None):
    rv = MediaFile()
    rv.location = os.path.abspath(filename)
    rv.filename = filename.strip()

    if root_dir:
        rv.filename = os.path.relpath(rv.filename, root_dir)

    season, episode = get_season_episode(filename)
    rv.file_type = file.type(filename)

    if (rv.file_type == FileType.VIDEO) or (rv.file_type == FileType.CAPTION):
        # tv show file
        if season:
            rv.media_type = MediaType.TV
            rv.season = season
            rv.episode = episode

        # movie file
        else:
            rv.media_type = MediaType.MOVIE

    return rv

def update_history(old, new, action):

    s = "{},{},\"{}\",\"{}\"".format(action_to_string(action), file.checksum(old), old, new)

    history_file = open(HISTORY_FILENAME, "a+")
    history_file.write(s + "\n")
    history_file.close()

def apply_action(old, new, action = Action.TEST, interactive = False, print_width = 0):

    print("[{}] \"{:<{width}}\" >> \"{}\"".format(action_to_string(action), old, new, width = print_width))

    if interactive:
        while True:
            s = input("[y]es, [n]o, [s]kip: ")

            if type(s) is str:
                s = s.strip().lower()

            if (s == "y") or (s == "yes"):
                print("yes")
                break
            elif (s == "n") or (s == "no"):
                print("no")
                return False
            if (s == "s") or (s == "skip"):
                print("skip")
                return True
            else:
                print("invalid option")
                continue

    if action != Action.TEST:

        # check if file exists
        if not os.path.exists(old):
            print_error("file doesn't exist \"{}\"".format(old))
            return False

        try:
            if action == Action.MOVE:
                file.move(old, new, make_dirs=True)
            elif action == Action.COPY:
                file.copy(old, new, make_dirs=True)
            else:
                return False

        except FileNotFoundError:
            print_error("file doesn't exist")
            return False

    # update history on success
    update_history(old, new, action)

    return True

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

def guess_title(media):

    filename = media.filename #file.basename

    words = re.split('[^a-zA-Z0-9]', filename)
    
    words = [word.lower() for word in words]
    
    # remove extension
    words = words[:-1]
    
    title = ""
    
    for word in words:
    
        # assume title stops when we reach a non-title word or "SxxExx"
        season, episode = get_season_episode(word)

        if season or (word in NON_TITLE_WORDS):
            break
        else:
            title += word + " "
    
    return title.strip()

def process_movie(mov, action, format, query = None, interactive = False, language = None):

    if not query:
        search = guess_title(mov)
    else:
        search = query

    print("movie file \"{}\"".format(mov.filename))
    print("search \"{}\"".format(search))

    # get subtitle language
    det_language = None
    if mov.file_type == FileType.CAPTION:
        det_language = get_language(mov.filename)

        # couldn't identify language
        if not det_language:
            #if not language:
            print_error("couldn't identify subtitle language")
            return True
        # identified a language
        elif language is not None:
            if language.lower() != det_language.lower():
                # skip other languages
                return True

    info = imdb.search_movie(search)

    if not info:
        print_error("not matches found")
        return False
    
    new_filename = format_movie(info, format, mov.filename, det_language)
    
    if not apply_action(mov.location, new_filename, action, interactive=interactive):
        return False

    print()
    return True

def process_tv(tv, action, format, query = None, interactive = False, language = None):

    if not query:
        search = guess_title(tv)
    else:
        search = query

    print("TV file \"{}\"".format(tv.filename))
    print("search \"{}\"".format(search))

    info = imdb.search_tv(search)

    if not info:
        print_error("not matches found")
        return False
    
    # get season and episode from filename
    season, episode = get_season_episode(tv.filename)

    # get subtitle language
    det_language = None
    if tv.file_type == FileType.CAPTION:
        det_language = get_language(tv.filename)

        # couldn't idenfify language
        if not det_language:
            print_error("couldn't identify subtitle language")
            return False
        # identified a language
        elif language is not None:
            if language.lower() != det_language.lower():
                # skip other languages
                return True

    # check if have info for this episode
    if season not in info.episodes:
        print_error("season {:>02} not found".format(season))
        return False
    
    if episode not in info.episodes[season]:
        print_error("S{:>02}E{:>02} not found".format(season, episode))
        return False
    
    new_filename = format_tv(info, format, season, episode, tv.filename, det_language)
    
    if not apply_action(tv.location, new_filename, action, interactive=interactive):
        return False

    print()
    return True
    
def format_help():

    s = ""
    for spec in [e.value for e in Format]:
        s += "\"%{}\" : {}\n".format(spec[0], spec[1])
    
    return s

def print_list(l):
    for item in l:
        print(str(item))

def main():
    
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    
    # require input file/directory or list file
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", "-i", required = False, type=str, action="store", help="input directory")
    group.add_argument("--list", "-l", required = False, type=str, action="store", help="file containing list of filenames")

    parser.add_argument("--tv-format", "-tvf", required = True, type=str, action="store", help=format_help())
    parser.add_argument("--movie-format", "-movf", required = True, type=str, action="store", help=format_help())
    parser.add_argument("--action", "-a", required = False, type=str, action="store", help="test, copy, or move")
    parser.add_argument("--query", "-q", required = False, type=str, action="store", help="search query")
    parser.add_argument("--interactive", "-int", required = False, action="store_true", help="interactive mode")
    parser.add_argument("--root", required = False, type=str, action="store", help="directory under which all input files are located")
    parser.add_argument("--language", "-lang", required = False, type=str, action="store", help="only use subtitles with this language, fallback to when language is not detected")

    args, args_unknown = parser.parse_known_args()

    input = args.input
    list_filename = args.list
    movie_format = args.movie_format
    tv_format = args.tv_format
    action = get_action(args.action)
    query = args.query
    interactive = args.interactive
    root_dir = args.root
    language = args.language

    # check for valid action
    if not action:
        return False
    
    if not args.list:
        # find episode and caption files
        files = file.listdir(input, recursive = True)
    else:
        list_file = open(list_filename, 'r')
        lines = list_file.readlines()
        
        files = []
        
        for line in lines:
            line = line.strip()
            if line != "":
                files.append(line)

        list_file.close()

    # sort files alphabetically
    files = sorted(files, key=str.lower)

    media = []
    
    # identify files
    for f in files:
        media.append(identify_media(f, root_dir))
    
    # filter by type
    movie_files = list(filter(lambda m: (m.media_type == MediaType.MOVIE), media))
    tv_files = list(filter(lambda m: (m.media_type == MediaType.TV), media))
    
    print("movie_files:")
    print_list(movie_files)
    print()
    
    print("tv_files:")
    print_list(tv_files)
    print()

    for m in movie_files:
        if not process_movie(m, action, movie_format, query, interactive, language):
            return False

    for m in tv_files:
        if not process_tv(m, action, tv_format, query, interactive, language):
            return False

    return True
    
if __name__ == "__main__":
    main()
    

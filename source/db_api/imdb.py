#!/usr/bin/env python3

from .common import TvInfo, MovieInfo
import imdb

imdb_api = imdb.IMDb()
past_movie_results = dict()
past_tv_results = dict()

def search_tv(query):
    global past_tv_results
    # check if already have results
    if query in past_tv_results:
        return past_tv_results[query]
    
    res = imdb_api.search_movie(query)
    
    if not res:
        return None, None

    series = imdb_api.get_movie(res[0].movieID)
    imdb_api.update(series, "episodes")
    
    info = TvInfo()
    info.title = series["title"]
    info.year = series["year"]
    
    for season in series["episodes"]:

        info.episodes[season] = dict()

        for episode in series["episodes"][season]:
        
            info.episodes[season][episode] = dict()
            info.episodes[season][episode]["title"] = series["episodes"][season][episode]["title"]
    
    # save to reuse
    past_tv_results[query] = info
    
    return info

def search_movie(query):
    global past_movie_results
    # check if already have results
    if query in past_movie_results:
        return past_movie_results[query]
    
    res = imdb_api.search_movie(query)
    
    if not res:
        return None

    movie = imdb_api.get_movie(res[0].movieID)
    
    info = MovieInfo()
    info.title = movie["title"]
    info.year = movie["year"]

    past_movie_results[query] = info 
    
    return info

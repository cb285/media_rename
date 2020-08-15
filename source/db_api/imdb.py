#!/usr/bin/env python3

import imdb

imdb_api = imdb.IMDb()
past_results = dict()

def search(query):
    
    # check if already have results
    if query in past_results:
        return past_results[query]
    
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
    past_results[query] = title, episodes
    
    return title, episodes

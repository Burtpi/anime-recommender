import json
from itertools import product
from collections import Counter
import requests
from functools import reduce
from operator import add

CLIENT_ID = ""
USERNAME = ""
EXCLUDE = [
    # e.g. 'movie'
]
# You need a data file with anime details (from MAL database) such as ID, Title, Start date, Mean, Media type, Genres
with open('data.json') as json_file:
    database = json.load(json_file)


def import_anime_list(client_id, username):
    headers = {
        'X-MAL-CLIENT-ID': client_id
    }
    response = requests.get(
        url=f"https://api.myanimelist.net/v2/users/{username}/animelist?fields=list_status,media_type&limit=1000",
        headers=headers
    )
    user = response.json()
    response.close()
    return user['data']


def create_anime_details_list(anime_list, anime_database):
    detailed_list = []
    for anime, data in product(anime_list, anime_database):
        if (anime['list_status']['status'] == "completed"
                and anime['node']['id'] == data['id']):
            detailed_list.append({
                "id": anime['node']['id'],
                "genres": data['genres'],
                "score": anime['list_status']['score'],
                "start_date": data['start_date'].split('-')[0]
            })
            anime_database.remove(data)
    return detailed_list


def exclude_anime(anime_database, exclude_list):
    for data in list(anime_database):
        if 'genres' not in data or 'start_date' not in data:
            anime_database.remove(data)
        else:
            for genre in data['genres']:
                if (genre['name'] in exclude_list
                        or data['media_type'] in exclude_list):
                    anime_database.remove(data)
                    break


def create_genre_list(anime_list):
    genres = []
    for anime in anime_list:
        for genre in anime['genres']:
            genres.append({genre['name']: anime['score']})
    return genres


def create_year_list(anime_list):
    years = []
    for anime in anime_list:
        years.append({anime['start_date']: anime['score']})
    return years


def create_factor_data(factor):
    factor_data = []
    factor_count = dict(Counter(tuple(i.keys())[0] for i in factor))
    factor_sum_score = dict(reduce(add, map(Counter, factor)))
    for element, score in product(range(len(factor_count)), range(len(factor_sum_score))):
        if list(factor_count.keys())[element] == list(factor_sum_score.keys())[score]:
            factor_data.append({
                "name": list(factor_count.keys())[element],
                "amount": list(factor_count.values())[element],
                "score": round(float(list(factor_sum_score.values())[score]) /
                               float(list(factor_count.values())[element]), 2)
            })
    return factor_data


def create_list_data(genre_data, year_data):
    list_data = [
        sorted(genre_data, key=lambda i: i['amount'], reverse=True),
        sorted(year_data, key=lambda i: i['amount'], reverse=True)
    ]
    with open('anime_data.json', 'w') as f:
        json.dump(list_data, f, indent=4)


def rec_system(anime_database, genre_data, year_data):
    rec_list = []
    max_amount_genre = max([d['amount'] for d in genre_data])
    max_amount_year = max([d['amount'] for d in year_data])
    max_amount = max([len(d['genres']) for d in anime_database])
    for anime in anime_database:
        count = 1
        score = 0
        for genre, subgen in product(anime['genres'], genre_data):
            if genre['name'] == subgen['name']:
                count += 1
                score += ((1 - (0.3 * (max_amount_genre - subgen['amount']) / max_amount_genre))
                          * subgen['score'])
        for year in year_data:
            if anime['start_date'] == year['name']:
                count += 1
                score += ((1 - (0.5 * (max_amount_year - year['amount']) / max_amount_genre))
                          * year['score'])
        if anime['start_date'] not in [year.values() for year in year_data]:
            count += 1
        score += anime['mean']
        score /= ((1 + 0.05 * ((max_amount - count) / max_amount))
                  * count)
        rec_list.append({
            'id': anime['id'],
            'name': anime['title'],
            'score': round(score, 2),
            'link': f"https://myanimelist.net/anime/{anime['id']}"
        })
    rec_list = sorted(rec_list, key=lambda i: i['score'], reverse=True)[:100]
    with open('anime.json', 'w') as f:
        json.dump(rec_list, f, indent=4)


if __name__ == "__main__":
    user_anime_list = import_anime_list(CLIENT_ID, USERNAME)
    anime_list_details = create_anime_details_list(user_anime_list, database)
    exclude_anime(database, EXCLUDE)
    genre_detailed = create_factor_data(create_genre_list(anime_list_details))
    year_detailed = create_factor_data(create_year_list(anime_list_details))
    create_list_data(genre_detailed, year_detailed)
    rec_system(database, genre_detailed, year_detailed)

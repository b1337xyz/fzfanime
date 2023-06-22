#!/usr/bin/env python3
from utils import *
from urllib.parse import quote
from time import sleep


class MAL:
    def __init__(self, session):
        self.db = load_json(MALDB)
        self.session = session
        self.api = 'https://api.jikan.moe/v4/anime/'

    def search(self, query: str = None, mal_id: int = None) -> dict:
        print(f' --- Jikan {query = }, {mal_id = }')
        url = self.api + f'?q={quote(query)}' if query else mal_id
        return self.session.get(url).json().get('data')

    def filter_by_year(self, year: int, data: list) -> list:
        by_year = [
            i for i in data
            if year in [i['year'], i["aired"]["prop"]["from"]["year"]]
        ]
        return by_year if by_year else data

    def get_info(self, title: str) -> dict:
        if (idMal := re.search(r'\[malid-(\d+)\]', title)) is not None:
            return self.search(idMal=idMal.group(1))

        year = get_year(title)
        query = clean_str(title)
        if len(query) < 3:
            print(f'Query length less than 3: {query = }')
            return

        if (info := self.search(query.lower())) is None:
            return

        info = self.filter_by_year(year, info) if year else info
        return fuzzy_sort(query, {
            i: clean_str(d['title']) for i, d in enumerate(info)
        }, info)

    def update(self, title: str, fullpath: str):
        info = self.get_info(title)
        if not info:
            return

        url = info['images']['jpg']['large_image_url']
        filename = f'mal-{info["mal_id"]}.jpg'
        image = save_image(url, filename)

        year = info.get('year', info["aired"]["prop"]["from"]["year"])
        rating = None if not info['rating'] else info['rating'].split()[0]

        self.db[title] = {
            'anilist_id': None,
            'duration': None,
            'episodes': info['episodes'],
            'genres': [i['name'] for i in info['genres']],
            'image': image,
            'is_adult': rating == "Rx",
            'mal_id': int(info['mal_id']),
            'rating': rating,
            'score': info['score'],
            'studios': [i['name'] for i in info['studios']],
            'title': clean_str(info['title']),
            'type': info['type'],
            'year': year,
            'aired': info['aired']['from'],
            'fullpath': fullpath
        }


class Anilist:
    def __init__(self, session):
        self.db = load_json(ANIDB)
        self.session = session
        self.api = 'https://graphql.anilist.co'

    def search(self, **variables) -> dict:
        variables.update({'page': 1, 'perPage': 15})
        print(' --- Anilist', variables)
        data = self.session.post(self.api, json={
            'query': API_QUERY, 'variables': variables
        }).json()
        return data['data']['Page']['media']

    def filter_by_year(self, year: int, data: list) -> list:
        by_year = [i for i in data if i['startDate']['year'] == year]
        return by_year if by_year else data

    def get_info(self, title: str, mal_id: int = None) -> dict:
        if mal_id:
            try:
                return self.search(idMal=mal_id)[0]
            except IndexError:
                pass

        year = get_year(title)
        query = clean_str(title)
        info = self.search(search=query.lower())
        info = self.filter_by_year(year, info) if year else info
        return fuzzy_sort(query, {
            i: d['title']['romaji'] for i, d in enumerate(info)
        }, info)

    def update(self, title: str, fullpath: str, fallback: dict):
        info = self.get_info(title, fallback.get('mal_id'))
        if not info and fallback:
            fallback['score'] *= 10  # bug: score can be None?
            self.db[title] = fallback
            return

        url = info['coverImage']['large']
        filename = f'anilist-{info["id"]}.jpg'
        image = save_image(url, filename)

        if (score := info['averageScore']) is None:
            score = fallback.get('score', 0) * 10

        self.db[title] = {
            'anilist_id': info['id'],
            'duration': info['duration'],
            'episodes': info['episodes'],
            'genres': info['genres'],
            'image': image,
            'is_adult': info['isAdult'],
            'mal_id': info['idMal'],
            'rating': None,
            'score': score,
            'studios': [i['name'] for i in info['studios']['nodes']],
            'title': clean_str(info['title']['romaji']),
            'type': None,
            'year': info['startDate']['year'],
            'aired': None,
            'fullpath': fullpath
        }


def main():
    session = requests.Session()
    mal = MAL(session)
    anilist = Anilist(session)
    titles = [i for i in get_titles() if i[1] not in mal.db]
    if not titles:
        print('Nothing new.')
        return

    total = len(titles)
    for idx, tmp in enumerate(titles, start=1):
        fullpath, title = tmp
        print(f'[{idx}/{total}] {title}')

        mal.update(title, fullpath)
        anilist.update(title, fullpath, mal.db.get(title, {}).copy())

        fill_the_gaps(anilist.db, mal.db)
        save_json(anilist.db, ANIDB)
        save_json(mal.db, MALDB)
        sleep(0.3)


if __name__ == '__main__':
    main()

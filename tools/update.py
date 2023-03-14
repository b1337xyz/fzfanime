#!/usr/bin/env python3
from utils import *
from urllib.parse import quote


class MAL:
    def __init__(self, session):
        self.db = load_json(MALDB)
        self.session = session

    def request(self, url: str) -> dict:
        try:
            return self.session.get(url).json()['data']
        except KeyError:
            return

    def filter_by_year(self, year: int, data: list) -> list:
        by_year = [
            i for i in data
            if year in [i['year'], i["aired"]["prop"]["from"]["year"]]
        ]
        return by_year if by_year else data

    def get_info(self, title: str) -> dict:
        malid = re.search(r'\[malid-(\d+)\]', title)
        if malid:
            malid = malid.group(1)
            url = f'https://api.jikan.moe/v4/anime/{malid}'
            return self.request(url)

        year = get_year(title)
        query = clean_str(title)
        if len(query) < 3:
            print(f'Query length less than 3: {query = }')
            return

        url = '{}?q={}'.format(JIKAN_API, quote(query.lower()))
        info = self.request(url)
        if not info:
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

        year = info['year'] if info['year'] else \
            info["aired"]["prop"]["from"]["year"]

        rating = None if not info['rating'] else info['rating'].split()[0]

        self.db[title] = {
            'anilist_id': None,
            'duration': None,
            'episodes': info['episodes'],
            'genres': [i['name'] for i in info['genres']],
            'image': image,
            'is_adult': rating == "Rx",
            'mal_id': info['mal_id'],
            'rating': rating,
            'score': info['score'],
            'studios': [i['name'] for i in info['studios']],
            'title': clean_str(info['title']),
            'type': info['type'],
            'year': year,
            'fullpath': fullpath
        }


class Anilist:
    def __init__(self, session):
        self.db = load_json(ANIDB)
        self.session = session

    def search_by_id(self, mal_id: int) -> dict:
        variables = {'idMal': mal_id, 'page': 1, 'perPage': 10}
        data = self.session.post(ANILIST_API, json={
            'query': api_query_by_malid, 'variables': variables
        }).json()
        return data['data']['Page']['media'][0]

    def search(self, query: str) -> dict:
        variables = {'search': query, 'page': 1, 'perPage': 20}
        data = self.session.post(ANILIST_API, json={
            'query': api_query, 'variables': variables
        }).json()
        return data['data']['Page']['media']

    def filter_by_year(self, year: int, data: list) -> list:
        by_year = [i for i in data if i['startDate']['year'] == year]
        return by_year if by_year else data

    def get_info(self, title: str, maldb: dict) -> dict:
        if title in maldb:
            malid = int(maldb[title]['mal_id'])
            try:
                return self.search_by_id(malid)
            except Exception:
                pass

        year = get_year(title)
        query = clean_str(title)
        info = self.search(query.lower())
        info = self.filter_by_year(year, info) if year else info
        return fuzzy_sort(query, {
            i: d['title']['romaji'] for i, d in enumerate(info)
        }, info)

    def update(self, title: str, fullpath: str, maldb: dict):
        info = self.get_info(title, maldb)
        if not info and title in maldb:
            self.db[title] = maldb[title].copy()
            if maldb[title]['score']:
                self.db[title]['score'] = int(maldb[title]['score'] * 10)
            return

        url = info['coverImage']['large']
        filename = f'anilist-{info["id"]}.jpg'
        image = save_image(url, filename)

        score = info['averageScore']
        if not score and title in maldb and maldb[title]['score']:
            score = int(maldb[title]['score'] * 10)

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
        anilist.update(title, fullpath, mal.db)

    fill_the_gaps(anilist.db, mal.db)
    save_json(anilist.db, ANIDB)
    fill_the_gaps(mal.db, anilist.db)
    save_json(mal.db, MALDB)


if __name__ == '__main__':
    main()

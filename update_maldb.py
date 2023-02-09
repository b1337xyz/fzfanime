#!/usr/bin/env python3
from utils import *
from urllib.parse import quote
from time import sleep

IMG_DIR = os.path.join(HOME, '.cache/mal_covers')
if not os.path.exists(IMG_DIR):
    os.mkdir(IMG_DIR)


def request(url: str) -> dict:
    sleep(0.5)
    data = session.get(url).json()
    try:
        return data['data']
    except KeyError:
        return


def filter_by_year(year: int, data: list) -> list:
    by_year = [
        i for i in data
        if year in [i['year'], i["aired"]["prop"]["from"]["year"]]
    ]
    return by_year if by_year else data


def get_info(title: str) -> dict:
    malid = re.search(r'\[malid-(\d+)\]', title)
    if malid:
        malid = malid.group(1)
        url = f'https://api.jikan.moe/v4/anime/{malid}'
        try:
            return request(url)
        except Exception:
            print(f'Failed to find by MALID: {malid}')

    year = get_year(title)
    query = clean_str(title)
    print(f'{GRN}{title = }\n{query = }{END}')
    if len(query) < 3:
        return

    url = '{}?q={}'.format(JIKAN_API, quote(query.lower()))
    results = request(url)
    if not results:
        return

    results = filter_by_year(year, results) if year else results
    return fuzzy_sort(query, {
        i: clean_str(d['title']) for i, d in enumerate(results)
    }, results)


def update_maldb(title: str, info: dict):
    year = info['year'] if info['year'] else \
        info["aired"]["prop"]["from"]["year"]
    image = save_image(info['images']['jpg']['large_image_url'], IMG_DIR)
    rating = None if not info['rating'] else info['rating'].split()[0]
    maldb[title] = {
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
    }


def main():
    global maldb, session
    session = requests.Session()
    maldb = load_json(MALDB)
    titles = [i for i in get_titles() if i[1] not in maldb]
    if not titles:
        print('Nothing to do')
        return

    total = len(titles)
    for idx, tmp in enumerate(titles, start=1):
        fullpath, title = tmp
        print('MALDB {} of {}: {}'.format(idx, total, title))

        info = get_info(title)
        if not info:
            print('Nothing found')
            continue

        update_maldb(title, info)
        maldb[title]['fullpath'] = fullpath
        print(json.dumps(maldb[title], indent=2))

    save_json(maldb, MALDB)


if __name__ == '__main__':
    main()

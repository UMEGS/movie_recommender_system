import string
import time

import nltk
import requests
import pandas as pd
from threading import Thread

from nltk.stem.porter import PorterStemmer
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed


base_url = "https://yts.mx/api"
details_url = base_url + "/v2/movie_details.json"
movie_data = []
total_movie_id = 45954



def get_movie_details(movie_id):
    params = {"movie_id": movie_id, "with_images": "true", "with_cast": "true"}
    try:
        response = requests.get(details_url, params=params)
        response_json = response.json()
        movie_details = response_json["data"]["movie"]
        if movie_details.get("id") == movie_id:
            movie = {
                "id": movie_details.get("id"),
                "imdb_code": movie_details.get("imdb_code"),
                "title": movie_details.get("title"),
                "title_english": movie_details.get("title_english"),
                "title_long": movie_details.get("title_long"),
                "year": movie_details.get("year"),
                "rating": movie_details.get("rating"),
                "runtime": movie_details.get("runtime"),
                "genres": movie_details.get("genres", []),
                "download_count": movie_details.get("download_count"),
                "like_count": movie_details.get("like_count"),
                "description_full": movie_details.get("description_full"),
                "language": movie_details.get("language"),
                "cast": [{"name": cast.get("name"), "character_name": cast.get("character_name")} for cast in
                         movie_details.get("cast", [])],
            }
            return movie
        else:
            return {
                "id": movie_id,
                "imdb_code": 'None',
                "title": 'None',
                "title_english": 'None',
                "title_long": '',
                "year": '',
                "rating": '',
                "runtime": '',
                "genres": 'None',
                "download_count": 'None',
                "like_count": 'None',
                "description_full": 'None',
                "language": 'None',
                "cast": [],
            }
    except Exception as e:
        return {
                "id": movie_id,
                "imdb_code": 'Error',
                "title": 'Error',
                "title_english": 'Error',
                "title_long": '',
                "year": '',
                "rating": '',
                "runtime": '',
                "genres": 'Error',
                "download_count": 'Error',
                "like_count": 'Error',
                "description_full": 'Error',
                "language": 'Error',
                "cast": [],
            }



def get_movie_data_range(movie_range,thread_id):
    for movie_id in movie_range:
        movie = get_movie_details(movie_id)
        if movie:
            movie_data.append(movie)
            # print("Movie Data Saved: {} Movie ID: {} Thread: {} ".format(len(movie_data),movie["id"],thread_id))
    # return movie_data


def movie_prerossing(df):
    df = df.copy(deep=True)
    stopwords = nltk.corpus.stopwords.words('english')
    ps = PorterStemmer()

    def description_preprossing(text):
        text = text.replace('-', ' ').translate(str.maketrans('', '', string.punctuation))
        text = ' '.join([word for word in text.split() if word not in stopwords])
        return text

    def get_top_3_cast(x):
        return [value for cast in eval(x)[:3] for value in (cast['name'], cast['character_name'])]

    def staming(text):
        return " ".join([ps.stem(word) for word in text.split()])

    print('drop null title')
    df.drop(index=df[(df.title_english.isnull()) | (df.title_english == 'None')].index, inplace=True)

    print('genres eval')
    df.genres = df.genres.apply(eval)

    print('top 3 cast')
    df.cast = df.cast.apply(get_top_3_cast)

    print('description fill na')
    df.description_full.fillna('', inplace=True)

    print('description preprossing')
    df.description_full = df.description_full.apply(description_preprossing)

    print('description split')
    df.description_full = df.description_full.apply(lambda x: x.split())

    print('genres replace')
    df.genres = df.genres.apply(lambda x: [i.replace(" ", "") for i in x])

    print('description replace')
    df.description_full = df.description_full.apply(lambda x: [i.replace(" ", "") for i in x])

    print('cast split')
    df.cast = df.cast.apply(lambda x: [i.replace(" ", "") for i in x])

    print('making tag')
    df['tag'] = df.genres + df.description_full + df.cast

    print('join and to lower')
    df.tag = df.tag.apply(lambda x: " ".join(x).lower())

    print('staming')
    df.tag = df['tag'].apply(staming)

    return df[['id', 'title_english', 'tag']]



# if __name__ == "__main__":
#     movie_data = get_movie_data_range(movie_id)
#     df = pd.DataFrame(movie_data)
#     df.to_excel("movies.xlsx", index=False)
#     print("Movie Data Saved")

def check_completed():
    return len(movie_data) > total_movie_id

def pbar_function(pbar):
    while not check_completed():
        # print("Movie Data Saved: {}".format(len(movie_data)))
        # pbar.reset(total=None)
        pbar.n = len(movie_data)
        pbar.refresh()
        time.sleep(0.5)

if __name__ == "__main__":
    # use multithreading to get movie data
    start = 1
    end = 46000
    step = 4000
    threads = []
    pbar = tqdm(total=total_movie_id)
    pbar_thread = Thread(target=pbar_function, args=(pbar,))
    pbar_thread.start()

    for i in range(start, end, step):
        thread = Thread(target=get_movie_data_range, args=(range(i, i + step), i))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    # pbar_thread = Thread(target=pbar_function, args=(pbar,))
    pbar_thread.join()
    pbar.close()


    # movie_data = [movie for movie_list in movie_data for movie in movie_list]
    df = pd.DataFrame(movie_data)
    df.to_excel("movies.xlsx", index=False)



# if __name__ == "__main__":
#     start = 1
#     end = 4600
#     step = 10
#     movie_data = []
#     i = 1
#     ranges = [range(i, i + step) for i in range(start, end, step)]
#
#     with tqdm(total=len(ranges)) as pbar:
#         with ThreadPoolExecutor(max_workers=len(ranges)) as ex:
#             futures = [ex.submit(get_movie_data_range, single_range) for single_range in ranges]
#             for future in as_completed(futures):
#                 result = future.result()
#                 movie_data.extend(result)
#                 pbar.update(1)
#                 # i += 1
#                 # print(i)
#
#     df = pd.DataFrame(movie_data)
#     df.to_excel("movies.xlsx", index=False)

# movies_list = []
# while True:
#     movie_details = get_movie_details(movie_id)
#     if movie_details is None or movie_details.get("id") == 10:
#         break
#
#     movies_list.append(movie_details)
#
#     print("Movie ID: {}".format(movie_details["id"]))
#     movie_id += 1
#
# print("Total movies: {}".format(len(movies_list)))
#
# df = pd.DataFrame(movie_data)
# df.to_excel("movies.xlsx", index=False)
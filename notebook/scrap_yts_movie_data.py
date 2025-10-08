import pickle
import string
import time
from multiprocessing import Process, Manager, cpu_count
from functools import partial

import nltk
import requests
import pandas as pd

from nltk.stem.porter import PorterStemmer
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed


base_url = "https://yts.mx/api"
details_url = base_url + "/v2/movie_details.json"
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



def get_movie_data_range(movie_range):
    """
    Fetch movie details for a range of movie IDs.
    Returns a list of movie dictionaries.
    """
    results = []
    for movie_id in movie_range:
        movie = get_movie_details(movie_id)
        if movie:
            results.append(movie)
    return results




def movie_prerossing(df):
    df = df.copy(deep=True)
    stopwords = nltk.corpus.stopwords.words('english')
    ps = PorterStemmer()

    def description_preprossing(text):
        text = text.replace('-', ' ').translate(str.maketrans('', '', string.punctuation))
        text = ' '.join([word for word in text.split() if word not in stopwords])
        return text

    def get_top_3_cast(x):
        return [value for cast in str_to_object(x)[:3] for value in (cast['name'], cast['character_name'])]

    def str_to_object(x):
        if type(x) == str:
            return eval(x)
        return x

    def staming(text):
        return " ".join([ps.stem(word) for word in text.split()])

    print('drop null title')
    df.drop(index=df[(df.title_english.isnull()) | (df.title_english == 'None')].index, inplace=True)

    print('genres eval')
    df.genres = df.genres.apply(str_to_object)

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

vectorizer = pickle.load(open('vectorizer.pk','rb'))
vectorized_tag = pickle.load(open('vectorized_tag.pk','rb'))
movie_list = pickle.load(open('movie_list.pkl','rb'))

def recommend(movie_id,top):
    movie_guess = get_movie_details(movie_id)
    if movie_guess.get('title_english') == 'None' or movie_guess.get('title_english') == 'Error':
        return []
    movie_guess = pd.DataFrame([movie_guess])
    movie_guess = movie_prerossing(movie_guess)
    movie_guess = vectorizer.transform(movie_guess['tag'])

    similarity = cosine_similarity(vectorized_tag,movie_guess)
    top_similarity = sorted(list(enumerate(similarity)), reverse=True, key=lambda x: x[1])[1:top+1]

    top_movie_index = [i[0] for i in top_similarity]
    return list(movie_list.iloc[top_movie_index].id.values)

# if __name__ == "__main__":
#     movie_data = get_movie_data_range(movie_id)
#     df = pd.DataFrame(movie_data)
#     df.to_excel("movies.xlsx", index=False)
#     print("Movie Data Saved")

if __name__ == "__main__":
    # Use multiprocessing to get movie data - much faster than multithreading
    start = 1
    end = 46000
    step = 500  # Smaller chunks for better load balancing

    # Create ranges for parallel processing
    ranges = [range(i, min(i + step, end)) for i in range(start, end, step)]

    # Use ProcessPoolExecutor for better performance
    # max_workers defaults to number of CPUs, but you can adjust
    max_workers = min(cpu_count() * 2, len(ranges))  # Use 2x CPU count for I/O-bound tasks

    print(f"Starting download with {max_workers} workers for {len(ranges)} chunks...")
    print(f"Total movies to fetch: {end - start}")

    movie_data = []

    with tqdm(total=len(ranges), desc="Downloading movie data") as pbar:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = {executor.submit(get_movie_data_range, movie_range): movie_range
                      for movie_range in ranges}

            # Process completed tasks as they finish
            for future in as_completed(futures):
                try:
                    result = future.result()
                    movie_data.extend(result)
                    pbar.update(1)
                    pbar.set_postfix({"Movies fetched": len(movie_data)})
                except Exception as e:
                    print(f"Error processing range: {e}")
                    pbar.update(1)

    print(f"\nTotal movies fetched: {len(movie_data)}")

    # Save to Excel
    df = pd.DataFrame(movie_data)
    df.to_excel("movies.xlsx", index=False)
    print("Movie data saved to movies.xlsx")



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
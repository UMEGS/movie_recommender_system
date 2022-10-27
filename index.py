import json
import numpy as np
import os
import pickle as pkl
import string
import nltk
import pandas as pd
from flask import Flask, render_template, request
import requests
from dotenv import load_dotenv
from nltk.stem.porter import PorterStemmer
from sklearn.metrics.pairwise import cosine_similarity

# nltk.download('stopwords')

load_dotenv()

print('listdir',os.listdir())
print('walk',os.walk('/'))

base_url = os.getenv('YTS_BASE_URL')
details_url = base_url + os.getenv('YTS_DETAILS_URL')

movie_list_path = os.getenv('MOVIE_LIST_PATH')
vectorized_tag_path = os.getenv('VECTORIZED_TAG_PATH')
vectorizer_path = os.getenv('VECTORIZER_PATH')


movie_list = pkl.load(open(movie_list_path, 'rb'))
vectorizer = pkl.load(open(vectorizer_path,'rb'))
vectorized_tag = pkl.load(open(vectorized_tag_path,'rb'))



app = Flask(__name__)



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
                'image': movie_details.get('medium_cover_image')

            }
            return movie
        else:
            return {
                "id": movie_id,"imdb_code": 'None',"title": 'None',"title_english": 'None',"title_long": '',
                "year": '',"rating": '',"runtime": '',"genres": 'None',"download_count": 'None',
                "like_count": 'None',"description_full": 'None',"language": 'None',"cast": [],'image': 'None'
            }
    except Exception as e:
        return {
                "id": movie_id,"imdb_code": 'Error',"title": 'Error',"title_english": 'Error',"title_long": '',
                "year": '',"rating": '',"runtime": '',"genres": 'Error',"download_count": 'Error',
                "like_count": 'Error',"description_full": 'Error',"language": 'Error',"cast": [],'image': 'Error'
            }

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


def recommend(movie_id,top=10):
    movie_guess = get_movie_details(movie_id)
    if movie_guess.get('title_english') == 'None' or movie_guess.get('title_english') == 'Error':
        return []
    movie_guess = pd.DataFrame([movie_guess])
    movie_guess = movie_prerossing(movie_guess)
    movie_guess = vectorizer.transform(movie_guess['tag'])

    similarity = cosine_similarity(vectorized_tag, movie_guess)
    top_similarity = sorted(list(enumerate(similarity)), reverse=True, key=lambda x: x[1])[1:top + 1]
    top_movie_index = [i[0] for i in top_similarity]
    top_movies = list(movie_list.iloc[top_movie_index].id.values)

    recommended_movies = []
    for id in top_movies:
        movie_data = get_movie_details(id)
        if movie_data.get('title_english') != 'None' and movie_data.get('title_english') != 'Error':
            recommended_movies.append({
                'title_english':movie_data.get('title_english'),
                'image':movie_data.get('image'),
                'id':movie_data.get('id')
                })

    return recommended_movies
@app.route('/recommend_api/<movie_id>', defaults={'top': 10})
@app.route('/recommend_api/<movie_id>/<top>', methods=['GET'])
def recommend_api(movie_id,top):
    movie_id,top = int(movie_id),int(top)
    movie_guess = get_movie_details(movie_id)
    if movie_guess.get('title_english') == 'None' or movie_guess.get('title_english') == 'Error':
        return []
    movie_guess = pd.DataFrame([movie_guess])
    movie_guess = movie_prerossing(movie_guess)
    movie_guess = vectorizer.transform(movie_guess['tag'])

    similarity = cosine_similarity(vectorized_tag,movie_guess)
    top_similarity = sorted(list(enumerate(similarity)), reverse=True, key=lambda x: x[1])[1:top+1]

    top_movie_index = [i[0] for i in top_similarity]
    return np.int64(movie_list.iloc[top_movie_index].id.values).tolist()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        selected_movie_id = int(request.form.get('movie'))
        recommended_movies = recommend(selected_movie_id)
        return render_template('index.html', recommended_movies=recommended_movies, movie_data=movie_list.to_dict('records'))
    return render_template('index.html', recommended_movies=[], movie_data=movie_list.to_dict('records'))

@app.route('/movie_detail/<id>', methods=['GET'])
def movie_detail(id):
    movie = movie_list[movie_list.id == int(id)]
    movie_poster = get_movie_details(int(id))
    return render_template('movie_details.html', movie=movie, movie_poster=movie_poster)

# st.title('Movie Recommender')
# movie_name = st.selectbox('Select a movie', movie_data['title'].values)
# if st.button('Recommend'):
#     recommend_movie = recommend(movie_name)
#     total_recommendations = len(recommend_movie)
#     progress_bar = st.progress(0)
#     for index,col in enumerate(st.columns(total_recommendations)):
#         col.image(recommend_movie[index][1], width=100, caption=recommend_movie[index][0], use_column_width=True)
#         progress_bar.progress((index+1)/total_recommendations)
#         time.sleep(0.2)
#     progress_bar.empty()

if __name__ == '__main__':
    app.run(debug=True,use_reloader=True)
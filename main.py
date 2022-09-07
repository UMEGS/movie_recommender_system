import os
import pickle as pkl
import time
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

movies_cosine_similarity = pkl.load(open('model/movies_cosine_similarity.pkl', 'rb'))
movie_data = pkl.load(open('model/movie_list.pkl', 'rb'))


def recommend(movie_name):
    movie_index = movie_data[movie_data['title'] == movie_name].index[0]
    distances = movies_cosine_similarity[movie_index]
    top_movies = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]
    recommended_movies = []
    for movie in top_movies:
        id = movie[0]
        movie_id = movie_data.iloc[id].movie_id
        name = movie_data.iloc[id].title
        movie_poster = fetch_poster(movie_id)
        if movie_poster:
            recommended_movies.append((name, movie_poster))

    return recommended_movies


def fetch_poster(movie_id):
    base_url = os.getenv('TMDB_BASE_URL')
    base_image_url = os.getenv('TMDB_IMAGE_BASE_URL')
    api_key = os.getenv('TMDB_API_KEY')
    bearer_key = os.getenv('TMDB_BEARER_KEY')
    url = f'{base_url}/3/movie/{movie_id}?api_key={api_key}'
    response = requests.get(url).json()
    if response.get('success') == False:
        return None
    else:
        poster_path = response['poster_path']
        poster_url = f'{base_image_url}/w500{poster_path}'
        return poster_url


st.title('Movie Recommender')
movie_name = st.selectbox('Select a movie', movie_data['title'].values)
if st.button('Recommend'):
    recommend_movie = recommend(movie_name)
    total_recommendations = len(recommend_movie)
    progress_bar = st.progress(0)
    for index,col in enumerate(st.columns(total_recommendations)):
        col.image(recommend_movie[index][1], width=100, caption=recommend_movie[index][0], use_column_width=True)
        progress_bar.progress((index+1)/total_recommendations)
        time.sleep(0.2)
    progress_bar.empty()






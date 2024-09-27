from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import os

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username1 = request.form["username1"]
        username2 = request.form["username2"]
        user1_movies = get_watched_movies(username1)
        user2_movies = get_watched_movies(username2)
        common_movies = set(tuple(movie['title'] for movie in user1_movies)) & set(tuple(movie['title'] for movie in user2_movies))
        
        # Uyum yüzdesini hesapla
        total_movies = len(user1_movies) + len(user2_movies)
        common_count = len(common_movies)
        compatibility_percentage = calculate_compatibility_percentage(common_count, total_movies)

        return render_template("result.html", username1=username1, username2=username2, 
                               common_movies=common_movies, compatibility_percentage=compatibility_percentage,
                               user1_movies=user1_movies, user2_movies=user2_movies)
    return render_template("index.html")

def get_watched_movies(username):
    watched_movies = []

    def get_movies(source):
        movies = source.find_all("li", class_="poster-container")
        for movie in movies:
            movie_title = movie.find("img")["alt"]  # Film ismini al
            
            # Kapak fotoğrafı özniteliklerini kontrol et
            movie_cover = movie.find("img").get("data-src") or movie.find("img").get("src")  # Önce 'data-src', sonra 'src'
            
            if movie_cover:  # Eğer kapak fotoğrafı varsa
                full_movie_cover = "https://letterboxd.com" + movie_cover if movie_cover.startswith("/") else movie_cover
            else:
                full_movie_cover = "https://via.placeholder.com/150"  # Kapak fotoğrafı yoksa varsayılan bir resim koy
            
            watched_movies.append({"title": movie_title, "cover": full_movie_cover})  # Film ismini ve kapak fotoğrafını ekle

    def connect_page():
        page_num = 1
        while True:
            url = f"https://letterboxd.com/{username}/films/page/{page_num}/"
            response = requests.get(url)
            source = BeautifulSoup(response.content, "lxml")
            if f'<a class="next" href="/{username}/films/' in str(source):
                get_movies(source)
                page_num += 1
            else:
                get_movies(source)
                break

    connect_page()
    return watched_movies

def calculate_compatibility_percentage(common_count, total_movies):
    if total_movies == 0:
        return 0
    # Yeni uyum oranı: Ortak film sayısına göre %50'den başlar ve yukarıya doğru gider
    base_percentage = 50
    additional_percentage = (common_count / total_movies) * 50  # Ortak film sayısına göre %50 daha eklenir
    return base_percentage + additional_percentage

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)

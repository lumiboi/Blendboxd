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
        
        # Ortak filmleri belirle
        common_movies = [movie for movie in user1_movies if movie in user2_movies]
        
        # Uyum yüzdesini hesapla
        compatibility_percentage = calculate_compatibility(len(common_movies))

        return render_template("result.html", username1=username1, username2=username2, 
                               common_movies=common_movies, compatibility_percentage=compatibility_percentage)
    return render_template("index.html")

def get_watched_movies(username):
    watched_movies = []

    def get_movies(source):
        movies = source.find_all("li", class_="poster-container")
        for movie in movies:
            movie_title = movie.find("img")["alt"]  # Film ismini al
            movie_cover = movie.find("img")["data-src"]  # Kapak fotoğrafını al (orijinalde data-src'den gelebilir)
            full_movie_cover = "https://letterboxd.com" + movie_cover if movie_cover.startswith("/") else movie_cover
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

def calculate_compatibility(common_movie_count):
    # Ortak film sayısına göre uyum oranı hesapla
    if common_movie_count == 0:
        return 0
    elif common_movie_count <= 5:
        return 0
    else:
        # %50'den başlayarak %50'nin üzerine ekle
        base_percentage = 50
        additional_percentage = (common_movie_count - 5) * 5  # Ortak film başına %5 ekleyelim
        final_percentage = base_percentage + additional_percentage

        # Uyum oranını %100 ile sınırla
        return min(final_percentage, 100)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)

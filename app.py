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
        compatibility_percentage = calculate_compatibility(len(user1_movies), len(user2_movies), len(common_movies))

        return render_template("result.html", username1=username1, username2=username2, 
                               common_movies=common_movies, compatibility_percentage=compatibility_percentage)
    return render_template("index.html")

def get_watched_movies(username):
    watched_movies = []

    def get_movies(source):
        movies = source.find_all("li", class_="poster-container")
        for movie in movies:
            # Film ismini al ve listeye ekle
            movie_title = movie.find("img")["alt"]
            watched_movies.append(movie_title)

    def connect_page():
        page_num = 1
        while True:
            url = f"https://letterboxd.com/{username}/films/page/{page_num}/"
            response = requests.get(url)
            if response.status_code != 200:
                break
            source = BeautifulSoup(response.content, "lxml")
            get_movies(source)

            # Sonraki sayfa kontrolü
            next_page = source.find("a", class_="next")
            if not next_page:
                break
            page_num += 1

    connect_page()
    return watched_movies

def calculate_compatibility(user1_movie_count, user2_movie_count, common_movie_count):
    # Eğer toplamda hiç film izlenmediyse uyum oranı 0 olmalı
    if user1_movie_count == 0 or user2_movie_count == 0:
        return 0

    # İki kullanıcının izleme oranlarına göre simetrik bir metrik oluştur
    user1_ratio = common_movie_count / user1_movie_count
    user2_ratio = common_movie_count / user2_movie_count

    # İki oranın ortalamasını alarak genel uyum oranını belirle
    compatibility_percentage = (user1_ratio + user2_ratio) / 2 * 100

    # Uyumluluk yüzdesinin %100'ü geçmemesini sağla
    return min(compatibility_percentage, 100)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)

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
        
        # Uyum yüzdesini hesapla (her iki kullanıcının da toplam film sayısına göre)
        compatibility_percentage = calculate_compatibility(len(user1_movies), len(user2_movies), len(common_movies))

        return render_template("result.html", username1=username1, username2=username2, 
                               common_movies=common_movies, compatibility_percentage=compatibility_percentage)
    return render_template("index.html")

def get_watched_movies(username):
    watched_movies = []

    def get_movies(source):
        movies = source.find_all("li", class_="poster-container")
        for movie in movies:
            movie_title = movie.find("img")["alt"]  # Film ismini al
            watched_movies.append({"title": movie_title})  # Sadece film ismini ekle

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

def calculate_compatibility(user1_movie_count, user2_movie_count, common_movie_count):
    # İki kullanıcının toplam izlediği film sayısına göre uyum oranı hesapla
    total_movies = user1_movie_count + user2_movie_count
    
    # Eğer iki kullanıcıdan biri hiç film izlememişse uyum oranı 0 olmalı
    if total_movies == 0:
        return 0
    
    # Eğer hiç ortak film yoksa uyum oranı %0 olmalı
    if common_movie_count == 0:
        return 0

    # Eğer ortak film sayısı 5'in üzerindeyse hesaplamaya %50 ekleyerek başla
    if common_movie_count > 5:
        compatibility_percentage = 50 + ((2 * common_movie_count / total_movies) * 100)
    else:
        # Ortak film sayısı 5'in altındaysa direkt uyumluluk hesapla
        compatibility_percentage = (2 * common_movie_count / total_movies) * 100
    
    return compatibility_percentage

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)

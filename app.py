from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import os

app = Flask(__name__)

TMDB_API_KEY = "f3abc39a6d4fbdcc0b2a79906b528658"  

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username1 = request.form["username1"]
        username2 = request.form["username2"]
        user1_movies = get_watched_movies(username1)
        user2_movies = get_watched_movies(username2)
        
        # Ortak filmleri belirle
        common_movies = list(set(user1_movies) & set(user2_movies))
        
        # İstenilen mantıkla uyumluluk yüzdesini hesapla
        compatibility_percentage = calculate_compatibility(user1_movies, user2_movies, common_movies)

        # Film tavsiyelerini al
        movie_recommendations = get_recommendations(common_movies)

        return render_template(
            "result.html",
            username1=username1,
            username2=username2,
            common_movies=common_movies,
            compatibility_percentage=compatibility_percentage,
            recommendations=movie_recommendations
        )
    return render_template("index.html")

def get_watched_movies(username):
    watched_movies = []

    def get_movies(source):
        movies = source.find_all("li", class_="poster-container")
        for movie in movies:
            movie_title = movie.find("img")["alt"].title()  # title() metodunu çağır
            watched_movies.append(movie_title)  # Sadece film ismini ekle

    def connect_page():
        page_num = 1
        while True:
            url = f"https://letterboxd.com/{username}/films/page/{page_num}/"
            response = requests.get(url)
            source = BeautifulSoup(response.content, "lxml")
            if source.find("a", class_="next"):  # Sonraki sayfa linkini kontrol et
                get_movies(source)
                page_num += 1
            else:
                get_movies(source)
                break

    connect_page()
    return watched_movies

def calculate_compatibility(user1_movies, user2_movies, common_movies):
    # İki kullanıcının toplam izlediği film sayısını hesapla
    total_movies = len(user1_movies) + len(user2_movies)
    
    # Eğer iki kullanıcıdan biri hiç film izlememişse uyum oranı 0 olmalı
    if total_movies == 0:
        return 0
    
    # Eğer hiç ortak film yoksa uyum oranı %0 olmalı
    if not common_movies:
        return 0

    common_movie_count = len(common_movies)

    # Eski mantıkla uyum yüzdesini hesapla
    if common_movie_count > 5:
        compatibility_percentage = 50 + ((2 * common_movie_count / total_movies) * 100)
    else:
        # Ortak film sayısı 5'in altındaysa direkt uyumluluk hesapla
        compatibility_percentage = (2 * common_movie_count / total_movies) * 100
    
    # Uyumluluk yüzdesinin %100'ü geçmemesini sağla
    return min(compatibility_percentage, 100)

def get_recommendations(common_movies):
    recommendations = []
    for movie in common_movies:
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie}"
        search_response = requests.get(search_url).json()
        
        if search_response.get("results"):
            movie_id = search_response["results"][0]["id"]
            recommendations_url = f"https://api.themoviedb.org/3/movie/{movie_id}/recommendations?api_key={TMDB_API_KEY}"
            rec_response = requests.get(recommendations_url).json()
            
            if rec_response.get("results"):
                for rec_movie in rec_response["results"]:
                    recommendations.append(rec_movie["title"])

    return list(set(recommendations))  # Benzersiz öneriler

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)

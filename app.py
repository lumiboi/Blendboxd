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
            movie_title = movie.find("img")["alt"]  # Film ismini al
            # IMDb'den poster alma
            movie_cover = get_movie_poster_from_imdb(movie_title)
            watched_movies.append({"title": movie_title, "cover": movie_cover})  # Film ismini ve kapak fotoğrafını ekle

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

def get_movie_poster_from_imdb(movie_title):
    search_url = f"https://www.imdb.com/find?q={movie_title.replace(' ', '+')}&s=tt"
    search_response = requests.get(search_url)
    search_soup = BeautifulSoup(search_response.content, "lxml")
    
    # İlk sonuçtaki film sayfasına git
    try:
        movie_link = search_soup.find("table", class_="findList").find("a")["href"]
        movie_page_url = f"https://www.imdb.com{movie_link}"
        movie_page_response = requests.get(movie_page_url)
        movie_page_soup = BeautifulSoup(movie_page_response.content, "lxml")
        
        # Poster URL'sini bul
        poster_url = movie_page_soup.find("div", class_="poster").find("img")["src"]
        return poster_url
    except (AttributeError, TypeError):
        return ""  # Eğer film bulunamazsa boş döndür

def calculate_compatibility(user1_movie_count, user2_movie_count, common_movie_count):
    total_movies = user1_movie_count + user2_movie_count
    
    if total_movies == 0:
        return 0
    
    if common_movie_count == 0:
        return 0

    if common_movie_count > 5:
        compatibility_percentage = 50 + ((2 * common_movie_count / total_movies) * 100)
    else:
        compatibility_percentage = (2 * common_movie_count / total_movies) * 100
    
    return compatibility_percentage

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)

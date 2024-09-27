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
        common_movies = set(user1_movies) & set(user2_movies)
        
        # Uyum yüzdesini hesapla
        total_movies = len(user1_movies) + len(user2_movies)
        common_count = len(common_movies)

        if common_count >= 20:
            compatibility_percentage = 70
        elif common_count >= 10:
            compatibility_percentage = 50
        else:
            compatibility_percentage = (common_count / (total_movies / 2)) * 100 if total_movies > 0 else 0
        
        return render_template("result.html", username1=username1, username2=username2, 
                               common_movies=common_movies, compatibility_percentage=compatibility_percentage)
    return render_template("index.html")

def get_watched_movies(username):
    watched_movies = []

    def get_movies(source):
        movies = source.find_all("li", class_="poster-container")
        for movie in movies:
            movie_link = movie.find("div")["data-target-link"]
            movie_title = movie.find("img")["alt"]  # Film ismini al
            watched_movies.append(movie_title)  # Sadece film ismini ekle

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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)

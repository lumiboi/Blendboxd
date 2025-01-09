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
        
        # Determine common movies
        common_movies = [movie for movie in user1_movies if movie in user2_movies]
        
        # Calculate compatibility percentage in a symmetric way
        compatibility_percentage = calculate_compatibility(user1_movies, user2_movies, common_movies)

        return render_template("result.html", username1=username1, username2=username2, 
                               common_movies=common_movies, compatibility_percentage=compatibility_percentage)
    return render_template("index.html")

def get_watched_movies(username):
    watched_movies = []

    def get_movies(source):
        movies = source.find_all("li", class_="poster-container")
        for movie in movies:
            movie_title = movie.find("img")["alt"]  # Get movie title
            watched_movies.append({"title": movie_title})  # Add only the movie title

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
    return [movie["title"] for movie in watched_movies]  # Return just the titles

def calculate_compatibility(user1_movies, user2_movies, common_movies):
    # Calculate total unique movies watched by both users
    total_unique_movies = len(set(user1_movies + user2_movies))
    
    # If no unique movies were watched, return 0
    if total_unique_movies == 0:
        return 0
    
    # If no common movies, compatibility is 0
    if not common_movies:
        return 0

    # Calculate compatibility based on the proportion of common movies to total unique movies
    compatibility_percentage = (len(common_movies) / total_unique_movies) * 100

    # Ensure compatibility percentage doesn't exceed 100%
    return min(compatibility_percentage, 100)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)

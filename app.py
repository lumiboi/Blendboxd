from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import os
import random

app = Flask(__name__)

TMDB_API_KEY = "f3abc39a6d4fbdcc0b2a79906b528658"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
    "Referer": "https://letterboxd.com/",
    "Cache-Control": "no-cache",
}

# ------------------ FILM LISTESI (RSS) ------------------

def get_films_from_rss(username: str, section: str) -> list:
    """Letterboxd RSS üzerinden film listesi alır (films, watchlist)."""
    try:
        url = f"https://letterboxd.com/{username}/{section}/rss/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, "xml")
        titles = []
        for item in soup.find_all("item"):
            title = item.find("title").get_text(strip=True)
            if title:
                name = title.split("(")[0].strip()
                titles.append(name.title())
        return list(dict.fromkeys(titles))
    except Exception:
        return []

def get_watched_movies(username):
    return get_films_from_rss(username, "films")

def get_watchlist(username):
    return get_films_from_rss(username, "watchlist")

# ------------------ UYUM HESABI ------------------

def calculate_compatibility(user1_movies, user2_movies, common_movies):
    total_movies = len(user1_movies) + len(user2_movies)
    if total_movies == 0 or not common_movies:
        return 0
    common_movie_count = len(common_movies)
    if common_movie_count > 5:
        compatibility_percentage = 50 + ((2 * common_movie_count / total_movies) * 100)
    else:
        compatibility_percentage = (2 * common_movie_count / total_movies) * 100
    return min(compatibility_percentage, 100)

# ------------------ REKOMENDASYON ------------------

def get_recommendations(common_movies):
    recommendations = []
    for movie in common_movies:
        try:
            search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={requests.utils.quote(movie)}"
            search_response = requests.get(search_url, timeout=20).json()
            if search_response.get("results"):
                movie_id = search_response["results"][0]["id"]
                rec_url = f"https://api.themoviedb.org/3/movie/{movie_id}/recommendations?api_key={TMDB_API_KEY}"
                rec_resp = requests.get(rec_url, timeout=20).json()
                if rec_resp.get("results"):
                    for rec_movie in rec_resp["results"]:
                        recommendations.append(rec_movie["title"])
        except:
            pass
    return list(set(recommendations))

# ------------------ TMDB FILM INFO ------------------

def get_movie_info(title):
    try:
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={requests.utils.quote(title)}"
        resp = requests.get(search_url, timeout=20).json()
        if resp.get("results"):
            movie = resp["results"][0]
            return {
                "title": movie.get("title", "Unknown"),
                "poster": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get("poster_path") else None,
            }
    except:
        pass
    return None

# ------------------ ROUTES ------------------

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username1 = request.form.get("username1", "").strip().lower()
        username2 = request.form.get("username2", "").strip().lower()
        user1_movies = get_watched_movies(username1)
        user2_movies = get_watched_movies(username2)

        common_movies = list(set(user1_movies) & set(user2_movies))
        compatibility_percentage = calculate_compatibility(user1_movies, user2_movies, common_movies)
        movie_recommendations = get_recommendations(common_movies) if common_movies else []

        return render_template(
            "result.html",
            username1=username1,
            username2=username2,
            common_movies=common_movies,
            compatibility_percentage=int(compatibility_percentage),
            recommendations=movie_recommendations,
        )
    return render_template("index.html")

@app.route("/picker", methods=["GET"])
def picker():
    return render_template("picker.html")

@app.route("/pick_movies", methods=["POST"])
def pick_movies():
    username = request.form.get("username", "").strip().lower()
    count = int(request.form.get("count", 1))
    watchlist = get_watchlist(username)
    selected_movies = random.sample(watchlist, min(count, len(watchlist))) if watchlist else []
    movies_info = []
    for movie in selected_movies:
        movie_info = get_movie_info(movie)
        if movie_info:
            movies_info.append(movie_info)
    return jsonify(movies_info)

@app.route("/duo_picker", methods=["GET", "POST"])
def duo_picker():
    lang = request.args.get("lang", "tr")
    if request.method == "POST":
        try:
            user_count = int(request.form.get("user_count", 1))
            film_count = int(request.form.get("film_count", 1))
            usernames = [request.form.get(f"username{i+1}", "").strip().lower() for i in range(user_count)]
            all_movies = []
            for username in usernames:
                watchlist = get_watchlist(username)
                selected_movies = random.sample(watchlist, min(film_count, len(watchlist))) if watchlist else []
                for movie in selected_movies:
                    movie_info = get_movie_info(movie)
                    if movie_info:
                        all_movies.append(movie_info)
            return render_template("duo_picker_result.html", movies=all_movies, usernames=usernames, lang=lang)
        except Exception as e:
            return render_template("duo_picker_result.html", error=str(e), lang=lang)
    return render_template("duo_picker.html", lang=lang)

# ------------------ MAIN ------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

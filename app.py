from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import os
import random

app = Flask(__name__)

TMDB_API_KEY = "f3abc39a6d4fbdcc0b2a79906b528658"
HEADERS = {"User-Agent": "Mozilla/5.0"}

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username1 = request.form["username1"]
        username2 = request.form["username2"]
        user1_movies = get_watched_movies(username1)
        user2_movies = get_watched_movies(username2)

        common_movies = list(set(user1_movies) & set(user2_movies))
        compatibility_percentage = calculate_compatibility(user1_movies, user2_movies, common_movies)
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

def get_follow_data(username):
    following, followers = set(), set()

    def get_users(page_name):
        page_num = 1
        while True:
            url = f"https://letterboxd.com/{username}/{page_name}/page/{page_num}/"
            resp = requests.get(url, headers=HEADERS)
            soup = BeautifulSoup(resp.content, "lxml")
            persons = soup.select("div.person-summary h3 a")
            if not persons:
                break
            for person in persons:
                username_clean = person.text.strip()
                if username_clean:
                    if page_name == "following":
                        following.add(username_clean)
                    else:
                        followers.add(username_clean)
            next_button = soup.find("a", class_="next")
            if next_button:
                page_num += 1
            else:
                break

    get_users("following")
    get_users("followers")

    return list(following), list(followers)

@app.route("/follow", methods=["GET", "POST"])
def follow_index():
    if request.method == "POST":
        username = request.form["username"].lower()
        following, followers = get_follow_data(username)
        difference_list = sorted(set(following) - set(followers))
        return render_template("follow-result.html", username=username, difference_list=difference_list)
    return render_template("followerboxd.html")

def get_watched_movies(username):
    watched_movies = []

    def get_movies(soup):
        for li in soup.select("ul.poster-list li"):
            img = li.find("img")
            if img and img.has_attr("alt"):
                watched_movies.append(img["alt"].strip().title())

    page = 1
    while True:
        url = f"https://letterboxd.com/{username}/films/page/{page}/"
        response = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(response.content, "lxml")
        get_movies(soup)
        if soup.find("a", class_="next"):
            page += 1
        else:
            break

    return watched_movies

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
    return list(set(recommendations))

@app.route('/picker', methods=['GET'])
def picker():
    return render_template("picker.html")

@app.route('/pick_movies', methods=['POST'])
def pick_movies():
    username = request.form.get('username')
    count = int(request.form.get('count', 1))
    watchlist = get_watchlist(username)
    selected_movies = random.sample(watchlist, min(count, len(watchlist)))
    movies_info = []
    for movie in selected_movies:
        movie_info = get_movie_info(movie)
        if movie_info:
            movies_info.append(movie_info)
    return jsonify(movies_info)

def get_watchlist(username):
    watchlist = []
    url = f"https://letterboxd.com/{username}/watchlist/"
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.content, "lxml")
    for li in soup.select("ul.poster-list li"):
        img = li.find("img")
        if img and img.has_attr("alt"):
            watchlist.append(img["alt"].strip().title())
    return watchlist

def get_movie_info(title):
    search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
    response = requests.get(search_url).json()
    if response.get("results"):
        movie_data = response["results"][0]
        return {
            "title": movie_data.get("title", "Unknown Title"),
            "poster": f"https://image.tmdb.org/t/p/w500{movie_data.get('poster_path', '')}"
        }
    return None

@app.route('/duo_picker', methods=['GET', 'POST'])
def duo_picker():
    lang = request.args.get('lang', 'tr')
    if request.method == 'POST':
        try:
            user_count = int(request.form.get('user_count', 1))
            film_count = int(request.form.get('film_count', 1))
            usernames = [request.form.get(f'username{i+1}') for i in range(user_count)]
            all_movies = []
            for username in usernames:
                watchlist = get_watchlist(username)
                selected_movies = random.sample(watchlist, min(film_count, len(watchlist)))
                for movie in selected_movies:
                    movie_info = get_movie_info(movie)
                    if movie_info:
                        all_movies.append(movie_info)
            return render_template("duo_picker_result.html", movies=all_movies, usernames=usernames, lang=lang)
        except Exception as e:
            return render_template("duo_picker_result.html", error=str(e), lang=lang)
    return render_template('duo_picker.html', lang=lang)

# --- FILM TADIM ARKADAŞI ---
@app.route("/match", methods=["GET"])
def match():
    return render_template("match.html")

@app.route("/matched", methods=["POST"])
def matched():
    username = request.form.get("username").strip()
    user_movies = get_watched_movies(username)

    # Letterboxd'dan rastgele veya sistemdeki kullanıcıları çekmek yerine
    # Örneğin, username'nin followers ve following listesinden potansiyel buddy'ler
    following, followers = get_follow_data(username)
    potential_users = list(set(following + followers))

    best_match = None
    best_score = 0
    common_movies_for_best = []

    for other in potential_users:
        try:
            other_movies = get_watched_movies(other)
            common = list(set(user_movies) & set(other_movies))
            score = calculate_compatibility(user_movies, other_movies, common)
            if score > best_score:
                best_score = score
                best_match = other
                common_movies_for_best = common
        except:
            continue  # bazı kullanıcılar gizli olabilir veya veri çekilemeyebilir

    buddy_recommendations = get_recommendations(common_movies_for_best) if common_movies_for_best else []

    return render_template(
        "matched.html",
        buddy_username=best_match or "Bulunamadı",
        compatibility_percentage=int(best_score),
        common_movies=common_movies_for_best,
        buddy_recommendations=buddy_recommendations
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)

from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import os
import random
import uuid


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

@app.route("/follow", methods=["GET", "POST"])
def follow_index():
    if request.method == "POST":
        username = request.form["username"].lower()
        following, followers = get_follow_data(username)
        difference_list = set(following) - set(followers)
        return render_template("follow-result.html", username=username, difference_list=difference_list)
    return render_template("followerboxd.html")

def get_follow_data(username):
    following = []
    followers = []

    def get_users(source, page_name):
        persons = source.find_all("div", attrs={"class": "person-summary"})
        for i in persons:
            if page_name == "following":
                following.append(i.find("h3").find("a")["href"])
            else:
                followers.append(i.find("h3").find("a")["href"])

    def connect_page(page_name):
        page_num = 1
        while True:
            url = f"https://letterboxd.com/{username}/{page_name}/page/{page_num}/"
            source = BeautifulSoup(requests.get(url).content, "lxml")
            if f'<a class="next" href="/{username}/{page_name}/' in str(source):
                get_users(source, page_name)
                page_num += 1
            else:
                get_users(source, page_name)
                break

    for page_name in ("following", "followers"):
        connect_page(page_name)

    return following, followers

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
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "lxml")
    movies = soup.find_all("li", class_="poster-container")
    for movie in movies:
        title = movie.find("img")["alt"].title()
        watchlist.append(title)
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
    lang = request.args.get('lang', 'tr')  # Varsayılan dil Türkçe
    if request.method == 'POST':
        try:
            user_count = int(request.form.get('user_count', 1))  # Kullanıcı sayısını al
            film_count = int(request.form.get('film_count', 1))  # Film sayısını al
            usernames = [request.form.get(f'username{i+1}') for i in range(user_count)]
            
            all_movies = []

            for username in usernames:
                watchlist = get_watchlist(username)
                selected_movies = random.sample(watchlist, min(film_count, len(watchlist)))  # Film sayısını doğru al
                for movie in selected_movies:
                    movie_info = get_movie_info(movie)
                    if movie_info:
                        all_movies.append(movie_info)

            return render_template("duo_picker_result.html", movies=all_movies, usernames=usernames, lang=lang)

        except Exception as e:
            return render_template("duo_picker_result.html", error=str(e), lang=lang)

    return render_template('duo_picker.html', lang=lang)

challenges = {}

@app.route('/create_challenge', methods=['GET', 'POST'])
def create_challenge():
    if request.method == 'POST':
        movie1 = request.form['movie1']
        movie2 = request.form['movie2']
        
        if not movie1 or not movie2:
            movie1, movie2 = get_random_movies()
        
        challenge_id = str(uuid.uuid4())
        challenges[challenge_id] = {"movie1": movie1, "movie2": movie2, "votes": {movie1: 0, movie2: 0}}
        
        return redirect(url_for("challenge", challenge_id=challenge_id))
    return render_template('create_challenge.html')  # GET isteği için



@app.route("/challenge/<challenge_id>", methods=["GET"])
def challenge(challenge_id):
    challenge_data = challenges.get(challenge_id)
    if not challenge_data:
        return "Meydan okuma bulunamadı!", 404
    
    return render_template("challenge.html", movie1=challenge_data["movie1"], movie2=challenge_data["movie2"], challenge_id=challenge_id)

@app.route("/vote/<challenge_id>", methods=["POST"])
def vote(challenge_id):
    challenge_data = challenges.get(challenge_id)
    if not challenge_data:
        return jsonify({"error": "Meydan okuma bulunamadı!"}), 404

    movie = request.json.get("movie")
    if movie not in [challenge_data["movie1"], challenge_data["movie2"]]:
        return jsonify({"error": "Geçersiz oy"}), 400
    
    challenge_data["votes"][movie] += 1
    return jsonify({"message": "Oyunuz kaydedildi!"})

@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    all_votes = {}
    for challenge in challenges.values():
        for movie, count in challenge["votes"].items():
            all_votes[movie] = all_votes.get(movie, 0) + count
    
    sorted_votes = sorted(all_votes.items(), key=lambda x: x[1], reverse=True)
    return jsonify(sorted_votes)



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)

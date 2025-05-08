from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import os
import random

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
            movie_title = movie.find("img")["alt"].title()
            watched_movies.append(movie_title)

    def connect_page():
        page_num = 1
        while True:
            url = f"https://letterboxd.com/{username}/films/page/{page_num}/"
            response = requests.get(url)
            source = BeautifulSoup(response.content, "lxml")
            if source.find("a", class_="next"):
                get_movies(source)
                page_num += 1
            else:
                get_movies(source)
                break

    connect_page()
    return watched_movies

def calculate_compatibility(user1_movies, user2_movies, common_movies):
    total_movies = len(user1_movies) + len(user2_movies)
    if total_movies == 0:
        return 0
    if not common_movies:
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
def to_picker():
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

# --- Yeni Eklenen Imaro Generator Kodu ---
from deepface import DeepFace
from PIL import Image
import cv2
import io
import base64

# Sabit fotoğraf URL'si
FIXED_IMAGE_URL = "https://i.hizliresim.com/p5s5as7.png"

# Görüntüyü dosyaya kaydetme
def save_image(data, path):
    try:
        img = Image.open(data)
        img.save(path)
    except Exception as e:
        raise Exception(f"Görüntü kaydedilemedi: {str(e)}")

# Görüntüyü base64'e çevirme
def image_to_base64(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    except Exception as e:
        raise Exception(f"Base64 dönüşümü başarısız: {str(e)}")

# Imaro Generator rotası
@app.route('/imaro-generator', methods=['GET', 'POST'])
def imaro_generator():
    if request.method == 'POST':
        # Kullanıcıdan yüklenen fotoğraf
        if 'profile_pic' not in request.files:
            return render_template('imaro-generator.html', error="Profil fotoğrafı yüklenmedi")
        
        profile_pic = request.files['profile_pic']
        if profile_pic.filename == '':
            return render_template('imaro-generator.html', error="Geçerli bir fotoğraf seçin")

        # Geçici dosyalar için yollar
        profile_pic_path = "temp_profile.png"
        fixed_image_path = "fixed_image.png"
        result_path = "result.png"

        try:
            # Profil fotoğrafını kaydet
            save_image(profile_pic, profile_pic_path)
            # Sabit fotoğrafı indir ve kaydet
            save_image(requests.get(FIXED_IMAGE_URL, stream=True).raw, fixed_image_path)

            # DeepFace ile yüz analizi
            try:
                DeepFace.verify(
                    img1_path=fixed_image_path,
                    img2_path=profile_pic_path,
                    model_name="Facenet",
                    enforce_detection=False
                )
            except Exception as deepface_error:
                print(f"DeepFace hatası, devam ediliyor: {str(deepface_error)}")

            # Görüntüleri harmanla
            img1 = cv2.imread(fixed_image_path)
            img2 = cv2.imread(profile_pic_path)
            if img1 is None or img2 is None:
                raise Exception("Görüntüler okunamadı")
            if img1.shape != img2.shape:
                img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
            blended = cv2.addWeighted(img1, 0.5, img2, 0.5, 0.0)
            cv2.imwrite(result_path, blended)

            # Sonucu base64'e çevir
            result_base64 = image_to_base64(result_path)

            # Geçici dosyaları sil
            for path in [profile_pic_path, fixed_image_path, result_path]:
                if os.path.exists(path):
                    os.remove(path)

            return render_template('imaro-generator.html', image=f"data:image/png;base64,{result_base64}")

        except Exception as e:
            # Hata durumunda dosyaları sil
            for path in [profile_pic_path, fixed_image_path, result_path]:
                if os.path.exists(path):
                    os.remove(path)
            return render_template('imaro-generator.html', error=f"Hata oluştu: {str(e)}")

    return render_template('imaro-generator.html')

# --- Mevcut Kodun Sonu ---
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)

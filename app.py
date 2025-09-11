import os
import random
import requests
from flask import Flask, render_template, request, jsonify
from bs4 import BeautifulSoup
import cloudscraper

app = Flask(__name__)

# --- CONFIGURATION ---
TMDB_API_KEY = "f3abc39a6d4fbdcc0b2a79906b528658"

# Cloudflare korumasını atlatmak için cloudscraper nesnesi oluşturuyoruz.
# Letterboxd'a yapılacak tüm istekler bu nesne üzerinden yapılacak.
scraper = cloudscraper.create_scraper()

# Global Headers (scraper tarafından otomatik yönetilse de, belirtmekte fayda var)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
    "Referer": "https://letterboxd.com/",
}

# --- UTILITY FUNCTIONS ---

def extract_film_title_from_li(li):
    """Extract best-guess film title from a Letterboxd poster <li>."""
    for attr in ("data-film-name", "data-film-title"):
        if li.has_attr(attr) and li.get(attr):
            return li.get(attr)
    if li.has_attr("data-film-slug") and li.get("data-film-slug"):
        return li.get("data-film-slug").replace('-', ' ')
    poster_div = li.find(class_="film-poster") or li.find("div", attrs={"data-film-name": True})
    if poster_div:
        for attr in ("data-film-name", "data-film-title"):
            if poster_div.has_attr(attr) and poster_div.get(attr):
                return poster_div.get(attr)
        if poster_div.has_attr("data-film-slug") and poster_div.get("data-film-slug"):
            return poster_div.get("data-film-slug").replace('-', ' ')
    img = li.find("img")
    if img and img.has_attr("alt") and img.get("alt"):
        return img.get("alt")
    a = li.find("a")
    if a:
        href = a.get("href", "")
        if "/film/" in href:
            try:
                slug = href.split("/film/")[1].split("/")[0]
                if slug:
                    return slug.replace('-', ' ')
            except Exception:
                pass
    return None

def extract_film_slug_from_li(li):
    """Extract film slug from a Letterboxd poster <li>."""
    a = li.find("a", href=True)
    if a and "/film/" in a.get("href", ""):
        try:
            return a.get("href").split("/film/")[1].split("/")[0]
        except Exception:
            pass
    poster_div = li.find(class_="film-poster")
    if poster_div and poster_div.get("data-film-slug"):
        return poster_div.get("data-film-slug").strip("/")
    return None

def get_films_from_rss(username: str, section: str) -> list:
    """Fallback: fetch films from Letterboxd RSS (recent items only)."""
    try:
        url = f"https://letterboxd.com/{username}/{section}/rss/"
        resp = scraper.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.content, "xml")
        titles = [item.find('title').get_text(strip=True).split('(')[0].strip().title() for item in soup.find_all('item') if item.find('title')]
        return list(dict.fromkeys(titles)) # Remove duplicates while preserving order
    except Exception:
        return []

def get_watched_movies(username):
    """Gets all watched movies for a user by scraping their films pages."""
    watched_movies = []
    page = 1
    while True:
        url = f"https://letterboxd.com/{username}/films/page/{page}/"
        try:
            response = scraper.get(url, headers=HEADERS, timeout=20)
            if response.status_code != 200:
                print(f"'{username}' için sayfa {page} yüklenemedi. Status: {response.status_code}")
                break # Sayfa bulunamazsa veya hata verirse döngüyü kır.
        except Exception as e:
            print(f"Hata: {e}")
            break

        soup = BeautifulSoup(response.content, "lxml")
        li_nodes = soup.select("li.poster-container, ul.poster-list li")
        
        movies_on_page = []
        for li in li_nodes:
            film_name = extract_film_title_from_li(li)
            if film_name:
                movies_on_page.append(film_name.strip().title())

        if not movies_on_page:
            # Eğer ilk sayfada hiç film bulunamazsa, RSS'i deneyip bitirelim.
            if page == 1:
                print(f"'{username}' için HTML'den film bulunamadı, RSS deneniyor.")
                return get_films_from_rss(username, 'films')
            break # Sonraki sayfalarda film yoksa döngüyü kır.

        watched_movies.extend(movies_on_page)
        
        # "Next" butonu varsa devam et
        if not soup.find("a", class_="next"):
            break
        page += 1
        
    return list(dict.fromkeys(watched_movies))

def get_watchlist(username):
    """Gets the watchlist for a user."""
    watchlist = []
    page = 1
    while True:
        url = f"https://letterboxd.com/{username}/watchlist/page/{page}/"
        try:
            response = scraper.get(url, headers=HEADERS, timeout=20)
            if response.status_code != 200:
                break
        except Exception as e:
            print(f"Hata: {e}")
            break
            
        soup = BeautifulSoup(response.content, "lxml")
        li_nodes = soup.select("li.poster-container, ul.poster-list li")

        movies_on_page = [extract_film_title_from_li(li).strip().title() for li in li_nodes if extract_film_title_from_li(li)]
        
        if not movies_on_page:
            if page == 1:
                return get_films_from_rss(username, 'watchlist')
            break
            
        watchlist.extend(movies_on_page)
        if not soup.find("a", class_="next"):
            break
        page += 1
        
    return list(dict.fromkeys(watchlist))

def get_follow_data(username):
    """Gets following and followers for a user."""
    users = set()
    display_name_map = {}

    for page_name in ["following", "followers"]:
        page_num = 1
        while True:
            url = f"https://letterboxd.com/{username}/{page_name}/page/{page_num}/"
            try:
                resp = scraper.get(url, headers=HEADERS, timeout=15)
                if resp.status_code != 200: break
            except Exception:
                break

            soup = BeautifulSoup(resp.content, "lxml")
            persons = soup.select("div.person-summary h3 a")
            if not persons: break

            for person in persons:
                slug = person.get("href", "/").strip().split('/')[1]
                display_name = person.text.strip()
                if slug:
                    users.add((slug, page_name))
                    display_name_map[slug] = display_name or slug
            
            if not soup.find("a", class_="next"): break
            page_num += 1

    following = [u for u, t in users if t == "following"]
    followers = [u for u, t in users if t == "followers"]
    return following, followers, display_name_map

def calculate_compatibility(user1_movies, user2_movies, common_movies):
    total_movies = len(user1_movies) + len(user2_movies)
    if total_movies == 0 or not common_movies:
        return 0
    common_movie_count = len(common_movies)
    compatibility_percentage = (2 * common_movie_count / total_movies) * 100
    # Skalayı biraz daha anlamlı hale getirmek için basit bir ayarlama
    return min(int(compatibility_percentage * 2.5), 100)

def get_recommendations(common_movies):
    """Gets movie recommendations from TMDB based on common movies."""
    recommendations = set()
    # Çok fazla istek yapmamak için ortak filmlerin bir kısmını alalım
    for movie in random.sample(common_movies, min(len(common_movies), 10)):
        try:
            search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie}"
            search_response = requests.get(search_url, timeout=10).json()
            if search_response.get("results"):
                movie_id = search_response["results"][0]["id"]
                recommendations_url = f"https://api.themoviedb.org/3/movie/{movie_id}/recommendations?api_key={TMDB_API_KEY}"
                rec_response = requests.get(recommendations_url, timeout=10).json()
                if rec_response.get("results"):
                    for rec_movie in rec_response["results"]:
                        recommendations.add(rec_movie["title"])
        except requests.RequestException:
            continue # Bir filmde hata olursa atla ve devam et
    return list(recommendations)

def get_movie_info(title):
    """Gets poster and title from TMDB."""
    try:
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={requests.utils.quote(title)}"
        response = requests.get(search_url, timeout=10).json()
        if response.get("results"):
            movie_data = response["results"][0]
            return {
                "title": movie_data.get("title", "Unknown Title"),
                "poster": f"https://image.tmdb.org/t/p/w500{movie_data.get('poster_path', '')}" if movie_data.get('poster_path') else None
            }
    except requests.RequestException:
        return None
    return None

# --- FLASK ROUTES ---

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username1 = request.form["username1"].strip().lower()
        username2 = request.form["username2"].strip().lower()
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

@app.route("/follow", methods=["GET", "POST"])
def follow_index():
    if request.method == "POST":
        username = request.form["username"].lower()
        following, followers, name_map = get_follow_data(username)
        difference_usernames = sorted(list(set(following) - set(followers)))
        difference_list = [{"username": u, "display_name": name_map.get(u, u)} for u in difference_usernames]
        return render_template("follow-result.html", username=username, difference_list=difference_list)
    return render_template("followerboxd.html")

@app.route('/picker')
def picker():
    return render_template("picker.html")

@app.route('/pick_movies', methods=['POST'])
def pick_movies():
    username = request.form.get('username')
    count = int(request.form.get('count', 1))
    watchlist = get_watchlist(username)
    if not watchlist:
        return jsonify({"error": f"'{username}' için izleme listesi bulunamadı veya profil gizli."}), 404
    
    selected_movies = random.sample(watchlist, min(count, len(watchlist)))
    movies_info = [info for movie in selected_movies if (info := get_movie_info(movie))]
    return jsonify(movies_info)

@app.route('/duo_picker', methods=['GET', 'POST'])
def duo_picker():
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
            return render_template("duo_picker_result.html", movies=all_movies, usernames=usernames)
        except Exception as e:
            return render_template("duo_picker_result.html", error=str(e))
    return render_template('duo_picker.html')
    
@app.route("/match")
def match():
    return render_template("match.html")

@app.route("/matched", methods=["POST"])
def matched():
    username = request.form.get("username").strip()
    user_movies = get_watched_movies(username)
    
    if not user_movies:
         return render_template(
            "matched.html",
            error=f"'{username}' kullanıcısının izlediği filmler bulunamadı. Profil gizli veya kullanıcı adı yanlış olabilir."
        )

    following, followers, _ = get_follow_data(username)
    potential_users = list(set(following + followers))
    
    best_match = None
    best_score = -1
    common_movies_for_best = []

    # Asenkron yapı kaldırıldı, bunun yerine sırayla kontrol ediyoruz.
    # Çok fazla takipçisi olan kullanıcılar için bu işlem biraz yavaş olabilir.
    for other_user in potential_users:
        other_movies = get_watched_movies(other_user)
        if not other_movies:
            continue
        
        common = list(set(user_movies) & set(other_movies))
        score = calculate_compatibility(user_movies, other_movies, common)
        
        if score > best_score:
            best_score = score
            best_match = other_user
            common_movies_for_best = common
            
    buddy_recommendations = get_recommendations(common_movies_for_best)

    return render_template(
        "matched.html",
        buddy_username=best_match or "Uygun biri bulunamadı",
        compatibility_percentage=int(best_score),
        common_movies=common_movies_for_best[:100], # Limiting for display
        buddy_recommendations=buddy_recommendations[:50] # Limiting for display
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)

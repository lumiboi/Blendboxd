from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import os
import random
import aiohttp
import asyncio
import nest_asyncio
nest_asyncio.apply()

app = Flask(__name__)

TMDB_API_KEY = "f3abc39a6d4fbdcc0b2a79906b528658"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
    "Referer": "https://letterboxd.com/",
    "Cache-Control": "no-cache",
}

def extract_film_title_from_li(li):
    """Extract best-guess film title from a Letterboxd poster <li>."""
    # Attributes on the <li>
    for attr in ("data-film-name", "data-film-title"):
        if li.has_attr(attr) and li.get(attr):
            return li.get(attr)
    if li.has_attr("data-film-slug") and li.get("data-film-slug"):
        return li.get("data-film-slug").replace('-', ' ')
    # Common child container
    poster_div = li.find(class_="film-poster") or li.find("div", attrs={"data-film-name": True})
    if poster_div:
        for attr in ("data-film-name", "data-film-title"):
            if poster_div.has_attr(attr) and poster_div.get(attr):
                return poster_div.get(attr)
        if poster_div.has_attr("data-film-slug") and poster_div.get("data-film-slug"):
            return poster_div.get("data-film-slug").replace('-', ' ')
    # Fallbacks
    img = li.find("img")
    if img:
        for alt_attr in ("alt", "data-alt", "data-image-alt"):
            if img.has_attr(alt_attr) and img.get(alt_attr):
                return img.get(alt_attr)
    # Try common anchor attributes
    a = li.find("a")
    if a:
        for text_attr in ("aria-label", "title"):
            if a.has_attr(text_attr) and a.get(text_attr):
                return a.get(text_attr)
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
    a = li.find("a")
    if not a:
        a = li.find("a", href=True)
    if a and a.get("href") and "/film/" in a.get("href"):
        href = a.get("href").split("?")[0]
        try:
            slug = href.split("/film/")[1].split("/")[0]
            return slug
        except Exception:
            return None
    # Try on film-poster div
    poster_div = li.find(class_="film-poster")
    if poster_div and poster_div.get("data-film-slug"):
        return poster_div.get("data-film-slug").strip("/")
    return None

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

def get_follow_data(username):
    following_usernames, followers_usernames = set(), set()
    display_name_by_username = {}

    def get_users(page_name):
        page_num = 1
        while True:
            url = f"https://letterboxd.com/{username}/{page_name}/page/{page_num}/"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.content, "lxml")
            persons = soup.select("div.person-summary h3 a")
            if not persons:
                break
            for person in persons:
                href = person.get("href", "/").strip()
                slug = href.strip("/").split("/")[0]
                display_name = person.text.strip()
                if slug:
                    display_name_by_username[slug] = display_name or slug
                    if page_name == "following":
                        following_usernames.add(slug)
                    else:
                        followers_usernames.add(slug)
            next_button = soup.find("a", class_="next")
            if next_button:
                page_num += 1
            else:
                break

    get_users("following")
    get_users("followers")

    return list(following_usernames), list(followers_usernames), display_name_by_username

@app.route("/follow", methods=["GET", "POST"])
def follow_index():
    if request.method == "POST":
        username = request.form["username"].lower()
        following, followers, name_map = get_follow_data(username)
        difference_usernames = sorted(set(following) - set(followers))
        difference_list = [{"username": u, "display_name": name_map.get(u, u)} for u in difference_usernames]
        return render_template("follow-result.html", username=username, difference_list=difference_list)
    return render_template("followerboxd.html")

def get_watched_movies(username):
    watched_movies = []

    def get_movies(soup):
        # Prefer robust selectors: Letterboxd often stores film names on list items
        # E.g., <li class="poster-container" data-film-name="...">
        li_nodes = soup.select("li.poster-container, ul.poster-list li, section.poster-list li, ol.poster-list li")
        for li in li_nodes:
            film_name = extract_film_title_from_li(li)
            if not film_name:
                slug = extract_film_slug_from_li(li)
                if slug:
                    film_name = slug.replace('-', ' ')
            if film_name:
                watched_movies.append(film_name.strip().title())

    page = 1
    while True:
        url = f"https://letterboxd.com/{username}/films/page/{page}/"
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.content, "lxml")
        get_movies(soup)
        # Some paginations use nav.pagination with rel="next"
        has_next = soup.find("a", class_="next") or soup.select_one('nav.pagination a[rel="next"]')
        if has_next:
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
        search_response = requests.get(search_url, timeout=20).json()
        if search_response.get("results"):
            movie_id = search_response["results"][0]["id"]
            recommendations_url = f"https://api.themoviedb.org/3/movie/{movie_id}/recommendations?api_key={TMDB_API_KEY}"
            rec_response = requests.get(recommendations_url, timeout=20).json()
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
    response = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(response.content, "lxml")
    li_nodes = soup.select("li.poster-container, ul.poster-list li, section.poster-list li, ol.poster-list li")
    for li in li_nodes:
        film_name = extract_film_title_from_li(li)
        if not film_name:
            slug = extract_film_slug_from_li(li)
            if slug:
                film_name = slug.replace('-', ' ')
        if film_name:
            watchlist.append(film_name.strip().title())
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

## duplicate HEADERS removed (consolidated above)

# --- ASYNC GET WATCHED MOVIES ---
async def fetch_page(session, url):
    async with session.get(url, headers=HEADERS) as resp:
        return await resp.text()

async def get_watched_movies_async(username):
    watched_movies = []
    async with aiohttp.ClientSession() as session:
        page = 1
        while True:
            url = f"https://letterboxd.com/{username}/films/page/{page}/"
            html = await fetch_page(session, url)
            soup = BeautifulSoup(html, "lxml")
            movies_on_page = []
            li_nodes = soup.select("li.poster-container, ul.poster-list li, section.poster-list li, ol.poster-list li")
            for li in li_nodes:
                film_name = extract_film_title_from_li(li)
                if not film_name:
                    slug = extract_film_slug_from_li(li)
                    if slug:
                        film_name = slug.replace('-', ' ')
                if film_name:
                    movies_on_page.append(film_name.strip().title())
            if not movies_on_page:
                break
            watched_movies.extend(movies_on_page)
            has_next = soup.find("a", class_="next") or soup.select_one('nav.pagination a[rel="next"]')
            if not has_next:
                break
            page += 1
    return watched_movies


# --- FILM TADIM ARKADAŞI ---  
@app.route("/match", methods=["GET"])
def match():
    # Kullanıcıdan Letterboxd username isteyecek formu gösterir
    return render_template("match.html")

@app.route("/matched", methods=["POST"])
def matched():
    username = request.form.get("username").strip()
    # Kullanıcının izlediği filmler
    user_movies = asyncio.run(get_watched_movies_async(username))

    # Potansiyel buddy kullanıcıları (takipçiler + following)
    following, followers = get_follow_data(username)
    potential_users = list(set(following + followers))

    best_match = None
    best_score = 0
    common_movies_for_best = []

    async def process_other(other):
        try:
            other_movies = await get_watched_movies_async(other)
            common = list(set(user_movies) & set(other_movies))
            score = calculate_compatibility(user_movies, other_movies, common)
            return other, score, common
        except:
            return None

    # Tüm kullanıcıları asenkron olarak işliyoruz
    tasks = [process_other(u) for u in potential_users]
    results = asyncio.run(asyncio.gather(*tasks))

    for result in results:
        if result:
            other, score, common = result
            if score > best_score:
                best_score = score
                best_match = other
                common_movies_for_best = common

    # Ortak filmleri ve önerileri sınırlama
    common_movies_for_best = common_movies_for_best[:100]  # sadece ilk 100 ortak film
    buddy_recommendations = get_recommendations(common_movies_for_best)[:50]  # sadece ilk 50 öneri

    return render_template(
        "matched.html",
        buddy_username=best_match or "Bulunamadı",
        compatibility_percentage=int(best_score),
        common_movies=common_movies_for_best,
        buddy_recommendations=buddy_recommendations
    )



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)

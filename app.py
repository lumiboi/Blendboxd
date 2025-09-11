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
    # Yeni attribute’ları da dene
    for attr in ("data-film-name", "data-film-title", "data-original-title", "data-name"):
        if li.has_attr(attr) and li.get(attr):
            return li.get(attr)
    if li.has_attr("data-film-slug") and li.get("data-film-slug"):
        return li.get("data-film-slug").replace('-', ' ')
    # Görsel alt metni
    img = li.find("img")
    if img:
        for alt_attr in ("alt", "data-alt", "data-image-alt", "title"):
            if img.has_attr(alt_attr) and img.get(alt_attr):
                return img.get(alt_attr)
    # Anchor içi başlıklar
    a = li.find("a", href=True)
    if a:
        if a.has_attr("title") and a.get("title"):
            return a.get("title")
        href = a.get("href", "")
        if "/film/" in href:
            try:
                slug = href.split("/film/")[1].split("/")[0]
                return slug.replace('-', ' ')
            except Exception:
                pass
    return None

def extract_film_slug_from_li(li):
    a = li.find("a", href=True)
    if a and "/film/" in a.get("href"):
        href = a.get("href").split("?")[0]
        try:
            slug = href.split("/film/")[1].split("/")[0]
            return slug
        except Exception:
            return None
    if li.has_attr("data-film-slug"):
        return li.get("data-film-slug").strip("/")
    return None

def get_movies_from_soup(soup, watched_movies):
    # Yeni selector’ları dene, eski olanları tutarak
    # Örn: li.film-poster-container, li.poster-container, ul.poster-list li vs.
    li_nodes = []
    # Örnek yeni olabilecek class’lar
    li_nodes.extend(soup.select("li.poster-container"))
    li_nodes.extend(soup.select("li.film-poster-container"))
    li_nodes.extend(soup.select("ul.poster-list li"))
    li_nodes.extend(soup.select("div.poster-list__item"))  # başka bir yaygın yapı
    li_nodes.extend(soup.select("ol.poster-list li"))
    li_nodes.extend(soup.select("section.poster-list li"))

    # Dedup etmek için set kullanabiliriz
    seen = set()
    for li in li_nodes:
        title = extract_film_title_from_li(li)
        if not title:
            slug = extract_film_slug_from_li(li)
            if slug:
                title = slug.replace('-', ' ')
        if title:
            normalized = title.strip().title()
            if normalized not in seen:
                seen.add(normalized)
                watched_movies.append(normalized)
    return len(seen)

def get_films_from_rss(username: str, section: str) -> list:
    try:
        url = f"https://letterboxd.com/{username}/{section}/rss/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, "xml")
        titles = []
        for item in soup.find_all('item'):
            title_tag = item.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
                name = title.split('(')[0].strip()
                if name:
                    titles.append(name.title())
        # benzersiz liste
        return list(dict.fromkeys(titles))
    except Exception:
        return []

def get_watched_movies(username):
    watched_movies = []
    page = 1
    while True:
        url = f"https://letterboxd.com/{username}/films/page/{page}/"
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            break
        soup = BeautifulSoup(response.content, "lxml")
        before = len(watched_movies)
        count_new = get_movies_from_soup(soup, watched_movies)
        # debug
        print(f"DEBUG {username} page {page}, new titles found: {count_new}")
        if page == 1 and len(watched_movies) == before:
            rss = get_films_from_rss(username, 'films')
            if rss:
                return rss
        # pagination kontrolü
        has_next = False
        # “next” linkini bul
        if soup.find("a", class_="next") or soup.select_one('nav.pagination a[rel="next"]'):
            has_next = True
        # alternatif yapı
        if soup.select_one("a[rel='next']"):
            has_next = True
        if has_next:
            page += 1
        else:
            break
    return watched_movies

def get_watchlist(username):
    watchlist = []
    try:
        url = f"https://letterboxd.com/{username}/watchlist/"
        response = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(response.content, "lxml")
        count_new = get_movies_from_soup(soup, watchlist)
        print(f"DEBUG watchlist {username}, found: {count_new}")
        if not watchlist:
            rss = get_films_from_rss(username, 'watchlist')
            if rss:
                return rss
    except Exception as e:
        print(f"Error in watchlist fetch: {e}")
    return watchlist

def calculate_compatibility(user1_movies, user2_movies, common_movies):
    total = len(user1_movies) + len(user2_movies)
    if total == 0 or not common_movies:
        return 0
    common_movie_count = len(common_movies)
    if common_movie_count > 5:
        compatibility = 50 + ((2 * common_movie_count / total) * 100)
    else:
        compatibility = (2 * common_movie_count / total) * 100
    return min(compatibility, 100)

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
                    for rec in rec_resp["results"]:
                        recommendations.append(rec.get("title"))
        except Exception as e:
            print(f"Error getting recommendation for {movie}: {e}")
    return list(set([r for r in recommendations if r]))

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username1 = request.form.get("username1", "").strip().lower()
        username2 = request.form.get("username2", "").strip().lower()
        user1_movies = get_watched_movies(username1)
        user2_movies = get_watched_movies(username2)

        common = list(set(user1_movies) & set(user2_movies))
        compatibility_percentage = calculate_compatibility(user1_movies, user2_movies, common)
        recommendations = []
        if common:
            recommendations = get_recommendations(common)

        return render_template(
            "result.html",
            username1=username1,
            username2=username2,
            common_movies=common,
            compatibility_percentage=int(compatibility_percentage),
            recommendations=recommendations
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
    selected = random.sample(watchlist, min(count, len(watchlist))) if watchlist else []
    movies_info = []
    for title in selected:
        info = get_movie_info(title)
        if info:
            movies_info.append(info)
    return jsonify(movies_info)

def get_movie_info(title):
    try:
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={requests.utils.quote(title)}"
        resp = requests.get(search_url, timeout=20).json()
        if resp.get("results"):
            movie = resp["results"][0]
            return {
                "title": movie.get("title", "Unknown"),
                "poster": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else None
            }
    except Exception as e:
        print(f"Error in get_movie_info for {title}: {e}")
    return None

@app.route("/duo_picker", methods=["GET", "POST"])
def duo_picker():
    lang = request.args.get('lang', 'tr')
    if request.method == "POST":
        try:
            user_count = int(request.form.get('user_count', 1))
            film_count = int(request.form.get('film_count', 1))
            usernames = [request.form.get(f'username{i+1}', '').strip().lower() for i in range(user_count)]
            all_movies = []
            for username in usernames:
                wl = get_watchlist(username)
                selected = random.sample(wl, min(film_count, len(wl))) if wl else []
                for title in selected:
                    info = get_movie_info(title)
                    if info:
                        all_movies.append(info)
            return render_template("duo_picker_result.html", movies=all_movies, usernames=usernames, lang=lang)
        except Exception as e:
            return render_template("duo_picker_result.html", error=str(e), lang=lang)
    return render_template("duo_picker.html", lang=lang)

@app.route("/match", methods=["GET"])
def match():
    return render_template("match.html")

@app.route("/matched", methods=["POST"])
def matched():
    username = request.form.get("username", "").strip().lower()
    user_movies = asyncio.run(get_watched_movies(username))
    following, followers, _ = get_follow_data(username)
    potential = list(set(following + followers))
    best_match = None
    best_score = 0
    common_for_best = []

    async def process_other(other):
        other_movies = await get_watched_movies(other)
        common = list(set(user_movies) & set(other_movies))
        score = calculate_compatibility(user_movies, other_movies, common)
        return other, score, common

    tasks = [process_other(u) for u in potential]
    results = asyncio.run(asyncio.gather(*tasks))

    for other, score, common in results:
        if score > best_score:
            best_score = score
            best_match = other
            common_for_best = common

    common_for_best = common_for_best[:100]
    buddy_recommendations = get_recommendations(common_for_best)[:50] if common_for_best else []

    return render_template(
        "matched.html",
        buddy_username=best_match or "Bulunamadı",
        compatibility_percentage=int(best_score),
        common_movies=common_for_best,
        buddy_recommendations=buddy_recommendations
    )

def get_follow_data(username):
    following = set()
    followers = set()
    name_map = {}

    def get_users(page_name):
        page = 1
        while True:
            url = f"https://letterboxd.com/{username}/{page_name}/page/{page}/"
            try:
                resp = requests.get(url, headers=HEADERS, timeout=20)
            except Exception as e:
                print(f"Error fetching follow data {url}: {e}")
                break
            soup = BeautifulSoup(resp.content, "lxml")
            persons = soup.select("div.person-summary h3 a")
            if not persons:
                break
            for person in persons:
                href = person.get("href", "").strip()
                slug = href.strip("/").split("/")[0]
                display = person.text.strip() or slug
                name_map[slug] = display
                if page_name == "following":
                    following.add(slug)
                else:
                    followers.add(slug)
            next_btn = soup.find("a", class_="next")
            if next_btn:
                page += 1
            else:
                break

    get_users("following")
    get_users("followers")
    return list(following), list(followers), name_map

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)

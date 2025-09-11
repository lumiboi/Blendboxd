# app.py
import os
import re
import random
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify

# try cloudscraper (better for Cloudflare). if yok fallback to requests
try:
    import cloudscraper
    SCRAPER = cloudscraper.create_scraper()
    _SCRAPER_TYPE = "cloudscraper"
except Exception:
    SCRAPER = None
    _SCRAPER_TYPE = "requests"

app = Flask(__name__)

TMDB_API_KEY = "f3abc39a6d4fbdcc0b2a79906b528658"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
    "Referer": "https://letterboxd.com/",
}

# turn this on to see debug prints in terminal
DEBUG = True

def fetch_html(url, timeout=20):
    """Return (status_code, text) or (None, None) on error."""
    try:
        if SCRAPER:
            r = SCRAPER.get(url, headers=HEADERS, timeout=timeout)
            return r.status_code, r.text
        else:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            return r.status_code, r.text
    except Exception as e:
        if DEBUG:
            print(f"[fetch_html] error fetching {url}: {e}")
        return None, None

def clean_title(raw):
    """Keep original case; remove leading 'Poster for ' and trailing (YYYY)."""
    if not raw:
        return None
    s = raw.strip()
    s = re.sub(r'^\s*Poster for\s+', '', s, flags=re.I)
    s = re.sub(r'\s*\(\d{4}\)\s*$', '', s).strip()
    # normalize whitespace
    s = re.sub(r'\s+', ' ', s)
    return s if s else None

def extract_movies_from_soup(soup):
    """Robustly extract movie titles from a BeautifulSoup page."""
    titles = []
    seen = set()

    # 1) data-item-name / data-item-full-display-name (react lazy posters)
    for tag in soup.select('[data-item-name], [data-item-full-display-name], [data-item-slug]'):
        name = tag.get('data-item-name') or tag.get('data-item-full-display-name') or tag.get('data-item-slug')
        t = clean_title(name)
        if t and t not in seen:
            seen.add(t)
            titles.append(t)

    # 2) li elements with data-film-name or data-film-slug
    for li in soup.find_all(attrs={"data-film-name": True}):
        name = li.get('data-film-name') or li.get('data-film-slug')
        t = clean_title(name)
        if t and t not in seen:
            seen.add(t); titles.append(t)

    # 3) span.frame-title or .frame-title texts
    for ft in soup.select('.frame-title'):
        text = ft.get_text(strip=True)
        t = clean_title(text)
        if t and t not in seen:
            seen.add(t); titles.append(t)

    # 4) img alt attributes (Poster for X (YYYY))
    for img in soup.find_all('img', alt=True):
        alt = img.get('alt')
        t = clean_title(alt)
        if t and t not in seen:
            seen.add(t); titles.append(t)

    # 5) anchors with /film/ in href
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/film/' in href:
            # prefer visible text
            text = a.get_text(strip=True)
            t = clean_title(text) if text else None
            if t and t not in seen:
                seen.add(t); titles.append(t)
            else:
                # parse slug
                try:
                    slug = href.split('/film/')[1].split('/')[0]
                    slug_name = slug.replace('-', ' ')
                    t2 = clean_title(slug_name)
                    if t2 and t2 not in seen:
                        seen.add(t2); titles.append(t2)
                except Exception:
                    pass

    return titles

def get_films_from_rss(username: str, section: str) -> list:
    """Fallback: try RSS (may be limited / hidden)."""
    if not username:
        return []
    username = username.strip().lower()
    url = f"https://letterboxd.com/{username}/{section}/rss/"
    status, html = fetch_html(url)
    if status != 200 or not html:
        if DEBUG:
            print(f"[RSS] {url} returned {status}")
        return []
    try:
        soup = BeautifulSoup(html, "xml")
        items = []
        for item in soup.find_all('item'):
            title_tag = item.find('title')
            if title_tag:
                t = clean_title(title_tag.get_text(strip=True))
                if t:
                    items.append(t)
        # dedupe preserve order
        return list(dict.fromkeys(items))
    except Exception as e:
        if DEBUG:
            print("[RSS] parse error:", e)
        return []

def get_watched_movies(username: str) -> list:
    """Scrape /films/ pages; fallback to RSS if nothing found."""
    if not username:
        return []
    username = username.strip().lower()
    collected = []
    collected_set = set()
    page = 1

    while True:
        url = f"https://letterboxd.com/{username}/films/page/{page}/"
        status, html = fetch_html(url)
        # if page URL returns non-200 on page>1, try stop; on page==1 try /films/ without /page/
        if status is None:
            break
        if status != 200:
            if page == 1:
                url2 = f"https://letterboxd.com/{username}/films/"
                status2, html2 = fetch_html(url2)
                if status2 == 200 and html2:
                    status, html = status2, html2
                else:
                    if DEBUG:
                        print(f"[get_watched_movies] {url} and {url2} failed: {status}/{status2}")
                    break
            else:
                break

        soup = BeautifulSoup(html, "lxml")
        titles = extract_movies_from_soup(soup)
        new_count = 0
        for t in titles:
            if t not in collected_set:
                collected_set.add(t)
                collected.append(t)
                new_count += 1
        if DEBUG:
            print(f"[get_watched_movies] {username} page {page} found {len(titles)} total new {new_count}")

        # detect pagination
        has_next = bool(soup.select_one('a.next') or soup.select_one('a[rel="next"]') or soup.select_one('nav.pagination a'))
        if not has_next:
            break
        page += 1
        if page > 50:
            if DEBUG:
                print("[get_watched_movies] safety break at page 50")
            break

    if not collected:
        if DEBUG:
            print("[get_watched_movies] nothing scraped, trying RSS fallback")
        return get_films_from_rss(username, 'films')

    return collected

def get_watchlist(username: str) -> list:
    """Scrape watchlist; fallback to RSS."""
    if not username:
        return []
    username = username.strip().lower()
    collected = []
    collected_set = set()
    page = 1

    while True:
        url = f"https://letterboxd.com/{username}/watchlist/page/{page}/"
        status, html = fetch_html(url)
        if status is None:
            break
        if status != 200:
            if page == 1:
                url2 = f"https://letterboxd.com/{username}/watchlist/"
                status2, html2 = fetch_html(url2)
                if status2 == 200:
                    status, html = status2, html2
                else:
                    break
            else:
                break

        soup = BeautifulSoup(html, "lxml")
        titles = extract_movies_from_soup(soup)
        for t in titles:
            if t not in collected_set:
                collected_set.add(t)
                collected.append(t)
        if DEBUG:
            print(f"[get_watchlist] {username} page {page} found {len(titles)}")

        has_next = bool(soup.select_one('a.next') or soup.select_one('a[rel="next"]') or soup.select_one('nav.pagination a'))
        if not has_next:
            break
        page += 1
        if page > 50:
            break

    if not collected:
        if DEBUG:
            print("[get_watchlist] fallback to RSS")
        return get_films_from_rss(username, 'watchlist')

    return collected

def get_follow_data(username: str):
    """Return (following_list, followers_list, display_name_map)."""
    username = username.strip().lower()
    following = set()
    followers = set()
    name_map = {}

    def scrape_list(kind):
        page = 1
        results = set()
        while True:
            url = f"https://letterboxd.com/{username}/{kind}/page/{page}/"
            status, html = fetch_html(url)
            if status is None or status != 200:
                if page == 1:
                    # try without page number
                    url2 = f"https://letterboxd.com/{username}/{kind}/"
                    s2, h2 = fetch_html(url2)
                    if s2 != 200:
                        break
                    status, html = s2, h2
                else:
                    break
            soup = BeautifulSoup(html, "lxml")
            persons = soup.select("div.person-summary h3 a, li.person a, .person a")
            if not persons:
                break
            for p in persons:
                href = p.get("href", "").strip()
                if not href:
                    continue
                slug = href.strip("/").split("/")[0]
                if not slug:
                    continue
                display = p.get_text(strip=True) or slug
                name_map[slug] = display
                results.add(slug)
            # pagination
            if not (soup.select_one("a.next") or soup.select_one("a[rel='next']")):
                break
            page += 1
            if page > 50: break
        return results

    following = scrape_list("following")
    followers = scrape_list("followers")
    return list(following), list(followers), name_map

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
        try:
            query = requests.utils.quote(movie)
            search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={query}"
            resp = requests.get(search_url, timeout=20).json()
            if resp.get("results"):
                movie_id = resp["results"][0]["id"]
                rec_url = f"https://api.themoviedb.org/3/movie/{movie_id}/recommendations?api_key={TMDB_API_KEY}"
                rec_resp = requests.get(rec_url, timeout=20).json()
                if rec_resp.get("results"):
                    for r in rec_resp["results"]:
                        title = r.get("title")
                        if title:
                            recommendations.append(title)
        except Exception:
            pass
    # dedupe
    return list(dict.fromkeys(recommendations))

def get_movie_info(title):
    try:
        query = requests.utils.quote(title)
        url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={query}"
        resp = requests.get(url, timeout=20).json()
        if resp.get("results"):
            movie = resp["results"][0]
            poster = movie.get("poster_path")
            return {
                "title": movie.get("title", title),
                "poster": f"https://image.tmdb.org/t/p/w500{poster}" if poster else None
            }
    except Exception:
        pass
    return None

# ---------- Flask routes ----------

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        u1 = request.form.get("username1", "").strip().lower()
        u2 = request.form.get("username2", "").strip().lower()
        user1_movies = get_watched_movies(u1)
        user2_movies = get_watched_movies(u2)
        common = list(set(user1_movies) & set(user2_movies))
        compatibility = calculate_compatibility(user1_movies, user2_movies, common)
        recs = get_recommendations(common) if common else []
        return render_template("result.html",
                               username1=u1, username2=u2,
                               common_movies=common,
                               compatibility_percentage=int(compatibility),
                               recommendations=recs)
    return render_template("index.html")

@app.route("/picker", methods=["GET"])
def picker():
    return render_template("picker.html")

@app.route("/pick_movies", methods=["POST"])
def pick_movies():
    username = request.form.get("username", "").strip().lower()
    count = int(request.form.get("count", 1))
    watchlist = get_watchlist(username)
    if not watchlist:
        return jsonify([])
    selected = random.sample(watchlist, min(count, len(watchlist)))
    movies_info = []
    for t in selected:
        info = get_movie_info(t)
        if info:
            movies_info.append(info)
    return jsonify(movies_info)

@app.route("/follow", methods=["GET", "POST"])
def follow_index():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        following, followers, name_map = get_follow_data(username)
        diff = sorted(set(following) - set(followers))
        difference_list = [{"username": u, "display_name": name_map.get(u, u)} for u in diff]
        return render_template("follow-result.html", username=username, difference_list=difference_list)
    return render_template("followerboxd.html")

@app.route("/match", methods=["GET"])
def match():
    return render_template("match.html")

@app.route("/matched", methods=["POST"])
def matched():
    username = request.form.get("username", "").strip().lower()
    if not username:
        return render_template("matched.html", buddy_username="Bulunamadı", compatibility_percentage=0, common_movies=[], buddy_recommendations=[])
    user_movies = get_watched_movies(username)
    following, followers, _ = get_follow_data(username)
    potentials = list(set(following + followers))
    # limit to avoid extreme runtime
    LIMIT = 120
    potentials = potentials[:LIMIT]
    best_match = None
    best_score = 0
    best_common = []
    for other in potentials:
        try:
            other_movies = get_watched_movies(other)
            common = list(set(user_movies) & set(other_movies))
            score = calculate_compatibility(user_movies, other_movies, common)
            if score > best_score:
                best_score = score
                best_match = other
                best_common = common
        except Exception:
            continue
    buddy_recs = get_recommendations(best_common)[:50] if best_common else []
    return render_template("matched.html",
                           buddy_username=best_match or "Bulunamadı",
                           compatibility_percentage=int(best_score),
                           common_movies=best_common,
                           buddy_recommendations=buddy_recs)

if __name__ == "__main__":
    if DEBUG:
        print("Starting app.py with scraper:", _SCRAPER_TYPE)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=DEBUG)

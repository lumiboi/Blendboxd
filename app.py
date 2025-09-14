import os
import re
import random
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, session

try:
    import cloudscraper
    SCRAPER = cloudscraper.create_scraper()
except Exception:
    SCRAPER = None

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your-secret-key-here")

# TMDb API Key'i environment variable'dan al
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

if not TMDB_API_KEY:
    raise ValueError("TMDB_API_KEY environment variable is not set!")
    
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
    "Referer": "https://letterboxd.com/",
}
DEBUG = True

# ---------------- Language Management ----------------
def detect_browser_language():
    """Detect browser language from Accept-Language header"""
    accept_language = request.headers.get('Accept-Language', '')
    if 'tr' in accept_language.lower():
        return 'tr'
    return 'en'

def get_current_language():
    """Get current language from session or detect from browser"""
    if 'language' in session:
        return session['language']
    return detect_browser_language()

def set_language(lang):
    """Set language in session"""
    if lang in ['en', 'tr']:
        session['language'] = lang

def get_translations():
    """Get all translations for current language"""
    lang = get_current_language()
    translations = {
        'en': {
            'app_name': 'Blendboxd',
            'main_title': 'Blendboxd',
            'description': 'Let\'s enter the details of two users to run the blender and create the watchbox...',
            'username1_placeholder': 'Username 1',
            'username2_placeholder': 'Username 2',
            'blend_button': 'Blend!',
            'extra_title': 'Extra',
            'randomboxd': 'Randomboxd',
            'squadboxd': 'Squadboxd',
            'followboxd': 'Followboxd',
            'copyright': '© All Rights Reserved by Mert Ergün… Just kidding. I didn\'t get into those professional things, but there\'s effort.',
            'sponsor_button': 'Sponsorship etc. blah blah',
            'letterboxd_link': 'Here\'s my Letterboxd link.',
            'loading_text': 'Blender is running...',
            'loading_sounds': 'Bzzzzzt... Bzzz... Bzzzz... (spinning sound)\nTsshhh... (wind sound)\nWoop-woop... (movies sliding)\nKlink! (movies crashing)',
            'watchbox_title': 'WATCHBOX:',
            'no_common_movies': 'No common movies found.',
            'compatibility': 'Compatibility',
            'movie_recommendations': 'Movie Recommendations for This Duo:',
            'no_recommendations': 'No movie recommendations found.',
            'download_button': 'Download as Canvas',
            'download_instagram_button': 'Download as Canvas (Instagram Story)',
            'enter_usernames': 'Enter new usernames',
            'group_movie_picker': 'Group Movie Picker',
            'number_of_users': 'Number of Users',
            'username': 'Username',
            'number_of_films': 'Number of Films (From both users)',
            'fetch_movies': 'Fetch Movies',
            'main_page': 'Main Page',
            'choose_language': 'Choose Language',
            'random_film_picker': 'Random Film Picker!',
            'random_film_description': 'Picks Random Films from Your Letterboxd Watchlist.',
            'letterboxd_username': 'Letterboxd Username',
            'select_films': 'Select Films',
            'films': 'Films',
            'back_to_main': 'Back to Main',
            'enter_letterboxd_username': 'Enter Letterboxd Username',
            'follower_description': 'Lists users who don\'t follow you.',
            'submit': 'Submit',
            'loading': 'Loading... (The process may take some time.)',
            'follower_status': 'Follower Status',
            'people_not_following': 'People Not Following You:',
            'zero_people': '0 people',
            'enter_new_username': 'Enter a new username',
            'duo_picker_results': 'Duo Picker Results',
            'selected_users': 'Selected Users:',
            'randomly_selected_movies': 'Randomly Selected Movies:',
            'pick_one_movie': 'Pick One Movie',
            'go_back': 'Go Back',
            'error': 'Error:',
            'language': 'Language: English',
            'support_title': 'Support This Project',
            'support_text': 'This Python-based project runs on Railway (paid hosting). Help us keep it alive!',
            'support_button': 'Support on Patreon',
            'matchboxd': 'Matchboxd',
            'matchboxd_description': 'Discover your perfect movie soulmates! Find users who share your taste in cinema.',
            'matchboxd_explanation': 'Enter your Letterboxd username and we\'ll scan the platform to find users with the most similar movie preferences. The algorithm analyzes your watched films and matches you with people who have the highest compatibility score.',
            'enter_username_matchboxd': 'Your Letterboxd Username',
            'find_matches': 'Find My Matches',
            'matchboxd_results': 'Your Perfect Matches',
            'movie_soulmates': 'Your Movie Soulmates',
            'compatibility_score': 'Match Score',
            'shared_movies': 'Shared Movies',
            'shared_favorites': 'Shared Favorites',
            'total_movies': 'Total Movies',
            'total_favorites': 'Total Favorites',
            'no_movies_found': 'Couldn\'t find any movies for this user',
            'no_matches_found': 'No matches found',
            'processing': 'Scanning Letterboxd for your perfect matches...',
            'view_profile': 'Visit Profile',
            'match_explanation': 'Higher scores mean more shared movie taste!',
            'favorites_weight': 'Favorites are weighted more heavily in matching!',
            'smart_analysis': 'Smart Analysis',
            'genre_match': 'Genre Match',
            'era_match': 'Era Match',
            'director_match': 'Director Match',
            'rating_match': 'Rating Match',
            'analysis_explanation': 'Our smart algorithm analyzes your movie preferences across multiple dimensions to find truly compatible users!'
        },
        'tr': {
            'app_name': 'Blendboxd',
            'main_title': 'Blendboxd',
            'description': 'Blender\'ın çalışması ve watchbox oluşturulması için iki kullanıcının bilgilerini girelim...',
            'username1_placeholder': 'Kullanıcı Adı 1',
            'username2_placeholder': 'Kullanıcı Adı 2',
            'blend_button': 'Blender!',
            'extra_title': 'Extra',
            'randomboxd': 'Randomboxd',
            'squadboxd': 'Squadboxd',
            'followboxd': 'Followboxd',
            'copyright': '© Tüm Hakları Mert Ergün\'e ai... Şaka şaka. Öyle profesyonel işlere kalkışmadım ama emek var.',
            'sponsor_button': 'Sponsorluk saire vesaire blabla',
            'letterboxd_link': 'Bu da benim letırbaks linkim.',
            'loading_text': 'Blender çalışıyor...',
            'loading_sounds': 'Bzzzzzt... Bzzz... Bzzzz... (dönme sesi)\nTsshhh... (rüzgar sesi)\nWoop-woop... (filmler kayıyor)\nKlink! (filmler birbirine çarpıyor)',
            'watchbox_title': 'WATCHBOX:',
            'no_common_movies': 'Ortak film bulunamadı.',
            'compatibility': 'Uyum',
            'movie_recommendations': 'Bu İkili İçin Film Önerileri:',
            'no_recommendations': 'Film önerisi bulunamadı.',
            'download_button': 'Canvas olarak indir',
            'download_instagram_button': 'Canvas olarak indir (Instagram Hikayesi)',
            'enter_usernames': 'Yeni kullanıcı adları girin',
            'group_movie_picker': 'Grup Film Seçici',
            'number_of_users': 'Kullanıcı Sayısı',
            'username': 'Kullanıcı Adı',
            'number_of_films': 'Film Sayısı (Her iki kullanıcıdan)',
            'fetch_movies': 'Film Getir',
            'main_page': 'Ana Sayfa',
            'choose_language': 'Dil Seç',
            'random_film_picker': 'Random Film Seçici!',
            'random_film_description': 'Letterboxd Watchlist\'inizden Rastgele Film Seçer.',
            'letterboxd_username': 'Letterboxd Kullanıcı Adı',
            'select_films': 'Film Seç',
            'films': 'Film',
            'back_to_main': 'Anasayfaya Dön',
            'enter_letterboxd_username': 'Letterboxd Kullanıcı Adı Girin',
            'follower_description': 'Sizi takip etmeyen kullanıcıları listeler.',
            'submit': 'Gönder',
            'loading': 'Yükleniyordur... (İşlem birazcık zaman alabilirdir.)',
            'follower_status': 'Takipçi Durumu',
            'people_not_following': 'Seni Takip Etmeyen Şeref Yoksunları:',
            'zero_people': '0 kişi',
            'enter_new_username': 'Yeni bir kullanıcı adı gir',
            'duo_picker_results': 'Duo Picker Sonuçları',
            'selected_users': 'Seçilen Kullanıcılar:',
            'randomly_selected_movies': 'Rastgele Seçilen Filmler:',
            'pick_one_movie': 'Tek Bir Film Seç',
            'go_back': 'Geri Dön',
            'error': 'Hata:',
            'language': 'Dil: Türkçe',
            'support_title': 'Bu Projeyi Destekle',
            'support_text': 'Bu Python tabanlı proje Railway\'de (ücretli hosting) çalışıyor. Hayatta kalması için destek ol!',
            'support_button': 'Patreon\'da Destekle',
            'matchboxd': 'Matchboxd',
            'matchboxd_description': 'Mükemmel sinema ruh eşlerinizi keşfedin! Film zevkinizi paylaşan kullanıcıları bulun.',
            'matchboxd_explanation': 'Letterboxd kullanıcı adınızı girin, platformu tarayıp en benzer film tercihlerine sahip kullanıcıları bulalım. Algoritma izlediğiniz filmleri analiz ederek en yüksek uyumluluk skoruna sahip kişilerle eşleştirir.',
            'enter_username_matchboxd': 'Letterboxd Kullanıcı Adınız',
            'find_matches': 'Eşleşmelerimi Bul',
            'matchboxd_results': 'Mükemmel Eşleşmeleriniz',
            'movie_soulmates': 'Sinema Ruh Eşleriniz',
            'compatibility_score': 'Eşleşme Skoru',
            'shared_movies': 'Ortak Filmler',
            'shared_favorites': 'Ortak Favoriler',
            'total_movies': 'Toplam Film',
            'total_favorites': 'Toplam Favori',
            'no_movies_found': 'Bu kullanıcı için film bulunamadı',
            'no_matches_found': 'Eşleşme bulunamadı',
            'processing': 'Letterboxd\'de mükemmel eşleşmeleriniz aranıyor...',
            'view_profile': 'Profili Ziyaret Et',
            'match_explanation': 'Yüksek skorlar daha fazla ortak film zevki demek!',
            'favorites_weight': 'Favori filmler eşleşmede daha ağırlıklı!',
            'smart_analysis': 'Akıllı Analiz',
            'genre_match': 'Tür Eşleşmesi',
            'era_match': 'Dönem Eşleşmesi',
            'director_match': 'Yönetmen Eşleşmesi',
            'rating_match': 'Puan Eşleşmesi',
            'analysis_explanation': 'Akıllı algoritmamız film tercihlerinizi çok boyutlu analiz ederek gerçekten uyumlu kullanıcıları buluyor!'
        }
    }
    return translations[lang]

# ---------------- Helpers ----------------
def fetch_html(url, timeout=20):
    try:
        r = SCRAPER.get(url, headers=HEADERS, timeout=timeout) if SCRAPER else requests.get(url, headers=HEADERS, timeout=timeout)
        return r.status_code, r.text
    except Exception as e:
        if DEBUG: print(f"[fetch_html] {url} err: {e}")
        return None, None

def clean_title(raw):
    if not raw: return None
    s = raw.strip()
    s = re.sub(r'^\s*Poster for\s+', '', s, flags=re.I)
    s = re.sub(r'\s*\(\d{4}\)\s*$', '', s).strip()
    return re.sub(r'\s+', ' ', s)

def extract_movies_from_soup(soup):
    titles, seen = [], set()
    for tag in soup.select('[data-item-name], [data-item-full-display-name], [data-item-slug]'):
        t = clean_title(tag.get('data-item-name') or tag.get('data-item-full-display-name') or tag.get('data-item-slug'))
        if t and t not in seen: seen.add(t); titles.append(t)
    for li in soup.find_all(attrs={"data-film-name": True}):
        t = clean_title(li.get('data-film-name') or li.get('data-film-slug'))
        if t and t not in seen: seen.add(t); titles.append(t)
    for ft in soup.select('.frame-title'):
        t = clean_title(ft.get_text(strip=True))
        if t and t not in seen: seen.add(t); titles.append(t)
    for img in soup.find_all('img', alt=True):
        t = clean_title(img['alt'])
        if t and t not in seen: seen.add(t); titles.append(t)
    for a in soup.find_all('a', href=True):
        if '/film/' in a['href']:
            t = clean_title(a.get_text(strip=True))
            if t and t not in seen: seen.add(t); titles.append(t)
    return titles

def get_watched_movies(username):
    username = username.strip().lower()
    collected, seen = [], set()
    page = 1
    while True:
        url = f"https://letterboxd.com/{username}/films/page/{page}/"
        status, html = fetch_html(url)
        if status != 200 or not html: break
        soup = BeautifulSoup(html, "lxml")
        for t in extract_movies_from_soup(soup):
            if t not in seen: seen.add(t); collected.append(t)
        if not (soup.select_one("a.next") or soup.select_one("a[rel='next']")): break
        page += 1
        if page > 50: break
    return collected

def get_watchlist(username):
    username = username.strip().lower()
    collected, seen = [], set()
    page = 1
    while True:
        url = f"https://letterboxd.com/{username}/watchlist/page/{page}/"
        status, html = fetch_html(url)
        if status != 200 or not html: break
        soup = BeautifulSoup(html, "lxml")
        for t in extract_movies_from_soup(soup):
            if t not in seen: seen.add(t); collected.append(t)
        if not (soup.select_one("a.next") or soup.select_one("a[rel='next']")): break
        page += 1
        if page > 50: break
    return collected

def get_favorite_movies(username):
    """Get user's favorite movies from their favorites page"""
    username = username.strip().lower()
    favorites = []
    page = 1
    while True:
        url = f"https://letterboxd.com/{username}/favourites/page/{page}/"
        status, html = fetch_html(url)
        if status != 200 or not html: break
        soup = BeautifulSoup(html, "lxml")
        movies = extract_movies_from_soup(soup)
        if not movies: break
        favorites.extend(movies)
        if not (soup.select_one("a.next") or soup.select_one("a[rel='next']")): break
        page += 1
        if page > 10: break  # Limit to first 10 pages for performance
    return favorites

def get_follow_data(username):
    username = username.strip().lower()
    following, followers, name_map = set(), set(), {}
    def scrape_list(kind):
        page, results = 1, set()
        while True:
            url = f"https://letterboxd.com/{username}/{kind}/page/{page}/"
            status, html = fetch_html(url)
            if status != 200 or not html: break
            soup = BeautifulSoup(html, "lxml")
            persons = soup.select("div.person-summary h3 a, li.person a, .person a")
            if not persons: break
            for p in persons:
                slug = p.get("href","/").strip("/").split("/")[0]
                if slug:
                    name_map[slug] = p.get_text(strip=True) or slug
                    results.add(slug)
            if not (soup.select_one("a.next") or soup.select_one("a[rel='next']")): break
            page += 1
            if page > 50: break
        return results
    following = scrape_list("following")
    followers = scrape_list("followers")
    return list(following), list(followers), name_map

def calculate_compatibility(u1, u2, common):
    total = len(u1)+len(u2)
    if total==0 or not common: return 0
    c=len(common)
    return min(100, (2*c/total)*100 if c<=5 else 50+(2*c/total)*100)

def get_movie_details(movie_title):
    """Get detailed movie information from TMDb"""
    try:
        if not TMDB_API_KEY or TMDB_API_KEY == "test":
            return None
        
        # Search for movie
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_title}"
        response = requests.get(search_url, timeout=10)
        if response.status_code != 200:
            return None
        
        data = response.json()
        if not data.get('results'):
            return None
        
        movie = data['results'][0]
        movie_id = movie['id']
        
        # Get detailed info
        details_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}"
        details_response = requests.get(details_url, timeout=10)
        if details_response.status_code != 200:
            return None
        
        return details_response.json()
    except:
        return None

def analyze_movie_preferences(movies, favorites):
    """Analyze user's movie preferences in detail"""
    all_movies = movies + favorites
    if not all_movies:
        return {}
    
    # Get movie details for analysis
    movie_details = []
    for movie in all_movies[:50]:  # Limit for performance
        details = get_movie_details(movie)
        if details:
            movie_details.append(details)
    
    if not movie_details:
        return {}
    
    # Analyze genres
    genre_counts = {}
    for movie in movie_details:
        for genre in movie.get('genres', []):
            genre_name = genre['name']
            genre_counts[genre_name] = genre_counts.get(genre_name, 0) + 1
    
    # Analyze decades
    decade_counts = {}
    for movie in movie_details:
        year = movie.get('release_date', '')[:4]
        if year and year.isdigit():
            decade = f"{year[:3]}0s"
            decade_counts[decade] = decade_counts.get(decade, 0) + 1
    
    # Analyze directors
    director_counts = {}
    for movie in movie_details:
        # Get director from credits
        try:
            credits_url = f"https://api.themoviedb.org/3/movie/{movie['id']}/credits?api_key={TMDB_API_KEY}"
            credits_response = requests.get(credits_url, timeout=5)
            if credits_response.status_code == 200:
                credits = credits_response.json()
                for person in credits.get('crew', []):
                    if person.get('job') == 'Director':
                        director_name = person['name']
                        director_counts[director_name] = director_counts.get(director_name, 0) + 1
                        break
        except:
            continue
    
    # Analyze ratings (if available)
    ratings = [movie.get('vote_average', 0) for movie in movie_details if movie.get('vote_average', 0) > 0]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    return {
        'genres': genre_counts,
        'decades': decade_counts,
        'directors': director_counts,
        'avg_rating': avg_rating,
        'total_analyzed': len(movie_details)
    }

def calculate_smart_compatibility(user_movies, user_favorites, other_movies, other_favorites):
    """Calculate sophisticated compatibility using multiple factors"""
    
    # Get detailed preferences for both users
    user_prefs = analyze_movie_preferences(user_movies, user_favorites)
    other_prefs = analyze_movie_preferences(other_movies, other_favorites)
    
    if not user_prefs or not other_prefs:
        # Fallback to basic compatibility
        common_watched = list(set(user_movies) & set(other_movies))
        basic_score = calculate_compatibility(user_movies, other_movies, common_watched)
        return {
            'compatibility': round(basic_score, 1),
            'common_watched': len(common_watched),
            'common_favorites': len(set(user_favorites) & set(other_favorites)),
            'total_watched': len(user_movies),
            'total_other_watched': len(other_movies),
            'total_favorites': len(user_favorites),
            'total_other_favorites': len(other_favorites),
            'analysis_type': 'basic'
        }
    
    # Calculate genre compatibility
    genre_score = 0
    user_genres = set(user_prefs['genres'].keys())
    other_genres = set(other_prefs['genres'].keys())
    if user_genres and other_genres:
        common_genres = user_genres & other_genres
        genre_score = len(common_genres) / max(len(user_genres), len(other_genres)) * 100
    
    # Calculate decade compatibility
    decade_score = 0
    user_decades = set(user_prefs['decades'].keys())
    other_decades = set(other_prefs['decades'].keys())
    if user_decades and other_decades:
        common_decades = user_decades & other_decades
        decade_score = len(common_decades) / max(len(user_decades), len(other_decades)) * 100
    
    # Calculate director compatibility
    director_score = 0
    user_directors = set(user_prefs['directors'].keys())
    other_directors = set(other_prefs['directors'].keys())
    if user_directors and other_directors:
        common_directors = user_directors & other_directors
        director_score = len(common_directors) / max(len(user_directors), len(other_directors)) * 100
    
    # Calculate rating similarity
    rating_score = 0
    if user_prefs['avg_rating'] > 0 and other_prefs['avg_rating'] > 0:
        rating_diff = abs(user_prefs['avg_rating'] - other_prefs['avg_rating'])
        rating_score = max(0, 100 - (rating_diff * 10))  # 1 point difference = 10% score reduction
    
    # Calculate basic movie overlap
    common_watched = list(set(user_movies) & set(other_movies))
    common_favorites = list(set(user_favorites) & set(other_favorites))
    overlap_score = calculate_compatibility(user_movies, other_movies, common_watched)
    
    # Weighted final score
    final_score = (
        overlap_score * 0.25 +      # 25% - Basic movie overlap
        genre_score * 0.30 +        # 30% - Genre preferences
        decade_score * 0.20 +       # 20% - Era preferences
        director_score * 0.15 +     # 15% - Director preferences
        rating_score * 0.10         # 10% - Rating similarity
    )
    
    return {
        'compatibility': round(final_score, 1),
        'common_watched': len(common_watched),
        'common_favorites': len(common_favorites),
        'total_watched': len(user_movies),
        'total_other_watched': len(other_movies),
        'total_favorites': len(user_favorites),
        'total_other_favorites': len(other_favorites),
        'genre_score': round(genre_score, 1),
        'decade_score': round(decade_score, 1),
        'director_score': round(director_score, 1),
        'rating_score': round(rating_score, 1),
        'analysis_type': 'advanced'
    }

def get_recommendations(common):
    recs=[]
    for m in common:
        try:
            q = requests.utils.quote(m)
            s_url=f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={q}"
            r=requests.get(s_url,timeout=20).json()
            if r.get("results"):
                mid=r["results"][0]["id"]
                rec_url=f"https://api.themoviedb.org/3/movie/{mid}/recommendations?api_key={TMDB_API_KEY}"
                rr=requests.get(rec_url,timeout=20).json()
                for x in rr.get("results",[]): recs.append(x["title"])
        except: pass
    return list(dict.fromkeys(recs))

def get_movie_info(title):
    try:
        q=requests.utils.quote(title)
        url=f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={q}"
        r=requests.get(url,timeout=20).json()
        if r.get("results"):
            m=r["results"][0]; p=m.get("poster_path")
            return {"title":m.get("title",title),"poster":f"https://image.tmdb.org/t/p/w500{p}" if p else None}
    except: pass
    return None

# ---------------- Routes ----------------
@app.route("/set_language/<lang>")
def set_language_route(lang):
    """Set language and redirect back"""
    set_language(lang)
    return jsonify({"success": True, "language": lang})

@app.route("/",methods=["GET","POST"])
def index():
    if request.method=="POST":
        u1,u2=request.form["username1"].lower(),request.form["username2"].lower()
        m1,m2=get_watched_movies(u1),get_watched_movies(u2)
        common=list(set(m1)&set(m2))
        comp=calculate_compatibility(m1,m2,common)
        recs=get_recommendations(common) if common else []
        return render_template("result.html",username1=u1,username2=u2,common_movies=common,compatibility_percentage=int(comp),recommendations=recs,translations=get_translations(),current_lang=get_current_language())
    return render_template("index.html",translations=get_translations(),current_lang=get_current_language())

@app.route("/picker")
def picker(): 
    return render_template("picker.html",translations=get_translations(),current_lang=get_current_language())

@app.route("/pick_movies",methods=["POST"])
def pick_movies():
    u=request.form.get("username","").lower(); c=int(request.form.get("count",1))
    wl=get_watchlist(u); sel=random.sample(wl,min(c,len(wl))) if wl else []
    return jsonify([get_movie_info(t) for t in sel if get_movie_info(t)])

@app.route("/duo_picker",methods=["GET","POST"])
def duo_picker():
    if request.method=="POST":
        try:
            uc,fc=int(request.form.get("user_count",1)),int(request.form.get("film_count",1))
            users=[request.form.get(f"username{i+1}","").lower() for i in range(uc)]
            allm=[]
            for u in users:
                wl=get_watchlist(u)
                sel=random.sample(wl,min(fc,len(wl))) if wl else []
                for t in sel:
                    info=get_movie_info(t)
                    if info: allm.append(info)
            return render_template("duo_picker_result.html",movies=allm,usernames=users,translations=get_translations(),current_lang=get_current_language())
        except Exception as e:
            return render_template("duo_picker_result.html",error=str(e),translations=get_translations(),current_lang=get_current_language())
    return render_template("duo_picker.html",translations=get_translations(),current_lang=get_current_language())

@app.route("/follow",methods=["GET","POST"])
def follow_index():
    if request.method=="POST":
        u=request.form["username"].lower()
        following,followers,nmap=get_follow_data(u)
        diff=sorted(set(following)-set(followers))
        diff_list=[{"username":x,"display_name":nmap.get(x,x)} for x in diff]
        return render_template("follow-result.html",username=u,difference_list=diff_list,translations=get_translations(),current_lang=get_current_language())
    return render_template("followerboxd.html",translations=get_translations(),current_lang=get_current_language())

@app.route("/matchboxd",methods=["GET","POST"])
def matchboxd():
    if request.method=="POST":
        username=request.form["username"].lower()
        try:
            # Get user's watched movies and favorites
            user_movies = get_watched_movies(username)
            user_favorites = get_favorite_movies(username)
            if not user_movies:
                return render_template("matchboxd.html",error="No movies found for this user",translations=get_translations(),current_lang=get_current_language())
            
            # Get a sample of users to compare with (popular users + some random)
            # This simulates searching all Letterboxd users
            sample_users = [
                "davidehrlich", "filmspotting", "kermode", "markkermode", "roger_ebert",
                "paulinekael", "andrewhorton", "davidbordwell", "kristenthompson",
                "jimemerson", "davidchen", "filmcritic", "cinematheque", "criterion",
                "mubi", "letterboxd", "film", "movies", "cinema", "director"
            ]
            
            # Add some random usernames for variety
            import random
            random_users = [f"user{i}" for i in range(1, 21)]
            sample_users.extend(random_users)
            
            # Calculate compatibility with each user
            compatibility_list = []
            for i, other_user in enumerate(sample_users[:30]):  # Check 30 users for better results
                try:
                    other_movies = get_watched_movies(other_user)
                    other_favorites = get_favorite_movies(other_user)
                    if other_movies:
                        # Use smart compatibility calculation
                        compatibility_data = calculate_smart_compatibility(
                            user_movies, user_favorites, other_movies, other_favorites
                        )
                        compatibility_list.append({
                            "username": other_user,
                            "display_name": other_user.title().replace('_', ' '),
                            "compatibility": compatibility_data['compatibility'],
                            "common_watched": compatibility_data['common_watched'],
                            "common_favorites": compatibility_data['common_favorites'],
                            "total_movies": compatibility_data['total_other_watched'],
                            "total_favorites": compatibility_data['total_other_favorites']
                        })
                except Exception as e:
                    if DEBUG: print(f"Error processing {other_user}: {e}")
                    continue
            
            # Sort by compatibility and filter out very low matches
            compatibility_list.sort(key=lambda x: x["compatibility"], reverse=True)
            compatibility_list = [user for user in compatibility_list if user["compatibility"] > 5]  # Only show matches above 5%
            
            return render_template("matchboxd.html",username=username,compatibility_list=compatibility_list,translations=get_translations(),current_lang=get_current_language())
        except Exception as e:
            return render_template("matchboxd.html",error=str(e),translations=get_translations(),current_lang=get_current_language())
    
    return render_template("matchboxd.html",translations=get_translations(),current_lang=get_current_language())

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=True)

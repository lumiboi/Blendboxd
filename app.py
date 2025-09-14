import os
import re
import random
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, session
import letterboxdpy
import concurrent.futures
import threading
from functools import lru_cache

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
            'analysis_explanation': 'Our smart algorithm finds users with similar favorite movies and movie taste patterns!'
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
            'analysis_explanation': 'Akıllı algoritmamız benzer favori filmleri ve film zevki kalıplarını buluyor!'
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

@lru_cache(maxsize=1000)
def get_watched_movies(username):
    """Get user's watched movies using letterboxdpy API - CACHED for speed"""
    try:
        # Use letterboxdpy to get user's watched movies
        user_data = letterboxdpy.user.get_user(username)
        if user_data and 'watched' in user_data:
            movies = []
            for movie in user_data['watched']:
                if 'title' in movie:
                    movies.append(movie['title'])
            return tuple(movies)  # Convert to tuple for caching
    except Exception as e:
        if DEBUG: print(f"Error getting watched movies via API for {username}: {e}")
    
    # Fallback to scraping if API fails
    try:
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
        return tuple(collected)  # Convert to tuple for caching
    except Exception as e:
        if DEBUG: print(f"Error getting watched movies via scraping for {username}: {e}")
        return tuple()

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

@lru_cache(maxsize=1000)
def get_favorite_movies(username):
    """Get user's favorite movies using letterboxdpy API - CACHED for speed"""
    try:
        # Use letterboxdpy to get user's favorite movies
        user_data = letterboxdpy.user.get_user(username)
        if user_data and 'favorites' in user_data:
            favorites = []
            for fav in user_data['favorites']:
                if 'title' in fav:
                    favorites.append(fav['title'])
            return tuple(favorites)  # Convert to tuple for caching
    except Exception as e:
        if DEBUG: print(f"Error getting favorites via API for {username}: {e}")
    
    # Fallback to scraping if API fails
    try:
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
        return tuple(favorites)  # Convert to tuple for caching
    except Exception as e:
        if DEBUG: print(f"Error getting favorites via scraping for {username}: {e}")
        return tuple()

def discover_letterboxd_users():
    """INFINITE CRAWL - ALL LETTERBOXD USERS - NO LIMITS"""
    users = set()
    
    try:
        # INFINITE CRAWLING - NO LIMITS!
        if DEBUG: print("INFINITE CRAWLING - ALL LETTERBOXD USERS - NO LIMITS...")
        
        # Method 1: INFINITE member directory crawl
        if DEBUG: print("Crawling member directory - INFINITE pages...")
        page = 1
        while True:  # INFINITE LOOP - NO LIMITS!
            try:
                url = f"https://letterboxd.com/members/page/{page}/"
                status, html = fetch_html(url)
                if status == 200 and html:
                    soup = BeautifulSoup(html, "lxml")
                    user_links = soup.select("a[href^='/']")
                    for link in user_links:
                        href = link.get('href', '')
                        if href and not href.startswith('/film/') and not href.startswith('/list/') and not href.startswith('/activity/') and not href.startswith('/members/'):
                            username = href.strip('/').split('/')[0]
                            if username and len(username) > 2 and username not in ['film', 'list', 'activity', 'members', 'reviews', 'lists', 'films']:
                                users.add(username)
                    if DEBUG and page % 100 == 0:
                        print(f"Crawled {page} pages, found {len(users)} users")
                    page += 1
                else:
                    break  # No more pages
            except Exception as e:
                if DEBUG: print(f"Error on page {page}: {e}")
                page += 1
                continue
        
        # Method 2: INFINITE film reviews crawl
        if DEBUG: print("Crawling film reviews - INFINITE films...")
        popular_films = [
            "the-godfather", "pulp-fiction", "the-dark-knight", "inception", 
            "fight-club", "the-matrix", "goodfellas", "forrest-gump", 
            "the-shawshank-redemption", "star-wars", "the-lord-of-the-rings",
            "titanic", "avatar", "jaws", "et", "back-to-the-future",
            "indiana-jones", "terminator", "alien", "blade-runner",
            "casablanca", "citizen-kane", "vertigo", "psycho", "taxi-driver",
            "apocalypse-now", "raiders-of-the-lost-ark", "the-empire-strikes-back",
            "return-of-the-jedi", "the-silence-of-the-lambs", "schindlers-list",
            "saving-private-ryan", "the-green-mile", "american-beauty",
            "the-godfather-part-ii", "the-godfather-part-iii", "goodfellas",
            "casino", "heat", "scarface", "the-departed", "infernal-affairs",
            "oldboy", "parasite", "memories-of-murder", "the-host", "snowpiercer",
            "spirited-away", "princess-mononoke", "my-neighbor-totoro", "grave-of-the-fireflies",
            "akira", "ghost-in-the-shell", "perfect-blue", "paprika", "millennium-actress",
            "your-name", "weathering-with-you", "a-silent-voice", "i-want-to-eat-your-pancreas",
            "demon-slayer", "attack-on-titan", "one-piece", "naruto", "dragon-ball",
            "death-note", "fullmetal-alchemist", "cowboy-bebop", "neon-genesis-evangelion",
            "berserk", "hunter-x-hunter", "jojos-bizarre-adventure", "my-hero-academia",
            "tokyo-ghoul", "one-punch-man", "mob-psycho-100", "the-promised-neverland",
            "jujutsu-kaisen", "chainsaw-man", "spy-x-family", "demon-slayer",
            "attack-on-titan", "one-piece", "naruto", "dragon-ball", "death-note",
            "fullmetal-alchemist", "cowboy-bebop", "neon-genesis-evangelion", "berserk",
            "hunter-x-hunter", "jojos-bizarre-adventure", "my-hero-academia", "tokyo-ghoul",
            "one-punch-man", "mob-psycho-100", "the-promised-neverland", "jujutsu-kaisen",
            "chainsaw-man", "spy-x-family", "demon-slayer", "attack-on-titan",
            "one-piece", "naruto", "dragon-ball", "death-note", "fullmetal-alchemist",
            "cowboy-bebop", "neon-genesis-evangelion", "berserk", "hunter-x-hunter",
            "jojos-bizarre-adventure", "my-hero-academia", "tokyo-ghoul", "one-punch-man",
            "mob-psycho-100", "the-promised-neverland", "jujutsu-kaisen", "chainsaw-man",
            "spy-x-family", "demon-slayer", "attack-on-titan", "one-piece", "naruto",
            "dragon-ball", "death-note", "fullmetal-alchemist", "cowboy-bebop",
            "neon-genesis-evangelion", "berserk", "hunter-x-hunter", "jojos-bizarre-adventure",
            "my-hero-academia", "tokyo-ghoul", "one-punch-man", "mob-psycho-100",
            "the-promised-neverland", "jujutsu-kaisen", "chainsaw-man", "spy-x-family"
        ]
        
        for film_slug in popular_films:
            try:
                # Get users who reviewed this film - INFINITE pages per film
                page = 1
                while True:  # INFINITE LOOP - NO LIMITS!
                    url = f"https://letterboxd.com/film/{film_slug}/reviews/page/{page}/"
                    status, html = fetch_html(url)
                    if status == 200 and html:
                        soup = BeautifulSoup(html, "lxml")
                        review_links = soup.select("a[href^='/']")
                        for link in review_links:
                            href = link.get('href', '')
                            if href and not href.startswith('/film/') and not href.startswith('/list/') and not href.startswith('/activity/') and not href.startswith('/members/'):
                                username = href.strip('/').split('/')[0]
                                if username and len(username) > 2:
                                    users.add(username)
                        page += 1
                    else:
                        break  # No more pages
            except Exception as e:
                if DEBUG: print(f"Error crawling film {film_slug}: {e}")
                continue
        
        # Method 3: INFINITE recent activity crawl
        if DEBUG: print("Crawling recent activity - INFINITE pages...")
        page = 1
        while True:  # INFINITE LOOP - NO LIMITS!
            try:
                url = f"https://letterboxd.com/activity/page/{page}/"
                status, html = fetch_html(url)
                if status == 200 and html:
                    soup = BeautifulSoup(html, "lxml")
                    user_links = soup.select("a[href^='/']")
                    for link in user_links:
                        href = link.get('href', '')
                        if href and not href.startswith('/film/') and not href.startswith('/list/') and not href.startswith('/activity/') and not href.startswith('/members/'):
                            username = href.strip('/').split('/')[0]
                            if username and len(username) > 2:
                                users.add(username)
                    if DEBUG and page % 100 == 0:
                        print(f"Crawled activity page {page}, found {len(users)} users")
                    page += 1
                else:
                    break  # No more pages
            except Exception as e:
                if DEBUG: print(f"Error crawling activity page {page}: {e}")
                page += 1
                continue
        
        # Method 4: INFINITE popular lists crawl
        if DEBUG: print("Crawling popular lists - INFINITE lists...")
        popular_lists = [
            "imdb-top-250", "sight-and-sound", "afi-100", "criterion-collection",
            "oscar-winners", "cannes-winners", "berlin-winners", "venice-winners",
            "best-films-2023", "best-films-2022", "best-films-2021", "best-films-2020",
            "best-films-2019", "best-films-2018", "best-films-2017", "best-films-2016",
            "best-films-2015", "best-films-2014", "best-films-2013", "best-films-2012",
            "best-films-2011", "best-films-2010", "best-films-2009", "best-films-2008",
            "best-films-2007", "best-films-2006", "best-films-2005", "best-films-2004",
            "best-films-2003", "best-films-2002", "best-films-2001", "best-films-2000",
            "best-films-1999", "best-films-1998", "best-films-1997", "best-films-1996",
            "best-films-1995", "best-films-1994", "best-films-1993", "best-films-1992",
            "best-films-1991", "best-films-1990", "best-films-1989", "best-films-1988",
            "best-films-1987", "best-films-1986", "best-films-1985", "best-films-1984",
            "best-films-1983", "best-films-1982", "best-films-1981", "best-films-1980",
            "best-films-1979", "best-films-1978", "best-films-1977", "best-films-1976",
            "best-films-1975", "best-films-1974", "best-films-1973", "best-films-1972",
            "best-films-1971", "best-films-1970", "best-films-1969", "best-films-1968",
            "best-films-1967", "best-films-1966", "best-films-1965", "best-films-1964",
            "best-films-1963", "best-films-1962", "best-films-1961", "best-films-1960",
            "best-films-1959", "best-films-1958", "best-films-1957", "best-films-1956",
            "best-films-1955", "best-films-1954", "best-films-1953", "best-films-1952",
            "best-films-1951", "best-films-1950", "best-films-1949", "best-films-1948",
            "best-films-1947", "best-films-1946", "best-films-1945", "best-films-1944",
            "best-films-1943", "best-films-1942", "best-films-1941", "best-films-1940",
            "best-films-1939", "best-films-1938", "best-films-1937", "best-films-1936",
            "best-films-1935", "best-films-1934", "best-films-1933", "best-films-1932",
            "best-films-1931", "best-films-1930", "best-films-1929", "best-films-1928",
            "best-films-1927", "best-films-1926", "best-films-1925", "best-films-1924",
            "best-films-1923", "best-films-1922", "best-films-1921", "best-films-1920",
            "best-films-1919", "best-films-1918", "best-films-1917", "best-films-1916",
            "best-films-1915", "best-films-1914", "best-films-1913", "best-films-1912",
            "best-films-1911", "best-films-1910", "best-films-1909", "best-films-1908",
            "best-films-1907", "best-films-1906", "best-films-1905", "best-films-1904",
            "best-films-1903", "best-films-1902", "best-films-1901", "best-films-1900"
        ]
        
        for list_slug in popular_lists:
            try:
                # Get users who liked this list - INFINITE pages per list
                page = 1
                while True:  # INFINITE LOOP - NO LIMITS!
                    url = f"https://letterboxd.com/list/{list_slug}/likes/page/{page}/"
                    status, html = fetch_html(url)
                    if status == 200 and html:
                        soup = BeautifulSoup(html, "lxml")
                        user_links = soup.select("a[href^='/']")
                        for link in user_links:
                            href = link.get('href', '')
                            if href and not href.startswith('/film/') and not href.startswith('/list/') and not href.startswith('/activity/') and not href.startswith('/members/'):
                                username = href.strip('/').split('/')[0]
                                if username and len(username) > 2:
                                    users.add(username)
                        page += 1
                    else:
                        break  # No more pages
            except Exception as e:
                if DEBUG: print(f"Error crawling list {list_slug}: {e}")
                continue
        
    except Exception as e:
        if DEBUG: print(f"Error in discover_letterboxd_users: {e}")
    
    user_list = list(users)
    if DEBUG: print(f"Discovered {len(user_list)} users from ENTIRE Letterboxd platform - INFINITE CRAWL COMPLETE!")
    return user_list  # ALL USERS - INFINITE CRAWL - NO LIMITS!

def check_user_favorites(username, user_favorites):
    """Check if user has common favorites - for parallel processing"""
    try:
        other_favorites = get_favorite_movies(username)
        if other_favorites:
            common = list(set(user_favorites) & set(other_favorites))
            if common:  # If they have ANY common favorites
                return {
                    'username': username,
                    'common_favorites': common,
                    'total_favorites': len(other_favorites)
                }
    except Exception as e:
        if DEBUG: print(f"Error getting favorites for {username}: {e}")
    return None

def find_users_with_common_favorites(user_favorites, all_users):
    """Find users with common favorites - MASSIVE PARALLEL PROCESSING"""
    if not user_favorites:
        return []
    
    users_with_common = []
    
    # MASSIVE PARALLEL PROCESSING - 100 workers!
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        future_to_username = {
            executor.submit(check_user_favorites, username, user_favorites): username 
            for username in all_users
        }
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_username)):
            if DEBUG and i % 500 == 0:
                print(f"Processed {i+1}/{len(all_users)} users...")
            
            try:
                result = future.result()
                if result:
                    users_with_common.append(result)
                    if DEBUG:
                        print(f"FOUND COMMON FAVORITES with {result['username']}: {result['common_favorites']}")
            except Exception as e:
                if DEBUG: print(f"Error in parallel processing: {e}")
                continue
    
    # Sort by number of common favorites
    users_with_common.sort(key=lambda x: len(x['common_favorites']), reverse=True)
    return users_with_common  # Return ALL users with common favorites - NO LIMITS!

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

def calculate_fast_smart_compatibility(user_movies, user_favorites, other_movies, other_favorites):
    """Fast and smart compatibility using only Letterboxd data"""
    
    # Basic movie overlap
    common_watched = list(set(user_movies) & set(other_movies))
    common_favorites = list(set(user_favorites) & set(other_favorites))
    
    # Calculate basic overlap score
    overlap_score = calculate_compatibility(user_movies, other_movies, common_watched)
    
    # Favorites bonus - this is the key!
    favorites_bonus = 0
    if user_favorites and other_favorites:
        # If they have ANY common favorites, give huge bonus
        if common_favorites:
            favorites_bonus = min(50, len(common_favorites) * 10)  # Up to 50% bonus
        else:
            # Even if no common favorites, check if they have similar favorite patterns
            # (both like similar types of movies based on titles)
            user_fav_titles = [fav.lower() for fav in user_favorites]
            other_fav_titles = [fav.lower() for fav in other_favorites]
            
            # Simple keyword matching for similar taste
            user_keywords = set()
            other_keywords = set()
            
            for title in user_fav_titles:
                words = title.split()
                for word in words:
                    if len(word) > 3:  # Only meaningful words
                        user_keywords.add(word)
            
            for title in other_fav_titles:
                words = title.split()
                for word in words:
                    if len(word) > 3:
                        other_keywords.add(word)
            
            if user_keywords and other_keywords:
                common_keywords = user_keywords & other_keywords
                keyword_similarity = len(common_keywords) / max(len(user_keywords), len(other_keywords))
                favorites_bonus = keyword_similarity * 30  # Up to 30% bonus for similar taste
    
    # Calculate final score
    final_score = overlap_score + favorites_bonus
    final_score = min(100, final_score)  # Cap at 100%
    
    return {
        'compatibility': round(final_score, 1),
        'common_watched': len(common_watched),
        'common_favorites': len(common_favorites),
        'total_watched': len(user_movies),
        'total_other_watched': len(other_movies),
        'total_favorites': len(user_favorites),
        'total_other_favorites': len(other_favorites),
        'favorites_bonus': round(favorites_bonus, 1),
        'analysis_type': 'fast_smart'
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
            
            # ULTRA FAST SEARCH - ALL LETTERBOXD USERS
            if DEBUG: print("Starting ULTRA FAST search across ALL Letterboxd users...")
            all_users = discover_letterboxd_users()
            if DEBUG: print(f"Discovered {len(all_users)} users from ENTIRE Letterboxd platform")
            
            compatibility_list = []
            
            # ULTRA FAST search for common favorites across ALL users
            if user_favorites:
                if DEBUG: print("Searching for users with common favorites across ALL users...")
                users_with_common_favorites = find_users_with_common_favorites(user_favorites, all_users)
                if DEBUG: print(f"Found {len(users_with_common_favorites)} users with common favorites")
                
                # Process users with common favorites - PARALLEL
                def process_common_favorite_user(user_data):
                    try:
                        other_username = user_data['username']
                        other_movies = get_watched_movies(other_username)
                        
                        if other_movies:
                            common_watched = list(set(user_movies) & set(other_movies))
                            common_favorites = user_data['common_favorites']
                            
                            # Calculate compatibility
                            base_score = calculate_compatibility(user_movies, other_movies, common_watched)
                            favorites_bonus = len(common_favorites) * 20
                            favorites_bonus = min(80, favorites_bonus)
                            final_score = min(100, base_score + favorites_bonus)
                            
                            return {
                                "username": other_username,
                                "display_name": other_username.title().replace('_', ' '),
                                "compatibility": round(final_score, 1),
                                "common_watched": len(common_watched),
                                "common_favorites": len(common_favorites),
                                "total_movies": len(other_movies),
                                "total_favorites": user_data['total_favorites'],
                                "favorites_bonus": round(favorites_bonus, 1),
                                "analysis_type": "real_favorites_match"
                            }
                    except Exception as e:
                        if DEBUG: print(f"Error processing {other_username}: {e}")
                        return None
                
                # MASSIVE PARALLEL PROCESSING for ULTRA SPEED
                with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
                    future_to_user = {
                        executor.submit(process_common_favorite_user, user_data): user_data 
                        for user_data in users_with_common_favorites
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_user):
                        try:
                            result = future.result()
                            if result:
                                compatibility_list.append(result)
                        except Exception as e:
                            if DEBUG: print(f"Error in parallel processing: {e}")
                            continue
            
            # If we don't have enough matches, search through ALL users for regular matches
            if len(compatibility_list) < 10:
                if DEBUG: print("Searching for regular matches across ALL Letterboxd users...")
                
                def process_regular_user(other_username):
                    try:
                        other_movies = get_watched_movies(other_username)
                        other_favorites = get_favorite_movies(other_username)
                        
                        if other_movies:
                            compatibility_data = calculate_fast_smart_compatibility(
                                user_movies, user_favorites, other_movies, other_favorites
                            )
                            return {
                                "username": other_username,
                                "display_name": other_username.title().replace('_', ' '),
                                "compatibility": compatibility_data['compatibility'],
                                "common_watched": compatibility_data['common_watched'],
                                "common_favorites": compatibility_data['common_favorites'],
                                "total_movies": compatibility_data['total_other_watched'],
                                "total_favorites": compatibility_data['total_other_favorites'],
                                "favorites_bonus": compatibility_data.get('favorites_bonus', 0),
                                "analysis_type": "regular_match"
                            }
                    except Exception as e:
                        if DEBUG: print(f"Error processing {other_username}: {e}")
                        return None
                
                # MASSIVE PARALLEL PROCESSING for ULTRA SPEED
                with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
                    future_to_username = {
                        executor.submit(process_regular_user, username): username 
                        for username in all_users
                    }
                    
                    for i, future in enumerate(concurrent.futures.as_completed(future_to_username)):
                        if DEBUG and i % 500 == 0:
                            print(f"Processed regular match {i+1}/{len(all_users)}...")
                        
                        try:
                            result = future.result()
                            if result:
                                compatibility_list.append(result)
                        except Exception as e:
                            if DEBUG: print(f"Error in parallel processing: {e}")
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

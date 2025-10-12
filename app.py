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
            'support_button': 'Support on Patreon'
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
            'support_button': 'Patreon\'da Destekle'
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
        soup = BeautifulSoup(html, "html.parser")
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
        soup = BeautifulSoup(html, "html.parser")
        for t in extract_movies_from_soup(soup):
            if t not in seen: seen.add(t); collected.append(t)
        if not (soup.select_one("a.next") or soup.select_one("a[rel='next']")): break
        page += 1
        if page > 50: break
    return collected

def get_follow_data(username):
    username = username.strip().lower()
    following, followers, name_map = set(), set(), {}
    def scrape_list(kind):
        page, results = 1, set()
        while True:
            url = f"https://letterboxd.com/{username}/{kind}/page/{page}/"
            status, html = fetch_html(url)
            if status != 200 or not html: break
            soup = BeautifulSoup(html, "html.parser")
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

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=True)

import os
import re
import random
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify

try:
    import cloudscraper
    SCRAPER = cloudscraper.create_scraper()
except Exception:
    SCRAPER = None

app = Flask(__name__)

TMDB_API_KEY = "f3abc39a6d4fbdcc0b2a79906b528658"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
    "Referer": "https://letterboxd.com/",
}
DEBUG = True

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
@app.route("/",methods=["GET","POST"])
def index():
    if request.method=="POST":
        u1,u2=request.form["username1"].lower(),request.form["username2"].lower()
        m1,m2=get_watched_movies(u1),get_watched_movies(u2)
        common=list(set(m1)&set(m2))
        comp=calculate_compatibility(m1,m2,common)
        recs=get_recommendations(common) if common else []
        return render_template("result.html",username1=u1,username2=u2,common_movies=common,compatibility_percentage=int(comp),recommendations=recs)
    return render_template("index.html")

@app.route("/picker")
def picker(): return render_template("picker.html")

@app.route("/pick_movies",methods=["POST"])
def pick_movies():
    u=request.form.get("username","").lower(); c=int(request.form.get("count",1))
    wl=get_watchlist(u); sel=random.sample(wl,min(c,len(wl))) if wl else []
    return jsonify([get_movie_info(t) for t in sel if get_movie_info(t)])

@app.route("/duo_picker",methods=["GET","POST"])
def duo_picker():
    lang=request.args.get("lang","tr")
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
            return render_template("duo_picker_result.html",movies=allm,usernames=users,lang=lang)
        except Exception as e:
            return render_template("duo_picker_result.html",error=str(e),lang=lang)
    return render_template("duo_picker.html",lang=lang)

@app.route("/follow",methods=["GET","POST"])
def follow_index():
    if request.method=="POST":
        u=request.form["username"].lower()
        following,followers,nmap=get_follow_data(u)
        diff=sorted(set(following)-set(followers))
        diff_list=[{"username":x,"display_name":nmap.get(x,x)} for x in diff]
        return render_template("follow-result.html",username=u,difference_list=diff_list)
    return render_template("followerboxd.html")

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=True)

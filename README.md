## Blendboxd (Letterboxd Toolkit)
![Uploading image.png…]()


Türkçe/English

---

### Türkçe

Blendboxd, Letterboxd profilleriyle çalışan modern bir Flask uygulamasıdır:

- İki kullanıcının izlediği filmleri harmanlayıp şık bir poster (Watchbox) üretir
- Bir kullanıcının watchlist’inden rastgele film seçer (Randomboxd)
- Birden fazla kişinin watchlist’inden seçim yapar (Squadboxd)
- Sizin takip ettiğiniz ama sizi takip etmeyenleri listeler (Followboxd) ve profil linkleri ekler

Arayüz cam (glassmorphism) ve parallax efektli; 16:9 ve Instagram Story boyutlarında, premium görünümlü görseller çıktılar.

#### Özellikler

- Letterboxd HTML değişimlerine dayanıklı tarama (anlamsal selector’lar, anchor ve görsel alt metinleri)
- Cloudflare’a uyumlu istekler (opsiyonel `cloudscraper`), yoksa `requests` ile devam
- HTML erişilemediğinde filmler ve watchlist için RSS yedek akışı
- Temiz ve zengin poster üretimi: gradyan başlık, uyum rozeti (pill), numara “chip”leri, dönüşümlü satırlar
- İstemci tarafında çok dilli (TR/EN) görünüm

#### Gereksinimler

- Python 3.9+
- Paketler: Flask, requests, beautifulsoup4 (bs4), cloudscraper (opsiyonel)

Kurulum:

```bash
pip install -r requirements.txt
```

Ya da manuel:

```bash
pip install flask requests beautifulsoup4 cloudscraper
```

#### Ortam

- Öneriler için TMDB kullanılır; `app.py` içindeki `TMDB_API_KEY` değerini ayarlayın.

#### Çalıştırma

```bash
python app.py
# Uygulama: http://127.0.0.1:5000
```

#### Rotalar

- `/` — Blendboxd: İki kullanıcı adı gir, Watchbox + öneriler oluştur
- `/picker` — Randomboxd: Watchlist’ten rastgele seçim
- `/duo_picker` — Squadboxd: Birden fazla kullanıcı watchlist’inden seçim
- `/follow` — Followboxd: Sizi takip etmeyenleri listele (tıklanabilir profiller)

#### Tarama nasıl çalışır (kısa)

- Birden çok selector denenir (`data-film-name`, `data-film-title`, `a[href*="/film/"]`, `img[alt]`, `div.film-poster`...)
- Hem klasik `.next` hem `nav.pagination a[rel="next"]` ile sayfalama
- İlk sayfada sonuç yoksa otomatik RSS yedeği
- `cloudscraper` varsa Cloudflare engellerine karşı daha sorunsuz

#### Canvas çıktıları

- 16:9 (1920×1080) ve 1080×1920 Story
- Gradyan başlık, uyum rozeti, sütun arkaplanları, dönüşümlü satırlar, numara chip’leri
- Taşmayı önlemek için dinamik satır yüksekliği

#### Dağıtım notları

- Flask’ı çalıştırabilen her platform (Railway, Render, Fly, Heroku, VPS)
- Ağ kısıtları varsa `cloudscraper` açık kalsın

#### Sorun giderme

- Bazı profillerde “No results”: Uygulama otomatik RSS’e düşer. Hâlâ boşsa kullanıcı adını ve gizlilik ayarını kontrol edin.
- Cloudflare engellerse `cloudscraper` kurun ve yeniden başlatın.
- Öneriler için `TMDB_API_KEY` anahtarınızın geçerli olduğundan emin olun.

#### Güvenlik ve Kullanım

- Letterboxd kullanım koşullarına saygı duyun. Aşırı istekler limitlere takılabilir. Gerektiğinde cache’leyin.

#### Lisans

- Proje “olduğu gibi” sunulur, garanti verilmez. Kullanım sorumluluğu sizdedir.

#### Teşekkür

- Letterboxd verileri: letterboxd.com
- Öneri meta verileri: TMDB

---

### English

Modern Flask app that works with Letterboxd profiles to:

- Blend two users’ watched films into a clean, sharable poster (Watchbox)
- Randomly pick titles from a user’s watchlist (Randomboxd)
- Pick from multiple users’ watchlists at once (Squadboxd)
- Show who you follow that doesn’t follow you back (Followboxd) with profile links

The UI uses a glassmorphism/parallax design and exports high‑quality canvases (16:9 and Instagram Story) with a premium look.

#### Features

- Resilient scraping against Letterboxd HTML changes (semantic selectors, anchors, image alts)
- Cloudflare‑aware fetching (optional `cloudscraper`), graceful fallback to `requests`
- RSS fallback for films and watchlists when HTML is not accessible
- Modern canvas poster generator: gradient header, compatibility pill, numbered chips, alternating rows
- Multilingual UI (TR/EN) client‑side toggle

#### Requirements

- Python 3.9+
- Packages: Flask, requests, beautifulsoup4 (bs4), cloudscraper (optional)

Install:

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install flask requests beautifulsoup4 cloudscraper
```

#### Environment

- Recommendations use TMDB; set `TMDB_API_KEY` in `app.py`.

#### Run locally

```bash
python app.py
# App runs on http://127.0.0.1:5000
```

#### Key Routes

- `/` — Blendboxd: enter two usernames and generate Watchbox + recommendations
- `/picker` — Randomboxd: random picks from a user’s watchlist
- `/duo_picker` — Squadboxd: picks from multiple users’ watchlists
- `/follow` — Followboxd: users you follow who don’t follow you back (with links)

#### Scraping (brief)

- Multiple selectors attempted (`data-film-name`, `data-film-title`, `a[href*="/film/"]`, `img[alt]`, `div.film-poster`)
- Pagination via `.next` and `nav.pagination a[rel="next"]`
- RSS fallback if the first page is empty
- Optional `cloudscraper` to get past Cloudflare pages

#### Canvas exporter

- 16:9 (1920×1080) and 1080×1920 Story
- Gradient title, compatibility pill, column backgrounds, alternating rows, number chips
- Dynamic row sizing to prevent overflow

#### Deployment notes

- Any platform that runs Flask (Railway, Render, Fly, Heroku, VPS)
- If behind strict networks, keep `cloudscraper` enabled

#### Troubleshooting

- “No results” on some profiles: the app auto‑falls back to RSS. If still empty, ensure the username is correct and public.
- If Cloudflare blocks requests, install `cloudscraper` and restart.
- For recommendations, verify `TMDB_API_KEY` is valid.

#### Security & Fair Use

- Respect Letterboxd’s Terms of Use. Heavy scraping can lead to rate limits. Use responsibly and cache where appropriate.

#### License

This project is provided as‑is without warranty. Use at your own risk.

#### Credits

- Letterboxd data: letterboxd.com
- Film metadata for recommendations: TMDB



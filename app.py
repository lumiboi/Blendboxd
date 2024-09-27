def calculate_compatibility(user1_movie_count, user2_movie_count, common_movie_count):
    # İki kullanıcının toplam izlediği film sayısına göre uyum oranı hesapla
    total_movies = user1_movie_count + user2_movie_count
    
    # Eğer iki kullanıcıdan biri hiç film izlememişse uyum oranı 0 olmalı
    if total_movies == 0:
        return 0
    
    # Eğer hiç ortak film yoksa uyum oranı %0 olmalı
    if common_movie_count == 0:
        return 0

    # Uyum oranını ortak filmlerin toplam filmlere oranına göre hesapla
    compatibility_percentage = (2 * common_movie_count / total_movies) * 100

    # Eğer ortak film sayısı 5'ten fazlaysa, %50 ile başlayarak ekleme yap
    if common_movie_count > 5:
        compatibility_percentage = 50 + compatibility_percentage
    
    # Eğer %100'ü geçerse, maksimum %100 olarak ayarla
    if compatibility_percentage > 100:
        compatibility_percentage = 100

    return compatibility_percentage

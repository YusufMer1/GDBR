import requests
from datetime import datetime
from django.utils.text import slugify
from django.conf import settings
from django.core.files.base import ContentFile


from .models import Game, GameOfTheYear

def filter_main_games(games, limit=None):

    blocked_words = [
        "remastered",
        "remaster",
        "definitive edition",
        "complete edition",
        "ultimate edition",
        "game of the year edition",
        "goty edition",
        "deluxe edition",
        "gold edition",
        "special edition",
        "collection",
        "bundle",
        "expansion",
        "season pass",
        "dlc",
        "Bundle"
    ]

    filtered_games = []

    for game in games:

        name = game.get("name", "").lower()

        if any(word in name for word in blocked_words):
            continue

        filtered_games.append(game)

        if limit is not None and len(filtered_games) >= limit:
            break

    return filtered_games

def get_game_from_igdb(igdb_id):

    access_token = get_access_token()

    if not access_token:
        return None

    url = "https://api.igdb.com/v4/games"

    headers = {
        "Client-ID": settings.IGDB_CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
    }

    data = f"""
        fields
            id,
            name,
            summary,
            first_release_date,
            rating,
            cover.image_id,
            screenshots.image_id,
            videos.name,
            videos.video_id;

        where id = {igdb_id};

        limit 1;
    """

    response = requests.post(
        url,
        headers=headers,
        data=data
    )

    if response.status_code != 200:
        print("API Hatası:", response.status_code)
        print(response.text)
        return None

    result = response.json()

    if not result:
        return None

    return result[0]

def get_top_games_by_genre_from_igdb(genre_id, limit=20):

    access_token = get_access_token()

    if not access_token:
        return []

    url = "https://api.igdb.com/v4/games"

    headers = {
        "Client-ID": settings.IGDB_CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
    }

    query = f"""
        fields
            id,
            name,
            rating,
            rating_count,
            cover.image_id,
            first_release_date,
            genres.name,
            version_parent;

        where
            genres = [{genre_id}]
            & rating != null
            & rating_count > 300
            & version_parent = null;

        sort rating desc;

        limit 100;
    """

    response = requests.post(
        url,
        headers=headers,
        data=query
    )

    if response.status_code != 200:
        print("IGDB Genre Hatası:")
        print(response.status_code)
        print(response.text)
        return []

    games = response.json()

    games = filter_main_games(games)

    filtered_games = []

    for game in games:

        name = game.get("name", "").lower()

        # Racing için GTA gibi oyunları ele
        if genre_id == 10:
            blocked_racing = [
                "grand theft auto",
                "gta",
            ]

            if any(word in name for word in blocked_racing):
                continue

        filtered_games.append(game)

        if len(filtered_games) >= limit:
            break

    return filtered_games

def save_game_from_igdb(igdb_id):

    game_data = get_game_from_igdb(igdb_id)

    if not game_data:
        print("Oyun bulunamadı.")
        return None

    title = game_data.get("name")
    description = game_data.get("summary", "")
    rating = game_data.get("rating")

    release_date = None

    if game_data.get("first_release_date"):
        release_date = datetime.fromtimestamp(
            game_data["first_release_date"]
        ).date()

    base_slug = slugify(title)
    slug = base_slug

    if Game.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{igdb_id}"

    # Önce IGDB ID'sine göre kontrol et
    game = Game.objects.filter(igdb_id=igdb_id).first()

    if game:

        game.title = title
        game.description = description
        game.release_date = release_date
        game.rating = rating

        base_slug = slugify(title)
        new_slug = base_slug

        existing_slug = Game.objects.filter(
            slug=new_slug
        ).exclude(id=game.id).exists()

        if existing_slug:
            new_slug = f"{base_slug}-{igdb_id}"

        game.slug = new_slug

        game.save()

        print(
            f"{title} mevcut kayıt güncellendi."
        )

        return game


    # Eski kayıt varsa onu bul
    game = Game.objects.filter(igdb_id=igdb_id).first()

    if game:

        game.title = title
        game.description = description
        game.release_date = release_date
        game.rating = rating

        game.save()

        # Kapak yoksa indir
        cover = game_data.get("cover")

        if (
            not game.cover_image
            and cover
            and cover.get("image_id")
        ):

            image_id = cover["image_id"]

            image_url = (
                "https://images.igdb.com/"
                "igdb/image/upload/t_cover_big/"
                f"{image_id}.jpg"
            )

            image_response = requests.get(image_url)

            if image_response.status_code == 200:

                file_name = f"{slug}.jpg"

                game.cover_image.save(
                    file_name,
                    ContentFile(image_response.content),
                    save=True
                )

                print("Eksik kapak resmi kaydedildi.")

        print(f"{title} mevcut kayıt güncellendi.")

        return game

    # Yeni oyun oluştur
    game = Game.objects.create(
        title=title,
        description=description,
        release_date=release_date,
        rating=rating,
        slug=slug,
        igdb_id=igdb_id,
    )

    # --------------------------------
    # KAPAK RESMİNİ İNDİR
    # --------------------------------

    cover = game_data.get("cover")

    if cover and cover.get("image_id"):

        image_id = cover["image_id"]

        image_url = (
            f"https://images.igdb.com/"
            f"igdb/image/upload/t_cover_big/"
            f"{image_id}.jpg"
        )

        image_response = requests.get(image_url)

        if image_response.status_code == 200:

            file_name = f"{slug}.jpg"

            game.cover_image.save(
                file_name,
                ContentFile(image_response.content),
                save=True
            )

            print("Kapak resmi kaydedildi.")

        else:

            print(
                "Kapak resmi indirilemedi:",
                image_response.status_code
            )

    print(f"{title} veritabanına eklendi.")

    return game

def search_igdb_game(game_name, access_token, year=None):

    url = "https://api.igdb.com/v4/games"

    headers = {
        "Client-ID": settings.IGDB_CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
    }

    safe_name = game_name.replace('"', '\\"')

    year_filter = ""

    if year is not None:

        start_date = int(
            datetime(year, 1, 1).timestamp()
        )

        end_date = int(
            datetime(year + 1, 1, 1).timestamp()
        )

        year_filter = f"""
            & first_release_date >= {start_date}
            & first_release_date < {end_date}
        """

    query = f'''
        search "{safe_name}";

        fields
            id,
            name,
            summary,
            first_release_date,
            rating,
            cover.image_id,
            version_parent;

        where
            version_parent = null
            {year_filter};

        limit 50;
    '''

    response = requests.post(
        url,
        headers=headers,
        data=query
    )

    if response.status_code != 200:

        print("IGDB arama hatası:")
        print(response.status_code)
        print(response.text)

        return None

    results = response.json()

    # Bundle, DLC, Remaster, Edition vs. temizle
    results = filter_main_games(results)

    if not results:

        print(
            f"Uygun ana oyun bulunamadı: "
            f"{game_name} ({year})"
        )

        return None

    # Önce tam isim eşleşmesini ara
    exact_matches = [
        game
        for game in results
        if game.get("name", "").casefold()
        == game_name.casefold()
    ]

    if exact_matches:

        game = exact_matches[0]

        print(
            "Doğru oyun bulundu:",
            game["id"],
            "->",
            game["name"]
        )

        return game

    # Tam isim yoksa filtrelenmiş sonuçları göster
    print(
        f"\nTam eşleşme bulunamadı: "
        f"{game_name} ({year})"
    )

    print("Uygun sonuçlar:")

    for game in results[:10]:

        print(
            game["id"],
            "->",
            game["name"]
        )

    return None

def get_access_token():

    url = "https://id.twitch.tv/oauth2/token"

    params = {
        "client_id": settings.IGDB_CLIENT_ID,
        "client_secret": settings.IGDB_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }

    response = requests.post(url, params=params)

    if response.status_code != 200:
        print("Access token alınamadı:")
        print(response.text)
        return None

    return response.json()["access_token"]

def get_top_rated_games_from_igdb(limit=10):

    access_token = get_access_token()

    if not access_token:
        return []

    url = "https://api.igdb.com/v4/games"

    headers = {
        "Client-ID": settings.IGDB_CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
    }

    query = """
        fields
            id,
            name,
            rating,
            rating_count,
            cover.image_id,
            first_release_date,
            summary,
            version_parent;

        where
            rating != null
            & rating_count > 1000
            & version_parent = null;

        sort rating desc;

        limit 50;
    """

    response = requests.post(
        url,
        headers=headers,
        data=query
    )

    if response.status_code != 200:
        print("IGDB Hatası:")
        print(response.status_code)
        print(response.text)
        return []

    games = response.json()

    return filter_main_games(
        games,
        limit=limit
    )

def get_current_year_games_from_igdb(limit=10):

    access_token = get_access_token()

    if not access_token:
        return []

    url = "https://api.igdb.com/v4/games"

    headers = {
        "Client-ID": settings.IGDB_CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
    }

    start_date = int(datetime(2026, 1, 1).timestamp())
    end_date = int(datetime(2027, 1, 1).timestamp())

    query = f"""
        fields
            id,
            name,
            rating,
            rating_count,
            first_release_date,
            summary,
            cover.image_id,
            version_parent;

        where
            first_release_date >= {start_date}
            & first_release_date < {end_date}
            & rating != null
            & rating_count > 10
            & version_parent = null;

        sort rating desc;

        limit 50;
    """

    response = requests.post(
        url,
        headers=headers,
        data=query
    )

    if response.status_code != 200:
        print("IGDB Hatası:")
        print(response.status_code)
        print(response.text)
        return []

    games = response.json()

    games = filter_main_games(
        games,
        limit=limit
    )

    for game in games:

        cover = game.get("cover")

        if cover and cover.get("image_id"):
            game["cover_url"] = (
                "https://images.igdb.com/"
                "igdb/image/upload/t_cover_big/"
                f"{cover['image_id']}.jpg"
            )
        else:
            game["cover_url"] = None

    return games

def save_game_of_the_year(year, game_name):

    access_token = get_access_token()

    if not access_token:
        return None

    # IGDB'de oyun ismini ara
    game_data = search_igdb_game(
        game_name,
        access_token,
        year
    )

    if not game_data:
        print(
            f"{year} - {game_name} IGDB'de bulunamadı."
        )
        return None

    # IGDB'nin gerçek ID'si
    igdb_id = game_data["id"]

    print(
        f"{game_name} → IGDB ID: {igdb_id}"
    )

    # Game tablosuna kaydet
    game = save_game_from_igdb(igdb_id)

    if not game:
        return None

    # GameOfTheYear tablosuna bağla
    goty, created = GameOfTheYear.objects.update_or_create(
        year=year,
        defaults={
            "winner": game,
        }
    )

    if created:
        print(
            f"{year} - {game.title} GOTY olarak eklendi."
        )
    else:
        print(
            f"{year} - {game.title} GOTY olarak güncellendi."
        )

    return goty

def search_games_from_igdb(search, limit=20):

    access_token = get_access_token()

    if not access_token:
        return []

    url = "https://api.igdb.com/v4/games"

    headers = {
        "Client-ID": settings.IGDB_CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
    }

    safe_search = search.replace('"', '\\"')

    query = f'''
        search "{safe_search}";

        fields
            id,
            name,
            summary,
            first_release_date,
            rating,
            rating_count,
            cover.image_id,
            genres.name,
            version_parent;

        where
            version_parent = null
            & rating != null
            & rating_count >= 20
            & first_release_date != null;

        limit 100;
    '''

    response = requests.post(
        url,
        headers=headers,
        data=query
    )

    if response.status_code != 200:

        print("IGDB Search Hatası:")
        print(response.status_code)
        print(response.text)

        return []

    results = response.json()


    # =========================
    # DLC / BUNDLE / REMASTER
    # =========================

    results = filter_main_games(
        results
    )


    # =========================
    # AYNI İSİMLİ OYUNLARI TEKLE
    # =========================

    unique_games = {}

    for game in results:

        normalized_name = (
            game
            .get("name", "")
            .strip()
            .casefold()
        )

        if not normalized_name:
            continue

        if normalized_name not in unique_games:

            unique_games[
                normalized_name
            ] = game

            continue


        current_game = unique_games[
            normalized_name
        ]

        new_date = game.get(
            "first_release_date"
        )

        current_date = current_game.get(
            "first_release_date"
        )


        # Aynı isimdeyse en eski sürümü tut
        if (
            new_date
            and current_date
            and new_date < current_date
        ):

            unique_games[
                normalized_name
            ] = game


    results = list(
        unique_games.values()
    )


    # =========================
    # TARİHLERİ ÇEVİR
    # =========================

    for game in results:

        timestamp = game.get(
            "first_release_date"
        )

        if timestamp:

            game["release_date"] = (
                datetime.fromtimestamp(
                    timestamp
                )
            )

        else:

            game["release_date"] = None


    # =========================
    # SONUÇLARI SIRALA
    # =========================

    search_lower = (
        search
        .strip()
        .casefold()
    )


    def game_score(game):

        name = (
            game
            .get("name", "")
            .casefold()
        )

        rating = (
            game.get("rating")
            or 0
        )

        rating_count = (
            game.get("rating_count")
            or 0
        )


        # Tam isim eşleşmesi
        exact_bonus = (
            10000
            if name == search_lower
            else 0
        )


        # Aranan kelimeyle başlayan oyun
        start_bonus = (
            500
            if name.startswith(
                search_lower
            )
            else 0
        )


        # Oy sayısı yüksek olanlara
        # ufak popülerlik avantajı
        popularity_bonus = min(
            rating_count,
            5000
        ) / 100


        return (
            exact_bonus
            + start_bonus
            + rating
            + popularity_bonus
        )


    results.sort(
        key=game_score,
        reverse=True
    )


    return results[:limit]

def import_games_by_name(search_name, limit=100):

    access_token = get_access_token()

    if not access_token:
        print("Access token alınamadı.")
        return

    url = "https://api.igdb.com/v4/games"

    headers = {
        "Client-ID": settings.IGDB_CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
    }

    query = f'''
        search "{search_name}";

        fields
            id,
            name,
            first_release_date,
            rating,
            cover.image_id;

        limit {limit};
    '''

    response = requests.post(
        url,
        headers=headers,
        data=query
    )

    if response.status_code != 200:
        print("IGDB Hatası:", response.status_code)
        print(response.text)
        return

    results = response.json()

    print(f"{len(results)} oyun bulundu.")

    for game_data in results:

        print(
            game_data["id"],
            "->",
            game_data["name"]
        )

def get_top_games_by_year_from_igdb(year, limit=5):


    access_token = get_access_token()

    if not access_token:
        return []

    url = "https://api.igdb.com/v4/games"

    headers = {
        "Client-ID": settings.IGDB_CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
    }

    start_date = int(datetime(year, 1, 1).timestamp())
    end_date = int(datetime(year + 1, 1, 1).timestamp())

    query = f"""
        fields
            id,
            name,
            rating,
            rating_count,
            first_release_date,
            cover.image_id,
            summary,
            version_parent;

        where
            first_release_date >= {start_date}
            & first_release_date < {end_date}
            & rating != null
            & rating_count > 50
            & version_parent = null;

        sort rating desc;

        limit 50;
    """

    response = requests.post(
        url,
        headers=headers,
        data=query
    )

    if response.status_code != 200:
        print(f"{year} IGDB Hatası:")
        print(response.status_code)
        print(response.text)
        return []

    games = response.json()

    # Daha önce yaptığımız remaster / edition filtresi
    games = filter_main_games(
        games,
        limit=limit
    )

    return games

def check_goty_release_years():


    for goty in GameOfTheYear.objects.all().order_by("year"):

        games = [goty.winner] + list(goty.nominees.all())

        for game in games:

            if not game.release_date:
                print(
                    f"{goty.year} | {game.title} | Çıkış tarihi YOK"
                )

            elif game.release_date.year != goty.year:
                print(
                    f"{goty.year} | "
                    f"{game.title} | "
                    f"{game.release_date.year} ❌ | "
                    f"IGDB ID: {game.igdb_id}"
                )

def search_igdb_game_by_year(game_name, year):


    access_token = get_access_token()

    if not access_token:
        return None

    url = "https://api.igdb.com/v4/games"

    headers = {
        "Client-ID": settings.IGDB_CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
    }

    start_date = int(
        datetime(year, 1, 1).timestamp()
    )

    end_date = int(
        datetime(year + 1, 1, 1).timestamp()
    )

    query = f'''
        search "{game_name}";

        fields
            id,
            name,
            first_release_date,
            rating,
            cover.image_id,
            version_parent;

        where
            first_release_date >= {start_date}
            & first_release_date < {end_date}
            & version_parent = null;

        limit 20;
    '''

    response = requests.post(
        url,
        headers=headers,
        data=query
    )

    if response.status_code != 200:
        print("IGDB Hatası:")
        print(response.status_code)
        print(response.text)
        return None

    results = response.json()

    if not results:
        print(
            f"{game_name} ({year}) bulunamadı."
        )
        return None

    print(f"\n{game_name} ({year}) sonuçları:\n")

    for game in results:
        print(
            game["id"],
            "->",
            game["name"]
        )

    return results


def find_exact_igdb_game(game_name, release_year):

    access_token = get_access_token()

    if not access_token:
        print("Access token alınamadı.")
        return None

    url = "https://api.igdb.com/v4/games"

    headers = {
        "Client-ID": settings.IGDB_CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
    }

    start_date = int(
        datetime(release_year, 1, 1).timestamp()
    )

    end_date = int(
        datetime(release_year + 1, 1, 1).timestamp()
    )

    safe_name = game_name.replace('"', '\\"')

    query = f'''
        search "{safe_name}";

        fields
            id,
            name,
            first_release_date,
            rating,
            cover.image_id,
            version_parent;

        where
            first_release_date >= {start_date}
            & first_release_date < {end_date}
            & version_parent = null;

        limit 50;
    '''

    response = requests.post(
        url,
        headers=headers,
        data=query
    )

    if response.status_code != 200:
        print("IGDB Hatası:")
        print(response.status_code)
        print(response.text)
        return None

    results = response.json()

    # Tam isim eşleşmesini bul
    exact_results = [
        game
        for game in results
        if game.get("name", "").casefold() == game_name.casefold()
    ]

    if len(exact_results) == 1:

        game = exact_results[0]

        print(
            f"Bulundu: {game['id']} -> {game['name']}"
        )

        return game

    if len(exact_results) > 1:

        print(
            f"\nBirden fazla tam eşleşme bulundu: "
            f"{game_name} ({release_year})"
        )

        for game in exact_results:
            print(
                game["id"],
                "->",
                game["name"]
            )

        return None

    print(
        f"\nTam eşleşme bulunamadı: "
        f"{game_name} ({release_year})"
    )

    print("Yakın sonuçlar:")

    for game in results[:10]:
        print(
            game["id"],
            "->",
            game["name"]
        )

    return None

def replace_wrong_goty_game(
    goty_year,
    wrong_title,
    correct_title,
    correct_release_year
):

    print("\n" + "=" * 70)

    print(
        f"{goty_year}: "
        f"{wrong_title} -> {correct_title}"
    )

    goty = GameOfTheYear.objects.get(
        year=goty_year
    )

    wrong_game = Game.objects.filter(
        title=wrong_title
    ).first()

    if not wrong_game:

        print(
            f"Yanlış kayıt bulunamadı: {wrong_title}"
        )

        return None

    # IGDB'den doğru oyunu bul
    game_data = find_exact_igdb_game(
        correct_title,
        correct_release_year
    )

    if not game_data:

        print(
            "Doğru IGDB kaydı kesin olarak "
            "belirlenemedi. Değişiklik yapılmadı."
        )

        return None

    # Doğru oyunu Game tablosuna kaydet
    correct_game = save_game_from_igdb(
        game_data["id"]
    )

    if not correct_game:

        print("Oyun veritabanına kaydedilemedi.")
        return None


    # =========================
    # WINNER MI?
    # =========================

    if goty.winner_id == wrong_game.id:

        goty.winner = correct_game
        goty.save()

        print(
            f"WINNER değiştirildi: "
            f"{wrong_game.title} -> "
            f"{correct_game.title}"
        )


    # =========================
    # NOMINEE MI?
    # =========================

    if goty.nominees.filter(
        id=wrong_game.id
    ).exists():

        goty.nominees.remove(
            wrong_game
        )

        goty.nominees.add(
            correct_game
        )

        print(
            f"NOMINEE değiştirildi: "
            f"{wrong_game.title} -> "
            f"{correct_game.title}"
        )

    return correct_game

def search_game_suggestions_from_igdb(
    search,
    limit=6
):

    search = search.strip()

    if len(search) < 2:
        return []


    access_token = get_access_token()

    if not access_token:
        return []


    url = "https://api.igdb.com/v4/games"


    headers = {
        "Client-ID":
            settings.IGDB_CLIENT_ID,

        "Authorization":
            f"Bearer {access_token}",
    }


    safe_search = (
        search
        .replace(
            '"',
            '\\"'
        )
    )


    # Autocomplete için mümkün olduğunca
    # hafif bir query kullanıyoruz.
    query = f'''
        search "{safe_search}";

        fields
            id,
            name,
            first_release_date,
            cover.image_id,
            version_parent;

        where
            version_parent = null;

        limit 20;
    '''


    try:

        response = requests.post(
            url,
            headers=headers,
            data=query,
            timeout=5
        )


        if response.status_code != 200:

            print(
                "IGDB Suggestion Error:",
                response.status_code,
                response.text
            )

            return []


        games = response.json()


    except requests.RequestException as error:

        print(
            "IGDB Suggestion Request Error:",
            error
        )

        return []


    # =====================================================
    # REMOVE INVALID RESULTS
    # =====================================================

    clean_games = []

    seen_names = set()


    for game in games:

        game_id = game.get(
            "id"
        )

        name = (
            game
            .get(
                "name",
                ""
            )
            .strip()
        )


        if not game_id or not name:
            continue


        normalized_name = (
            name.casefold()
        )


        if normalized_name in seen_names:
            continue


        seen_names.add(
            normalized_name
        )


        clean_games.append(
            game
        )


    # =====================================================
    # SORT RESULTS
    # =====================================================

    search_lower = (
        search.casefold()
    )


    def suggestion_score(game):

        name = (
            game
            .get(
                "name",
                ""
            )
            .casefold()
        )


        # Tam eşleşme en üstte
        if name == search_lower:
            return 10000


        # Aranan ifadeyle başlayanlar
        if name.startswith(
            search_lower
        ):
            return 5000


        # Kelimelerden biri başlıyorsa
        words = (
            name
            .replace(
                ":",
                " "
            )
            .replace(
                "-",
                " "
            )
            .split()
        )


        if any(
            word.startswith(
                search_lower
            )
            for word in words
        ):
            return 2500


        # İsmin herhangi bir yerindeyse
        if search_lower in name:
            return 1000


        return 0


    clean_games.sort(
        key=suggestion_score,
        reverse=True
    )


    return clean_games[:limit]
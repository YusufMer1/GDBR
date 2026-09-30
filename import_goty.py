import os
import sys
import requests
import django


# -----------------------------------------
# DJANGO AYARLARI
# -----------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings"
)

django.setup()


from games.models import Game, GameOfTheYear
from django.utils.text import slugify


# -----------------------------------------
# IGDB
# -----------------------------------------

from django.conf import settings


CLIENT_ID = settings.IGDB_CLIENT_ID
CLIENT_SECRET = settings.IGDB_CLIENT_SECRET


# -----------------------------------------
# GOTY VERİLERİ
# -----------------------------------------

GOTY_DATA = {

    2008: {
        "winner": "Grand Theft Auto IV",
        "nominees": [
            "LittleBigPlanet",
            "Fallout 3",
            "Gears of War 2",
            "Metal Gear Solid 4: Guns of the Patriots",
        ],
    },

    2009: {
        "winner": "Uncharted 2: Among Thieves",
        "nominees": [
            "Assassin's Creed II",
            "Batman: Arkham Asylum",
            "Call of Duty: Modern Warfare 2",
            "Left 4 Dead 2",
        ],
    },

    2010: {
        "winner": "Red Dead Redemption",
        "nominees": [
            "Call of Duty: Black Ops",
            "God of War III",
            "Halo: Reach",
            "Mass Effect 2",
        ],
    },

    2011: {
        "winner": "The Elder Scrolls V: Skyrim",
        "nominees": [
            "Batman: Arkham City",
            "The Legend of Zelda: Skyward Sword",
            "Portal 2",
            "Uncharted 3: Drake's Deception",
        ],
    },

    2012: {
        "winner": "The Walking Dead",
        "nominees": [
            "Assassin's Creed III",
            "Dishonored",
            "Journey",
            "Mass Effect 3",
        ],
    },

    2013: {
        "winner": "Grand Theft Auto V",
        "nominees": [
            "BioShock Infinite",
            "The Last of Us",
            "Super Mario 3D World",
            "Tomb Raider",
        ],
    },

    2014: {
        "winner": "Dragon Age: Inquisition",
        "nominees": [
            "Bayonetta 2",
            "Dark Souls II",
            "Hearthstone",
            "Middle-earth: Shadow of Mordor",
        ],
    },

    2015: {
        "winner": "The Witcher 3: Wild Hunt",
        "nominees": [
            "Bloodborne",
            "Fallout 4",
            "Metal Gear Solid V: The Phantom Pain",
            "Super Mario Maker",
        ],
    },

    2016: {
        "winner": "Overwatch",
        "nominees": [
            "Doom",
            "Inside",
            "Titanfall 2",
            "Uncharted 4: A Thief's End",
        ],
    },

    2017: {
        "winner": "The Legend of Zelda: Breath of the Wild",
        "nominees": [
            "Horizon Zero Dawn",
            "Persona 5",
            "PlayerUnknown's Battlegrounds",
            "Super Mario Odyssey",
        ],
    },

    2018: {
        "winner": "God of War",
        "nominees": [
            "Assassin's Creed Odyssey",
            "Celeste",
            "Marvel's Spider-Man",
            "Monster Hunter: World",
            "Red Dead Redemption 2",
        ],
    },

    2019: {
        "winner": "Sekiro: Shadows Die Twice",
        "nominees": [
            "Control",
            "Death Stranding",
            "Resident Evil 2",
            "Super Smash Bros. Ultimate",
            "The Outer Worlds",
        ],
    },

    2020: {
        "winner": "The Last of Us Part II",
        "nominees": [
            "Animal Crossing: New Horizons",
            "Doom Eternal",
            "Final Fantasy VII Remake",
            "Ghost of Tsushima",
            "Hades",
        ],
    },

    2021: {
        "winner": "It Takes Two",
        "nominees": [
            "Deathloop",
            "Metroid Dread",
            "Psychonauts 2",
            "Ratchet & Clank: Rift Apart",
            "Resident Evil Village",
        ],
    },

    2022: {
        "winner": "Elden Ring",
        "nominees": [
            "A Plague Tale: Requiem",
            "God of War Ragnarök",
            "Horizon Forbidden West",
            "Stray",
            "Xenoblade Chronicles 3",
        ],
    },

    2023: {
        "winner": "Baldur's Gate 3",
        "nominees": [
            "Alan Wake 2",
            "The Legend of Zelda: Tears of the Kingdom",
            "Marvel's Spider-Man 2",
            "Resident Evil 4",
            "Super Mario Bros. Wonder",
        ],
    },

    2024: {
        "winner": "Astro Bot",
        "nominees": [
            "Balatro",
            "Black Myth: Wukong",
            "Elden Ring: Shadow of the Erdtree",
            "Final Fantasy VII Rebirth",
            "Metaphor: ReFantazio",
        ],
    },

    2025: {
        "winner": "Clair Obscur: Expedition 33",
        "nominees": [
            "Death Stranding 2: On the Beach",
            "Donkey Kong Bananza",
            "Hades II",
            "Hollow Knight: Silksong",
            "Kingdom Come: Deliverance II",
        ],
    },
}


# -----------------------------------------
# IGDB TOKEN
# -----------------------------------------

def get_access_token():

    url = "https://id.twitch.tv/oauth2/token"

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
    }

    response = requests.post(url, data=data)

    if response.status_code != 200:

        print("Token alınamadı:")
        print(response.text)

        return None

    return response.json()["access_token"]


# -----------------------------------------
# IGDB'DEN OYUN ARA
# -----------------------------------------

def search_igdb_game(name, access_token):

    url = "https://api.igdb.com/v4/games"

    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
    }

    query = f'''
        search "{name}";
        fields
            id,
            name,
            summary,
            rating,
            first_release_date,
            cover.image_id;
        limit 5;
    '''

    response = requests.post(
        url,
        headers=headers,
        data=query
    )

    if response.status_code != 200:

        print("IGDB Hatası:", response.status_code)
        print(response.text)

        return None

    results = response.json()

    if not results:

        print("IGDB'de bulunamadı:", name)

        return None

    # En basit durumda ilk sonucu kullanıyoruz
    return results[0]


# -----------------------------------------
# GAME TABLOSUNA EKLE
# -----------------------------------------

def get_or_create_game(name, access_token):

    # Önce kendi veritabanımızda ara
    game = Game.objects.filter(
        title__iexact=name
    ).first()

    if game:

        print("Zaten mevcut:", game.title)

        return game


    # IGDB'de ara
    data = search_igdb_game(
        name,
        access_token
    )

    if not data:

        return None


    title = data.get("name")

    summary = data.get(
        "summary",
        ""
    )

    rating = data.get(
        "rating"
    )


    release_date = None

    if data.get("first_release_date"):

        from datetime import datetime

        release_date = datetime.fromtimestamp(
            data["first_release_date"]
        ).date()


    slug = slugify(title)


    # Slug çakışması
    existing = Game.objects.filter(
        slug=slug
    ).first()

    if existing:

        return existing


    game = Game.objects.create(

        title=title,

        description=summary,

        rating=rating,

        release_date=release_date,

        slug=slug,

        igdb_id=data["id"],
    )


    # -----------------------------------------
    # COVER
    # -----------------------------------------

    cover = data.get("cover")

    if cover and cover.get("image_id"):

        image_id = cover["image_id"]

        image_url = (
            "https://images.igdb.com/"
            "igdb/image/upload/t_cover_big/"
            f"{image_id}.jpg"
        )

        image_response = requests.get(
            image_url
        )

        if image_response.status_code == 200:

            from django.core.files.base import ContentFile

            file_name = f"{slug}.jpg"

            game.cover_image.save(
                file_name,
                ContentFile(
                    image_response.content
                ),
                save=True
            )


    print("EKLENDİ:", game.title)

    return game


# -----------------------------------------
# GOTY OLUŞTUR
# -----------------------------------------

def import_goty():

    access_token = get_access_token()

    if not access_token:

        return


    for year, data in GOTY_DATA.items():

        print()
        print("=" * 50)
        print(year)
        print("=" * 50)


        # WINNER
        winner = get_or_create_game(
            data["winner"],
            access_token
        )

        if not winner:

            print(
                "Winner bulunamadı:",
                data["winner"]
            )

            continue


        # GOTY kaydı
        goty, created = GameOfTheYear.objects.get_or_create(

            year=year,

            defaults={
                "winner": winner
            }
        )


        if not created:

            goty.winner = winner
            goty.save()


        # NOMINEES
        for nominee_name in data["nominees"]:

            nominee = get_or_create_game(
                nominee_name,
                access_token
            )

            if nominee:

                goty.nominees.add(
                    nominee
                )


        print(
            f"{year} GOTY tamamlandı."
        )


if __name__ == "__main__":

    import_goty()
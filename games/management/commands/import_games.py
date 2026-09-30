from django.core.management.base import BaseCommand
from games.models import Game, Genre

import requests
from django.utils.text import slugify
from datetime import datetime

from games.api import CLIENT_ID, ACCESS_TOKEN


class Command(BaseCommand):

    help = "IGDB'den popüler oyunları getirir ve veritabanına kaydeder."

    def handle(self, *args, **kwargs):

        url = "https://api.igdb.com/v4/games"

        headers = {
            "Client-ID": CLIENT_ID,
            "Authorization": f"Bearer {ACCESS_TOKEN}",
        }

        query = """
        fields
            id,
            name,
            summary,
            first_release_date,
            rating,
            cover.image_id,
            genres.name;
        sort popularity desc;
        limit 100;
        """

        response = requests.post(
            url,
            headers=headers,
            data=query
        )

        if response.status_code != 200:
            self.stdout.write(
                self.style.ERROR(
                    f"IGDB API Hatası: {response.status_code}"
                )
            )
            self.stdout.write(response.text)
            return

        games = response.json()

        self.stdout.write(
            self.style.SUCCESS(
                f"{len(games)} oyun IGDB'den alındı."
            )
        )

        for data in games:

            igdb_id = data["id"]
            name = data.get("name")

            if not name:
                continue

            # --------------------------------
            # ÇIKIŞ TARİHİ
            # --------------------------------

            release_date = None

            if data.get("first_release_date"):
                release_date = datetime.fromtimestamp(
                    data["first_release_date"]
                ).date()

            # Tarihi olmayan oyunları atla
            if not release_date:
                self.stdout.write(
                    self.style.WARNING(
                        f"{name} atlandı: çıkış tarihi yok."
                    )
                )
                continue

            # --------------------------------
            # GAME OLUŞTUR / BUL
            # --------------------------------

            slug = slugify(name)

            existing_game = Game.objects.filter(
                slug=slug
            ).first()

            if existing_game:
                game = existing_game

                # Daha önce eklenmiş oyunlara IGDB ID'sini ekle
                if game.igdb_id is None:
                    game.igdb_id = igdb_id
                    game.save(update_fields=["igdb_id"])

                self.stdout.write(
                    f"Zaten mevcut: {name}"
                )

            else:

                # Aynı isimde slug varsa IGDB ID ekle
                if Game.objects.filter(slug=slug).exists():
                    slug = f"{slug}-{igdb_id}"

                game = Game.objects.create(
                    title=name,
                    description=data.get("summary") or "Açıklama bulunamadı.",
                    release_date=release_date,
                    rating=data.get("rating"),
                    slug=slug,
                    igdb_id=igdb_id,
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Eklendi: {name}"
                    )
                )

            # --------------------------------
            # TÜRLER
            # --------------------------------

            for genre_data in data.get("genres", []):

                genre_name = genre_data.get("name")

                if not genre_name:
                    continue

                genre_slug = slugify(genre_name)

                genre, created = Genre.objects.get_or_create(
                    slug=genre_slug,
                    defaults={
                        "name": genre_name
                    }
                )

                game.genres.add(genre)

            # --------------------------------
            # KAPAK RESMİ
            # --------------------------------

            cover = data.get("cover")

            if cover:

                image_id = cover.get("image_id")

                if image_id:

                    image_url = (
                        f"https://images.igdb.com/"
                        f"igdb/image/upload/t_cover_big/"
                        f"{image_id}.jpg"
                    )

                    image_response = requests.get(
                        image_url,
                        timeout=15
                    )

                    if image_response.status_code == 200:

                        file_name = f"{slug}.jpg"

                        from django.core.files.base import ContentFile

                        game.cover_image.save(
                            file_name,
                            ContentFile(image_response.content),
                            save=True
                        )

                        self.stdout.write(
                            f"  Kapak kaydedildi: {name}"
                        )

                    else:

                        self.stdout.write(
                            self.style.WARNING(
                                f"  Kapak indirilemedi: {name}"
                            )
                        )

            # --------------------------------
            # GAME KAYDET
            # --------------------------------

            game.save()

        self.stdout.write(
            self.style.SUCCESS(
                "İşlem tamamlandı."
            )
        )
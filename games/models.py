from django.db import models
from django.utils.text import slugify
from django.conf import settings


class Genre(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True
    )
    slug = models.SlugField(unique=True, blank=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name



class Game(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField()
    cover_image = models.ImageField(upload_to='games/', null=True, max_length=255, blank=True)
    release_date = models.DateField(null=True, blank=True)
    genres = models.ManyToManyField(Genre, blank=True)
    slug = models.SlugField(
        max_length=200,
        unique=True
    )
    rating = models.FloatField(null=True, blank=True)
    igdb_id = models.IntegerField(
        unique=True,
        null=True,
        blank=True
    )
    igdb_id = models.IntegerField(
        unique=True,
        null=True,
        blank=True
    )
    

    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Comment(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey('account.Profile',on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class GameOfTheYear(models.Model):

    year = models.IntegerField()

    winner = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name="goty_wins"
    )

    nominees = models.ManyToManyField(
        Game,
        blank=True,
        related_name="goty_nominees"
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    class Meta:
        ordering = ["-year"]

    def __str__(self):
        return f"{self.year} - {self.winner.title}"

class GameSeries(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)

    description = models.TextField(blank=True)

    cover_image = models.ImageField(
        upload_to="series/",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.name


class GameSeriesEntry(models.Model):
    series = models.ForeignKey(
        GameSeries,
        on_delete=models.CASCADE,
        related_name="entries"
    )

    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE
    )

    play_order = models.PositiveIntegerField()

    class Meta:
        ordering = ["play_order"]

    def __str__(self):
        return f"{self.series.name} - {self.game.title}"


class GameLibrary(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="game_libraries"
    )

    name = models.CharField(
        max_length=100
    )

    description = models.TextField(
        blank=True
    )

    is_public = models.BooleanField(
        default=False
    )

    games = models.ManyToManyField(
        "Game",
        related_name="libraries",
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # Ana sayfada gösterilecek özel library
    is_featured = models.BooleanField(
        default=False
    )

    class Meta:
        ordering = ["-created_at"]


    def __str__(self):
        return f"{self.name} - {self.user.username}"


class GameLibraryView(models.Model):

    library = models.ForeignKey(
        GameLibrary,
        on_delete=models.CASCADE,
        related_name="views"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="library_views"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )


    class Meta:

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "library",
                    "user"
                ],
                name="unique_library_view_per_user"
            )

        ]


    def __str__(self):

        return (
            f"{self.user.username} -> "
            f"{self.library.name}"
        )
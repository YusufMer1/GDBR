from django.contrib import admin
from .models import Game, GameOfTheYear, Genre, GameSeries, GameSeriesEntry, GameLibrary


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    list_display = ("title", "slug")
    search_fields = ("title",)

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "slug")


@admin.register(GameOfTheYear)
class GameOfTheYearAdmin(admin.ModelAdmin):
    list_display = ("year", "winner")
    ordering = ("-year",)
    autocomplete_fields = ("winner", "nominees")

class GameSeriesEntryInline(admin.TabularInline):
    model = GameSeriesEntry
    extra = 1
    autocomplete_fields = ["game"]
    ordering = ["play_order"]


@admin.register(GameSeries)
class GameSeriesAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
    )

    search_fields = (
        "name",
    )

    prepopulated_fields = {
        "slug": ("name",)
    }

    inlines = [
        GameSeriesEntryInline
    ]


@admin.register(GameSeriesEntry)
class GameSeriesEntryAdmin(admin.ModelAdmin):
    list_display = (
        "series",
        "game",
        "play_order",
    )

    list_filter = (
        "series",
    )

    search_fields = (
        "game__title",
        "series__name",
    )

    autocomplete_fields = [
        "game",
    ]

    ordering = (
        "series",
        "play_order",
    )

@admin.register(GameLibrary)
class GameLibraryAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "user",
        "game_count",
        "is_public",
        "is_featured",
        "total_views",
        "created_at",
    )

    list_filter = (
        "is_public",
        "is_featured",
        "created_at",
    )

    search_fields = (
        "name",
        "user__username",
        "user__email",
    )

    filter_horizontal = (
        "games",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "total_views",
    )

    fieldsets = (

        (
            "Library Information",
            {
                "fields": (
                    "user",
                    "name",
                    "description",
                )
            }
        ),

        (
            "Games",
            {
                "fields": (
                    "games",
                )
            }
        ),

        (
            "Visibility",
            {
                "fields": (
                    "is_public",
                    "is_featured",
                )
            }
        ),

        (
            "Statistics",
            {
                "fields": (
                    "total_views",
                    "created_at",
                    "updated_at",
                )
            }
        ),

    )

    def game_count(self, obj):

        return obj.games.count()

    game_count.short_description = "Games"


    def total_views(self, obj):

        return obj.views.count()

    total_views.short_description = "Views"
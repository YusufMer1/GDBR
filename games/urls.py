from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("games/<slug:slug>/", views.game_detail, name="game_detail"),
    path(
        "search/",
        views.search_games,
        name="search_games"
    ),
    path(
         "search/suggestions/",
         views.search_suggestions,
        name="search_suggestions"
    ),

    path(
        "game/igdb/<int:igdb_id>/",
        views.game_detail_igdb,
        name="game_detail_igdb"
    ),
    path(
        "game-of-the-year/",
        views.game_of_the_year,
        name="game_of_the_year"
    ),

    path(
        "series/",
        views.game_series,
        name="game_series"
    ),

    path(
        "series/<slug:slug>/",
        views.game_series_detail,
        name="game_series_detail"
    ),
    path(
        "genre-games/<int:genre_id>/",
        views.genre_games_ajax,
        name="genre_games_ajax"
    ),
    path(
        "about/",
        views.about,
        name="about"
    ),
    path(
        "2026-games/",
        views.games_2026,
        name="games_2026"
    ),
    path(
        "contact/",
        views.contact,
        name="contact"
    ),
    path(
        "libraries/",
        views.my_libraries,
        name="my_libraries"
    ),

    path(
        "libraries/create/",
        views.create_library,
        name="create_library"
    ),

    path(
        "libraries/<int:library_id>/",
        views.library_detail,
        name="library_detail"
    ),

    path(
        "libraries/<int:library_id>/delete/",
        views.delete_library,
        name="delete_library"
    ),

    path(
        "libraries/add-game/",
        views.add_game_to_library,
        name="add_game_to_library"
    ),

    path(
        "libraries/<int:library_id>/remove/<int:game_id>/",
        views.remove_game_from_library,
        name="remove_game_from_library"
    ),

    path(
        "ai/chat/",
        views.ai_chat,
        name="ai_chat"
    ),
    path(
        "game/<slug:slug>/media/",
        views.game_media,
        name="game_media"
    ),
    
]

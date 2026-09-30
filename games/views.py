from django.http import JsonResponse
from django.shortcuts import (
    render,
    get_object_or_404,
    redirect,
)

import time
import json
from .ai import ask_gdbr_ai

from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import F, Count
from django.contrib.auth import get_user_model
from datetime import datetime

from django.core.cache import cache


from .models import (
    Game,
    GameOfTheYear,
    Genre,
    GameSeries,
    GameLibrary,
    GameLibraryView,
)

from .api import (
    search_games_from_igdb,
    save_game_from_igdb,
    get_top_rated_games_from_igdb,
    get_current_year_games_from_igdb,
    get_game_from_igdb,
    get_top_games_by_genre_from_igdb,
    search_game_suggestions_from_igdb,
)


# =========================================================
# HOME
# =========================================================

def home(request):

    

    search = request.GET.get(
        "q",
        ""
    ).strip()

    genre_slug = request.GET.get(
        "genre",
        ""
    ).strip()

    
    genres = (
        Genre.objects
        .all()
        .order_by("name")
    )

    

    
    # Local database games
    games = Game.objects.all()

    


    # IGDB sections
    trending_games = cache.get(
        "home_trending_games"
    )

    if trending_games is None:

        trending_games = get_top_rated_games_from_igdb()

        cache.set(
            "home_trending_games",
            trending_games,
            60 * 15
        )

    current_year_games = cache.get(
        "home_current_year_games"
    )

    if current_year_games is None:

        current_year_games = get_current_year_games_from_igdb()

        cache.set(
            "home_current_year_games",
            current_year_games,
            60 * 30
        )



    # Popular Series
    popular_series = (
        GameSeries.objects
        .all()[:6]
    )


    # Default genre: Action
    default_genre_id = 4

    

    genre_games = cache.get(
        "home_genres"
    )

    if genre_games is None:

        genre_games = get_top_games_by_genre_from_igdb(default_genre_id, limit=20)

        cache.set(
            "home_genres",
            genre_games,
            60 * 60
        )

   

    featured_libraries = (
        GameLibrary.objects
        .filter(
            is_public=True,
            is_featured=True
        )
        .select_related(
            "user"
        )
        .prefetch_related(
            "games"
        )
        .annotate(
            total_views=Count(
                "views"
            )
        )
        .order_by(
            "-total_views",
            "-created_at"
        )[:4]
    )


    # =====================================================
    # FAVORITE GAMES
    # =====================================================

    favouritegames_slugs = [

        "red-dead-redemption-2",
        "uncharted-4-a-thiefs-end",
        "grand-theft-auto-v",
        "assassins-creed-ii",
        "god-of-war",
        "marvels-spider-man-2",
        "resident-evil-4",
        "elden-ring-nightreign",
        "black-myth-wukong",
        "the-last-of-us-part-ii",
        "baldurs-gate-iii",
        "bioshock-infinite",
        "horizon-zero-dawn",

    ]


    favouritegames = list(

        Game.objects.filter(
            slug__in=favouritegames_slugs
        )

    )


    # =====================================================
    # FILTERS
    # =====================================================

    if genre_slug:

        games = games.filter(
            genres__slug=genre_slug
        )


    if search:

        games = games.filter(
            title__icontains=search
        )


    # =====================================================
    # PAGINATION
    # =====================================================

    paginator = Paginator(
        games,
        20
    )

    page_number = request.GET.get(
        "page"
    )

    games = paginator.get_page(
        page_number
    )


    context = {

        "games": games,

        "genres": genres,

        "selected_genre": genre_slug,

        "search_query": search,

        "trending_games": trending_games,

        "current_year_games": current_year_games,

        "favouritegames": favouritegames,

        "popular_series": popular_series,

        "genre_games": genre_games,

        "featured_libraries": featured_libraries,

    }

    

    

    return render(
        request,
        "game/home.html",
        context
    )


# =========================================================
# GENRE AJAX
# =========================================================

def genre_games_ajax(
    request,
    genre_id
):

    games = (
        get_top_games_by_genre_from_igdb(
            genre_id,
            limit=20
        )
    )


    return render(
        request,
        "game/genre_games_cards.html",
        {
            "genre_games": games
        }
    )




def game_media(request, slug):

    game = get_object_or_404(
        Game,
        slug=slug
    )


    if not game.igdb_id:

        return JsonResponse({
            "screenshots": [],
            "videos": [],
        })


    cache_key = (
        f"game_media_{game.igdb_id}"
    )


    media = cache.get(
        cache_key
    )


    if media is None:

        igdb_data = get_game_from_igdb(
            game.igdb_id
        )


        media = {
            "screenshots":
                igdb_data.get(
                    "screenshots",
                    []
                )
                if igdb_data
                else [],

            "videos":
                igdb_data.get(
                    "videos",
                    []
                )
                if igdb_data
                else [],
        }


        cache.set(
            cache_key,
            media,
            60 * 60 * 6
        )


    return JsonResponse(
        media
    )

# =========================================================
# GAME DETAIL
# =========================================================

def game_detail(request, slug):

    game = get_object_or_404(
        Game,
        slug=slug
    )


    comments = (
        game.comments
        .all()
        .order_by("-created_at")
    )


    # =====================================================
    # USER LIBRARIES
    # =====================================================

    library_options = []

    if request.user.is_authenticated:

        libraries = (
            GameLibrary.objects
            .filter(user=request.user)
            .prefetch_related("games")
            .order_by("-created_at")
        )

        libraries = list(libraries)

        for library in libraries:

            contains_game = any(
                library_game.id == game.id
                for library_game in library.games.all()
            )

            library_options.append({
                "library": library,
                "contains_game": contains_game,
            })


    # =====================================================
    # COMMENTS POST
    # =====================================================

    if (
        request.user.is_authenticated
        and request.method == "POST"
    ):

        content = request.POST.get(
            "content",
            ""
        ).strip()

        if content:

            game.comments.create(
                user=request.user,
                content=content
            )

        return redirect(
            "game_detail",
            slug=slug
        )


    return render(
        request,
        "game_detail.html",
        {
            "game": game,
            "comments": comments,
            "library_options": library_options,
        }
    )

# =========================================================
# GAME OF THE YEAR
# =========================================================

def game_of_the_year(request):

    goty_games = (

        GameOfTheYear.objects
        .filter(
            year__gte=2008,
            year__lte=2025
        )
        .select_related(
            "winner"
        )
        .prefetch_related(
            "nominees"
        )
        .order_by(
            "-year"
        )

    )


    return render(
        request,
        "game/goty.html",
        {
            "goty_games": goty_games
        }
    )


# =========================================================
# SEARCH
# =========================================================
User = get_user_model()

def search_games(request):

    search_query = request.GET.get(
        "q",
        ""
    ).strip()

    search_type = request.GET.get(
        "type",
        "games"
    ).strip()


    game_results = []
    library_results = []
    user_results = []

    user_libraries = []


    # =====================================================
    # SEARCH GAMES
    # =====================================================

    if (
        search_query
        and search_type == "games"
    ):

        game_results = search_games_from_igdb(
            search_query,
            limit=20
        )


        if request.user.is_authenticated:

            libraries = list(
                GameLibrary.objects
                .filter(
                    user=request.user
                )
                .prefetch_related(
                    "games"
                )
                .order_by(
                    "-created_at"
                )
            )


            for library in libraries:

                library.igdb_game_ids = {
                    game.igdb_id
                    for game in library.games.all()
                    if game.igdb_id
                }


            for game in game_results:

                game_id = game.get("id")

                game["library_options"] = []

                for library in libraries:

                    game["library_options"].append({
                        "library": library,
                        "contains_game":
                            game_id
                            in library.igdb_game_ids,
                    })


            user_libraries = libraries


    # =====================================================
    # SEARCH LIBRARIES
    # =====================================================

    elif (
        search_query
        and search_type == "libraries"
    ):

        library_results = (
            GameLibrary.objects
            .filter(
                is_public=True,
                name__icontains=search_query
            )
            .select_related(
                "user"
            )
            .prefetch_related(
                "games"
            )
            .order_by(
                "-created_at"
            )
        )


    # =====================================================
    # SEARCH USERS
    # =====================================================

    elif (
        search_query
        and search_type == "users"
    ):

        user_results = (
            User.objects
            .filter(
                username__icontains=search_query
            )
            .order_by(
                "username"
            )[:30]
        )


    return render(
        request,
        "game/search_results.html",
        {
            "search_query": search_query,
            "search_type": search_type,

            "results": game_results,

            "library_results": library_results,

            "user_results": user_results,

            "user_libraries": user_libraries,
        }
    )

# =========================================================
# IGDB GAME DETAIL
# =========================================================

def game_detail_igdb(
    request,
    igdb_id
):

    game = (
        Game.objects
        .filter(
            igdb_id=igdb_id
        )
        .first()
    )


    if not game:

        game = save_game_from_igdb(
            igdb_id
        )


    if game:

        return redirect(
            "game_detail",
            slug=game.slug
        )


    return redirect(
        "search_games"
    )


# =========================================================
# GAME SERIES
# =========================================================

def game_series(request):

    series = (
        GameSeries.objects
        .all()
    )


    return render(
        request,
        "game/game_series.html",
        {
            "series": series
        }
    )


# =========================================================
# GAME SERIES DETAIL
# =========================================================

def game_series_detail(
    request,
    slug
):

    series = get_object_or_404(
        GameSeries,
        slug=slug
    )


    entries = (

        series.entries
        .select_related(
            "game"
        )
        .all()

    )


    return render(
        request,
        "game/game_series_detail.html",
        {

            "series": series,

            "entries": entries,

        }
    )


# =========================================================
# ABOUT
# =========================================================

def about(request):

    return render(
        request,
        "about.html"
    )


# =========================================================
# 2026 GAMES
# =========================================================

def games_2026(request):

    games = (
        get_current_year_games_from_igdb(
            limit=30
        )
    )


    return render(
        request,
        "game/games_2026.html",
        {
            "games_2026": games
        }
    )


# =========================================================
# CONTACT
# =========================================================

def contact(request):

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        subject = request.POST.get(
            "subject",
            ""
        ).strip()

        message = request.POST.get(
            "message",
            ""
        ).strip()


        if (
            not name
            or not email
            or not message
        ):

            messages.error(
                request,
                "Please fill in all required fields."
            )


        else:

            if not subject:

                subject = (
                    "GDBR Contact Message"
                )


            email_subject = (
                f"[GDBR Contact] {subject}"
            )


            email_body = f"""
New message from GDBR Contact Form

Name:
{name}

Email:
{email}

Subject:
{subject}

Message:
{message}
"""


            try:

                send_mail(

                    subject=email_subject,

                    message=email_body,

                    from_email=(
                        settings.DEFAULT_FROM_EMAIL
                    ),

                    recipient_list=[
                        settings.CONTACT_EMAIL
                    ],

                    fail_silently=False,

                )


                messages.success(
                    request,
                    "Your message has been sent successfully."
                )


                return redirect(
                    "contact"
                )


            except Exception as error:

                print(
                    "EMAIL ERROR:",
                    error
                )


                messages.error(
                    request,
                    "The message could not be sent. Please try again later."
                )


    return render(
        request,
        "contact.html",
        {
            "contact_email":
                settings.CONTACT_EMAIL
        }
    )


# =========================================================
# MY LIBRARIES
# =========================================================

@login_required(
    login_url="login"
)
def my_libraries(request):

    libraries = (

        GameLibrary.objects
        .filter(
            user=request.user
        )
        .prefetch_related(
            "games"
        )
        .order_by(
            "-created_at"
        )

    )


    return render(
        request,
        "game/my_libraries.html",
        {
            "libraries": libraries
        }
    )


# =========================================================
# CREATE LIBRARY
# =========================================================

@login_required(
    login_url="login"
)
@require_POST
def create_library(request):

    name = request.POST.get(
        "name",
        ""
    ).strip()


    description = request.POST.get(
        "description",
        ""
    ).strip()


    visibility = request.POST.get(
        "visibility",
        "private"
    )


    if not name:

        messages.error(
            request,
            "Library name is required."
        )


        return redirect(
            "my_libraries"
        )


    is_public = (
        visibility == "public"
    )


    GameLibrary.objects.create(

        user=request.user,

        name=name,

        description=description,

        is_public=is_public,

    )


    messages.success(
        request,
        f'"{name}" was created successfully.'
    )


    return redirect(
        "my_libraries"
    )


# =========================================================
# LIBRARY DETAIL
# =========================================================

def library_detail(
    request,
    library_id
):

    library = get_object_or_404(
        GameLibrary.objects.prefetch_related(
            "games"
        ),
        id=library_id
    )


    # =====================================================
    # PRIVATE LIBRARY CONTROL
    # =====================================================

    if not library.is_public:

        if (
            not request.user.is_authenticated
            or library.user != request.user
        ):

            messages.error(
                request,
                "This library is private."
            )

            return redirect(
                "home"
            )


    # =====================================================
    # UNIQUE VIEW
    # =====================================================

    if request.user.is_authenticated:

        GameLibraryView.objects.get_or_create(
            library=library,
            user=request.user
        )


    games = library.games.all()


    return render(
        request,
        "game/library_detail.html",
        {
            "library": library,
            "games": games,
        }
    )


# =========================================================
# DELETE LIBRARY
# =========================================================

@login_required(
    login_url="login"
)
@login_required
def delete_library(
    request,
    library_id
):

    library = get_object_or_404(
        GameLibrary,
        id=library_id
    )

    if library.user != request.user:

        messages.error(
            request,
            "You do not have permission to delete this library."
        )

        return redirect(
            "library_detail",
            library_id=library.id
        )

    if request.method == "POST":

        library.delete()

        messages.success(
            request,
            "Library deleted successfully."
        )

        return redirect(
            "my_libraries"
        )

    return redirect(
        "library_detail",
        library_id=library.id
    )

# =========================================================
# ADD GAME TO LIBRARY
# =========================================================

@login_required(
    login_url="login"
)
@require_POST
def add_game_to_library(request):

    library_id = request.POST.get(
        "library_id"
    )

    igdb_id = request.POST.get(
        "igdb_id"
    )


    if (
        not library_id
        or not igdb_id
    ):

        messages.error(
            request,
            "Library or game information is missing."
        )


        return redirect(
            request.META.get(
                "HTTP_REFERER",
                "home"
            )
        )


    # User can only add games
    # to their own library.
    library = get_object_or_404(

        GameLibrary,

        id=library_id,

        user=request.user,

    )


    # Try local database first.
    game = (

        Game.objects
        .filter(
            igdb_id=igdb_id
        )
        .first()

    )


    # If game isn't stored locally,
    # download it from IGDB.
    if not game:

        game = save_game_from_igdb(
            int(igdb_id)
        )


    if not game:

        messages.error(
            request,
            "The game could not be added."
        )


        return redirect(
            request.META.get(
                "HTTP_REFERER",
                "home"
            )
        )


    # Check whether game is
    # already in this library.
    if (
        library.games
        .filter(
            id=game.id
        )
        .exists()
    ):

        messages.info(
            request,
            f'"{game.title}" is already in "{library.name}".'
        )


    else:

        # IMPORTANT:
        # Game is added ONLY to
        # the selected library.
        library.games.add(
            game
        )


        messages.success(
            request,
            f'"{game.title}" was added to "{library.name}".'
        )


    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "home"
        )
    )


# =========================================================
# REMOVE GAME FROM LIBRARY
# =========================================================

@login_required(
    login_url="login"
)
@login_required
def remove_game_from_library(
    request,
    library_id,
    game_id
):

    library = get_object_or_404(
        GameLibrary,
        id=library_id
    )


    # =====================================================
    # OWNER CHECK
    # =====================================================

    if library.user != request.user:

        messages.error(
            request,
            "You do not have permission to modify this library."
        )

        return redirect(
            "library_detail",
            library_id=library.id
        )


    # =====================================================
    # ONLY POST
    # =====================================================

    if request.method != "POST":

        return redirect(
            "library_detail",
            library_id=library.id
        )


    # =====================================================
    # GET GAME
    # =====================================================

    game = get_object_or_404(
        Game,
        id=game_id
    )


    # =====================================================
    # REMOVE GAME
    # =====================================================

    if library.games.filter(
        id=game.id
    ).exists():

        library.games.remove(
            game
        )

        messages.success(
            request,
            f"{game.title} was removed from the library."
        )


    return redirect(
        "library_detail",
        library_id=library.id
    )

def search_suggestions(request):

    query = request.GET.get(
        "q",
        ""
    ).strip()


    search_type = request.GET.get(
        "type",
        "games"
    ).strip()


    if len(query) < 2:

        return JsonResponse({
            "results": []
        })


    results = []


    # =====================================================
    # GAMES
    # =====================================================

    if search_type == "games":

        games = (
            search_game_suggestions_from_igdb(
                query,
                limit=6
            )
        )


        for game in games:

            game_id = game.get(
                "id"
            )


            game_name = (
                game
                .get(
                    "name",
                    ""
                )
                .strip()
            )


            if (
                not game_id
                or not game_name
            ):
                continue


            release_year = ""

            timestamp = game.get(
                "first_release_date"
            )


            if timestamp:

                try:

                    release_year = (
                        datetime
                        .fromtimestamp(
                            timestamp
                        )
                        .year
                    )

                except (
                    ValueError,
                    OSError,
                    TypeError
                ):

                    release_year = ""


            subtitle = "Game"

            if release_year:

                subtitle = (
                    f"Game · {release_year}"
                )


            results.append({
                "type":
                    "game",

                "id":
                    game_id,

                "title":
                    game_name,

                "subtitle":
                    subtitle,
            })


    # =====================================================
    # LIBRARIES
    # =====================================================

    elif search_type == "libraries":

        libraries = (
            GameLibrary.objects
            .filter(
                is_public=True,
                name__icontains=query
            )
            .select_related(
                "user"
            )
            .only(
                "id",
                "name",
                "user__username"
            )
            .order_by(
                "name"
            )[:6]
        )


        for library in libraries:

            results.append({
                "type":
                    "library",

                "id":
                    library.id,

                "title":
                    library.name,

                "subtitle":
                    f"by {library.user.username}",
            })


    # =====================================================
    # USERS
    # =====================================================

    elif search_type == "users":

        users = (
            User.objects
            .filter(
                username__icontains=query
            )
            .only(
                "id",
                "username"
            )
            .order_by(
                "username"
            )[:6]
        )


        for user in users:

            results.append({
                "type":
                    "user",

                "id":
                    user.id,

                "title":
                    user.username,

                "subtitle":
                    "User",
            })


    return JsonResponse({
        "results": results
    })



@login_required
@require_POST
def ai_chat(request):

    try:

        data = json.loads(
            request.body
        )

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "error": "Invalid request."
            },
            status=400
        )


    question = data.get(
        "question",
        ""
    ).strip()


    if not question:

        return JsonResponse(
            {
                "error": "Please enter a question."
            },
            status=400
        )


    if len(question) > 1000:

        return JsonResponse(
            {
                "error": "Your question is too long."
            },
            status=400
        )


    try:

        answer = ask_gdbr_ai(
            question
        )

    except Exception as error:

        print(
            "GDBR AI ERROR:",
            type(error).__name__,
            repr(error)
        )

        return JsonResponse(
            {
                "error":
                    "The AI assistant is temporarily unavailable."
            },
            status=500
        )


    return JsonResponse(
        {
            "answer": answer
        }
    )
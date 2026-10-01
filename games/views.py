import json
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .ai import ask_gdbr_ai
from .api import (
    search_games_from_igdb,
    save_game_from_igdb,
    get_top_rated_games_from_igdb,
    get_current_year_games_from_igdb,
    get_game_from_igdb,
    get_top_games_by_genre_from_igdb,
    search_game_suggestions_from_igdb,
)
from .models import (
    Game,
    GameOfTheYear,
    Genre,
    GameSeries,
    GameLibrary,
    GameLibraryView,
)


User = get_user_model()


# =========================================================
# RATE LIMIT SETTINGS
# =========================================================

AI_MAX_REQUESTS = 20
AI_RATE_LIMIT_SECONDS = 10 * 60

CONTACT_MAX_REQUESTS = 5
CONTACT_RATE_LIMIT_SECONDS = 60 * 60


# =========================================================
# HELPERS
# =========================================================

def get_client_ip(request):

    forwarded_for = request.META.get(
        "HTTP_X_FORWARDED_FOR"
    )

    if forwarded_for:

        return (
            forwarded_for
            .split(",")[0]
            .strip()
        )

    return request.META.get(
        "REMOTE_ADDR",
        "unknown"
    )


def safe_back_redirect(
    request,
    fallback="home"
):

    referer = request.META.get(
        "HTTP_REFERER"
    )

    if (
        referer
        and url_has_allowed_host_and_scheme(
            referer,
            allowed_hosts={
                request.get_host()
            },
            require_https=request.is_secure(),
        )
    ):

        return redirect(
            referer
        )

    return redirect(
        fallback
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
    games = (
        Game.objects
        .all()
        .order_by("id")
    )

    # =====================================================
    # TRENDING GAMES
    # =====================================================

    trending_games = cache.get(
        "home_trending_games"
    )

    if trending_games is None:

        trending_games = (
            get_top_rated_games_from_igdb()
        )

        cache.set(
            "home_trending_games",
            trending_games,
            60 * 15
        )

    # =====================================================
    # CURRENT YEAR
    # =====================================================

    current_year_games = cache.get(
        "home_current_year_games"
    )

    if current_year_games is None:

        current_year_games = (
            get_current_year_games_from_igdb()
        )

        cache.set(
            "home_current_year_games",
            current_year_games,
            60 * 30
        )

    # =====================================================
    # POPULAR SERIES
    # =====================================================

    popular_series = (
        GameSeries.objects
        .all()[:6]
    )

    # =====================================================
    # GENRE GAMES
    # =====================================================

    default_genre_id = 4

    genre_games = cache.get(
        "home_genres"
    )

    if genre_games is None:

        genre_games = (
            get_top_games_by_genre_from_igdb(
                default_genre_id,
                limit=20
            )
        )

        cache.set(
            "home_genres",
            genre_games,
            60 * 60
        )

    # =====================================================
    # FEATURED LIBRARIES
    # =====================================================

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

    cache_key = (
        f"genre_games_{genre_id}"
    )

    games = cache.get(
        cache_key
    )

    if games is None:

        games = (
            get_top_games_by_genre_from_igdb(
                genre_id,
                limit=20
            )
        )

        cache.set(
            cache_key,
            games,
            60 * 30
        )

    return render(
        request,
        "game/genre_games_cards.html",
        {
            "genre_games": games
        }
    )


# =========================================================
# GAME MEDIA
# =========================================================

def game_media(
    request,
    slug
):

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

        igdb_data = (
            get_game_from_igdb(
                game.igdb_id
            )
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

def game_detail(
    request,
    slug
):

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

        libraries = list(
            libraries
        )

        for library in libraries:

            contains_game = any(

                library_game.id == game.id

                for library_game
                in library.games.all()

            )

            library_options.append({

                "library":
                    library,

                "contains_game":
                    contains_game,

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

            if len(content) > 2000:

                messages.error(
                    request,
                    "Comment cannot exceed "
                    "2000 characters."
                )

                return redirect(
                    "game_detail",
                    slug=slug
                )

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
            "game":
                game,

            "comments":
                comments,

            "library_options":
                library_options,
        }
    )


# =========================================================
# GAME OF THE YEAR
# =========================================================

def game_of_the_year(
    request
):

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
            "goty_games":
                goty_games
        }
    )


# =========================================================
# SEARCH
# =========================================================

def search_games(
    request
):

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

        game_results = (
            search_games_from_igdb(
                search_query,
                limit=20
            )
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

                    for game
                    in library.games.all()

                    if game.igdb_id
                }

            for game in game_results:

                game_id = game.get(
                    "id"
                )

                game["library_options"] = []

                for library in libraries:

                    game[
                        "library_options"
                    ].append({

                        "library":
                            library,

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
            "search_query":
                search_query,

            "search_type":
                search_type,

            "results":
                game_results,

            "library_results":
                library_results,

            "user_results":
                user_results,

            "user_libraries":
                user_libraries,
        }
    )


# =========================================================
# IGDB GAME DETAIL
# =========================================================

@login_required(
    login_url="login"
)
def game_detail_igdb(
    request,
    igdb_id
):

    if igdb_id <= 0:

        return redirect(
            "search_games"
        )

    game = (

        Game.objects
        .filter(
            igdb_id=igdb_id
        )
        .first()

    )

    if not game:

        game = (
            save_game_from_igdb(
                igdb_id
            )
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

def game_series(
    request
):

    series = (

        GameSeries.objects
        .all()

    )

    return render(
        request,
        "game/game_series.html",
        {
            "series":
                series
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
            "series":
                series,

            "entries":
                entries,
        }
    )


# =========================================================
# ABOUT
# =========================================================

def about(
    request
):

    return render(
        request,
        "about.html"
    )


# =========================================================
# 2026 GAMES
# =========================================================

def games_2026(
    request
):

    games = cache.get(
        "games_2026"
    )

    if games is None:

        games = (
            get_current_year_games_from_igdb(
                limit=30
            )
        )

        cache.set(
            "games_2026",
            games,
            60 * 60
        )

    return render(
        request,
        "game/games_2026.html",
        {
            "games_2026":
                games
        }
    )


# =========================================================
# CONTACT
# =========================================================

def contact(
    request
):

    if request.method == "POST":

        # =================================================
        # RATE LIMIT
        # =================================================

        client_ip = get_client_ip(
            request
        )

        contact_key = (
            f"contact_rate_{client_ip}"
        )

        contact_count = cache.get(
            contact_key,
            0
        )

        if (
            contact_count
            >= CONTACT_MAX_REQUESTS
        ):

            messages.error(
                request,
                "Too many messages were sent. "
                "Please try again later."
            )

            return redirect(
                "contact"
            )

        # =================================================
        # FORM DATA
        # =================================================

        name = request.POST.get(
            "name",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip().lower()

        subject = request.POST.get(
            "subject",
            ""
        ).strip()

        message = request.POST.get(
            "message",
            ""
        ).strip()

        # =================================================
        # REQUIRED FIELDS
        # =================================================

        if (
            not name
            or not email
            or not message
        ):

            messages.error(
                request,
                "Please fill in all required fields."
            )

            return redirect(
                "contact"
            )

        # =================================================
        # EMAIL VALIDATION
        # =================================================

        try:

            validate_email(
                email
            )

        except ValidationError:

            messages.error(
                request,
                "Please enter a valid email address."
            )

            return redirect(
                "contact"
            )

        # =================================================
        # INPUT LENGTHS
        # =================================================

        if len(name) > 100:

            messages.error(
                request,
                "Name is too long."
            )

            return redirect(
                "contact"
            )

        if len(subject) > 200:

            messages.error(
                request,
                "Subject is too long."
            )

            return redirect(
                "contact"
            )

        if len(message) > 5000:

            messages.error(
                request,
                "Message cannot exceed "
                "5000 characters."
            )

            return redirect(
                "contact"
            )

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

            sent_count = send_mail(

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

            if sent_count != 1:

                messages.error(
                    request,
                    "The message could not be sent. "
                    "Please try again later."
                )

                return redirect(
                    "contact"
                )

            # Only count successful emails.
            cache.set(
                contact_key,
                contact_count + 1,
                CONTACT_RATE_LIMIT_SECONDS
            )

            messages.success(
                request,
                "Your message has been "
                "sent successfully."
            )

            return redirect(
                "contact"
            )

        except Exception as error:

            print(
                "CONTACT EMAIL ERROR:",
                type(error).__name__
            )

            messages.error(
                request,
                "The message could not be sent. "
                "Please try again later."
            )

            return redirect(
                "contact"
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
def my_libraries(
    request
):

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
            "libraries":
                libraries
        }
    )


# =========================================================
# CREATE LIBRARY
# =========================================================

@login_required(
    login_url="login"
)
@require_POST
def create_library(
    request
):

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

    if len(name) > 100:

        messages.error(
            request,
            "Library name is too long."
        )

        return redirect(
            "my_libraries"
        )

    if len(description) > 2000:

        messages.error(
            request,
            "Library description is too long."
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

        GameLibrary.objects
        .select_related(
            "user"
        )
        .prefetch_related(
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

    games = (
        library.games
        .all()
    )

    return render(
        request,
        "game/library_detail.html",
        {
            "library":
                library,

            "games":
                games,
        }
    )


# =========================================================
# DELETE LIBRARY
# =========================================================

@login_required(
    login_url="login"
)
@require_POST
def delete_library(
    request,
    library_id
):

    library = get_object_or_404(

        GameLibrary,

        id=library_id,

        user=request.user,

    )

    library.delete()

    messages.success(
        request,
        "Library deleted successfully."
    )

    return redirect(
        "my_libraries"
    )


# =========================================================
# ADD GAME TO LIBRARY
# =========================================================

@login_required(
    login_url="login"
)
@require_POST
def add_game_to_library(
    request
):

    library_id = request.POST.get(
        "library_id"
    )

    igdb_id = request.POST.get(
        "igdb_id"
    )

    # =====================================================
    # BASIC VALIDATION
    # =====================================================

    if not library_id:

        messages.error(
            request,
            "Library information is missing."
        )

        return safe_back_redirect(
            request
        )

    try:

        library_id = int(
            library_id
        )

        igdb_id = int(
            igdb_id
        )

    except (
        TypeError,
        ValueError,
    ):

        messages.error(
            request,
            "Invalid game information."
        )

        return safe_back_redirect(
            request
        )

    if (
        library_id <= 0
        or igdb_id <= 0
    ):

        messages.error(
            request,
            "Invalid game information."
        )

        return safe_back_redirect(
            request
        )

    # =====================================================
    # GET USER LIBRARY
    # =====================================================

    library = get_object_or_404(

        GameLibrary,

        id=library_id,

        user=request.user,

    )

    # =====================================================
    # LOCAL GAME
    # =====================================================

    game = (

        Game.objects
        .filter(
            igdb_id=igdb_id
        )
        .first()

    )

    # =====================================================
    # FETCH FROM IGDB
    # =====================================================

    if not game:

        try:

            game = (
                save_game_from_igdb(
                    igdb_id
                )
            )

        except Exception as error:

            print(
                "IGDB SAVE ERROR:",
                type(error).__name__
            )

            game = None

    if not game:

        messages.error(
            request,
            "The game could not be added."
        )

        return safe_back_redirect(
            request
        )

    # =====================================================
    # ADD TO LIBRARY
    # =====================================================

    if (
        library.games
        .filter(
            id=game.id
        )
        .exists()
    ):

        messages.info(
            request,
            f'"{game.title}" is already '
            f'in "{library.name}".'
        )

    else:

        library.games.add(
            game
        )

        messages.success(
            request,
            f'"{game.title}" was added '
            f'to "{library.name}".'
        )

    return safe_back_redirect(
        request
    )


# =========================================================
# REMOVE GAME FROM LIBRARY
# =========================================================

@login_required(
    login_url="login"
)
@require_POST
def remove_game_from_library(
    request,
    library_id,
    game_id
):

    library = get_object_or_404(
        GameLibrary,
        id=library_id,
        user=request.user,
    )

    game = get_object_or_404(
        Game,
        id=game_id
    )

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


# =========================================================
# SEARCH SUGGESTIONS
# =========================================================

def search_suggestions(
    request
):

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

    # Prevent unnecessarily huge searches.
    if len(query) > 100:

        return JsonResponse({
            "results": []
        })

    results = []

    # =====================================================
    # GAMES
    # =====================================================

    if search_type == "games":

        suggestion_cache_key = (
            "search_suggestion:"
            f"{query.lower()}"
        )

        games = cache.get(
            suggestion_cache_key
        )

        if games is None:

            games = (
                search_game_suggestions_from_igdb(
                    query,
                    limit=6
                )
            )

            cache.set(
                suggestion_cache_key,
                games,
                60 * 5
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
                    TypeError,
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


# =========================================================
# AI CHAT
# =========================================================

@login_required(
    login_url="login"
)
@require_POST
def ai_chat(
    request
):

    # =====================================================
    # RATE LIMIT
    # =====================================================

    rate_key = (
        f"ai_rate_limit_user_{request.user.id}"
    )

    request_count = cache.get(
        rate_key,
        0
    )

    if request_count >= AI_MAX_REQUESTS:

        return JsonResponse(
            {
                "error":
                    "You have sent too many messages. "
                    "Please try again later."
            },
            status=429
        )

    # =====================================================
    # JSON
    # =====================================================

    try:

        data = json.loads(
            request.body
        )

    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
    ):

        return JsonResponse(
            {
                "error":
                    "Invalid request."
            },
            status=400
        )

    if not isinstance(
        data,
        dict
    ):

        return JsonResponse(
            {
                "error":
                    "Invalid request."
            },
            status=400
        )

    question = data.get(
        "question",
        ""
    )

    if not isinstance(
        question,
        str
    ):

        return JsonResponse(
            {
                "error":
                    "Invalid question."
            },
            status=400
        )

    question = (
        question.strip()
    )

    if not question:

        return JsonResponse(
            {
                "error":
                    "Please enter a question."
            },
            status=400
        )

    if len(question) > 1000:

        return JsonResponse(
            {
                "error":
                    "Your question is too long."
            },
            status=400
        )

    # =====================================================
    # COUNT REQUEST
    # =====================================================

    cache.set(
        rate_key,
        request_count + 1,
        AI_RATE_LIMIT_SECONDS
    )

    # =====================================================
    # OPENAI
    # =====================================================

    try:

        answer = (
            ask_gdbr_ai(
                question
            )
        )

    except Exception as error:

        print(
            "GDBR AI ERROR:",
            type(error).__name__
        )

        return JsonResponse(
            {
                "error":
                    "The AI assistant is "
                    "temporarily unavailable."
            },
            status=500
        )

    return JsonResponse(
        {
            "answer":
                answer
        }
    )
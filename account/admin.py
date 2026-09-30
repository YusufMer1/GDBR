from django.contrib import admin

from django.contrib.auth import get_user_model

from django.contrib.auth.admin import UserAdmin

from .models import Profile

from games.models import GameLibrary


User = get_user_model()



# =========================================================
# LIBRARY INLINE
# =========================================================

class GameLibraryInline(admin.StackedInline):

    model = GameLibrary

    extra = 0

    show_change_link = True

    filter_horizontal = (
        "games",
    )

    fields = (
        "name",
        "description",
        "is_public",
        "is_featured",
        "games",
    )


# =========================================================
# CUSTOM USER ADMIN
# =========================================================

admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    inlines = [
        GameLibraryInline,
    ]



# =========================================================
# PROFILE ADMIN
# =========================================================

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "user_email",
        "library_count",
    )

    search_fields = (
        "user__username",
        "user__email",
    )

    readonly_fields = (
        "library_count",
    )

    fields = (
        "user",
        "avatar",
        "library_count",
    )


    def user_email(self, obj):

        return obj.user.email

    user_email.short_description = "Email"


    def library_count(self, obj):

        return obj.user.game_libraries.count()

    library_count.short_description = "Libraries"
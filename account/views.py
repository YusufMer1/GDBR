import hashlib
import secrets
import smtplib

from datetime import timedelta

from PIL import Image

from django.conf import settings
from django.contrib import messages

from django.contrib.auth import (
    authenticate,
    get_user_model,
    login as auth_login,
    logout as auth_logout,
    update_session_auth_hash,
)

from django.contrib.auth.hashers import (
    make_password,
    check_password,
)

from django.contrib.auth.password_validation import (
    validate_password,
)

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.validators import validate_email

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from django.utils import timezone

from .models import (
    Profile,
    PendingRegistration,
)


User = get_user_model()


# =========================================================
# SECURITY SETTINGS
# =========================================================

MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB

ALLOWED_AVATAR_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

LOGIN_MAX_ATTEMPTS = 10
LOGIN_BLOCK_SECONDS = 15 * 60

REGISTER_MAX_EMAILS = 5
REGISTER_BLOCK_SECONDS = 10 * 60


# =========================================================
# HELPERS
# =========================================================

def get_client_ip(request):

    forwarded_for = request.META.get(
        "HTTP_X_FORWARDED_FOR"
    )

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.META.get(
        "REMOTE_ADDR",
        "unknown"
    )


def safe_cache_part(value):

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def validate_avatar_file(avatar):

    if avatar.size > MAX_AVATAR_SIZE:
        raise ValidationError(
            "Avatar must be smaller than 5 MB."
        )

    content_type = getattr(
        avatar,
        "content_type",
        ""
    )

    if content_type not in ALLOWED_AVATAR_TYPES:
        raise ValidationError(
            "Avatar must be a JPG, PNG, or WEBP image."
        )

    try:

        image = Image.open(avatar)
        image.verify()

    except Exception:

        raise ValidationError(
            "The uploaded avatar is not a valid image."
        )

    finally:

        try:
            avatar.seek(0)
        except Exception:
            pass


# =========================================================
# REGISTER
# =========================================================

def register(request):

    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip().lower()

        password1 = request.POST.get(
            "password1",
            ""
        )

        password2 = request.POST.get(
            "password2",
            ""
        )

        # =====================================================
        # USERNAME
        # =====================================================

        if not username:

            messages.error(
                request,
                "Username is required."
            )

            return redirect(
                "register"
            )

        if len(username) < 3:

            messages.error(
                request,
                "Username must be at least 3 characters long."
            )

            return redirect(
                "register"
            )

        if User.objects.filter(
            username__iexact=username
        ).exists():

            messages.error(
                request,
                "This username is already taken."
            )

            return redirect(
                "register"
            )

        # =====================================================
        # EMAIL
        # =====================================================

        if not email:

            messages.error(
                request,
                "Email is required."
            )

            return redirect(
                "register"
            )

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
                "register"
            )

        if not email.endswith(
            "@gmail.com"
        ):

            messages.error(
                request,
                "Only Gmail addresses are allowed."
            )

            return redirect(
                "register"
            )

        if User.objects.filter(
            email__iexact=email
        ).exists():

            messages.error(
                request,
                "An account with this email already exists."
            )

            return redirect(
                "register"
            )

        # =====================================================
        # PASSWORD
        # =====================================================

        if not password1:

            messages.error(
                request,
                "Password is required."
            )

            return redirect(
                "register"
            )

        if password1 != password2:

            messages.error(
                request,
                "Passwords do not match."
            )

            return redirect(
                "register"
            )

        temporary_user = User(
            username=username,
            email=email,
        )

        try:

            validate_password(
                password1,
                user=temporary_user
            )

        except ValidationError as error:

            for message in error.messages:

                messages.error(
                    request,
                    message
                )

            return redirect(
                "register"
            )

        # =====================================================
        # EXISTING VERIFICATION
        # =====================================================

        existing_pending = (
            PendingRegistration.objects
            .filter(
                email__iexact=email,
                expires_at__gt=timezone.now()
            )
            .order_by("-created_at")
            .first()
        )

        if existing_pending:

            if (
                timezone.now()
                - existing_pending.created_at
            ) < timedelta(seconds=60):

                messages.info(
                    request,
                    "A verification code was already sent. "
                    "Please wait before requesting another one."
                )

                return redirect(
                    "verify_email",
                    token=existing_pending.token
                )

        # =====================================================
        # REGISTER RATE LIMIT
        # =====================================================

        client_ip = get_client_ip(
            request
        )

        register_key = (
            "register_email:"
            + safe_cache_part(client_ip)
        )

        register_count = cache.get(
            register_key,
            0
        )

        if register_count >= REGISTER_MAX_EMAILS:

            messages.error(
                request,
                "Too many verification emails were requested. "
                "Please try again later."
            )

            return redirect(
                "register"
            )

        # =====================================================
        # DELETE OLD PENDING REGISTRATIONS
        # =====================================================

        PendingRegistration.objects.filter(
            email__iexact=email
        ).delete()

        PendingRegistration.objects.filter(
            username__iexact=username
        ).delete()

        # =====================================================
        # CREATE VERIFICATION CODE
        # =====================================================

        verification_code = str(
            secrets.randbelow(
                900000
            ) + 100000
        )

        pending = (
            PendingRegistration.objects.create(

                username=username,

                email=email,

                password_hash=make_password(
                    password1
                ),

                verification_code_hash=make_password(
                    verification_code
                ),

                expires_at=(
                    timezone.now()
                    + timedelta(
                        minutes=10
                    )
                ),
            )
        )

        # =====================================================
        # SEND EMAIL
        # =====================================================

        try:

            email_message = EmailMessage(

                subject="GDBR Verification Code",

                body=(
                    "Welcome to GDBR!\n\n"
                    f"Your verification code is: "
                    f"{verification_code}\n\n"
                    "This code expires in 10 minutes.\n\n"
                    "If you did not create this account, "
                    "you can ignore this email."
                ),

                from_email=settings.DEFAULT_FROM_EMAIL,

                to=[
                    email
                ],
            )

            sent_count = email_message.send(
                fail_silently=False
            )

            if sent_count != 1:

                pending.delete()

                messages.error(
                    request,
                    "We couldn't send the verification code. "
                    "Please try again."
                )

                return redirect(
                    "register"
                )

            # Email successfully sent.
            cache.set(
                register_key,
                register_count + 1,
                REGISTER_BLOCK_SECONDS
            )

        except smtplib.SMTPRecipientsRefused:

            pending.delete()

            messages.error(
                request,
                "This Gmail address could not be reached."
            )

            return redirect(
                "register"
            )

        except smtplib.SMTPAuthenticationError:

            pending.delete()

            messages.error(
                request,
                "The email verification service is "
                "temporarily unavailable."
            )

            return redirect(
                "register"
            )

        except smtplib.SMTPException:

            pending.delete()

            messages.error(
                request,
                "We couldn't send the verification email. "
                "Please try again."
            )

            return redirect(
                "register"
            )

        except Exception:

            pending.delete()

            messages.error(
                request,
                "Something went wrong while sending "
                "the verification email."
            )

            return redirect(
                "register"
            )

        messages.success(
            request,
            "A verification code has been sent "
            "to your Gmail address."
        )

        return redirect(
            "verify_email",
            token=pending.token
        )

    return render(
        request,
        "account/register.html"
    )


# =========================================================
# LOGIN
# =========================================================

def login(request):

    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        client_ip = get_client_ip(
            request
        )

        login_identifier = (
            client_ip
            + ":"
            + username.lower()
        )

        login_key = (
            "login_attempt:"
            + safe_cache_part(
                login_identifier
            )
        )

        failed_attempts = cache.get(
            login_key,
            0
        )

        if failed_attempts >= LOGIN_MAX_ATTEMPTS:

            return render(
                request,
                "account/login.html",
                {
                    "error":
                        "Too many failed login attempts. "
                        "Please try again later."
                }
            )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            cache.delete(
                login_key
            )

            auth_login(
                request,
                user
            )

            return redirect(
                "home"
            )

        cache.set(
            login_key,
            failed_attempts + 1,
            LOGIN_BLOCK_SECONDS
        )

        return render(
            request,
            "account/login.html",
            {
                "error":
                    "Invalid username or password."
            }
        )

    return render(
        request,
        "account/login.html"
    )


# =========================================================
# LOGOUT
# =========================================================

def logout_view(request):

    if request.user.is_authenticated:

        auth_logout(
            request
        )

    return redirect(
        "login"
    )


# =========================================================
# PROFILE
# =========================================================

def profile(request):

    if not request.user.is_authenticated:

        return redirect(
            "login"
        )

    profile_obj, _ = (
        Profile.objects.get_or_create(
            user=request.user
        )
    )

    errors = []
    success = None

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip().lower()

        password = request.POST.get(
            "password",
            ""
        )

        password2 = request.POST.get(
            "password2",
            ""
        )

        avatar = request.FILES.get(
            "avatar"
        )

        # =====================================================
        # USERNAME
        # =====================================================

        if (
            username
            and username != request.user.username
        ):

            if User.objects.filter(
                username__iexact=username
            ).exclude(
                pk=request.user.pk
            ).exists():

                errors.append(
                    "Username already taken."
                )

            elif len(username) < 3:

                errors.append(
                    "Username must be at least "
                    "3 characters long."
                )

            else:

                request.user.username = (
                    username
                )

        # =====================================================
        # EMAIL
        # =====================================================

        if (
            email
            and email != request.user.email
        ):

            # Do NOT change an account email without
            # verifying the new address first.
            errors.append(
                "Email changes require verification. "
                "Email changing is temporarily disabled."
            )

        # =====================================================
        # PASSWORD
        # =====================================================

        if password or password2:

            if password != password2:

                errors.append(
                    "Passwords do not match."
                )

            else:

                try:

                    validate_password(
                        password,
                        user=request.user
                    )

                except ValidationError as error:

                    errors.extend(
                        error.messages
                    )

                else:

                    request.user.set_password(
                        password
                    )

        # =====================================================
        # AVATAR
        # =====================================================

        if avatar:

            try:

                validate_avatar_file(
                    avatar
                )

            except ValidationError as error:

                errors.extend(
                    error.messages
                )

            else:

                profile_obj.avatar = (
                    avatar
                )

        # =====================================================
        # SAVE
        # =====================================================

        if not errors:

            request.user.save()

            profile_obj.save()

            if password:

                update_session_auth_hash(
                    request,
                    request.user
                )

            success = (
                "Profile updated successfully."
            )

    return render(
        request,
        "account/profile.html",
        {
            "user":
                request.user,

            "profile":
                profile_obj,

            "errors":
                errors,

            "success":
                success,
        }
    )


# =========================================================
# VERIFY EMAIL
# =========================================================

def verify_email(
    request,
    token
):

    pending = get_object_or_404(
        PendingRegistration,
        token=token
    )

    # =====================================================
    # EXPIRED
    # =====================================================

    if timezone.now() > pending.expires_at:

        pending.delete()

        messages.error(
            request,
            "Verification code has expired. "
            "Please register again."
        )

        return redirect(
            "register"
        )

    # =====================================================
    # POST
    # =====================================================

    if request.method == "POST":

        code = request.POST.get(
            "code",
            ""
        ).strip()

        if not code:

            messages.error(
                request,
                "Please enter the verification code."
            )

            return redirect(
                "verify_email",
                token=pending.token
            )

        if (
            not code.isdigit()
            or len(code) != 6
        ):

            messages.error(
                request,
                "Please enter a valid "
                "6-digit verification code."
            )

            return redirect(
                "verify_email",
                token=pending.token
            )

        # =================================================
        # ATTEMPT LIMIT
        # =================================================

        if pending.attempts >= 5:

            pending.delete()

            messages.error(
                request,
                "Too many incorrect attempts. "
                "Please register again."
            )

            return redirect(
                "register"
            )

        # =================================================
        # CHECK CODE
        # =================================================

        if not check_password(
            code,
            pending.verification_code_hash
        ):

            pending.attempts += 1

            pending.save(
                update_fields=[
                    "attempts"
                ]
            )

            remaining = (
                5
                - pending.attempts
            )

            if remaining <= 0:

                pending.delete()

                messages.error(
                    request,
                    "Too many incorrect attempts. "
                    "Please register again."
                )

                return redirect(
                    "register"
                )

            messages.error(
                request,
                f"Incorrect verification code. "
                f"{remaining} attempts remaining."
            )

            return redirect(
                "verify_email",
                token=pending.token
            )

        # =================================================
        # FINAL USERNAME CHECK
        # =================================================

        if User.objects.filter(
            username__iexact=pending.username
        ).exists():

            pending.delete()

            messages.error(
                request,
                "This username is no longer available."
            )

            return redirect(
                "register"
            )

        # =================================================
        # FINAL EMAIL CHECK
        # =================================================

        if User.objects.filter(
            email__iexact=pending.email
        ).exists():

            pending.delete()

            messages.error(
                request,
                "An account with this email "
                "already exists."
            )

            return redirect(
                "register"
            )

        # =================================================
        # CREATE USER
        # =================================================

        user = User(
            username=pending.username,
            email=pending.email
        )

        # Password was already hashed during registration.
        user.password = (
            pending.password_hash
        )

        user.save()

        pending.delete()

        messages.success(
            request,
            "Your email has been verified successfully. "
            "You can now sign in."
        )

        return redirect(
            "login"
        )

    # =====================================================
    # GET
    # =====================================================

    return render(
        request,
        "account/verify_email.html",
        {
            "email":
                pending.email,

            "token":
                pending.token,
        }
    )
import secrets
import smtplib

from datetime import timedelta

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


        # Check basic email format
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


        # Only Gmail
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


        if len(password1) < 8:

            messages.error(
                request,
                "Password must be at least 8 characters long."
            )

            return redirect(
                "register"
            )

        # =====================================================
        # PREVENT DUPLICATE VERIFICATION EMAILS
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

            # Son kod çok yakın zamanda gönderildiyse
            # tekrar email gönderme.
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
        # SEND VERIFICATION EMAIL
        # =====================================================

        try:

            print("========================================")
            print("REGISTER EMAIL DEBUG")
            print("FROM:", repr(settings.DEFAULT_FROM_EMAIL))
            print("TO:", repr(email))
            print("CODE:", verification_code)
            print("========================================")

            email_message = EmailMessage(
                subject="GDBR Verification Code",
                body=(
                    f"Your GDBR verification code is: {verification_code}\n\n"
                    "This code expires in 10 minutes."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )

            sent_count = email_message.send(
                fail_silently=False
            )

            print("EMAIL SENT RESULT:", sent_count)

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


        # =====================================================
        # RECIPIENT REJECTED
        # =====================================================

        except smtplib.SMTPRecipientsRefused as error:

            pending.delete()

            print(
                "SMTP RECIPIENT ERROR:",
                repr(error)
            )

            messages.error(
                request,
                "This Gmail address could not be reached."
            )

            return redirect(
                "register"
            )


        # =====================================================
        # GMAIL AUTH ERROR
        # =====================================================

        except smtplib.SMTPAuthenticationError as error:

            pending.delete()

            print(
                "SMTP AUTH ERROR:",
                repr(error)
            )

            messages.error(
                request,
                "The email verification service is temporarily unavailable."
            )

            return redirect(
                "register"
            )


        # =====================================================
        # SMTP ERROR
        # =====================================================

        except smtplib.SMTPException as error:

            pending.delete()

            print(
                "SMTP ERROR:",
                repr(error)
            )

            messages.error(
                request,
                "We couldn't send the verification email. "
                "Please try again."
            )

            return redirect(
                "register"
            )


        # =====================================================
        # OTHER ERROR
        # =====================================================

        except Exception as error:

            pending.delete()

            print(
                "EMAIL ERROR TYPE:",
                type(error).__name__
            )

            print(
                "EMAIL ERROR:",
                repr(error)
            )

            messages.error(
                request,
                "Something went wrong while sending the verification email."
            )

            return redirect(
                "register"
            )


        # =====================================================
        # SUCCESS
        # =====================================================

        messages.success(
            request,
            "A verification code has been sent to your Gmail address."
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


        user = authenticate(
            request,
            username=username,
            password=password
        )


        if user is not None:

            auth_login(
                request,
                user
            )

            return redirect(
                "home"
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

            try:

                validate_email(
                    email
                )

            except ValidationError:

                errors.append(
                    "Please enter a valid email address."
                )


            if not email.endswith(
                "@gmail.com"
            ):

                errors.append(
                    "Only Gmail addresses are allowed."
                )


            elif User.objects.filter(
                email__iexact=email
            ).exclude(
                pk=request.user.pk
            ).exists():

                errors.append(
                    "Email already in use."
                )

            else:

                if not errors:

                    request.user.email = (
                        email
                    )


        # =====================================================
        # PASSWORD
        # =====================================================

        if password or password2:

            if password != password2:

                errors.append(
                    "Passwords do not match."
                )


            elif len(password) < 8:

                errors.append(
                    "Password must be at least 8 characters long."
                )


            else:

                request.user.set_password(
                    password
                )


        # =====================================================
        # AVATAR
        # =====================================================

        if avatar:

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
    # EXPIRED CODE
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


        # =================================================
        # EMPTY CODE
        # =================================================

        if not code:

            messages.error(
                request,
                "Please enter the verification code."
            )


            return redirect(
                "verify_email",
                token=pending.token
            )


        # =================================================
        # CODE FORMAT
        # =================================================

        if (
            not code.isdigit()
            or len(code) != 6
        ):

            messages.error(
                request,
                "Please enter a valid 6-digit verification code."
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
                "An account with this email already exists."
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


        # Password is already securely hashed.
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


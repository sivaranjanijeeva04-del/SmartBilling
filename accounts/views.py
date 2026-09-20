from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from .models import CompanyProfile

def login_view(request):

    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            return redirect("dashboard")

        return render(
            request,
            "login.html",
            {
                "error": "Invalid username or password."
            }
        )

    return render(request, "login.html")


def signup_view(request):

    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":

        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:

            return render(
                request,
                "signup.html",
                {
                    "error": "Passwords do not match."
                }
            )

        if User.objects.filter(username=username).exists():

            return render(
                request,
                "signup.html",
                {
                    "error": "Username already exists."
                }
            )

        if User.objects.filter(email=email).exists():

            return render(
                request,
                "signup.html",
                {
                    "error": "Email already exists."
                }
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        login(request, user)

        return redirect("dashboard")

    return render(request, "signup.html")


@login_required
def profile_view(request):
    if request.method == "POST":

        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()

        if not first_name:
            return render(request, "profile.html", {
                "error": "First name is required."
            })

        if not email:
            return render(request, "profile.html", {
                "error": "Email address is required."
            })

        if User.objects.filter(email=email).exclude(
            id=request.user.id
        ).exists():
            return render(request, "profile.html", {
                "error": "This email address is already in use."
            })

        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.email = email

        request.user.save()

        return render(request, "profile.html", {
            "success": "Profile updated successfully."
        })

    return render(request, "profile.html")

@login_required
def change_password_view(request):

    if request.method == "POST":

        current_password = request.POST.get("current_password", "")
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not request.user.check_password(current_password):
            return render(request, "change_password.html", {
                "error": "Current password is incorrect."
            })

        if len(new_password) < 8:
            return render(request, "change_password.html", {
                "error": "New password must contain at least 8 characters."
            })

        if new_password != confirm_password:
            return render(request, "change_password.html", {
                "error": "New passwords do not match."
            })

        if current_password == new_password:
            return render(request, "change_password.html", {
                "error": "New password must be different from current password."
            })

        request.user.set_password(new_password)
        request.user.save()

        login(request, request.user)

        return render(request, "change_password.html", {
            "success": "Password changed successfully."
        })

    return render(request, "change_password.html")


@login_required
def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("login")

    return redirect("dashboard")

@login_required
def settings_view(request):

    company, created = CompanyProfile.objects.get_or_create(
        id=1,
        defaults={
            "company_name": "SmartBilling"
        }
    )

    if request.method == "POST":

        company_name = request.POST.get("company_name", "").strip()
        phone = request.POST.get("company_phone", "").strip()
        email = request.POST.get("company_email", "").strip()
        gst_number = request.POST.get("gst_number", "").strip()
        address = request.POST.get("company_address", "").strip()

        if not company_name:
            return render(request, "settings.html", {
                "company": company,
                "error": "Company name is required."
            })

        company.company_name = company_name
        company.phone = phone
        company.email = email
        company.gst_number = gst_number
        company.address = address
        company.save()

        return render(request, "settings.html", {
            "company": company,
            "success": "Company details saved successfully."
        })

    return render(request, "settings.html", {
        "company": company
    })
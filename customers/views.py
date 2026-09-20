from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .models import Customer


@login_required
def customer_list(request):
    search = request.GET.get("search", "").strip()

    customers = (
        Customer.objects
        .all()
        .order_by("-created_at")
    )

    if search:
        customers = customers.filter(
            name__icontains=search
        ) | customers.filter(
            email__icontains=search
        ) | customers.filter(
            phone__icontains=search
        )

    return render(request, "customers.html", {
        "customers": customers,
        "search": search,
    })


@login_required
def add_customer(request):

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()

        # Required fields
        if not name or not phone:
            return render(
                request,
                "customer_form.html",
                {
                    "error": "Name and phone number are required.",
                    "form_data": request.POST
                }
            )

        # Phone validation
        if not phone.isdigit():
            return render(
                request,
                "customer_form.html",
                {
                    "error": "Phone number must contain only digits.",
                    "form_data": request.POST
                }
            )

        if len(phone) < 10 or len(phone) > 15:
            return render(
                request,
                "customer_form.html",
                {
                    "error": "Please enter a valid phone number.",
                    "form_data": request.POST
                }
            )

        # Email validation
        if email and "@" not in email:
            return render(
                request,
                "customer_form.html",
                {
                    "error": "Please enter a valid email address.",
                    "form_data": request.POST
                }
            )

        Customer.objects.create(
            name=name,
            email=email,
            phone=phone,
            address=address
        )

        return redirect("customers")

    return render(request, "customer_form.html")


@login_required
def edit_customer(request, id):

    customer = get_object_or_404(Customer, id=id)

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()

        if not name or not phone:
            return render(
                request,
                "customer_form.html",
                {
                    "customer": customer,
                    "error": "Name and phone number are required.",
                    "form_data": request.POST
                }
            )

        if not phone.isdigit():
            return render(
                request,
                "customer_form.html",
                {
                    "customer": customer,
                    "error": "Phone number must contain only digits.",
                    "form_data": request.POST
                }
            )

        if len(phone) < 10 or len(phone) > 15:
            return render(
                request,
                "customer_form.html",
                {
                    "customer": customer,
                    "error": "Please enter a valid phone number.",
                    "form_data": request.POST
                }
            )

        if email and "@" not in email:
            return render(
                request,
                "customer_form.html",
                {
                    "customer": customer,
                    "error": "Please enter a valid email address.",
                    "form_data": request.POST
                }
            )

        customer.name = name
        customer.email = email
        customer.phone = phone
        customer.address = address

        customer.save()

        return redirect("customers")

    return render(
        request,
        "customer_form.html",
        {"customer": customer}
    )


@login_required
def delete_customer(request, id):
    if request.method == "POST":
        customer = get_object_or_404(Customer, id=id)
        customer.delete()

    return redirect("customers")
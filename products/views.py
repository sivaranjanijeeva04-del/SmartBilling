from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from decimal import Decimal, InvalidOperation

from .models import Product
from django.db.models import Q

@login_required
def product_list(request):

    search = request.GET.get("search", "").strip()
    category = request.GET.get("category", "").strip()
    stock_status = request.GET.get("stock_status", "").strip()

    products = (
        Product.objects
        .all()
        .order_by("-created_at")
    )

    # Search
    if search:
        products = products.filter(
            Q(name__icontains=search)
            | Q(category__icontains=search)
        )

    # Category filter
    if category:
        products = products.filter(
            category=category
        )

    # Stock filter
    if stock_status == "in_stock":

        products = products.filter(
            stock__gt=5
        )

    elif stock_status == "low_stock":

        products = products.filter(
            stock__gt=0,
            stock__lte=5
        )

    elif stock_status == "out_of_stock":

        products = products.filter(
            stock=0
        )

    categories = (
        Product.objects
        .values_list(
            "category",
            flat=True
        )
        .distinct()
        .order_by("category")
    )

    context = {
        "products": products,
        "categories": categories,
        "search": search,
        "category": category,
        "stock_status": stock_status,
    }

    return render(
        request,
        "products.html",
        context
    )
@login_required
def add_product(request):

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        category = request.POST.get("category", "").strip()
        price = request.POST.get("price", "").strip()
        stock = request.POST.get("stock", "").strip()
        description = request.POST.get("description", "").strip()

        # Required field validation
        if not name or not category or not price or not stock:
            return render(
                request,
                "product_form.html",
                {
                    "error": "Please fill in all required fields.",
                    "form_data": request.POST
                }
            )

        # Price validation
        try:
            price = Decimal(price)
        except (InvalidOperation, TypeError):
            return render(
                request,
                "product_form.html",
                {
                    "error": "Please enter a valid price.",
                    "form_data": request.POST
                }
            )

        if price <= 0:
            return render(
                request,
                "product_form.html",
                {
                    "error": "Price must be greater than 0.",
                    "form_data": request.POST
                }
            )

        # Stock validation
        try:
            stock = int(stock)
        except (ValueError, TypeError):
            return render(
                request,
                "product_form.html",
                {
                    "error": "Please enter a valid stock quantity.",
                    "form_data": request.POST
                }
            )

        if stock < 0:
            return render(
                request,
                "product_form.html",
                {
                    "error": "Stock cannot be negative.",
                    "form_data": request.POST
                }
            )

        Product.objects.create(
            name=name,
            category=category,
            price=price,
            stock=stock,
            description=description
        )

        return redirect("products")

    return render(request, "product_form.html")


@login_required
def edit_product(request, id):

    product = get_object_or_404(Product, id=id)

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        category = request.POST.get("category", "").strip()
        price = request.POST.get("price", "").strip()
        stock = request.POST.get("stock", "").strip()
        description = request.POST.get("description", "").strip()

        if not name or not category or not price or not stock:
            return render(
                request,
                "product_form.html",
                {
                    "product": product,
                    "error": "Please fill in all required fields.",
                    "form_data": request.POST
                }
            )

        try:
            price = Decimal(price)
        except (InvalidOperation, TypeError):
            return render(
                request,
                "product_form.html",
                {
                    "product": product,
                    "error": "Please enter a valid price.",
                    "form_data": request.POST
                }
            )

        if price <= 0:
            return render(
                request,
                "product_form.html",
                {
                    "product": product,
                    "error": "Price must be greater than 0.",
                    "form_data": request.POST
                }
            )

        try:
            stock = int(stock)
        except (ValueError, TypeError):
            return render(
                request,
                "product_form.html",
                {
                    "product": product,
                    "error": "Please enter a valid stock quantity.",
                    "form_data": request.POST
                }
            )

        if stock < 0:
            return render(
                request,
                "product_form.html",
                {
                    "product": product,
                    "error": "Stock cannot be negative.",
                    "form_data": request.POST
                }
            )

        product.name = name
        product.category = category
        product.price = price
        product.stock = stock
        product.description = description

        product.save()

        return redirect("products")

    return render(
        request,
        "product_form.html",
        {"product": product}
    )


@login_required
def delete_product(request, id):
    if request.method == "POST":
        product = get_object_or_404(Product, id=id)
        product.delete()

    return redirect("products")
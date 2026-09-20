from decimal import Decimal
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse
from django.utils import timezone

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from products.models import Product
from customers.models import Customer
from payments.models import Payment
from accounts.models import CompanyProfile

from .models import Invoice, InvoiceItem


# =========================================================
# Invoice Number Generator
# =========================================================

def generate_invoice_number():
    today = timezone.localdate()

    prefix = f"INV-{today.strftime('%Y%m%d')}"

    last_invoice = (
        Invoice.objects
        .filter(invoice_number__startswith=prefix)
        .order_by("-id")
        .first()
    )

    if last_invoice:
        try:
            last_number = int(
                last_invoice.invoice_number.split("-")[-1]
            )
        except (ValueError, IndexError):
            last_number = 0

        next_number = last_number + 1

    else:
        next_number = 1

    return f"{prefix}-{next_number:04d}"


# =========================================================
# Dashboard
# =========================================================

@login_required
def dashboard(request):

    # -----------------------------------------
    # Basic Statistics
    # -----------------------------------------

    total_products = Product.objects.count()

    total_customers = Customer.objects.count()

    total_invoices = Invoice.objects.count()

    total_payments = Payment.objects.count()


    # -----------------------------------------
    # Total Revenue
    # Paid invoices only
    # -----------------------------------------

    total_revenue = (
        Invoice.objects
        .filter(payment_status="Paid")
        .aggregate(
            total=Sum("grand_total")
        )["total"]
        or Decimal("0.00")
    )


    # -----------------------------------------
    # Total Paid
    # -----------------------------------------

    total_paid = (
        Payment.objects
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )


    # -----------------------------------------
    # ALL Pending / Partial Invoices
    # -----------------------------------------

    all_pending_invoices = (
        Invoice.objects
        .filter(
            payment_status__in=[
                "Pending",
                "Partial"
            ]
        )
        .select_related("customer")
        .order_by("-invoice_date")
    )


    # -----------------------------------------
    # Actual Pending Amount
    # -----------------------------------------

    pending_amount = Decimal("0.00")


    for invoice in all_pending_invoices:

        paid_amount = (
            Payment.objects
            .filter(invoice=invoice)
            .aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )


        remaining_amount = (
            invoice.grand_total -
            paid_amount
        )


        if remaining_amount < 0:
            remaining_amount = Decimal("0.00")


        pending_amount += remaining_amount


    # -----------------------------------------
    # Only latest 5 for Dashboard display
    # -----------------------------------------

    pending_invoices = all_pending_invoices[:5]


    # Add remaining amount to displayed invoices

    for invoice in pending_invoices:

        paid_amount = (
            Payment.objects
            .filter(invoice=invoice)
            .aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )


        remaining_amount = (
            invoice.grand_total -
            paid_amount
        )


        if remaining_amount < 0:
            remaining_amount = Decimal("0.00")


        invoice.paid_amount = paid_amount

        invoice.remaining_amount = remaining_amount


    # -----------------------------------------
    # Low Stock Products
    # -----------------------------------------

    low_stock_products = (
        Product.objects
        .filter(stock__lte=5)
        .order_by("stock", "name")[:5]
    )


    # -----------------------------------------
    # Recent Invoices
    # -----------------------------------------

    recent_invoices = (
        Invoice.objects
        .select_related("customer")
        .order_by("-invoice_date")[:5]
    )


    # -----------------------------------------
    # Recent Payments
    # -----------------------------------------

    recent_payments = (
        Payment.objects
        .select_related(
            "invoice",
            "invoice__customer"
        )
        .order_by("-payment_date")[:5]
    )


    # -----------------------------------------
    # Context
    # -----------------------------------------

    context = {

        "total_products": total_products,

        "total_customers": total_customers,

        "total_invoices": total_invoices,

        "total_payments": total_payments,

        "total_revenue": total_revenue,

        "total_paid": total_paid,

        "pending_amount": pending_amount,

        "low_stock_products": low_stock_products,

        "pending_invoices": pending_invoices,

        "recent_invoices": recent_invoices,

        "recent_payments": recent_payments,
    }


    return render(
        request,
        "dashboard.html",
        context
    )
# =========================================================
# Invoice List
# =========================================================

@login_required
def invoice_list(request):

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()

    invoices = Invoice.objects.select_related(
        "customer"
    ).prefetch_related(
        "payments",
        "items"
    ).all().order_by("-invoice_date")

    if search:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search)
            | Q(customer__name__icontains=search)
        )

    if status:
        invoices = invoices.filter(
            payment_status=status
        )

    # Calculate paid and balance for each invoice
    for invoice in invoices:

        paid_amount = invoice.payments.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        remaining_amount = invoice.grand_total - paid_amount

        if remaining_amount < 0:
            remaining_amount = Decimal("0")

        invoice.paid_amount = paid_amount
        invoice.remaining_amount = remaining_amount

        if remaining_amount == 0:
            invoice.display_status = "Paid"
        elif paid_amount > 0:
            invoice.display_status = "Partial"
        else:
            invoice.display_status = "Pending"

    return render(
        request,
        "invoice_list.html",
        {
            "invoices": invoices,
            "search": search,
            "status": status,
        }
    )
# =========================================================
# Add Invoice
# =========================================================

@login_required
def add_invoice(request):

    customers = Customer.objects.all().order_by("name")
    products = Product.objects.all().order_by("name")

    if request.method == "POST":

        customer_id = request.POST.get("customer")
        product_ids = request.POST.getlist("product")
        quantities = request.POST.getlist("quantity")

        discount_value = request.POST.get("discount", "0").strip()
        tax_value = request.POST.get("tax", "0").strip()

        # -----------------------------
        # Basic validation
        # -----------------------------
        if not customer_id:
            return render(
                request,
                "add_invoice.html",
                {
                    "customers": customers,
                    "products": products,
                    "error": "Please select a customer."
                }
            )

        if not product_ids or not quantities:
            return render(
                request,
                "add_invoice.html",
                {
                    "customers": customers,
                    "products": products,
                    "error": "Please add at least one product."
                }
            )

        if len(product_ids) != len(quantities):
            return render(
                request,
                "add_invoice.html",
                {
                    "customers": customers,
                    "products": products,
                    "error": "Invalid product or quantity data."
                }
            )

        # -----------------------------
        # Customer validation
        # -----------------------------
        customer = get_object_or_404(Customer, id=customer_id)

        # -----------------------------
        # Discount and tax validation
        # -----------------------------
        try:
            discount = Decimal(discount_value or "0")
            tax = Decimal(tax_value or "0")
        except:
            return render(
                request,
                "add_invoice.html",
                {
                    "customers": customers,
                    "products": products,
                    "error": "Discount and tax must be valid numbers."
                }
            )

        if discount < 0 or tax < 0:
            return render(
                request,
                "add_invoice.html",
                {
                    "customers": customers,
                    "products": products,
                    "error": "Discount and tax cannot be negative."
                }
            )

        subtotal = Decimal("0")

        # Store validated items before creating invoice
        invoice_items = []

        # -----------------------------
        # Validate products & stock
        # -----------------------------
        with transaction.atomic():

            for product_id, quantity_value in zip(product_ids, quantities):

                if not product_id:
                    continue

                try:
                    quantity = int(quantity_value)

                    if quantity <= 0:
                        raise ValueError

                except:
                    return render(
                        request,
                        "add_invoice.html",
                        {
                            "customers": customers,
                            "products": products,
                            "error": "Quantity must be a valid positive number."
                        }
                    )

                # Lock product row while checking stock
                product = get_object_or_404(
                    Product.objects.select_for_update(),
                    id=product_id
                )

                if product.stock <= 0:
                    return render(
                        request,
                        "add_invoice.html",
                        {
                            "customers": customers,
                            "products": products,
                            "error": f"{product.name} is out of stock."
                        }
                    )

                if quantity > product.stock:
                    return render(
                        request,
                        "add_invoice.html",
                        {
                            "customers": customers,
                            "products": products,
                            "error": (
                                f"Only {product.stock} units of "
                                f"{product.name} are available."
                            )
                        }
                    )

                item_total = product.price * quantity

                subtotal += item_total

                invoice_items.append(
                    {
                        "product": product,
                        "quantity": quantity,
                        "price": product.price,
                        "total": item_total,
                    }
                )

            # -----------------------------
            # Discount validation
            # -----------------------------
            if discount > subtotal:
                return render(
                    request,
                    "add_invoice.html",
                    {
                        "customers": customers,
                        "products": products,
                        "error": "Discount cannot be greater than subtotal."
                    }
                )

            # -----------------------------
            # Grand total
            # -----------------------------
            grand_total = subtotal - discount + tax

            if grand_total < 0:
                grand_total = Decimal("0")

            # -----------------------------
            # Generate invoice
            # -----------------------------
            invoice = Invoice.objects.create(
                invoice_number=generate_invoice_number(),
                customer=customer,
                subtotal=subtotal,
                discount=discount,
                tax=tax,
                grand_total=grand_total,
                payment_status="Pending",
            )

            # -----------------------------
            # Create invoice items
            # Reduce stock
            # -----------------------------
            for item in invoice_items:

                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=item["product"],
                    quantity=item["quantity"],
                    price=item["price"],
                    total=item["total"],
                )

                item["product"].stock -= item["quantity"]
                item["product"].save(update_fields=["stock"])

        # -----------------------------
        # Redirect to invoice detail
        # -----------------------------
        return redirect(
            "invoice_detail",
            id=invoice.id
        )

    return render(
        request,
        "add_invoice.html",
        {
            "customers": customers,
            "products": products,
        }
    )

@login_required
def invoice_detail(request, id):

    invoice = get_object_or_404(
        Invoice.objects.select_related("customer"),
        id=id
    )

    items = invoice.items.select_related("product").all()

    company = CompanyProfile.objects.first()

    paid_amount = invoice.payments.aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    remaining_amount = invoice.grand_total - paid_amount

    if remaining_amount < 0:
        remaining_amount = Decimal("0")

    payments = invoice.payments.all().order_by("-payment_date")

    context = {
        "invoice": invoice,
        "items": items,
        "company": company,
        "paid_amount": paid_amount,
        "remaining_amount": remaining_amount,
        "payments": payments,
    }

    return render(
        request,
        "invoice_detail.html",
        context
    )
# =========================================================
# Download Invoice PDF
# =========================================================

@login_required
def download_invoice_pdf(request, id):

    invoice = get_object_or_404(
        Invoice.objects
        .select_related("customer"),
        id=id
    )


    items = (
        invoice.items
        .select_related("product")
    )


    company = CompanyProfile.objects.first()


    response = HttpResponse(
        content_type="application/pdf"
    )


    response["Content-Disposition"] = (
        f'attachment; '
        f'filename="Invoice-{invoice.invoice_number}.pdf"'
    )


    pdf = canvas.Canvas(
        response,
        pagesize=A4
    )


    width, height = A4


    # -------------------------------------------------
    # Company Details
    # -------------------------------------------------

    y = height - 40


    if company:

        pdf.setFont(
            "Helvetica-Bold",
            18
        )

        pdf.drawString(
            40,
            y,
            company.company_name
        )


        y -= 20


        pdf.setFont(
            "Helvetica",
            10
        )


        if company.address:

            pdf.drawString(
                40,
                y,
                company.address[:90]
            )

            y -= 15


        if company.phone:

            pdf.drawString(
                40,
                y,
                f"Phone: {company.phone}"
            )

            y -= 15


        if company.email:

            pdf.drawString(
                40,
                y,
                f"Email: {company.email}"
            )

            y -= 15


        if company.gst_number:

            pdf.drawString(
                40,
                y,
                f"GSTIN: {company.gst_number}"
            )

            y -= 25


    else:

        pdf.setFont(
            "Helvetica-Bold",
            18
        )

        pdf.drawString(
            40,
            y,
            "SmartBilling"
        )

        y -= 30


    # -------------------------------------------------
    # Invoice Heading
    # -------------------------------------------------

    pdf.setFont(
        "Helvetica-Bold",
        16
    )

    pdf.drawString(
        40,
        y,
        "INVOICE"
    )


    y -= 25


    pdf.setFont(
        "Helvetica",
        10
    )


    pdf.drawString(
        40,
        y,
        f"Invoice Number: {invoice.invoice_number}"
    )


    y -= 15


    pdf.drawString(
        40,
        y,
        f"Customer: {invoice.customer.name}"
    )


    y -= 15


    pdf.drawString(
        40,
        y,
        (
            "Date: "
            +
            invoice.invoice_date.strftime(
                "%d-%m-%Y %H:%M"
            )
        )
    )


    y -= 30


    # -------------------------------------------------
    # Table Header
    # -------------------------------------------------

    pdf.setFont(
        "Helvetica-Bold",
        10
    )


    pdf.drawString(
        40,
        y,
        "Product"
    )


    pdf.drawString(
        270,
        y,
        "Qty"
    )


    pdf.drawString(
        330,
        y,
        "Price"
    )


    pdf.drawString(
        420,
        y,
        "Total"
    )


    y -= 10


    pdf.line(
        40,
        y,
        550,
        y
    )


    y -= 20


    # -------------------------------------------------
    # Items
    # -------------------------------------------------

    pdf.setFont(
        "Helvetica",
        10
    )


    for item in items:

        product_name = item.product.name[:35]


        pdf.drawString(
            40,
            y,
            product_name
        )


        pdf.drawString(
            270,
            y,
            str(item.quantity)
        )


        pdf.drawString(
            330,
            y,
            f"Rs. {item.price}"
        )


        pdf.drawString(
            420,
            y,
            f"Rs. {item.total}"
        )


        y -= 20


        if y < 100:

            pdf.showPage()

            y = height - 50


    # -------------------------------------------------
    # Summary
    # -------------------------------------------------

    y -= 10


    pdf.line(
        330,
        y,
        550,
        y
    )


    y -= 20


    pdf.setFont(
        "Helvetica",
        10
    )


    pdf.drawString(
        330,
        y,
        "Subtotal:"
    )


    pdf.drawRightString(
        550,
        y,
        f"Rs. {invoice.subtotal}"
    )


    y -= 18


    pdf.drawString(
        330,
        y,
        "Discount:"
    )


    pdf.drawRightString(
        550,
        y,
        f"Rs. {invoice.discount}"
    )


    y -= 18


    pdf.drawString(
        330,
        y,
        "Tax:"
    )


    pdf.drawRightString(
        550,
        y,
        f"Rs. {invoice.tax}"
    )


    y -= 20


    pdf.setFont(
        "Helvetica-Bold",
        12
    )


    pdf.drawString(
        330,
        y,
        "Grand Total:"
    )


    pdf.drawRightString(
        550,
        y,
        f"Rs. {invoice.grand_total}"
    )


    y -= 25


    pdf.setFont(
        "Helvetica-Bold",
        10
    )


    pdf.drawString(
        330,
        y,
        f"Payment Status: {invoice.payment_status}"
    )


    # Footer

    pdf.setFont(
        "Helvetica",
        9
    )


    pdf.drawString(
        40,
        40,
        "Thank you for your business!"
    )


    pdf.save()


    return response


# =========================================================
# Sales History
# =========================================================

@login_required
def sales_history(request):

    search = request.GET.get(
        "search",
        ""
    ).strip()


    status = request.GET.get(
        "status",
        ""
    ).strip()


    sales = (
        Invoice.objects
        .select_related("customer")
        .prefetch_related("items")
        .order_by("-invoice_date")
    )


    # Search
    if search:

        sales = sales.filter(
            Q(
                invoice_number__icontains=search
            )
            |
            Q(
                customer__name__icontains=search
            )
        )


    # Status filter
    if status:

        sales = sales.filter(
            payment_status=status
        )


    # Filtered sales total
    total_sales = (
        sales.aggregate(
            total=Sum("grand_total")
        )["total"]
        or Decimal("0.00")
    )


    context = {

        "sales": sales,

        "search": search,

        "status": status,

        "total_sales": total_sales,
    }


    return render(
        request,
        "sales_history.html",
        context
    )
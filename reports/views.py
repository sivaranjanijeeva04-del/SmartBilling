import csv
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from products.models import Product
from customers.models import Customer
from billing.models import Invoice
from payments.models import Payment


@login_required
def reports_dashboard(request):

    # =========================================================
    # DATE FILTER
    # =========================================================

    date_filter = request.GET.get(
        "date_filter",
        "all"
    ).strip()

    start_date = None
    end_date = None

    today = timezone.localdate()


    # Today
    if date_filter == "today":

        start_date = today
        end_date = today


    # This Week
    elif date_filter == "week":

        start_date = (
            today - timedelta(days=today.weekday())
        )

        end_date = today


    # This Month
    elif date_filter == "month":

        start_date = today.replace(day=1)

        end_date = today


    # This Year
    elif date_filter == "year":

        start_date = today.replace(
            month=1,
            day=1
        )

        end_date = today


    # Custom Date
    elif date_filter == "custom":

        start_date_value = request.GET.get(
            "start_date",
            ""
        ).strip()

        end_date_value = request.GET.get(
            "end_date",
            ""
        ).strip()


        try:

            if start_date_value:
                start_date = datetime.strptime(
                    start_date_value,
                    "%Y-%m-%d"
                ).date()


            if end_date_value:
                end_date = datetime.strptime(
                    end_date_value,
                    "%Y-%m-%d"
                ).date()


        except ValueError:

            start_date = None
            end_date = None


    # =========================================================
    # BASE QUERYSETS
    # =========================================================

    invoice_queryset = Invoice.objects.all()

    payment_queryset = Payment.objects.all()


    # =========================================================
    # APPLY DATE FILTER
    # =========================================================

    if start_date and end_date:

        start_datetime = timezone.make_aware(
            datetime.combine(
                start_date,
                time.min
            )
        )

        end_datetime = timezone.make_aware(
            datetime.combine(
                end_date,
                time.max
            )
        )


        invoice_queryset = invoice_queryset.filter(
            invoice_date__range=[
                start_datetime,
                end_datetime
            ]
        )


        payment_queryset = payment_queryset.filter(
            payment_date__range=[
                start_datetime,
                end_datetime
            ]
        )


    elif start_date:

        start_datetime = timezone.make_aware(
            datetime.combine(
                start_date,
                time.min
            )
        )


        invoice_queryset = invoice_queryset.filter(
            invoice_date__gte=start_datetime
        )


        payment_queryset = payment_queryset.filter(
            payment_date__gte=start_datetime
        )


    elif end_date:

        end_datetime = timezone.make_aware(
            datetime.combine(
                end_date,
                time.max
            )
        )


        invoice_queryset = invoice_queryset.filter(
            invoice_date__lte=end_datetime
        )


        payment_queryset = payment_queryset.filter(
            payment_date__lte=end_datetime
        )


    # =========================================================
    # SYSTEM OVERVIEW
    # =========================================================

    total_products = Product.objects.count()

    total_customers = Customer.objects.count()

    total_invoices = invoice_queryset.count()

    total_payments = payment_queryset.count()


    # =========================================================
    # TOTAL SALES
    # =========================================================

    total_sales = (
        invoice_queryset.aggregate(
            total=Sum("grand_total")
        )["total"]
        or Decimal("0.00")
    )


    # =========================================================
    # TOTAL PAID
    # =========================================================

    total_paid = (
        payment_queryset.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )


    # =========================================================
    # PENDING AMOUNT
    # =========================================================

    pending_amount = (
        total_sales - total_paid
    )


    if pending_amount < 0:

        pending_amount = Decimal("0.00")


    # =========================================================
    # INVOICE STATUS
    # =========================================================

    paid_invoices = invoice_queryset.filter(
        payment_status="Paid"
    ).count()


    partial_invoices = invoice_queryset.filter(
        payment_status="Partial"
    ).count()


    pending_invoices = invoice_queryset.filter(
        payment_status="Pending"
    ).count()


    # =========================================================
    # PAYMENT METHOD - CASH
    # =========================================================

    cash_total = (
        payment_queryset
        .filter(
            payment_method="Cash"
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )


    # =========================================================
    # PAYMENT METHOD - CARD
    # =========================================================

    card_total = (
        payment_queryset
        .filter(
            payment_method="Card"
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )


    # =========================================================
    # PAYMENT METHOD - UPI
    # =========================================================

    upi_total = (
        payment_queryset
        .filter(
            payment_method="UPI"
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )


    # =========================================================
    # PAYMENT METHOD - BANK TRANSFER
    # =========================================================

    bank_total = (
        payment_queryset
        .filter(
            payment_method="Bank Transfer"
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )


    # =========================================================
    # RECENT PAYMENTS
    # =========================================================

    recent_payments = (
        payment_queryset
        .select_related(
            "invoice",
            "invoice__customer"
        )
        .order_by(
            "-payment_date"
        )[:5]
    )


    # =========================================================
    # RECENT INVOICES
    # =========================================================

    recent_invoices = (
        invoice_queryset
        .select_related(
            "customer"
        )
        .order_by(
            "-invoice_date"
        )[:5]
    )


    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        # System Overview
        "total_products": total_products,
        "total_customers": total_customers,
        "total_invoices": total_invoices,
        "total_payments": total_payments,


        # Sales
        "total_sales": total_sales,
        "total_paid": total_paid,
        "pending_amount": pending_amount,


        # Invoice Status
        "paid_invoices": paid_invoices,
        "partial_invoices": partial_invoices,
        "pending_invoices": pending_invoices,


        # Payment Methods
        "cash_total": cash_total,
        "card_total": card_total,
        "upi_total": upi_total,
        "bank_total": bank_total,


        # Recent Activity
        "recent_payments": recent_payments,
        "recent_invoices": recent_invoices,


        # Date Filter
        "date_filter": date_filter,

        "start_date": (
            start_date.strftime("%Y-%m-%d")
            if start_date
            else ""
        ),

        "end_date": (
            end_date.strftime("%Y-%m-%d")
            if end_date
            else ""
        ),
    }


    return render(
        request,
        "reports.html",
        context
    )


# =============================================================
# CSV EXPORT
# =============================================================

@login_required
def export_reports_csv(request):

    # ---------------------------------------------------------
    # Date Filter
    # ---------------------------------------------------------

    date_filter = request.GET.get(
        "date_filter",
        "all"
    ).strip()

    start_date = None
    end_date = None

    today = timezone.localdate()


    # Today
    if date_filter == "today":

        start_date = today
        end_date = today


    # This Week
    elif date_filter == "week":

        start_date = (
            today - timedelta(days=today.weekday())
        )

        end_date = today


    # This Month
    elif date_filter == "month":

        start_date = today.replace(day=1)

        end_date = today


    # This Year
    elif date_filter == "year":

        start_date = today.replace(
            month=1,
            day=1
        )

        end_date = today


    # Custom Date
    elif date_filter == "custom":

        start_date_value = request.GET.get(
            "start_date",
            ""
        ).strip()

        end_date_value = request.GET.get(
            "end_date",
            ""
        ).strip()


        try:

            if start_date_value:

                start_date = datetime.strptime(
                    start_date_value,
                    "%Y-%m-%d"
                ).date()


            if end_date_value:

                end_date = datetime.strptime(
                    end_date_value,
                    "%Y-%m-%d"
                ).date()


        except ValueError:

            start_date = None
            end_date = None


    # ---------------------------------------------------------
    # Querysets
    # ---------------------------------------------------------

    invoices = (
        Invoice.objects
        .select_related("customer")
        .all()
        .order_by("-invoice_date")
    )


    payments = (
        Payment.objects
        .select_related(
            "invoice",
            "invoice__customer"
        )
        .all()
        .order_by("-payment_date")
    )


    # ---------------------------------------------------------
    # Date Filtering
    # ---------------------------------------------------------

    if start_date and end_date:

        start_datetime = timezone.make_aware(
            datetime.combine(
                start_date,
                time.min
            )
        )

        end_datetime = timezone.make_aware(
            datetime.combine(
                end_date,
                time.max
            )
        )


        invoices = invoices.filter(
            invoice_date__range=[
                start_datetime,
                end_datetime
            ]
        )


        payments = payments.filter(
            payment_date__range=[
                start_datetime,
                end_datetime
            ]
        )


    elif start_date:

        start_datetime = timezone.make_aware(
            datetime.combine(
                start_date,
                time.min
            )
        )


        invoices = invoices.filter(
            invoice_date__gte=start_datetime
        )


        payments = payments.filter(
            payment_date__gte=start_datetime
        )


    elif end_date:

        end_datetime = timezone.make_aware(
            datetime.combine(
                end_date,
                time.max
            )
        )


        invoices = invoices.filter(
            invoice_date__lte=end_datetime
        )


        payments = payments.filter(
            payment_date__lte=end_datetime
        )


    # ---------------------------------------------------------
    # Create CSV Response
    # ---------------------------------------------------------

    response = HttpResponse(
        content_type="text/csv"
    )


    response["Content-Disposition"] = (
        'attachment; filename="smartbilling_report.csv"'
    )


    writer = csv.writer(response)


    # =========================================================
    # INVOICE REPORT
    # =========================================================

    writer.writerow([
        "INVOICE REPORT"
    ])


    writer.writerow([
        "Invoice Number",
        "Customer",
        "Invoice Date",
        "Invoice Total",
        "Payment Status"
    ])


    for invoice in invoices:

        writer.writerow([

            invoice.invoice_number,

            invoice.customer.name,

            invoice.invoice_date.strftime(
                "%d-%m-%Y"
            ),

            invoice.grand_total,

            invoice.payment_status,

        ])


    # Empty Row

    writer.writerow([])

    writer.writerow([])


    # =========================================================
    # PAYMENT REPORT
    # =========================================================

    writer.writerow([
        "PAYMENT HISTORY"
    ])


    writer.writerow([
        "Invoice Number",
        "Customer",
        "Payment Date",
        "Amount",
        "Payment Method",
        "Notes"
    ])


    for payment in payments:

        writer.writerow([

            payment.invoice.invoice_number,

            payment.invoice.customer.name,

            payment.payment_date.strftime(
                "%d-%m-%Y"
            ),

            payment.amount,

            payment.payment_method,

            payment.notes,

        ])


    return response
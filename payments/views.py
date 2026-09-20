from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from .models import Payment
from billing.models import Invoice


@login_required
def payment_list(request):

    search = request.GET.get("search", "").strip()
    payment_method = request.GET.get("payment_method", "").strip()

    payments = Payment.objects.select_related(
        "invoice",
        "invoice__customer"
    ).all().order_by("-payment_date")

    if search:
        payments = payments.filter(
            Q(invoice__invoice_number__icontains=search)
            | Q(invoice__customer__name__icontains=search)
        )

    if payment_method:
        payments = payments.filter(
            payment_method=payment_method
        )

    total_payments = payments.aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    cash_total = payments.filter(
        payment_method="Cash"
    ).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    upi_total = payments.filter(
        payment_method="UPI"
    ).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    card_total = payments.filter(
        payment_method="Card"
    ).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    context = {
        "payments": payments,
        "search": search,
        "payment_method": payment_method,
        "total_payments": total_payments,
        "cash_total": cash_total,
        "upi_total": upi_total,
        "card_total": card_total,
    }

    return render(
        request,
        "payments.html",
        context
    )


@login_required
def add_payment(request):

    # Only invoices which still have balance
    invoices = Invoice.objects.filter(
        payment_status__in=["Pending", "Partial"]
    ).select_related(
        "customer"
    ).order_by("-invoice_date")

    invoice_data = []

    for invoice in invoices:

        paid_amount = invoice.payments.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        remaining_amount = invoice.grand_total - paid_amount

        if remaining_amount < 0:
            remaining_amount = Decimal("0")

        invoice_data.append({
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "customer_name": invoice.customer.name,
            "grand_total": invoice.grand_total,
            "paid_amount": paid_amount,
            "remaining_amount": remaining_amount,
        })

    selected_invoice_id = request.GET.get("invoice", "")

    if request.method == "POST":

        invoice_id = request.POST.get("invoice")
        amount_value = request.POST.get("amount", "").strip()
        payment_method = request.POST.get("payment_method", "").strip()
        notes = request.POST.get("notes", "").strip()

        # -----------------------------
        # Basic validation
        # -----------------------------
        if not invoice_id:
            return render(
                request,
                "add_payment.html",
                {
                    "invoice_data": invoice_data,
                    "selected_invoice_id": selected_invoice_id,
                    "error": "Please select an invoice."
                }
            )

        if not amount_value:
            return render(
                request,
                "add_payment.html",
                {
                    "invoice_data": invoice_data,
                    "selected_invoice_id": invoice_id,
                    "error": "Please enter payment amount."
                }
            )

        try:
            amount = Decimal(amount_value)
        except:
            return render(
                request,
                "add_payment.html",
                {
                    "invoice_data": invoice_data,
                    "selected_invoice_id": invoice_id,
                    "error": "Please enter a valid payment amount."
                }
            )

        if amount <= 0:
            return render(
                request,
                "add_payment.html",
                {
                    "invoice_data": invoice_data,
                    "selected_invoice_id": invoice_id,
                    "error": "Payment amount must be greater than zero."
                }
            )

        allowed_methods = [
            "Cash",
            "Card",
            "UPI",
            "Bank Transfer",
        ]

        if payment_method not in allowed_methods:
            return render(
                request,
                "add_payment.html",
                {
                    "invoice_data": invoice_data,
                    "selected_invoice_id": invoice_id,
                    "error": "Please select a valid payment method."
                }
            )

        # -----------------------------
        # Lock invoice during payment
        # -----------------------------
        with transaction.atomic():

            invoice = get_object_or_404(
                Invoice.objects.select_for_update(),
                id=invoice_id
            )

            paid_amount = invoice.payments.aggregate(
                total=Sum("amount")
            )["total"] or Decimal("0")

            remaining_amount = invoice.grand_total - paid_amount

            if remaining_amount <= 0:
                invoice.payment_status = "Paid"
                invoice.save(update_fields=["payment_status"])

                return render(
                    request,
                    "add_payment.html",
                    {
                        "invoice_data": invoice_data,
                        "selected_invoice_id": invoice_id,
                        "error": "This invoice is already fully paid."
                    }
                )

            if amount > remaining_amount:
                return render(
                    request,
                    "add_payment.html",
                    {
                        "invoice_data": invoice_data,
                        "selected_invoice_id": invoice_id,
                        "error": (
                            f"Payment amount cannot exceed remaining "
                            f"balance of ₹{remaining_amount:.2f}."
                        )
                    }
                )

            # -----------------------------
            # Create payment
            # -----------------------------
            Payment.objects.create(
                invoice=invoice,
                amount=amount,
                payment_method=payment_method,
                notes=notes,
            )

            # -----------------------------
            # Update invoice status
            # -----------------------------
            new_paid_amount = paid_amount + amount

            if new_paid_amount >= invoice.grand_total:
                invoice.payment_status = "Paid"

            elif new_paid_amount > 0:
                invoice.payment_status = "Partial"

            else:
                invoice.payment_status = "Pending"

            invoice.save(
                update_fields=["payment_status"]
            )

        return redirect(
            "invoice_detail",
            id=invoice.id
        )

    context = {
        "invoice_data": invoice_data,
        "selected_invoice_id": selected_invoice_id,
    }

    return render(
        request,
        "add_payment.html",
        context
    )
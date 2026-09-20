from django.db import models


class CompanyProfile(models.Model):

    company_name = models.CharField(
        max_length=200,
        default="SmartBilling"
    )

    phone = models.CharField(
        max_length=20,
        blank=True
    )

    email = models.EmailField(
        blank=True
    )

    gst_number = models.CharField(
        max_length=50,
        blank=True
    )

    address = models.TextField(
        blank=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.company_name
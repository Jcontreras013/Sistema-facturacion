from django import forms

from .models import Client, CreditPayment


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "document", "phone", "email", "address", "credit_limit", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "document": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "credit_limit": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CreditPaymentForm(forms.ModelForm):
    class Meta:
        model = CreditPayment
        fields = ["amount", "payment_method", "notes"]
        widgets = {
            "amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01", "autofocus": True}),
            "payment_method": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.TextInput(attrs={"class": "form-control"}),
        }

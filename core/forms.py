from django import forms

from .models import Company


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            "business_name",
            "trade_name",
            "rtn",
            "address",
            "phone",
            "email",
            "invoice_regime",
            "cai_code",
            "establishment_code",
            "emission_point_code",
            "document_type_code",
            "range_start",
            "range_end",
            "next_correlative",
            "emission_limit_date",
            "default_isv_rate",
        ]
        widgets = {
            "business_name": forms.TextInput(attrs={"class": "form-control"}),
            "trade_name": forms.TextInput(attrs={"class": "form-control"}),
            "rtn": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "invoice_regime": forms.Select(attrs={"class": "form-select"}),
            "cai_code": forms.TextInput(attrs={"class": "form-control"}),
            "establishment_code": forms.TextInput(attrs={"class": "form-control"}),
            "emission_point_code": forms.TextInput(attrs={"class": "form-control"}),
            "document_type_code": forms.TextInput(attrs={"class": "form-control"}),
            "range_start": forms.NumberInput(attrs={"class": "form-control"}),
            "range_end": forms.NumberInput(attrs={"class": "form-control"}),
            "next_correlative": forms.NumberInput(attrs={"class": "form-control"}),
            "emission_limit_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "default_isv_rate": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

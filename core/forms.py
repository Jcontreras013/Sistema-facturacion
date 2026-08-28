from django import forms
from django.contrib.auth.models import Group, User

from .models import Company
from .permissions import ADMIN_GROUP, CASHIER_GROUP


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
            "contingency_enabled",
            "contingency_range_start",
            "contingency_range_end",
            "contingency_next_correlative",
            "default_isv_rate",
            "receipt_format",
            "auto_print_on_sale",
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
            "contingency_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "contingency_range_start": forms.NumberInput(attrs={"class": "form-control"}),
            "contingency_range_end": forms.NumberInput(attrs={"class": "form-control"}),
            "contingency_next_correlative": forms.NumberInput(attrs={"class": "form-control"}),
            "default_isv_rate": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "receipt_format": forms.Select(attrs={"class": "form-select"}),
            "auto_print_on_sale": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("contingency_enabled"):
            start = cleaned_data.get("contingency_range_start")
            end = cleaned_data.get("contingency_range_end")
            next_c = cleaned_data.get("contingency_next_correlative")
            if not (start and end):
                raise forms.ValidationError(
                    "Para activar la contingencia sin internet, define el correlativo inicial y final del rango reservado."
                )
            if start > end:
                raise forms.ValidationError("El correlativo inicial de contingencia debe ser menor o igual al final.")
            if not next_c:
                cleaned_data["contingency_next_correlative"] = start
            elif not (start <= next_c <= end + 1):
                raise forms.ValidationError("El próximo correlativo de contingencia debe estar dentro del rango.")
        return cleaned_data


ROLE_CHOICES = [
    (CASHIER_GROUP, "Caja"),
    (ADMIN_GROUP, "Supervisor"),
]


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña", widget=forms.PasswordInput(attrs={"class": "form-control"}), min_length=8
    )
    role = forms.ChoiceField(label="Rol", choices=ROLE_CHOICES, widget=forms.Select(attrs={"class": "form-select"}))

    class Meta:
        model = User
        fields = ["username", "email", "is_active"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            group = Group.objects.get(name=self.cleaned_data["role"])
            user.groups.set([group])
        return user


class UserUpdateForm(forms.ModelForm):
    password = forms.CharField(
        label="Nueva contraseña (dejar en blanco para no cambiarla)",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=False,
        min_length=8,
    )
    role = forms.ChoiceField(label="Rol", choices=ROLE_CHOICES, widget=forms.Select(attrs={"class": "form-select"}))

    class Meta:
        model = User
        fields = ["username", "email", "is_active"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, lock_role=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock_role = lock_role
        if lock_role:
            del self.fields["role"]
            del self.fields["is_active"]

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            if not self.lock_role:
                group = Group.objects.get(name=self.cleaned_data["role"])
                user.groups.set([group])
        return user

from django import forms

from .models import Register


class RegisterForm(forms.ModelForm):
    class Meta:
        model = Register
        fields = ["name", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. Caja 1"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

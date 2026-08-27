from django import forms

from .models import Category, Product, Promotion, PurchaseOrder, Provider, StockMovement


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
        }


class ProviderForm(forms.ModelForm):
    class Meta:
        model = Provider
        fields = ["name", "contact_name", "phone", "email", "address", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "contact_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "code",
            "barcode",
            "name",
            "category",
            "provider",
            "unit",
            "purchase_price",
            "sale_price",
            "wholesale_price",
            "wholesale_min_qty",
            "tax_rate",
            "stock",
            "min_stock",
            "expiration_date",
            "is_active",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "barcode": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "provider": forms.Select(attrs={"class": "form-select"}),
            "unit": forms.Select(attrs={"class": "form-select"}),
            "purchase_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "sale_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "wholesale_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "wholesale_min_qty": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "tax_rate": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "stock": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "min_stock": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "expiration_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_barcode(self):
        return self.cleaned_data.get("barcode") or None


class PromotionForm(forms.ModelForm):
    class Meta:
        model = Promotion
        fields = ["name", "product", "category", "discount_percent", "start_date", "end_date", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. Fin de semana de ofertas"}),
            "product": forms.Select(attrs={"class": "form-select"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "discount_percent": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01", "max": "100"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get("product")
        category = cleaned_data.get("category")
        if not product and not category:
            raise forms.ValidationError("Selecciona un producto o una categoría para la promoción.")
        if product and category:
            raise forms.ValidationError("Elige solo un producto o una categoría, no ambos.")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("La fecha de fin debe ser igual o posterior a la fecha de inicio.")
        return cleaned_data


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ["provider", "notes"]
        widgets = {
            "provider": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.TextInput(attrs={"class": "form-control", "placeholder": "Notas (opcional)"}),
        }


class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ["movement_type", "reason_category", "quantity", "reason"]
        widgets = {
            "movement_type": forms.Select(attrs={"class": "form-select"}),
            "reason_category": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "reason": forms.TextInput(attrs={"class": "form-control", "placeholder": "Detalle (opcional)"}),
        }

import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render

from inventory.models import Product
from sales.models import Sale


@login_required
def dashboard(request):
    today = datetime.date.today()
    today_sales = Sale.objects.filter(created_at__date=today, status="completada")
    today_total = today_sales.aggregate(total=Sum("total"))["total"] or 0

    month_start = today.replace(day=1)
    month_sales = Sale.objects.filter(
        created_at__date__gte=month_start, created_at__date__lte=today, status="completada"
    )
    month_total = month_sales.aggregate(total=Sum("total"))["total"] or 0

    products = Product.objects.filter(is_active=True)
    low_stock_products = [p for p in products if p.is_low_stock][:10]
    recent_sales = Sale.objects.select_related("client", "user").all()[:8]

    return render(
        request,
        "core/dashboard.html",
        {
            "today_sales_count": today_sales.count(),
            "today_total": today_total,
            "month_total": month_total,
            "low_stock_products": low_stock_products,
            "low_stock_count": len(low_stock_products),
            "recent_sales": recent_sales,
            "total_products": products.count(),
        },
    )

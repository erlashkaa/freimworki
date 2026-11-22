from .models import Category


def finance_navigation(request):
    if not request.user.is_authenticated:
        return {"finance_category_count": 0}
    return {
        "finance_category_count": Category.objects.filter(
            owner=request.user,
        ).count(),
    }

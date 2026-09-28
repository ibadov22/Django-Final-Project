from .models import Category


def site_context(request):
    return {"nav_categories": Category.objects.all()}

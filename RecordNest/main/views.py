from django.shortcuts import render
from records.views import get_popular_discogs_records
from collection.recommender_semantic import recommend_records
from collection.models import CachedRecommendation


# Create your views here.
def index(request):
    return render(request, 'main/base.html')


def home(request):
    if request.user.is_authenticated:
        cached = CachedRecommendation.objects.filter(user=request.user).first()
        if cached:
            recs = cached.data
        else:
            recs = recommend_records(request.user, top_n=14)
            CachedRecommendation.objects.update_or_create(
                user=request.user,
                defaults={"data": recs}
            )

        mode = "recommendations"
        records = recs
    else:
        mode = "popular"
        records = get_popular_discogs_records(limit=12)

    return render(request, "main/home.html", {
        "mode": mode,
        "records": records,
    })


from concurrent.futures import ThreadPoolExecutor
from django.core.cache import cache
from .recommender_semantic import recommend_records
from .models import CachedRecommendation

# Un pool global de hilos (máx 4 tareas simultáneas)
executor = ThreadPoolExecutor(max_workers=4)


def update_recommendations_async(user):
    def task():
        try:
            recs = recommend_records(user, top_n=20)

            if recs:
                CachedRecommendation.objects.update_or_create(
                    user=user,
                    defaults={"data": recs}
                )
                print(f"✅ Recomendaciones guardadas en DB para {user.username}")
            else:
                print(f"⚠️ recommend_records devolvió vacío, no se sobrescriben recomendaciones de {user.username}")

        except Exception as e:
            print(f"❌ Error al recalcular recomendaciones: {e}")

    executor.submit(task)

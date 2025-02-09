from django.core.paginator import Paginator
from django.shortcuts import render
import discogs_client

d = discogs_client.Client(
    'RecordNest/0.1',
    user_token='evTZafZyPDstFshQJVwKuGfBhcrbjGgXzYBJdMWl'
)


def search(request):
    query = request.GET.get("q", "").strip()

    try:
        page_number = int(request.GET.get('page', 1))
        if page_number < 1:
            page_number = 1
    except ValueError:
        page_number = 1

    print(f"📄 Página solicitada: {page_number}")

    if not query:
        return render(request, 'records/search.html', {
            'error': "Debes ingresar un término de búsqueda",
            'query': query
        })

    try:
        results = d.search(query, type="master", per_page=8, page=page_number)
        total_pages = results.pages  # Número total de páginas
        print(f"📄 Total de páginas disponibles según Discogs: {total_pages}")

        results_page = results.page(page_number)
        processed_results = []

        for record in results_page:
            try:
                # Obtener `main_release` si está disponible
                main_release = None
                if hasattr(record, 'main_release') and record.main_release:
                    main_release = record.main_release
                    main_release.refresh()

                first_image_url = None
                if main_release and hasattr(main_release, 'images') and main_release.images:
                    first_image_url = main_release.images[0]['uri']
                artists = ', '.join(
                    artist.name for artist in getattr(main_release, 'artists', [])
                ) if main_release and hasattr(main_release, 'artists') else "Desconocido"

                processed_results.append({
                    'image_url': first_image_url,
                    'title': main_release.title if main_release else record.title,
                    'artists': artists
                })
            except Exception as e:
                print(f"⚠️ Error al procesar un resultado ({record.title}): {type(e).__name__} - {e}")

        print(f"✅ Total de resultados en la página {page_number}: {len(processed_results)}")

        paginator = Paginator(processed_results, 8)
        page_obj = paginator.get_page(page_number)

        print(f"🔍 Parámetros GET: {request.GET}")

        return render(request, 'records/search.html', {
            'query': query,
            'page_obj': page_obj,
            'total_pages': total_pages,
            'current_page': page_number
        })

    except Exception as e:
        print(f"❌ Error general en la búsqueda: {type(e).__name__} - {e}")
        return render(request, 'records/search.html', {
            'error': f"Error en la búsqueda: {str(e)}",
            'query': query
        })

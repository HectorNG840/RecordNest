from django.db.models import Count
from django.shortcuts import render
from collection.models import UserRecord, Wishlist
from django.utils import timezone
from datetime import datetime, timedelta
from records.utils import get_discogs_client
from collections import Counter
from users.models import CustomUser as User
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta

def most_added_records(request):
    most_added_qs = (
        UserRecord.objects
        .values('title', 'artists', 'cover_image')
        .annotate(total_added=Count('id'))
        .order_by('-total_added')[:10]
    )

    most_added = []
    for item in most_added_qs:
        most_added.append({
            'title': item['title'],
            'artists': item['artists'] or 'Desconocido',
            'image_url': item['cover_image'] or '/static/images/placeholder-image.png',
            'total_added': item['total_added'],
        })

    context = {
        'most_added': most_added
    }

    return render(request, 'stats/most_added.html', context)


def fetch_master_details(master_id, total_wished):
    d = get_discogs_client()
    try:
        master = d.master(master_id)
        master.refresh()
        release = master.main_release
        release.refresh()
        release_data = release.data

        title = release_data.get('title', 'Sin título')
        artists = ', '.join(a['name'] for a in release_data.get('artists', [])) or 'Desconocido'
        

        image_url = release_data.get('images', [{}])[0].get('uri', '')

        return {
            'master_id': master_id,
            'title': title,
            'artists': artists,
            'total_wished': total_wished,
            'image_url': image_url,
        }

    except Exception as e:
        print(f"❌ Error fetching Discogs master {master_id}: {e}")
        return {
            'master_id': master_id,
            'title': 'Desconocido',
            'artists': 'Desconocido',
            'total_wished': total_wished,
            'image_url': '',
        }


def most_wished_records(request):
    # Contar los discos más añadidos a la wishlist
    most_wished = (
        Wishlist.objects
        .values('discogs_master_id')
        .annotate(total_wished=Count('id'))
        .order_by('-total_wished')[:10]
    )

    most_wished_data = []

    master_ids = [(item['discogs_master_id'], item['total_wished']) for item in most_wished]

    with ThreadPoolExecutor(max_workers=10) as executor:
        most_wished_data = list(executor.map(lambda x: fetch_master_details(x[0], x[1]), master_ids))

    context = {
        'most_wished': most_wished_data
    }

    return render(request, 'stats/most_wished.html', context)


def fetch_record(master_id, total, client):
    try:
        master = client.master(master_id)
        master.refresh()
        release = master.main_release
        release.refresh()
        data = release.data
        return {
            'id': master_id,
            'title': data.get('title', 'Sin título'),
            'artists': ', '.join(a['name'] for a in data.get('artists', [])) or 'Desconocido',
            'cover_image': data.get('images', [{}])[0].get('uri', ''),
            'total': total
        }
    except Exception as e:

        return {
            'id': master_id,
            'title': 'Desconocido',
            'artists': 'Desconocido',
            'cover_image': '/static/images/placeholder-image.png',
            'total': total
        }


def top_records(request):
    list_type = request.GET.get('type', 'wished')

    if list_type == 'added':
        top_records_qs = (
            UserRecord.objects
            .annotate(total=Count('id'))
            .order_by('-total')[:10]
        )

        records = []
        for record in top_records_qs:
            artists_names = ', '.join([a.name for a in record.artists.all()]) or 'Desconocido'
            records.append({
                'id': record.id,
                'title': record.title,
                'artists': artists_names,
                'cover_image': record.cover_image or '/static/images/placeholder-image.png',
                'total': record.total
            })

        title = "Top 10 Discos más añadidos a las colecciones"

    else:

        most_wished = (
            Wishlist.objects
            .values('discogs_master_id')
            .annotate(total=Count('id'))
            .order_by('-total')[:10]
        )

        d = get_discogs_client()
        records_dict = {}

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_master = {
                executor.submit(fetch_record, item['discogs_master_id'], item['total'], d): item
                for item in most_wished
            }
            for future in as_completed(future_to_master):
                record = future.result()
                records_dict[record['id']] = record

        records = [
            records_dict[item['discogs_master_id']]
            for item in most_wished
            if item['discogs_master_id'] in records_dict
        ]

        title = "Top 10 Discos más deseados"

    context = {
        'records': records,
        'title': title,
        'list_type': list_type
    }
    return render(request, 'stats/top_records.html', context)



@login_required
def statistics(request):
    user = request.user
    now = datetime.now()

    # 🔹 Leer filtros desde GET
    start_date_str = request.GET.get("start_date")  # antes era start_month
    end_date_str = request.GET.get("end_date")      # antes era end_month

    start_date = None
    end_date = None

    if start_date_str:
        # convertir string YYYY-MM-DD a datetime
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

    # 🔹 Query base
    user_records_qs = UserRecord.objects.filter(user=user)
    all_records_qs = UserRecord.objects.all()

    # 🔹 Aplicar filtro de fechas solo en los gráficos
    user_records_filtered = user_records_qs
    all_records_filtered = all_records_qs

    if start_date:
        user_records_filtered = user_records_filtered.filter(added_at__date__gte=start_date)
        all_records_filtered = all_records_filtered.filter(added_at__date__gte=start_date)
    if end_date:
        user_records_filtered = user_records_filtered.filter(added_at__date__lte=end_date)
        all_records_filtered = all_records_filtered.filter(added_at__date__lte=end_date)

    # === Estadísticas personales (no se filtran) ===
    total_added = user_records_qs.count()
    total_wished = Wishlist.objects.filter(user=user).count()

    yearly_added = user_records_qs.filter(added_at__year=now.year).count()

    # === Gráficos ===

    # 1️⃣ Discos añadidos por mes del usuario
    records_per_month_qs = (
        user_records_filtered
        .values('added_at__year', 'added_at__month')
        .annotate(count=Count('id'))
        .order_by('added_at__year', 'added_at__month')
    )
    monthly_labels = [f"{r['added_at__year']}-{r['added_at__month']:02d}" for r in records_per_month_qs]
    monthly_values = [r['count'] for r in records_per_month_qs]

    # 2️⃣ Discos añadidos por mes global
    global_records_per_month_qs = (
        all_records_filtered
        .values('added_at__year', 'added_at__month')
        .annotate(count=Count('id'))
        .order_by('added_at__year', 'added_at__month')
    )
    global_monthly_labels = [f"{r['added_at__year']}-{r['added_at__month']:02d}" for r in global_records_per_month_qs]
    global_monthly_values = [r['count'] for r in global_records_per_month_qs]

    # 3️⃣ Estilos del usuario filtrados
    style_list = []
    for r in user_records_filtered:
        if r.styles:
            style_list.extend([g.strip() for g in r.styles.split(',')])
    style_counts = Counter(style_list)
    user_styles = [{'name': g, 'count': c} for g, c in style_counts.most_common(5)]
    user_styles_labels = [x['name'] for x in user_styles]
    user_styles_values = [x['count'] for x in user_styles]

    # 4️⃣ Estilos globales filtrados
    global_styles_list = []
    for r in all_records_filtered:
        if r.styles:
            global_styles_list.extend([g.strip() for g in r.styles.split(',')])
    global_style_counts = Counter(global_styles_list)
    global_styles = [{'name': g, 'count': c} for g, c in global_style_counts.most_common(5)]
    global_styles_labels = [x['name'] for x in global_styles]
    global_styles_values = [x['count'] for x in global_styles]

    # 5️⃣ Artistas globales filtrados
    global_artist_list = []
    for r in all_records_filtered:
        global_artist_list.extend([a.name for a in r.artists.all()])
    global_artist_counts = Counter(global_artist_list)
    global_top_artists = [{'name': a, 'count': c} for a, c in global_artist_counts.most_common(5)]
    global_artist_labels = [x['name'] for x in global_top_artists]
    global_artist_values = [x['count'] for x in global_top_artists]

    # 6️⃣ Artistas del usuario filtrados
    artist_list = []
    for r in user_records_filtered:
        artist_list.extend([a.name for a in r.artists.all()])
    artist_counts = Counter(artist_list)
    top_artists = [{'name': a, 'count': c} for a, c in artist_counts.most_common(5)]
    artist_labels = [x['name'] for x in top_artists]
    artist_values = [x['count'] for x in top_artists]

    # Contexto final
    context = {
        'total_added': total_added,
        'total_wished': total_wished,
        'monthly_labels': monthly_labels,
        'monthly_values': monthly_values,
        'yearly_added': yearly_added,
        'total_users': User.objects.count(),
        'total_records': all_records_qs.count(),
        'total_wishes': Wishlist.objects.count(),
        'user_styles_labels': user_styles_labels,
        'user_styles_values': user_styles_values,
        'global_styles_labels': global_styles_labels,
        'global_styles_values': global_styles_values,
        'global_monthly_labels': global_monthly_labels,
        'global_monthly_values': global_monthly_values,
        'global_artist_labels': global_artist_labels,
        'global_artist_values': global_artist_values,
        'artist_labels': artist_labels,
        'artist_values': artist_values,
        'start_date': start_date_str,
        'end_date': end_date_str,
    }

    return render(request, 'stats/statistics.html', context)



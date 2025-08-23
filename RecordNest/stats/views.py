from django.db.models import Count
from django.shortcuts import render
from collection.models import UserRecord, Wishlist
from django.utils import timezone
from datetime import datetime, timedelta
from records.views import get_discogs_client
from collections import Counter
from users.models import CustomUser as User
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.contrib.auth.decorators import login_required

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

    # Usamos ThreadPoolExecutor para hacer las peticiones concurrentemente
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Ejecutamos las tareas en paralelo
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
        records = (
            UserRecord.objects
            .values('title', 'artists', 'cover_image')
            .annotate(total=Count('id'))
            .order_by('-total')[:10]
        )
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

    # ------------------------
    # Estadísticas personales
    # ------------------------
    total_added = UserRecord.objects.filter(user=user).count()
    total_wished = Wishlist.objects.filter(user=user).count()

    # Discos añadidos por mes/año
    records_per_month_qs = (
        UserRecord.objects
        .filter(user=user)
        .values('added_at__year', 'added_at__month')
        .annotate(count=Count('id'))
        .order_by('added_at__year', 'added_at__month')
    )

    # Preparar datos para el gráfico
    monthly_labels = []
    monthly_values = []
    for r in records_per_month_qs:
        year = r['added_at__year']
        month = r['added_at__month']
        monthly_labels.append(f"{year}-{month:02d}")
        monthly_values.append(r['count'])

    yearly_added = sum([r['count'] for r in records_per_month_qs if r['added_at__year'] == now.year])

    # ------------------------
    # Estadísticas generales
    # ------------------------
    total_users = User.objects.count()
    total_records = UserRecord.objects.count()
    total_wishes = Wishlist.objects.count()

    # ------------------------
    # Estilos más frecuentes del usuario
    # ------------------------
    user_records = UserRecord.objects.filter(user=user)
    style_list = []
    for r in user_records:
        if r.styles:
            style_list.extend([g.strip() for g in r.styles.split(',')])

    style_counts = Counter(style_list)
    user_styles = [{'name': g, 'count': c} for g, c in style_counts.most_common(5)]
    user_styles_labels = [x['name'] for x in user_styles]
    user_styles_values = [x['count'] for x in user_styles]

    # ------------------------
    # Comparación global de estilos
    # ------------------------
    all_records = UserRecord.objects.all()
    global_styles_list = []
    for r in all_records:
        if r.styles:
            global_styles_list.extend([g.strip() for g in r.styles.split(',')])

    global_style_counts = Counter(global_styles_list)
    global_styles = [{'name': g, 'count': c} for g, c in global_style_counts.most_common(5)]
    global_styles_labels = [x['name'] for x in global_styles]
    global_styles_values = [x['count'] for x in global_styles]

    # ------------------------
    # Discos añadidos globalmente por mes/año
    # ------------------------
    global_records_per_month_qs = (
        UserRecord.objects
        .values('added_at__year', 'added_at__month')
        .annotate(count=Count('id'))
        .order_by('added_at__year', 'added_at__month')
    )

    global_monthly_labels = []
    global_monthly_values = []
    for r in global_records_per_month_qs:
        year = r['added_at__year']
        month = r['added_at__month']
        global_monthly_labels.append(f"{year}-{month:02d}")
        global_monthly_values.append(r['count'])

    # ------------------------
    # Artistas más frecuentes globales
    # ------------------------
    global_artist_list = []
    for r in all_records:
        if r.artists:
            global_artist_list.extend([a.strip() for a in r.artists.split(',')])

    global_artist_counts = Counter(global_artist_list)
    global_top_artists = [{'name': a, 'count': c} for a, c in global_artist_counts.most_common(5)]
    global_artist_labels = [x['name'] for x in global_top_artists]
    global_artist_values = [x['count'] for x in global_top_artists]

    # ------------------------
    # Top discos añadidos
    # ------------------------
    top_added_records = (
        UserRecord.objects
        .values('title', 'artists', 'cover_image')
        .annotate(total=Count('id'))
        .order_by('-total')[:10]
    )
    # ------------------------
    # Artistas más frecuentes del usuario
    # ------------------------
    artist_list = []
    for r in user_records:
        if r.artists:
            artist_list.extend([a.strip() for a in r.artists.split(',')])

    artist_counts = Counter(artist_list)
    top_artists = [{'name': a, 'count': c} for a, c in artist_counts.most_common(5)]
    artist_labels = [x['name'] for x in top_artists]
    artist_values = [x['count'] for x in top_artists]

    # ------------------------
    # Contexto final
    # ------------------------

    context = {
        'total_added': total_added,
        'total_wished': total_wished,
        'monthly_labels': monthly_labels,
        'monthly_values': monthly_values,
        'yearly_added': yearly_added,
        'total_users': total_users,
        'total_records': total_records,
        'total_wishes': total_wishes,
        'user_styles_labels': user_styles_labels,
        'user_styles_values': user_styles_values,
        'global_styles_labels': global_styles_labels,
        'global_styles_values': global_styles_values,
        'global_monthly_labels': global_monthly_labels,
        'global_monthly_values': global_monthly_values,
        'global_artist_labels': global_artist_labels,
        'global_artist_values': global_artist_values,
        'top_added_records': top_added_records,
        'artist_labels': artist_labels,
        'artist_values': artist_values,
    }

    return render(request, 'stats/statistics.html', context)


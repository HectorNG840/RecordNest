from requests_oauthlib import OAuth1Session
import discogs_client
from django.conf import settings

def get_oauth_session():
    return OAuth1Session(
        settings.DISCOGS_CONSUMER_KEY,
        client_secret=settings.DISCOGS_CONSUMER_SECRET,
        resource_owner_key=settings.DISCOGS_OAUTH_TOKEN,
        resource_owner_secret=settings.DISCOGS_OAUTH_SECRET
    )


def get_discogs_client():
    return discogs_client.Client(
        'RecordNest/1.0',
        consumer_key=settings.DISCOGS_CONSUMER_KEY,
        consumer_secret=settings.DISCOGS_CONSUMER_SECRET,
        token=settings.DISCOGS_OAUTH_TOKEN,
        secret=settings.DISCOGS_OAUTH_SECRET
    )
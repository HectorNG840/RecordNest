from requests_oauthlib import OAuth1Session

REQUEST_TOKEN_URL = 'https://api.discogs.com/oauth/request_token'
AUTHORIZE_URL = 'https://www.discogs.com/oauth/authorize'
ACCESS_TOKEN_URL = 'https://api.discogs.com/oauth/access_token'

CONSUMER_KEY = 'RGqvUKwokTQuBwTPXLHE'
CONSUMER_SECRET = 'AtLdLqCHnURhKdnnPxxsvEOvhfPGpTUj'
CALLBACK_URL = 'http://localhost/callback'

oauth = OAuth1Session(CONSUMER_KEY, client_secret=CONSUMER_SECRET, callback_uri=CALLBACK_URL)
fetch_response = oauth.fetch_request_token(REQUEST_TOKEN_URL)
resource_owner_key = fetch_response.get('oauth_token')
resource_owner_secret = fetch_response.get('oauth_token_secret')

print("Autoriza la app aquí:")
print(f"{AUTHORIZE_URL}?oauth_token={resource_owner_key}")

verifier = input("Pega el oauth_verifier: ")

oauth = OAuth1Session(
    CONSUMER_KEY,
    client_secret=CONSUMER_SECRET,
    resource_owner_key=resource_owner_key,
    resource_owner_secret=resource_owner_secret,
    verifier=verifier
)
access_token_response = oauth.fetch_access_token(ACCESS_TOKEN_URL)

print("ACCESS TOKEN:", access_token_response['oauth_token'])
print("ACCESS SECRET:", access_token_response['oauth_token_secret'])

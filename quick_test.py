import urllib.request, json

data = json.dumps({'email': 'admin@kmr-mail.online', 'password': 'himarra228'}).encode()
req = urllib.request.Request(
    'http://kmr-mail.online:8000/api/login',
    data=data,
    headers={'Content-Type': 'application/json'}
)
try:
    resp = urllib.request.urlopen(req, timeout=15)
    print(f'Status: {resp.status}')
    print(f'Response: {resp.read().decode()}')
except urllib.error.HTTPError as e:
    print(f'HTTP Error: {e.code}')
    print(f'Response: {e.read().decode()}')
except Exception as e:
    print(f'Error: {e}')

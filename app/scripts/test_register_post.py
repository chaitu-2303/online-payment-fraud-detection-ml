import urllib.parse
import urllib.request
import sys

url = 'http://127.0.0.1:8000/register'
data = urllib.parse.urlencode({
    'username': 'newuser2',
    'password': 'pass1234',
    'confirm_password': 'pass1234',
}).encode('utf-8')

class CustomHTTPRedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_response(self, request, response):
        print(f'Redirect Status: {response.status}')
        return response

req = urllib.request.Request(url, data=data)
opener = urllib.request.build_opener(CustomHTTPRedirectHandler())
try:
    resp = opener.open(req)
    print('Final Status:', resp.getcode())
    if resp.getcode() == 200:
        body = resp.read().decode('utf-8', errors='replace')
        print('Registration returned form (200), checking headers...')
        print('Location:', resp.headers.get('Location', 'N/A'))
except urllib.error.HTTPError as e:
    print('HTTP Error:', e.code, e.msg)
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)

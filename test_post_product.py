import requests
url = 'https://www.example.com/'
try:
    r = requests.post('http://127.0.0.1:5000/scrape', json={'type':'product','url':url}, timeout=10)
    print('HTTP', r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text[:1000])
except Exception as e:
    print('ERROR', e)

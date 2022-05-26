import requests

def parse_raw_html(url, fname):
    r = requests.get(url)
    with open(fname, 'w') as f:
        f.write(r.text)
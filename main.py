from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re

app = Flask(__name__, static_folder='.')
CORS(app)

def scrape_article(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
    except Exception as e:
        return {"title": "No title found", "content": f"Error fetching page: {e}"}

    if response.status_code != 200:
        return {"title": "No title found", "content": f"Error fetching page: status {response.status_code}"}

    soup = BeautifulSoup(response.text, "html.parser")

    # Try JSON-LD first for high-quality fields
    ld = None
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or script.get_text() or '{}')
        except Exception:
            continue
        # data can be a list or dict
        if isinstance(data, list):
            for d in data:
                if isinstance(d, dict) and ('Article' in str(d.get('@type', '')) or 'NewsArticle' in str(d.get('@type', ''))):
                    ld = d
                    break
        elif isinstance(data, dict):
            if 'Article' in str(data.get('@type', '')) or 'NewsArticle' in str(data.get('@type', '')):
                ld = data
                break

    # title: prefer JSON-LD headline, then og:title, then h1
    title = None
    if ld and ld.get('headline'):
        title = ld.get('headline')
    if not title:
        meta_og = soup.find('meta', property='og:title')
        if meta_og and meta_og.get('content'):
            title = meta_og.get('content')
    if not title:
        h1 = soup.find('h1')
        title = h1.get_text(strip=True) if h1 else None

    # description: JSON-LD, meta description, og:description
    description = None
    if ld and ld.get('description'):
        description = ld.get('description')
    if not description:
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc.get('content')
    if not description:
        meta_ogd = soup.find('meta', property='og:description')
        if meta_ogd and meta_ogd.get('content'):
            description = meta_ogd.get('content')

    # content: JSON-LD articleBody or fallbacks (article, main, content containers)
    content = ''
    if ld and ld.get('articleBody'):
        content = ld.get('articleBody')
    else:
        selectors = ['article', 'main', '#content', '#main', '.article', '.post', '.entry-content', '#mw-content-text']
        container = None
        for sel in selectors:
            c = soup.select_one(sel)
            if c:
                container = c
                break
        if not container:
            container = soup

        # collect meaningful paragraphs
        paras = []
        for p in container.find_all('p'):
            text = p.get_text(strip=True)
            if len(text) > 50:
                paras.append(text)
            if len(paras) >= 8:
                break
        content = "\n\n".join(paras)

    # image: try ld or og:image
    image = None
    if ld and ld.get('image'):
        img = ld.get('image')
        if isinstance(img, dict):
            image = img.get('url')
        elif isinstance(img, list):
            image = img[0]
        else:
            image = img
    if not image:
        meta_img = soup.find('meta', property='og:image')
        if meta_img and meta_img.get('content'):
            image = meta_img.get('content')

    return {
        "title": title or "No title found",
        "description": description or "",
        "content": (content or "")[:3000],
        "image": image or ""
    }

def scrape_product(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
    except Exception as e:
        return {"title": "NO product name", "price": "", "description": f"Error fetching page: {e}"}

    if response.status_code != 200:
        return {"title": "NO product name", "price": "", "description": f"Error fetching page: status {response.status_code}"}

    soup = BeautifulSoup(response.text, "html.parser")

    # Try JSON-LD Product data
    ld_product = None
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or script.get_text() or '{}')
        except Exception:
            continue
        if isinstance(data, list):
            for d in data:
                if isinstance(d, dict) and 'Product' in str(d.get('@type', '')):
                    ld_product = d
                    break
        elif isinstance(data, dict) and 'Product' in str(data.get('@type', '')):
            ld_product = data
            break

    title = None
    if ld_product and ld_product.get('name'):
        title = ld_product.get('name')
    else:
        h1 = soup.find('h1')
        title = h1.get_text(strip=True) if h1 else None

    price_text = ''
    availability = ''
    if ld_product:
        offers = ld_product.get('offers') or {}
        if isinstance(offers, list):
            offers = offers[0]
        price_text = offers.get('price') if isinstance(offers, dict) else ''
        availability = offers.get('availability') if isinstance(offers, dict) else ''

    # fallback: look for elements with 'price' in class or itemprop
    if not price_text:
        price_el = soup.select_one('[itemprop~="price"], [class*="price"], [id*="price"]')
        if price_el:
            price_text = price_el.get_text(strip=True)

    # description: JSON-LD description, meta, or paragraph fallback
    desc_text = ''
    if ld_product and ld_product.get('description'):
        desc_text = ld_product.get('description')
    else:
        meta = soup.find('meta', attrs={'name': 'description'})
        if meta and meta.get('content'):
            desc_text = meta.get('content')
        else:
            ps = soup.find_all('p')
            desc_text = '\n\n'.join(p.get_text(strip=True) for p in ps[:4]) if ps else ''

    # image: JSON-LD image or og:image
    image = ''
    if ld_product and ld_product.get('image'):
        img = ld_product.get('image')
        if isinstance(img, list):
            image = img[0]
        elif isinstance(img, dict):
            image = img.get('url', '')
        else:
            image = img
    else:
        meta_img = soup.find('meta', property='og:image')
        if meta_img and meta_img.get('content'):
            image = meta_img.get('content')

    return {
        "title": title or "NO product name",
        "price": price_text or "No price found",
        "availability": availability or "",
        "description": desc_text or "No description found",
        "image": image or ""
    }


def scrape_listing(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
    except Exception as e:
        return {"items": [], "error": f"Error fetching page: {e}"}

    if response.status_code != 200:
        return {"items": [], "error": f"Error fetching page: status {response.status_code}"}

    soup = BeautifulSoup(response.text, "html.parser")

    # Candidate selectors for listing items
    selectors = [
        '.product', '.product-item', '.product-listing', '.item', '.listing',
        'li.product', '.search-result', '.result-item', '.grid-item'
    ]

    candidates = []
    for sel in selectors:
        found = soup.select(sel)
        if found:
            candidates.extend(found)
    # If none found, try common list container children
    if not candidates:
        containers = soup.select('ul, .products, .results, .listing, #results')
        for c in containers:
            candidates.extend(c.find_all('li', recursive=False))

    # Deduplicate and limit
    seen = set()
    items = []
    for el in candidates:
        if len(items) >= 30:
            break
        text = el.get_text(separator=' ', strip=True)
        if not text:
            continue
        key = text[:200]
        if key in seen:
            continue
        seen.add(key)

        # title: look for headings or link text
        title_el = el.select_one('h1, h2, h3, .title, .product-title, a')
        title = title_el.get_text(strip=True) if title_el else (text.split('\n')[0] if text else '')

        # link
        a = el.find('a', href=True)
        link = urljoin(url, a['href']) if a else ''

        # price
        price_el = el.select_one('[class*="price"], [itemprop~="price"], [data-price]')
        price = price_el.get_text(strip=True) if price_el else ''

        # image
        img = el.find('img')
        image = urljoin(url, img.get('src')) if img and img.get('src') else ''

        # snippet: short paragraph or trimmed text
        snippet = ''
        p = el.find('p')
        if p:
            snippet = p.get_text(strip=True)[:200]
        else:
            snippet = text[:200]

        items.append({
            'title': title,
            'url': link,
            'price': price,
            'image': image,
            'snippet': snippet
        })

    return {'items': items}

def scrape_listing(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
    except Exception as e:
        return {"items": [], "error": str(e)}

    if response.status_code != 200:
        return {"items": [], "error": f"Status {response.status_code}"}

    soup = BeautifulSoup(response.text, "html.parser")

    items = []

    # Generic logic: links with titles
    links = soup.select("a")

    for a in links:
        title = a.get_text(strip=True)
        href = a.get("href")

        if not title or not href:
            continue
        if len(title) < 5:
            continue

        items.append({
            "title": title,
            "url": href
        })

        if len(items) >= 10:
            break

    return {
        "count": len(items),
        "items": items
    }

@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.json
    page_type = data["type"]
    url = data["url"]

    if page_type == "article":
        return jsonify(scrape_article(url))
    elif page_type == "product":
        return jsonify(scrape_product(url))
    elif page_type == "listing":
        return jsonify(scrape_listing(url))
    

    return jsonify({"error": "Page type not supported"})


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/<path:filename>')
def serve_file(filename):
    return send_from_directory('.', filename)

if __name__ == "__main__":
    app.run(debug=True)

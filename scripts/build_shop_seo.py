#!/usr/bin/env python3
"""Вписывает в shop.html готовый (без JavaScript) список моделей и разметку Product для Google.
Берёт модели из PRODUCTS и цены/наличие из kaspi-prices.json. Запускается после обновления цен."""
import json, re, os, html as H
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOP = os.path.join(ROOT, 'shop.html'); PR = os.path.join(ROOT, 'kaspi-prices.json')
BASE = 'https://caproyal.kz/'
s = open(SHOP, encoding='utf-8').read()
P = json.loads(re.search(r'const PRODUCTS=(\[.*?\]);', s, re.S).group(1))
try: KP = json.load(open(PR, encoding='utf-8')).get('items', {})
except Exception: KP = {}

def price(p):
    ps = [KP[k]['p'] for k in (f"{p['id']}|{i}" for i in range(len(p['colors']))) if KP.get(k, {}).get('p') and KP[k].get('a')]
    return min(ps) if ps else p['price']
def instock(p):
    rows = [KP.get(f"{p['id']}|{i}") for i in range(len(p['colors']))]
    return not any(rows) or any(r and r.get('a') for r in rows)
sm = lambda u: u[:-5] + '-s.webp'
money = lambda n: f"{n:,}".replace(',', ' ') + ' ₸'

items, cards = [], []
for n, p in enumerate(P, 1):
    pr = price(p); url = f"{BASE}shop.html#m-{p['id']}"
    colors = ', '.join(c['n'] for c in p['colors'])
    items.append({'@type': 'ListItem', 'position': n, 'item': {
        '@type': 'Product', 'name': f"Кепка CAPROYAL модель {p['id']}", 'sku': p['id'], 'url': url,
        'brand': {'@type': 'Brand', 'name': 'CAPROYAL'},
        'image': [BASE + p['cards'][0]] + [BASE + c['img'][0] for c in p['colors']],
        'description': f"{p['mat']}. Форма: {p['form']}. Регулировка: {p['adj']}. Цвета: {colors}.",
        'color': colors, 'material': p['mat'],
        'offers': {'@type': 'Offer', 'price': pr, 'priceCurrency': 'KZT', 'url': url,
                   'availability': 'https://schema.org/' + ('InStock' if instock(p) else 'OutOfStock')}}})
    cards.append(f'<article class="card" data-id="{p["id"]}" style="opacity:1;transform:none">'
                 f'<div class="ph"><img class="a" src="{sm(p["cards"][0])}" alt="Кепка CAPROYAL модель {p["id"]}" loading="lazy"></div>'
                 f'<h2 class="nm">модель {p["id"]}</h2><div class="sub">{H.escape(p["mat"])} · {H.escape(p["form"])}</div>'
                 f'<div class="pr">{money(pr)}</div><div class="dots"><small>цвета: {H.escape(colors)}</small></div></article>')

ld = {'@context': 'https://schema.org', '@type': 'ItemList', 'name': 'Кепки CAPROYAL', 'itemListElement': items}
s = re.sub(r'<!--SEO:JSONLD-->.*?<!--/SEO:JSONLD-->',
           lambda m: '<!--SEO:JSONLD--><script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script><!--/SEO:JSONLD-->', s, flags=re.S)
s = re.sub(r'<!--SEO:GRID-->.*?<!--/SEO:GRID-->', lambda m: '<!--SEO:GRID-->' + ''.join(cards) + '<!--/SEO:GRID-->', s, flags=re.S)
open(SHOP, 'w', encoding='utf-8').write(s)
print('SEO: моделей', len(P))

#!/usr/bin/env python3
"""Обновляет kaspi-prices.json: цены и наличие всех карточек Kaspi из объекта KASPI в shop.html.
Запуск: python3 scripts/kaspi_prices.py  (GitHub Actions запускает сам раз в 3 часа).
Если Kaspi не ответил — старая цена сохраняется, файл не портится."""
import json, re, sys, time, urllib.request, datetime, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOP = os.path.join(ROOT, 'shop.html')
OUT = os.path.join(ROOT, 'kaspi-prices.json')
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/130 Safari/537.36')

html = open(SHOP, encoding='utf-8').read()
kaspi = json.loads(re.search(r'const KASPI=(\{.*?\});\n', html).group(1))
codes = [c for cs in kaspi.values() for sz in cs.values() for c in sz.values()]

try:
    old = json.load(open(OUT, encoding='utf-8'))
except Exception:
    old = {'items': {}}
items = dict(old.get('items', {}))

def fetch(code):
    req = urllib.request.Request(f'https://kaspi.kz/shop/p/{code}/',
                                 headers={'User-Agent': UA, 'Accept-Language': 'ru'})
    with urllib.request.urlopen(req, timeout=25) as r:
        h = r.read().decode('utf-8', 'replace')
    price = None
    for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
        try:
            d = json.loads(b)
        except Exception:
            continue
        for o in (d.get('offers') or []) if isinstance(d, dict) else []:
            if o.get('@type') == 'Offer' and o.get('price'):
                price = int(float(o['price']))
                avail = 'InStock' in (o.get('availability') or '')
                return price, avail
    m = re.search(r'"price":(\d+),"discount"', h)
    if m:
        return int(m.group(1)), True
    return None, False   # карточка открылась, но предложений нет (нет в продаже)

ok = fail = 0
for i, code in enumerate(codes):
    for attempt in range(3):
        try:
            price, avail = fetch(code)
            if price:
                items[code] = {'p': price, 'a': 1 if avail else 0}
            else:
                items[code] = {'p': items.get(code, {}).get('p'), 'a': 0}
            ok += 1
            break
        except Exception as e:
            time.sleep(6 * (attempt + 1))
    else:
        fail += 1          # оставляем прежнее значение
    time.sleep(1.2)

print(f'ok={ok} fail={fail} of {len(codes)}')
if ok == 0:
    print('Kaspi не ответил — файл не меняю'); sys.exit(0)

data = {'updated': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), 'items': items}
if data['items'] == old.get('items'):
    print('цены не изменились'); sys.exit(0)
json.dump(data, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('kaspi-prices.json обновлён')

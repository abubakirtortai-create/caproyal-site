#!/usr/bin/env python3
"""Обновляет kaspi-prices.json: цена и наличие на Kaspi — по одной карточке на каждый цвет модели
(42 карточки вместо 157: у продавца цена одинакова для всех размеров одного цвета).
Ключ в файле: "<модель>|<номер цвета>" → {"p": цена, "a": 1/0 в наличии, "c": код карточки}.
Запуск: python3 scripts/kaspi_prices.py  (GitHub Actions запускает сам раз в 3 часа).
Если Kaspi не ответил — прежняя цена сохраняется, файл не портится."""
import json, re, sys, time, urllib.request, datetime, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOP = os.path.join(ROOT, 'shop.html')
OUT = os.path.join(ROOT, 'kaspi-prices.json')
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/130 Safari/537.36')
MAIN_SIZES = ('59-61', '61-62')   # какую карточку цвета читать

html = open(SHOP, encoding='utf-8').read()
kaspi = json.loads(re.search(r'const KASPI=(\{.*?\});\n', html).group(1))
targets = []
for model, colors in kaspi.items():
    for ci, sizes in colors.items():
        size = next((s for s in MAIN_SIZES if s in sizes), sorted(sizes)[0])
        targets.append((f'{model}|{ci}', sizes[size]))

try:
    old = json.load(open(OUT, encoding='utf-8'))
except Exception:
    old = {}
old_items = {k: v for k, v in old.get('items', {}).items() if '|' in k}   # старый формат (157 кодов) отбрасываем
items = {}

def fetch(code):
    req = urllib.request.Request(f'https://kaspi.kz/shop/p/{code}/',
                                 headers={'User-Agent': UA, 'Accept-Language': 'ru'})
    with urllib.request.urlopen(req, timeout=25) as r:
        h = r.read().decode('utf-8', 'replace')
    for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
        try:
            d = json.loads(b)
        except Exception:
            continue
        for o in (d.get('offers') or []) if isinstance(d, dict) else []:
            if o.get('@type') == 'Offer' and o.get('price'):
                return int(float(o['price'])), 'InStock' in (o.get('availability') or '')
    m = re.search(r'"price":(\d+),"discount"', h)
    if m:
        return int(m.group(1)), True
    return None, False          # карточка есть, но сейчас не продаётся

ok = fail = 0
for key, code in targets:
    prev = old_items.get(key, {})
    for attempt in range(3):
        try:
            price, avail = fetch(code)
            items[key] = {'p': price or prev.get('p'), 'a': 1 if (price and avail) else 0, 'c': code}
            ok += 1
            break
        except Exception:
            time.sleep(5 * (attempt + 1))
    else:
        fail += 1
        if prev:
            items[key] = prev          # Kaspi не ответил — оставляем прежнее
    time.sleep(1)

print(f'ok={ok} fail={fail} of {len(targets)}')
if ok == 0:
    print('Kaspi не ответил — файл не меняю'); sys.exit(0)
if items == old_items:
    print('цены не изменились'); sys.exit(0)
data = {'updated': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), 'items': items}
json.dump(data, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('kaspi-prices.json обновлён')

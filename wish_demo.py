import time
import re
import json
import urllib.parse
from itertools import zip_longest
import requests
import traceback


def get_xsrf() ->dict:
    base_link = 'https://www.wish.com/'
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.162 Safari/537.36"
    }
    resp = requests.get(base_link, headers=headers)
    pattern = re.compile(r'sweeper_uuid="(.*?)";')
    match = pattern.search(resp.text)
    cookies = resp.cookies.get_dict()
    if match:
        cookies.update({'sweeper_uuid': match.group(0)})
    return cookies


def get_login_session(email, password, cookies) ->dict:
    login_link = 'https://www.wish.com/api/email-login'
    payload = urllib.parse.urlencode({
        'email': email, 'password': password, '_buckets': '', '_experiments': ''
    })
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.162 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-XSRFToken': cookies.get('_xsrf'),
    }
    resp = requests.post(login_link, data=payload, headers=headers, cookies=cookies)
    cookies.update({'sweeper_uuid': resp.json().get('sweeper_uuid')})
    cookies.update(resp.cookies.get_dict())
    return cookies


def get_filtered_feed(cid, cookies, page, count) ->dict:
    feed_link = 'https://www.wish.com/api/feed/get-filtered-feed'
    headers = {
        'Accept': "application/json, text/plain, */*",
        'Content-Type': "application/x-www-form-urlencoded",
        'Referer': "https://www.wish.com/feed/tabbed_feed_latest",
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.162 Safari/537.36",
        'X-XSRFToken': cookies.get('_xsrf'),
    }
    for i in range(page):
        payload = urllib.parse.urlencode({
            'count': count, 'offset': i * count,
            'request_categories': False, 'request_branded_filter': False,
            'request_id': cid,
        })
        while True:
            try:
                resp = requests.post(feed_link, data=payload, headers=headers, cookies=cookies, timeout=180)
            except Exception as e:
                time.sleep(60)
                print('ERROR: %s\nSLEEP 60s...' % e)
                continue
            else:
                yield resp.json()
                break


def get_product_detail(cookies, cid) ->dict:
    url = "https://www.wish.com/api/product/get"
    payload = urllib.parse.urlencode({'cid': cid, 'request_sizing_chart_info': True, 'do_not_track': True})
    headers = {
        'Accept': "application/json, text/plain, */*",
        'Content-Type': "application/x-www-form-urlencoded",
        'Referer': "https://www.wish.com/feed/tabbed_feed_latest/product/" + cid,
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.162 Safari/537.36",
        'X-XSRFToken': cookies.get('_xsrf'),
    }

    while True:
        try:
            resp = requests.post(url, data=payload, headers=headers, cookies=cookies, timeout=180)
        except Exception as e:
            time.sleep(60)
            print('ERROR: %s\nSLEEP 60s...' % e)
            continue
        else:
            return resp.json()


def parse_category_json(json_data, category) ->list:
    results = []
    products = json_data['data']['products']
    for product in products:
        try:
            cid = product['id']
            link = 'https://www.wish.com/product/' + cid
            quantity = product['feed_tile_text']
            currency = product['localized_value']['symbol']
            price = product['commerce_product_info']['logging_fields']['log_product_price']
        except KeyError as e:
            # print('KeyError: ' + str(e))
            continue
        rec = {'cid': cid, "link": link, "price": currency + price, "quantity": quantity, "category": category}
        results.append(rec)
    else:
        return results


def parse_product_json(json_data, category, price_flag) ->list:
    contest = json_data['data']['contest']
    title = contest['meta_title']
    description =  "<p class=\"additional-description\">" + contest['description'].replace('\n','<br>') + "</p >"
    contest_selected_picture = contest['contest_selected_picture']
    extra_photo_urls = contest['extra_photo_urls'].values()
    if extra_photo_urls:
        extra_photo_urls = list(extra_photo_urls)
        extra_photo_urls = list(map(lambda s: re.sub(r'small', 'large', s), extra_photo_urls))
        extra_photo_urls.insert(0, contest_selected_picture)
    else:
        extra_photo_urls = [contest_selected_picture]

    results = []
    commerce_product_info = contest['commerce_product_info']['variations']
    rows = list(zip_longest(commerce_product_info, extra_photo_urls[:len(commerce_product_info)]))
    position = 1
    for index, row in enumerate(rows, start=1):
        if row[0] is None:
            break
        price = row[0]['price']
        if index == 1 and int(price) <= price_flag:
            break
        elif int(price) <= price_flag:
            continue
        color = row[0]['color'] if row[0]['color'] else ''
        size = row[0]['size'] if row[0]['size'] else ''
        retail_price = row[0]['retail_price']
        inventory = row[0]['inventory']
        image_link = row[1] if row[1] else ''
        results.append({
            "Collection": category,
            "Handle": title.lower(),
            "Title": title,
            "Body (HTML)": description,
            "Vendor": 'ThePicksmart',
            "Type": "",
            "Tags": "",
            "Published": True,
            "Option1 Name": "Size" if size else '',
            "Option1 Value": size,
            "Option2 Name": "Color" if color else '',
            "Option2 Value": color,
            "Option3 Name": "",
            "Option3 Value": "",
            "Variant SKU": 0,
            "Variant Grams": 0,
            "Variant Inventory Tracker": "",
            "Variant Inventory Qty": inventory,
            "Variant Inventory Policy": "deny",
            "Variant Fulfillment Service": "manual",
            "Variant Price": (price + 14) * 2,
            "Variant Compare At Price": round(retail_price / 0.7),
            "Variant Requires Shipping": False,
            "Variant Taxable": False,
            "Variant Barcode": "",
            "Image Src": image_link,
            "Image Position": position if image_link else '',
            "Image Alt Text": "",
            "Gift Card": False,
            "SEO Title": "",
            "SEO Description": "",
            "Google Shopping ": {
                " Google Product Category": "",
                " Gender": "",
                " Age Group": "",
                " MPN": "",
                " AdWords Grouping": "",
                " AdWords Labels": "",
                " Condition": "",
                " Custom Product": "",
                " Custom Label 0": "",
                " Custom Label 1": "",
                " Custom Label 2": "",
                " Custom Label 3": "",
                " Custom Label 4": ""
            },
            "Variant Image": "",
            "Variant Weight Unit": "kg",
            "Variant Tax Code": ""
        })
        position += 1
    return results


if __name__ == '__main__':
    EMAIL = 'reg@ljh.me'
    PASSWORD = '123456'
    COUNT = 20 # 每页显示数据量
    PAGE = 25 # 每个类型翻页数量
    PRICE_FLAG = 20 # 保留价格大于20的数据

    categories_id = {
        # 'tag_53dc186321a86318bdc87ef8': 'Fashion',
        # 'tag_53dc186421a86318bdc87f20': 'Gadgets',
        # 'tag_53dc314721a86346c126eaec': 'Sports & Outdoors',
        # 'tag_53dc186321a86318bdc87ef9': 'Tops',
        # 'tag_53dc186321a86318bdc87f07': 'Bottoms',
        # 'tag_53dc186421a86318bdc87f1c': 'Watches',
        # 'tag_53dc186421a86318bdc87f31': 'Shoes',
        # 'tag_5899202d6fa88c49f7c6bb5d': 'Automotive',
        # 'tag_53dc2e9e21a86346c126eae4': 'Underwear',
        # 'tag_53dc186421a86318bdc87f22': 'Wallets & Bags',
        # 'tag_53dc186421a86318bdc87f16': 'Accessories',
        # 'tag_54ac6e18f8a0b3724c6c473f': 'Hobbies',
        # 'tag_53dc186421a86318bdc87f0f': 'Phone Upgrades',
        'tag_53e9157121a8633c567eb0c2': 'Home Decor',
    }

    cookies = get_xsrf()
    login_cookies = get_login_session(EMAIL, PASSWORD, cookies)

    for category_id in categories_id:
        generator_categories_json_data = get_filtered_feed(category_id, login_cookies, PAGE, COUNT)
        category = categories_id[category_id]

        with open(category + '.json', 'w') as f:
            f.write('[')
        try:
            for index, json_data in enumerate(generator_categories_json_data, start=1):
                print(category + ' download page %d.' % index)
                category_results = parse_category_json(json_data, category)
                for rec in category_results:
                    cid = rec['cid']
                    print('\t[%s] product detail download.' % cid)
                    product_json = get_product_detail(login_cookies, cid)
                    # 限速在这里
                    time.sleep(3)
                    product_results = parse_product_json(product_json, category, PRICE_FLAG)
                    if product_results:
                        with open(category + '.json', 'a+') as f:
                            f.write(json.dumps(product_results)[1:-1] + ',')
        except:
            traceback.print_exc()
        finally:
            with open(category + '.json', 'rb+') as f:
                f.seek(-1, 2)
                f.write(b']')

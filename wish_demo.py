import time
import re
import json
import urllib.parse
import requests


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


def get_filtered_feed(request_id, cookies, count=20) ->dict:
    feed_link = 'https://www.wish.com/api/feed/get-filtered-feed'
    payload = urllib.parse.urlencode({
        'count': count, 'offset': 0,
        'request_categories': False, 'request_branded_filter': False,
        'request_id': request_id,
    })
    headers = {
        'Accept': "application/json, text/plain, */*",
        'Content-Type': "application/x-www-form-urlencoded",
        'Referer': "https://www.wish.com/feed/tabbed_feed_latest",
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.162 Safari/537.36",
        'X-XSRFToken': cookies.get('_xsrf'),
    }
    resp = requests.post(feed_link, data=payload, headers=headers, cookies=cookies)
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
        except Exception as e:
            print(e)
            continue
        rec = {'cid': cid, "link": link, "price": currency + price, "quantity": quantity, "category": category}
        results.append(rec)
    else:
        return results


def parse_product_json(json_data) ->list:
    contest = json_data['data']['contest']
    title = contest['meta_title']
    description = contest['description']
    contest_selected_picture = contest['contest_selected_picture']

    results = []
    commerce_product_info = contest['commerce_product_info']['variations']
    for rec in commerce_product_info:
        merchant = rec['merchant']
        color = rec['color']
        size = rec['size']
        price = rec['price']
        retail_price = rec['retail_price']
        inventory = rec['inventory']

        results.append({
            "Handle": title.lower(),
            "Title": title,
            "Body (HTML)": description,
            "Vendor": merchant,
            "Type": "",
            "Tags": "",
            "Published": True,
            "Option1 Name": "Size",
            "Option1 Value": size,
            "Option2 Name": "Color",
            "Option2 Value": color,
            "Option3 Name": "",
            "Option3 Value": "",
            "Variant SKU": 0,
            "Variant Grams": 0,
            "Variant Inventory Tracker": "",
            "Variant Inventory Qty": inventory,
            "Variant Inventory Policy": "deny",
            "Variant Fulfillment Service": "manual",
            "Variant Price": price,
            "Variant Compare At Price": retail_price,
            "Variant Requires Shipping": False,
            "Variant Taxable": False,
            "Variant Barcode": "",
            "Image Src": contest_selected_picture,
            "Image Position": 1,
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
            "Variant Image": contest_selected_picture,
            "Variant Weight Unit": "kg",
            "Variant Tax Code": ""
        })
    else:
        return results


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
    resp = requests.post(url, data=payload, headers=headers, cookies=cookies)
    return resp.json()


if __name__ == '__main__':
    EMAIL = 'reg@ljh.me'
    PASSWORD = '123456'
    PER_CATEGORY_ENTRIES_TO_SCRAPE = 20

    categories_id = {
        'tag_53dc186321a86318bdc87ef8': 'Fashion',
        'tag_53dc186421a86318bdc87f20': 'Gadgets',
        'tag_53dc314721a86346c126eaec': 'Sports & Outdoors',
        'tag_53dc186321a86318bdc87ef9': 'Tops',
        'tag_53dc186321a86318bdc87f07': 'Bottoms',
        'tag_53dc186421a86318bdc87f1c': 'Watches',
        'tag_53dc186421a86318bdc87f31': 'Shoes',
        'tag_5899202d6fa88c49f7c6bb5d': 'Automotive',
        'tag_53dc2e9e21a86346c126eae4': 'Underwear',
        'tag_53dc186421a86318bdc87f22': 'Wallets & Bags',
        'tag_53dc186421a86318bdc87f16': 'Accessories',
        'tag_54ac6e18f8a0b3724c6c473f': 'Hobbies',
        'tag_53dc186421a86318bdc87f0f': 'Phone Upgrades',
        'tag_53e9157121a8633c567eb0c2': 'Home Decor',
    }

    cookies = get_xsrf()
    login_cookies = get_login_session(EMAIL, PASSWORD, cookies)

    category_results = []
    for category_id in categories_id:
        json_data = get_filtered_feed(category_id, login_cookies)
        category_results.extend(parse_category_json(json_data, categories_id[category_id]))
        print(categories_id[category_id] + ' download.')
        # break
    #     time.sleep(3)
    # else:
    #     with open('results.json', 'w') as f:
    #         json.dump(results, f)

    product_results = []
    for rec in category_results:
        cid = rec['cid']
        print('\t[%s]product detail download.' % cid)
        product_json = get_product_detail(login_cookies, cid)
        product_results.extend(parse_product_json(product_json))
    else:
        with open('convertcsv.json', 'w') as f:
            json.dump(product_results, f)

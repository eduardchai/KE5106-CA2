import os
import unicodedata
import pprint
import time
import json
import re
import requests
from bs4 import BeautifulSoup as soup
from selenium import webdriver
from selenium.webdriver.common import action_chains
from selenium.webdriver.common.keys import Keys  
from selenium.webdriver.chrome.options import Options
from pymongo import MongoClient

whitelist = ["Instant Booking", "Address"]
base_url = "https://www.hungrygowhere.com"
limit = 9999

client = MongoClient('', #ip_address:port
                     username='', #username
                     password='', #password
                     authSource='admin',
                     authMechanism='SCRAM-SHA-1')

def get_browser(driver=None):
    if driver == "chrome":
        chrome_options = Options()  
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")  
        chrome_options.binary_location = '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary'

        return webdriver.Chrome(executable_path=os.path.abspath("chromedriver"), chrome_options=chrome_options)
    else:
        # pjs = r'C:\Anaconda3\phantomjs.exe' # Windows
        pjs = '/usr/local/bin/phantomjs' # MacOS

        return webdriver.PhantomJS(pjs)

def normalize(text):
    return unicodedata.normalize("NFKD", text).strip()

def get_rating_value(star_view_el):
    rating = 0
    if star_view_el.find("span", "sprite star-voted star-05"):
        rating = 0.5
    elif star_view_el.find("span", "sprite star-voted star-1"):
        rating = 1
    elif star_view_el.find("span", "sprite star-voted star-15"):
        rating = 1.5
    elif star_view_el.find("span", "sprite star-voted star-2"):
        rating = 2
    elif star_view_el.find("span", "sprite star-voted star-25"):
        rating = 2.5
    elif star_view_el.find("span", "sprite star-voted star-3"):
        rating = 3
    elif star_view_el.find("span", "sprite star-voted star-35"):
        rating = 3.5
    elif star_view_el.find("span", "sprite star-voted star-4"):
        rating = 4
    elif star_view_el.find("span", "sprite star-voted star-45"):
        rating = 4.5
    elif star_view_el.find("span", "sprite star-voted star-5"):
        rating = 5

    return rating

def get_latlong_from_postal(postal):
    onemap_url = f'https://developers.onemap.sg/commonapi/search?searchVal={postal}&returnGeom=Y&getAddrDetails=N&pageNum=1'

    res = requests.get(onemap_url)
    data = res.json()
    results = data["results"]

    longitude = None
    latitude = None

    if len(results) > 0:
        result = results[0]
        if "LATITUDE" in result:
            latitude = result["LATITUDE"]
        if "LONGITUDE" in result:
            longitude = result["LONGITUDE"]

    return latitude, longitude

def review_page(url, restaurant_id):
    db = client["KE5106"]

    browser = get_browser("chrome")
    browser.get(url)

    html = browser.page_source
    content = soup(html, "html.parser")

    review_num = content.select("div.module-ibl-navi li.active")[0].text
    review_num = re.findall(r'\d+', review_num)

    if len(review_num) > 0:
        review_num = int(review_num[0])
    else:
        review_num = 0

    col_restaurant = db["hgw_restaurants"]
    if review_num > 0:
        overall_rating_container = content.find("div", {"class":"overall-col overall-total"})
        star_view = overall_rating_container.find("div", {"class":"sprite star-view"})
        rest_rating = get_rating_value(star_view)
        col_restaurant.update_one({'_id':restaurant_id}, {"$set":{"rating":rest_rating}}, upsert=True)

        no_of_pages = int(review_num / 5) + 1
        url_pagination = url + "?sort=helpful_votes&page="

        for i in range(1, no_of_pages+1):
            browser.get(url_pagination+str(i))
            elements = browser.find_elements_by_css_selector("div.entry a.see-all.no-line")
            for element in elements:
                browser.execute_script("arguments[0].click();", element)
                time.sleep(0.3)
            
            html = browser.page_source.encode('utf-8')
            content = soup(html, "html.parser")
            review_list = content.find("div", {"class":"review-list"})
            if review_list:
                col_reviews = db["hgw_reviews"]
                review_items = review_list.find_all("div", {"class":"item review_item"})
                for item in review_items:
                    review = {}
                    entry = item.find("div", {"class":"entry"})
                    review["title"] = normalize(entry.find("h4").text)
                    review["body"] = normalize(entry.find("div", {"class":"desc"}).text)
                    
                    user_detail = entry.find("div", {"class":"user-detail"}).text.split("•")
                    user_detail = [x.strip() for x in user_detail]
                    review["user"] = user_detail[0]
                    review["date"] = user_detail[1]

                    star_view = entry.find("div", {"class":"sprite star-view"})
                    if star_view:
                        review["rating"] = get_rating_value(star_view)
                        review["restaurant_id"] = restaurant_id
                    
                    col_reviews.update_one({'title':review['title']}, {"$set":review}, upsert=True)
    else:
        col_restaurant.update_one({'_id':restaurant_id}, {"$set":{"rating":0}}, upsert=True)

def individual_page(url):
    db = client["KE5106"]
    col = db["hgw_restaurants"]
    
    page = requests.get(url)
    content = soup(page.content, "html.parser")

    data = {}

    data["title"] = normalize(content.find("h1").text)
    data["_id"] = data["title"]

    address = normalize(content.find("p", {"class":"address"}).text)
    data["address"] = address

    postal_code = re.findall(r'\d{6}', address)
    if postal_code:
        postal_code = postal_code[0]
        lat, long = get_latlong_from_postal(postal_code)
        data["postal_code"] = postal_code
        data["latitude"] = lat
        data["longitude"] = long
    else:
        data["postal_code"] = None
        data["latitude"] = None
        data["longitude"] = None

    data["description"] = normalize(content.find("div", {"class":"des-view"}).text)

    dl_elements = content.select("div.info-detail dl.dl-list")

    for dl in dl_elements:
        dt = dl.find("dt").text
        dd = dl.find("dd").text

        if dt not in whitelist:
            key = dt.lower().replace(" ", "_")
            val = dd.strip().replace("\n", " ")
            data[key] = val

    col.update_one({'_id':data['_id']}, {"$set":data}, upsert=True)
    
    review_page_url = url + "review/"
    review_page(review_page_url, data['_id'])
    print(data['_id'], "done!")
    
    return data

def main():
    pp = pprint.PrettyPrinter(indent=2)

    url = base_url + "/restaurant-reservations/"

    browser = get_browser("chrome")
    browser.get(url)

    html = browser.page_source
    content = soup(html, "html.parser")

    directory_container = content.find("ol", {"class":"az-list"})
    li_parents = directory_container.find_all("li", {"class":"box"})
    
    count = 0

    for li_parent in li_parents:
        ul = li_parent.find("ul")
        li_elements = ul.find_all("li") 
        for li in li_elements:
            a_element = li.find("a")
            individual_page(base_url + a_element['href'])
            # pp.pprint(individual_page(base_url + a_element['href']))
            count += 1
            if count == limit:
                return

if __name__ == "__main__":
    main()
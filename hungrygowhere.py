import os
import unicodedata
import pprint
import time
from bs4 import BeautifulSoup as soup
from selenium import webdriver
from selenium.webdriver.common import action_chains
from selenium.webdriver.common.keys import Keys  
from selenium.webdriver.chrome.options import Options

whitelist = ["Instant Booking", "Address"]
base_url = "https://www.hungrygowhere.com"
limit = 3

def get_browser(driver=None):
    if driver == "chrome":
        chrome_options = Options()  
        # chrome_options.add_argument("--headless")  
        chrome_options.binary_location = '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary'

        return webdriver.Chrome(executable_path=os.path.abspath("chromedriver"), chrome_options=chrome_options)
    else:
        # pjs = r'C:\Anaconda3\phantomjs.exe' # Windows
        pjs = '/usr/local/bin/phantomjs' # MacOS

        return webdriver.PhantomJS(pjs)

def normalize(text):
    return unicodedata.normalize("NFKD", text).strip()

def review_page(url):
    browser = get_browser("chrome")
    browser.get(url)
    action = action_chains.ActionChains(browser)

    elem = browser.find_element_by_tag_name("body")

    count = 0
    while True:
        elem.send_keys(Keys.PAGE_DOWN)
        time.sleep(0.2)
        try:
            elements = browser.find_elements_by_css_selector("div.entry a.see-all.no-line")
            print("count", count, len(elements))
            if count >= len(elements):
                break

            count = 0
            for element in elements:
                action.move_to_element(element)
                action.click()
                action.perform()
                count += 1
                time.sleep(0.1)
        except Exception as ex:
            print(ex)

    html = browser.page_source
    content = soup(html, "html.parser")

    reviews = []

    review_list = content.find("div", {"class":"review-list"})

    if review_list:
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
            rating = 0
            if star_view.find("span", "sprite star-voted star-05"):
                rating = 0.5
            elif star_view.find("span", "sprite star-voted star-1"):
                rating = 1
            elif star_view.find("span", "sprite star-voted star-15"):
                rating = 1.5
            elif star_view.find("span", "sprite star-voted star-2"):
                rating = 2
            elif star_view.find("span", "sprite star-voted star-25"):
                rating = 2.5
            elif star_view.find("span", "sprite star-voted star-3"):
                rating = 3
            elif star_view.find("span", "sprite star-voted star-35"):
                rating = 3.5
            elif star_view.find("span", "sprite star-voted star-4"):
                rating = 4
            elif star_view.find("span", "sprite star-voted star-45"):
                rating = 4.5
            elif star_view.find("span", "sprite star-voted star-5"):
                rating = 5

            review["rating"] = rating
            reviews.append(review)

    return reviews


def individual_page(url):
    browser = get_browser()
    browser.get(url)

    try:
        element = browser.find_element_by_css_selector("a.see-all.no-line.read-all")
        element.click()
    except Exception:
        pass
    
    html = browser.page_source
    content = soup(html, "html.parser")

    data = {}

    summary_container = content.find("div", {"class":"module-ibl-summary"})
    data["title"] = normalize(summary_container.find("h1").text)
    data["address"] = normalize(summary_container.find("p", {"class":"address"}).text)
    data["description"] = normalize(summary_container.find("div", {"class":"des-view"}).text)

    try:
        data["review_num"] = summary_container.find("span", {"class":"review-num"}).text
    except Exception:
        data["review_num"] = 0

    info_detail = content.find("div", {"class":"info-detail"})
    dl_elements = info_detail.find_all("dl", {"class":"dl-list"})

    for dl in dl_elements:
        dt = dl.find("dt").text
        dd = dl.find("dd").text

        if dt not in whitelist:
            key = dt.lower().replace(" ", "_")
            val = dd.strip().replace("\n", " ")
            data[key] = val

    review_page_url = url + "review/"
    data["reviews"] = review_page(review_page_url)

    return data

def main():
    pp = pprint.PrettyPrinter(indent=2)

    url = base_url + "/restaurant-reservations/"

    browser = get_browser()
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
            pp.pprint(individual_page(base_url + a_element['href']))
            print("")
            count += 1
            if count == limit:
                return

if __name__ == "__main__":
    main()
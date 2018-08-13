import os
import unicodedata
import pprint
from bs4 import BeautifulSoup as soup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys  
from selenium.webdriver.chrome.options import Options

whitelist = ["Instant Booking", "Address"]
base_url = "https://www.hungrygowhere.com"
limit = 3

def get_browser(driver=None):
    if driver == "chrome":
        chrome_options = Options()  
        chrome_options.add_argument("--headless")  
        chrome_options.binary_location = '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary'

        return webdriver.Chrome(executable_path=os.path.abspath("chromedriver"), chrome_options=chrome_options)
    else:
        # pjs = r'C:\Anaconda3\phantomjs.exe' # Windows
        pjs = '/usr/local/bin/phantomjs' # MacOS

        return webdriver.PhantomJS(pjs)

def normalize(text):
    return unicodedata.normalize("NFKD", text)

def review_page(url):
    browser = get_browser()
    browser.get(url)

    html = browser.page_source
    content = soup(html, "html.parser")

    review = {}

    fav_review = content.find("div", {"class":"module-reviews favourite-review"})
    entry = fav_review.find("div", {"class":"entry"})
    review["title"] = normalize(entry.find("h4").text)

    user_detail = entry.find("div", {"class":"user-detail"}).text.split("•")
    user_detail = [x.strip() for x in user_detail]
    review["user"] = user_detail[0]
    review["review_date"] = user_detail[1]

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
    review["description"] = normalize(entry.find("div", {"class":"desc"}).text)

    return review


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
    data["review_num"] = summary_container.find("span", {"class":"review-num"}).text
    data["description"] = normalize(summary_container.find("div", {"class":"des-view"}).text)

    info_detail = content.find("div", {"class":"info-detail"})
    dl_elements = info_detail.find_all("dl", {"class":"dl-list"})

    for dl in dl_elements:
        dt = dl.find("dt").text
        dd = dl.find("dd").text

        if dt not in whitelist:
            key = dt.lower().replace(" ", "_")
            val = dd.strip().replace("\n", " ")
            data[key] = val

    review_list = content.find("div", {"class":"review-list"})
    review_items = review_list.find_all("div", {"class":"item review_item"})

    reviews = []
    for item in review_items:
        entry = item.find("div", {"class":"entry"})
        h5 = entry.find("h5")
        a_element = h5.find("a")
        review = review_page(base_url + a_element["href"])
        reviews.append(review)

    data["reviews"] = reviews

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
"""
This python script dowloads the meta data of foursquare venues, actual data is
downloaded by another component. To download venues from across Singapore, mrt
location name is used as seeds with a radius of 5 Km.

https://api.foursquare.com/v2/venues/explore api is used to download the meta
data. The mrt names have been taken from shape file downloaded from LTA data
mall (https://www.mytransport.sg/content/dam/datamall/datasets/Geospatial/TrainStation.zip).

Change the limit value in config file to download more venues.

By default, it reads and writes to 'KE5106' database. You may change it in config.py.
"""

from pymongo import MongoClient
import geopandas as gpd
import requests
import time
import json
import config


def explore_location(loc_name, radius, offset):
    url = "https://api.foursquare.com/v2/venues/explore"

    querystring = {"client_id":config.CLIENT_ID,
                   "client_secret":config.CLIENT_SECRET,
                   "near":loc_name+",Singapore",
                   "radius": radius,
                   "offset": offset,
                   "section":"food","limit":"50","v":config.VERSION}
    headers = {
        'Cache-Control': "no-cache",
        }

    response = requests.request("GET", url, headers=headers, params=querystring)
    return json.loads(response.text)

def get_result_count(mrt_name):
    url = "https://api.foursquare.com/v2/venues/explore"

    querystring = {"client_id":config.CLIENT_ID,
                   "client_secret":config.CLIENT_SECRET,
                   "near":mrt_name+", Singapore",
                   "section":"food","limit":"50","v":config.VERSION}
    headers = {
        'Cache-Control': "no-cache",
        }

    response = requests.request("GET", url, headers=headers, params=querystring)
    json_output = json.loads(response.text)
    count = 0
    if(json_output["meta"]["code"] == 200):
        count = json_output["response"]["totalResults"]
    return count

def extract_venues(json_output):
    groups = json_output["response"].get("groups", [])
    items = []
    venues = []
    for group in groups:
        if (group["name"] == "recommended"):
            items = group["items"]
    for item in items:
        venue = item["venue"]
        venue["hasDetails"] = False
        venue["lastScraped"] = int(time.time())
        venue["location"].pop("labeledLatLngs", None)
        venue.pop("photos", None)

        if "categories" in venue:
            for category in venue["categories"]:
                category.pop("icon", None)

        venues.append(venue)
    return venues

def write_to_mongo(client, venues):

    if(check_limit(client)): return

    if(len(venues) >= config.LIMIT):
        print("number of downloaded venues exceed the limit...")
        venues = venues[0:config.LIMIT]

    if(len(venues) == 0): return
    db = client[config.DATABASE]
    db.fsqr_venues_raw.insert_many(venues)
    print("total entries written: ", len(venues))

def check_limit(client):
    db = client[config.DATABASE]
    count = db.fsqr_venues_raw.count_documents({"hasDetails": False})
    if (count >= config.LIMIT): return True
    return False

def main():
    mrt_shp = gpd.read_file("./TrainStation_Oct2017/")
    mrt_names = [" ".join(mrt.split(" ")[:-2]) for mrt in mrt_shp["STN_NAME"]]
    client = MongoClient()
    visited_venues = set()

    for mrt_name in mrt_names:
        if (check_limit(client)): break

        total_results = get_result_count(mrt_name)
        offset = 1
        while offset < total_results:
            json_output = explore_location(mrt_name, 5000, offset)
            if(json_output["meta"]["code"]==200):
                venues = extract_venues(json_output)
                write_to_mongo(client,
                               [venue for venue in venues if venue["id"] not in visited_venues])
                visited_venues.update([venue["id"] for venue in venues])
                print("completed", mrt_name, offset, "total downloaded", len(venues))
            offset += 50

    client.close()

if __name__ == "__main__":
    main()

"""
The purpose of this script is move data dumped in raw layer to access layer.
Cleaning of unecessary keys and denormalization is done here for downloaded venues.

By default, it reads and writes to 'KE5106' database. You may change it in config.py.
"""

from pymongo import MongoClient
from tqdm import tqdm
import config

def transform(venue):

    venue.pop("createdAt", None)

    venue["location"].pop("formattedAddress", None)

    for key in venue["location"]:
        venue[key] = venue["location"][key]
    venue.pop("location", None)

    venue.pop("hasDetails", None)
    venue.pop("lastScraped", None)

    venue["category"] = venue["categories"][0]["name"]
    venue.pop("categories", None)

    groups = venue["attributes"]["groups"]
    for group in groups:
        if group["type"] == "serves":
            venue["serves"] = \
            [serve["displayValue"] for serve in group["items"]]

    venue.pop("attributes", None)
    venue["likes"] = venue["likes"]["count"]

    if ("price" in venue):
        venue["priceTier"] = venue["price"]["tier"]
        venue.pop("price", None)

    venue["tipCount"] = venue["stats"]["tipCount"]
    venue.pop("stats", None)

    if("hours" in venue and "timeframes" in venue["hours"]):
        venue["openHours"] = venue["hours"]["timeframes"]
        venue.pop("hours", None)

    if("popular" in venue and "timeframes" in venue["popular"]):
        venue["popularHours"] = venue["popular"]["timeframes"]
        venue.pop("popular", None)

    return venue

def main():

    client = MongoClient()
    db = client[config.DATABASE]

    all_venues = db.fsqr_venues_raw.find({"hasDetails": True})
    size = db.fsqr_venues_raw.count_documents({"hasDetails": True})
    print("Total venues with details:", size)

    added_venues = set()
    cursor = db.fsqr_venues.find()
    for venue in cursor: added_venues.add(venue["id"])
    print("already in db", len(added_venues))

    for venue in tqdm(all_venues):
        if venue["id"] not in added_venues:
            venue = transform(venue)
            db.fsqr_venues.insert_one(venue)
            added_venues.add(venue["id"])

    #write back
    return None

if __name__ == "__main__":
    main()

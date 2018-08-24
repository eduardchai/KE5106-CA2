"""
This script downloads the venue details for previously downloaded meta data.
Each meta in fsqr_venues_raw collection have lastScraped and hasDetails fields.
Details of only those venues with hasDetails as False will be downloaded.
This is to make sure that, venues which already have details, do not get
downloaded. lastScraped can be used to refresh the details of the previously
downloaded venues, which are past some expiration time.
Though this has not been implemented here.

By default, it reads and writes to 'KE5106' database. You may change it in config.py.
"""
import requests
import json
import config
from pymongo import MongoClient
from time import time
from tqdm import tqdm

STATUS_CODE_SUCCESS = 200

def get_venue_details(venue_id):
    endpoint = "https://api.foursquare.com/v2/venues/" + str(venue_id)
    headers = {
        "Cache-Control": "no-cache"
    }
    params = {
        "client_id": config.CLIENT_ID,
        "client_secret": config.CLIENT_SECRET,
        "v": config.VERSION
    }

    response = requests.get(endpoint, headers=headers, params=params)
    if response.status_code != STATUS_CODE_SUCCESS:
        print("Response Status Code: " + str(response.status_code))
        raise("Not Successful")

    return response.text

def get_venue_hours_details(venue_id):
    endpoint = "https://api.foursquare.com/v2/venues/" + str(venue_id) + "/hours"
    headers = {
        "Cache-Control": "no-cache"
    }
    params = {
        "client_id": config.CLIENT_ID,
        "client_secret": config.CLIENT_SECRET,
        "v": config.VERSION
    }

    response = requests.get(endpoint, headers=headers, params=params)
    if response.status_code != STATUS_CODE_SUCCESS:
        print("Response Status Code: " + str(response.status_code))
        raise("Not Successful")

    return response.text

def extract_venue_hours_details(json_output):
    response = json.loads(json_output)
    hours = response["response"]["hours"]
    popular = response["response"]["popular"]
    for timeframe in hours.get("timeframes", []):
        timeframe.pop("includesToday", None)
        timeframe.pop("segments", None)
    for timeframe in popular.get("timeframes", []):
        timeframe.pop("includesToday", None)
        timeframe.pop("segments", None)
    venue_hours = {
        "hours": hours,
        "popular": popular
    }

    return venue_hours

def extract_venue_details(json_output):
    response = json.loads(json_output)
    venue = response["response"]["venue"]
    venue_id = venue["id"]
    remove_keys_list = [
        "id", "name", "contact", "location", "canonicalUrl","categories",
        "verified", "url", "dislike", "ok", "ratingColor",
        "ratingSignals", "menu", "allowMenuUrlEdit", "beenHere", "specials",
        "photos", "reasons", "hereNow", "tips", "shortUrl","timeZone", "listed",
        "hours", "popular", "pageUpdates", "inbox", "parent", "hierarchy",
        "bestPhoto", "colors"
    ]
    for keys in remove_keys_list:
        venue.pop(keys, None)
    venue["likes"].pop("groups", None)
    venue["likes"].pop("summary", None)

    json_output_venue_hours = get_venue_hours_details(venue_id)
    venue_hours = extract_venue_hours_details(json_output_venue_hours)
    venue = {**venue, **venue_hours}

    return venue

def update_venue_details_mongodb(db, venue_id, venue_details):
    db.fsqr_venues_raw.update(
        {
            "id": venue_id
        },
        {
            "$set": venue_details
        },
        upsert=False
    )
    db.fsqr_venues_raw.update(
        {
            "id": venue_id
        },
        {
            "$set": {
                "hasDetails": True,
                "lastScraped": int(time())
            }
        },
        upsert=False
    )

def get_venue_ids(db):
    return db.fsqr_venues_raw.distinct(
        "id",
        {
            "hasDetails": False
        }
    )

def main():
    client = MongoClient()
    db = client[config.DATABASE]
    print(db)
    venue_ids = get_venue_ids(db)
    for venue_id in tqdm(venue_ids):
        json_output = get_venue_details(venue_id)
        venue_details = extract_venue_details(json_output)
        update_venue_details_mongodb(db, venue_id, venue_details)
    client.close()

if __name__ == "__main__":
    main()

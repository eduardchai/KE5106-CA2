"""
This scrips downloads tips for each of the venue. By using the CLIENT_ID and
CLIENT_SECRET, 2 tips per venue can be downloaed sorted by recency. Only
tips of those venues which are not in fsqr_reviews collection are downloaded.
To add new tips, createdAt field of tips can be used to download only those
tips which are more recent than last most recent tip for that venue.
Maximum of 200 tips can be downloaded, sorted by recency using OAUTH_TOKEN
configuration insead of CLIENT_ID and CLIENT_SECRET.

By default, it reads and writes to 'KE5106' database. You may change it in config.py.
"""

from pymongo import MongoClient
import config
import requests
import json

def download_tips(venue_id):


    url = "https://api.foursquare.com/v2/venues/"+venue_id+"/tips/"

    querystring = {"client_id":config.CLIENT_ID,
                   "client_secret":config.CLIENT_SECRET,
                   "limit":"500","v":config.VERSION,
                   #"oauth_token": config.OAUTH_TOKEN,
                   "offset":"0",
                   "sort":"recent"}

    headers = {
        'Cache-Control': "no-cache",
        }

    response = requests.request("GET", url,
                                headers=headers, params=querystring)

    if response.status_code != 200:
        print("Response Status Code: " + str(response.status_code))
        raise("Not Successful")

    tips_json = json.loads(response.text)

    tips =  tips_json["response"]["tips"]["items"]

    return tips

def clean(tip, venue_id):

    keys_to_remove = ["type","canonicalUrl",
                      "logView","authorInteractionType", "photo",
                      "like","todo","photourl"]
    for key in keys_to_remove:
        tip.pop(key, None)
    tip["user"].pop("photo", None)
    tip["venue_id"] = venue_id
    return tip

def main():
    client = MongoClient()
    db = client[config.DATABASE]

    fsqr_venues = db["fsqr_venues"].find()
    print("total_venues:", fsqr_venues.count())

    added_tips = db.fsqr_reviews.find({})
    venues_set = set([tips["venue_id"] for tips in added_tips])
    print("already added venues: ", len(venues_set))

    for venue in (fsqr_venues):
        if (venue["id"] not in venues_set):
            tips = download_tips(venue["id"])
            tips = [clean(tip, venue["id"]) for tip in tips]
            print(venue["name"],"tips:", len(tips))
            if (len(tips) > 0):
                db.fsqr_reviews.insert_many(tips)
            venues_set.add(venue["id"])

    client.close()


if __name__=="__main__":
    main()

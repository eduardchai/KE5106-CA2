"""
This script is used to merge hungrygowhere and foursquare data. The merging is done by grouping them using postal code and restaurant name similarities. Hence, only data with postal code is considered.
"""
import config
import geopandas
import re, math
from tqdm import tqdm
from collections import Counter
from dateutil import parser
from pymongo import MongoClient
from shapely.geometry import Point

WORD = re.compile(r'\w+')

 # Load shapefile of Singapore subzone
SUBZONE_MAP = geopandas.read_file('./subzone/MP14_SUBZONE_WEB_PL.shp')
SUBZONE_MAP = SUBZONE_MAP.to_crs(epsg=4326)

DATA_RESTAURANTS = []
DATA_REVIEWS = []

# Connect to MongoDB
CLIENT = MongoClient('35.240.220.8:27017',
                    username='AdminUser',
                    password='12345678!',
                    authSource='admin',
                    authMechanism='SCRAM-SHA-1')
DATABASE = CLIENT[config.DATABASE]

def get_cosine(vec1, vec2):
    """
    Calculate cosine distance between 2 sentences to determine their similarities
    """
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])

    sum1 = sum([vec1[x]**2 for x in vec1.keys()])
    sum2 = sum([vec2[x]**2 for x in vec2.keys()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    else:
        return float(numerator) / denominator

def text_to_vector(text):
    """
    Convert text to vector
    """
    words = WORD.findall(text)
    return Counter(words)

def normalise(text):
    """
    Remove non-alphanumeric characters from a sentence and transform to lowercase
    """
    clean = re.sub(r'\([^)]*\)', '', text)
    return re.sub(r'[^a-zA-Z0-9_\s]+', '', clean).strip().lower()

def create_restaurant_id(name, postal):
    """
    Create restaurant id from its name and postal code
    """
    return re.sub(r'[^a-zA-Z0-9_\s]+', '', name).strip().replace(" ", "_").lower() + "_" + postal

def create_review_id(restaurant_id, user, ts):
    """
    Create review id from restaurant id, user name, and timestamp of the review
    """
    return restaurant_id + "_" + user.lower() + "_" + str(ts)

def to_timestamp(text):
    """
    Convert date text into timestamp value
    """
    dt = parser.parse(text)
    return int(dt.timestamp())

def get_subzone(lng, lat):
    """
    Get subzone name by its longitude and latitude
    """
    if lng and lat:
        # Setting the coordinates for the point
        pt = Point((lng, lat)) # Longitude & Latitude
        try:
            subzone_name = SUBZONE_MAP[SUBZONE_MAP.geometry.intersects(pt)].SUBZONE_N.values[0]
            return subzone_name
        except Exception:
            return None
    else:
        return None

def merge_reviews(old_id, restaurant_id):
    """
    Merge foursquare reviews with hungrygowhere reviews
    """
    col_reviews_fsqr = DATABASE["fsqr_reviews"]
    data_fsqr_reviews = list(col_reviews_fsqr.find({"venue_id":old_id}))
    for row in data_fsqr_reviews:
        user = row["user"]["firstName"]
        ts = row["createdAt"]
        review_id = create_review_id(restaurant_id, user, ts)
        DATA_REVIEWS.append({
            "_id": review_id,
            "restaurant_id": restaurant_id,
            "title": None,
            "body": row["text"],
            "date": ts,
            "rating": None,
            "user": user,
            "source": "foursquare"
        })
    
def merge_restaurant(row):
    """
    Merge foursquare restaurants with restaurants reviews
    """
    lat = float(row["lat"]) if row["lat"] else None
    lng = float(row["lng"]) if row["lng"] else None
    
    subzone_name = get_subzone(lng, lat)
        
    DATA_RESTAURANTS.append({
        "_id": create_restaurant_id(row["name"],row["postalCode"]),
        "name": row["name"],
        "postal_code": row["postalCode"],
        "address": row["address"] if "address" in row else None,
        "latitude": lat,
        "longitude": lng,
        "subzone": subzone_name,
        "rating": row["rating"] if "rating" in row else None,
        "category": row["category"],
        "source": "foursquare"
    })

def load_hungrygowhere():
    """
    Load hungrygowhere data
    """
    # Get mongod collections
    col_restaurants_hgw = DATABASE["hgw_restaurants"]
    col_reviews_hgw = DATABASE["hgw_reviews"]

    # Convert record into list
    data_hgw = list(col_restaurants_hgw.find())

    print("Loading hungrygowhere...")
    for row in tqdm(data_hgw):
        restaurant_id = create_restaurant_id(row["title"], row["postal_code"])
        avg_price = None
        if "average_price" in row:
            avg_price = row["average_price"].split(" ")[0].replace("$", "")
        
        lat = float(row["latitude"]) if row["latitude"] else None
        lng = float(row["longitude"]) if row["longitude"] else None

        subzone_name = get_subzone(lng, lat)
            
        DATA_RESTAURANTS.append({
            "_id": restaurant_id,
            "name": row["title"],
            "postal_code": row["postal_code"],
            "address": row["address"],
            "latitude": lat,
            "longitude": lng,
            "subzone": subzone_name,
            "rating": row["rating"],
            "category": row["cuisine"],
            "avg_price": float(avg_price) if avg_price else None,
            "source": "hungrygowhere"
        })
        
        reviews = col_reviews_hgw.find({"restaurant_id":row["_id"]})
        for review in reviews:
            try:
                user = review["user"]
                ts = to_timestamp(review["date"])
                review_id = create_review_id(restaurant_id, user, ts)
                DATA_REVIEWS.append({
                    "_id": review_id,
                    "restaurant_id": restaurant_id,
                    "title": review["title"],
                    "body": review["body"],
                    "date": ts,
                    "rating": review["rating"],
                    "user": user,
                    "source": "hungrygowhere"
                })
            except Exception as ex:
                print(ex)
    print("")

def merge_with_foursquare():
    """
    Merge foursquare data with hungrygowhere data
    """
    # Get mongod collections
    col_restaurants_fsqr = DATABASE["fsqr_venues"]

    # Convert record into list
    data_fsqr = list(col_restaurants_fsqr.find())

    print("Merging hungrygowhere with foursquare...")
    for row_i in tqdm(data_fsqr):
        found = False
        if "postalCode" in row_i:
            for row_j in DATA_RESTAURANTS:
                if row_i["postalCode"] == row_j["postal_code"]:
                    name_hgw = text_to_vector(normalise(row_j["name"]))
                    name_fsqr = text_to_vector(normalise(row_i["name"]))
                    similarity_score = get_cosine(name_hgw, name_fsqr)
                    if similarity_score > 0.2:
                        found = True
                        merge_reviews(row_i["id"], row_j["_id"])
                        break
            if not found:
                merge_restaurant(row_i)
                merge_reviews(row_i["id"], create_restaurant_id(row_i["name"], row_i["postalCode"]))
    print("")

if __name__ == "__main__":
    load_hungrygowhere()
    merge_with_foursquare()

    col_restaurants = DATABASE["restaurants"]
    col_reviews = DATABASE["reviews"]

    print("Insert restaurants data to mongodb...")
    for row in tqdm(DATA_RESTAURANTS):
        col_restaurants.update_one({"_id":row["_id"]}, {"$set":row}, upsert=True)
    print("")
    
    print("Insert reviews data to mongodb...")
    for row in tqdm(DATA_REVIEWS):
        col_reviews.update_one({"_id":row["_id"]}, {"$set":row}, upsert=True)
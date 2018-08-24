"""
This script is going to determine whether a review is negative or positive. Polarity is score between -1 (most negative) to +1 (most positive).

By default, it reads and writes to 'KE5106' database. You may change it in config.py.
"""

from pymongo import MongoClient
from textblob import TextBlob
from tqdm import tqdm
import config

def get_polarity(text):
    blob = TextBlob(text[1:1000])
    return blob.sentiment.polarity

def main():
    
    #1. Connect to mongo db
    client = MongoClient()
    db = client[config.DATABASE]
    
    #2. Query all the reviews without sentiment field
    exist = False
    count = db["reviews"].count_documents({ "sentiment": { "$exists": exist } })
    print("total reviews without sentiment =", count)
    reviews = db["reviews"].find( { "sentiment": { "$exists": exist } })
    
    #3. Do sentiment analysis on it
    for review in tqdm(reviews):
        polarity = get_polarity(review["body"])
        #4. Update the reivew
        db["reviews"].update_one(
                {"_id": review["_id"]},
                {"$set": {"sentiment": polarity}})
        
    client.close()
    return None


if __name__ == "__main__":
    main()
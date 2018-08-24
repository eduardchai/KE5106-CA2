# KE5106 - Web scraping

In this assessment, we are going to scrap hungrygowhere and foursquare for restaurants and reviews data. The data will be store in MongoDB.

## Pre-requisites
- python v3.6 and above
- MongoDB installed
- [Phantomjs](http://phantomjs.org/download.html) or [ChromeDriver](http://chromedriver.chromium.org/downloads)

## Initial setup

Install python libraries by running:
```
pip install -r requirements.txt
```

## How to run

_Notes: Scripts need to be run in this sequence._

### 1 - Hungrygowhere

Go to `./1-hungrygowhere/` folder.
```
1. Locate your phantomjs or chromedriver
2. Open hungrygowehere.py
3. Go to `get_browser` function and update location of phantomjs or chromedriver accordingly.
``` 

Run script by running:
```
python hungrygowhere.py
```

Additional configuration can be seen in `config.py`.

### 2 - Foursquare

We need to register for Foursquare API to run this script. Free account can call the API 50-500 times a day. Premium account is needed to scrap the whole data. More details can be seen [here](https://developer.foursquare.com).

Go to `./2-hungrygowhere/` folder.
```
1. Open config.py
2. Update CLIENT_ID and CLIENT_SECRET with your foursquare account CLIENT_ID and CLIENT_SECRET.
```

Run script by running:
```
python foursquare.py
```

Additional configuration can be seen in `config.py`.

### 3 - Merge hungrygowhere and foursquare

Go to `./3-merge/` folder.

Run script by running:
```
python merge.py
```

Additional configuration can be seen in `config.py`.

### 4 - Sentiment analysis on reviews

Go to `./4-sentiment-analysis/` folder.

Run script by running:
```
python sentiment_analysis.py
```

Additional configuration can be seen in `config.py`.


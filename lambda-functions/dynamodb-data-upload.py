import boto3
import datetime
import csv
from decimal import Decimal
import json
from botocore.vendored import requests

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('yelp-restaurants')

with open('restaurants.csv', newline='') as f:
    reader=csv.reader(f)
    restaurants=list(reader)
restaurants=restaurants[1:]

for restaurant in restaurants:
    if restaurant[6] == '':
        print(restaurant[0])
    tableEntry = {
        'id': restaurant[0],
        'name': restaurant[1],
        'address': restaurant[2],
        'coordinates': restaurant[3],
        'review_count': restaurant[4],
        'rating': restaurants[1][5],
        'zip_code': restaurant[6],
        'cuisine': restaurant[7]
    }
table.put_item(Item={'insertedAtTimestamp': str(datetime.datetime.now()),
            'id': tableEntry['id'],
            'name': tableEntry['name'],
            'address': tableEntry['address'],
            'rating': tableEntry['rating'],
            'review_count': tableEntry['review_count'],
            'coordinates': tableEntry['coordinates'],
            'zip_code': tableEntry['zip_code'],
            'cuisine': tableEntry['cuisine']
})

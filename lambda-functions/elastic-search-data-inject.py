import boto3
import json
from botocore.vendored import requests
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import csv

host = {ES_HOST_URL}
region = 'us-east-1'
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

es = Elasticsearch(
    hosts = [{'host': host, 'port': 443}],
    http_auth = awsauth,
    use_ssl = True,
    verify_certs = True,
    connection_class = RequestsHttpConnection
)
print(es)
with open('Restaurants.csv', newline='') as f:
    reader = csv.reader(f)
    restaurants = list(reader)

for restaurant in restaurants:
    index_data={'id': restaurant[0],'categories': restaurant[7]}
    print ('dataObject',index_data)

    es.index(index="restaurants", doc_type="Restaurant", id=restaurant[0], body=index_data, refresh=True)

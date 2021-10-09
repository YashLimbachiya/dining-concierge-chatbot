import boto3
from boto3.dynamodb.conditions import Attr
from requests_aws4auth import AWS4Auth
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import requests
import json
import os
import logging

sqs = boto3.client('sqs')
sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

""" --- Constants --- """
sqs_url = os.environ.get('SQS_URL')
max_sqs_poll_msgs = 10
elastic_search_host = os.environ.get('ELASTIC_SEARCH_HOST')
elastic_search_region = os.environ.get('ELASTIC_SEARCH_REGION')
elastic_search_index = os.environ.get('ELASTIC_SEARCH_INDEX')
dynamodb_table = os.environ.get('DYNAMODB_TABLE')
from_email = os.environ.get('FROM_EMAIL')
subject = 'Your restaurant suggestions are here!'
sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')


def send_email(emails, message):
    message = Mail(
        from_email=from_email,
        to_emails=emails,
        subject=subject,
        html_content=message)
    try:
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
    except Exception as e:
        print(e.message)


def send_sms(msgToSend, phoneNumber):
    response = sns.publish(
        PhoneNumber='+1{}'.format(phoneNumber),
        Message=msgToSend,
        MessageStructure='string'
    )

    print('SNS Response-> {}'.format(response))
    return response


def delete_message_from_queue(receipt_handle):
    try:
        sqs.delete_message(QueueUrl=sqs_url, ReceiptHandle=receipt_handle)
        print('Message with ReceiptHandle {} deleted'.format(receipt_handle))
    except Exception as e:
        logger.error('Error while deleting message with ReceiptHandle {}'.format(receipt_handle))
        logger.error(e)


def fetch_from_queue():
    sqs_response = sqs.receive_message(QueueUrl=sqs_url, MaxNumberOfMessages=max_sqs_poll_msgs)
    return sqs_response['Messages'] if 'Messages' in sqs_response.keys() else []


def query_dynamo_db(ids, cuisine, location, numberOfPpl, date, time):
    table = dynamodb.Table(dynamodb_table)
    counter = 0
    messageToSend = 'Hello! Here are my {cuisine} restaurant suggestions in {location} for {numberOfPpl} people, for {date} at {time}: '.format(
                cuisine=cuisine,
                location=location,
                numberOfPpl=numberOfPpl,
                date=date,
                time=time,
            )

    for id in ids:
        if counter == 3:
            break

        response = table.scan(FilterExpression=Attr('id').eq(id))
        item = response['Items'][0] if len(response['Items']) > 0 else None
        if response is None or item is None:
            continue
        restaurantMsg = '' + str(counter) + '. '
        name = item['name']
        address = item['address']
        restaurantMsg += name +', located at ' + address +'. '
        messageToSend += restaurantMsg
        counter += 1

    return messageToSend


def query_elastic_search(cuisine):
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, elastic_search_region, 'es', session_token=credentials.token)

    es_query = '{}{}/_search?q={cuisine}'.format(elastic_search_host, elastic_search_index, cuisine=cuisine)
    es_data = {}

    es_response = requests.get(es_query, auth=awsauth)

    data = json.loads(es_response.content.decode('utf-8'))
    try:
        es_data = data['hits']['hits']
    except KeyError:
        logger.debug('Error extracting hits from ES response')
        
    # extract bID from AWS ES
    ids = []
    for restaurant in es_data:
        ids.append(restaurant['_source']['id'])
      
    return ids


def lambda_handler(event, context):
    print('Cloud Watch event-> {}'.format(event))
    
    messages = fetch_from_queue()
    
    print('Received {} messages from SQS'.format(len(messages)))
    
    for message in messages:
        body = json.loads(message['Body'])
        print('Message Body-> {}'.format(body))
        
        cuisine = body['cuisine']['value']['interpretedValue']
        location = body['location']['value']['interpretedValue']
        numberOfPpl = body['numberOfPpl']['value']['interpretedValue']
        date = body['date']['value']['interpretedValue']
        time = body['time']['value']['interpretedValue']
        phoneNumber = body['phoneNumber']['value']['interpretedValue']
        emailAddress = body['emailAddress']['value']['interpretedValue']
        
        ids = query_elastic_search(cuisine)
        print(ids)

        final_message = query_dynamo_db(ids, cuisine, location, numberOfPpl, date, time)
        print(final_message)

        # send final_message to phoneNumber using SNS
        # send_sms(final_message, phoneNumber)

        send_email(emailAddress, final_message)

        receipt_handle = message['ReceiptHandle']
        delete_message_from_queue(receipt_handle)

    return {
        'statusCode': 200,
        'body': 'Received {} messages from SQS'.format(len(messages))
    }
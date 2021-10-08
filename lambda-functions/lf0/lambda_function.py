import boto3
import os

botId = os.environ.get('BOT_ID')
botAliasId = os.environ.get('BOT_ALIAS_ID')
localeId = 'en_US'
sessionId = 'test_session'

def lambda_handler(event, context):
    # Lex client uses 'lexv2-runtime'
    client = boto3.client('lexv2-runtime')

    message = event['messages'][0]['unstructured']['text']
    print(message)

    # Send the message to the lex using the recognize_text function
    response = client.recognize_text(
        botId=botId,
        botAliasId=botAliasId,
        localeId=localeId,
        sessionId=sessionId,
        text=message
    )

    print(response)

    return {
        'statusCode': 200,
        'messages': [{'type': 'unstructured', 'unstructured': {'text': response['messages'][0]['content']}}]
    }

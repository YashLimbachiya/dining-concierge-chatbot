"""
This Lambda Function demonstrates an implementation of the Lex Code Hook Interface
in order to serve the Dining Concierge Chatbot which gives restaurant suggestions to the users.
"""
import boto3
import math
import dateutil.parser
import datetime
import time
import os
import json
import logging

sqs = boto3.client('sqs')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

""" --- Constants --- """
dining_suggestions_intent = 'DiningSuggestionsIntent'
default_location = 'Manhattan'
default_cuisines = ['indian', 'chinese', 'japanese', 'italian', 'american']
min_number_of_ppl = 2
max_number_of_ppl = 20
sqs_url = os.environ.get('SQS_URL')


""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """


def get_slots(intent_request):
    return intent_request['sessionState']['intent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'ElicitSlot',
                'slotToElicit': slot_to_elicit,
            },
            'intent': {
                'name': intent_name,
                'slots': slots
            }
        },
        'messages': [message]
    }


def close(session_attributes, intent_name, fulfillment_state, message):
    return {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Close'
            },
            'intent': {
                'name': intent_name,
                'state': fulfillment_state
            }
        },
        'messages': [message]
    }


def delegate(session_attributes, intent_name, slots):
    return {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Delegate'
            },
            'intent': {
                'name': intent_name,
                'slots': slots
            }
        }
    }


""" --- Helper Functions --- """


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            'isValid': is_valid,
            'violatedSlot': violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def send_to_sqs(slots):
    response = sqs.send_message(
        QueueUrl=sqs_url,
        MessageBody=json.dumps(slots)
    )
    logger.info('SQS Response-> ')
    logger.info(response)


def validate_dining_suggestions(location, cuisine, numberOfPpl, date, time, phoneNumber):
    numberOfPpl = parse_int(numberOfPpl) if numberOfPpl is not None else numberOfPpl

    logger.info('Location captured-> {}, Default Location -> {}'.format(location, default_location))
    if location is None:
        logger.debug('Location is None')
        return build_validation_result(False,
                                       'location',
                                       'Great. I can help you with that. What city or city area are you looking to dine in?')
    elif location.lower() != default_location.lower():
        logger.debug('Location {} is not valid.'.format(location))
        return build_validation_result(False,
                                       'location',
                                       'I can find a restaurant for you in {}, Can you please try again?'.format(default_location))

    logger.info('Cuisine captured-> {}, Default Cuisines -> {}'.format(cuisine, default_cuisines))
    if cuisine is None:
        logger.debug('Cuisine is None')
        return build_validation_result(False,
                                       'cuisine',
                                       'Got it, {}. What cuisine would you like to try?'.format(default_location))
    elif cuisine.lower() not in default_cuisines:
        logger.debug('Invalid Cuisine-> {}'.format(cuisine))
        return build_validation_result(False,
                                       'cuisine',
                                       'Sorry, I can\'t find restaurants for {} cuisine. Could you try another one?'.format(cuisine))

    logger.info('Number of People captured-> {}, Max number of people -> {}'.format(numberOfPpl, max_number_of_ppl))
    if numberOfPpl is None:
        logger.debug('numberOfPpl is None')
        return build_validation_result(False,
                                       'numberOfPpl',
                                       'Ok, how many people are in your party?')
    elif numberOfPpl < min_number_of_ppl or numberOfPpl > max_number_of_ppl:
        logger.debug('Invalid numberOfPpl-> {}'.format(numberOfPpl))
        return build_validation_result(False,
                                       'numberOfPpl',
                                       'I suggest to book for a minimum of {} & a maximum of {} people.'.format(min_number_of_ppl, max_number_of_ppl))

    logger.info('Date -> {}'.format(date))
    date_obj = datetime.datetime.strptime(date, '%Y-%m-%d').date() if date is not None else None
    if date is None:
        logger.debug('Date is None')
        return build_validation_result(False, 'date', 'A few more to go. What date?')
    else:
        if not isvalid_date(date):
            logger.debug('Invalid Date-> {}'.format(date))
            return build_validation_result(False, 'date', 'I did not understand that, what date would you like to go to the restaurant?')
        elif date_obj < datetime.date.today():
            logger.debug('Date is in the past-> {}'.format(date))
            return build_validation_result(False, 'date', 'You can reserve your seats only in the future. What date would you like to go to the restaurant?')

    logger.info('Time -> {}'.format(time))
    if time is None:
        logger.debug('Time is None')
        return build_validation_result(False, 'time', 'What time?')
    else:
        if len(time) != 5:
            logger.debug('Invalid Time-> {}'.format(time))
            return build_validation_result(False, 'time', 'Invalid Time format -> {}. Can you try again?'.format(time))

        hour, minute = time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            logger.debug('Invalid Time-> {}'.format(time))
            return build_validation_result(False, 'time', 'Invalid Time format -> {}. Can you try again?'.format(time))

        time_obj = datetime.datetime.strptime(time, '%H:%M').time()
        combined_datetime = datetime.datetime.combine(date_obj, time_obj)
        if combined_datetime < datetime.datetime.now():
            # Time is in the past
            logger.debug('Time is in the past-> {}'.format(time))
            return build_validation_result(False, 'time', 'You can reserve your seats only in the future. Can you specify a time in the future?')

    logger.info('Phone Number -> {}'.format(phoneNumber))
    if phoneNumber is None:
        logger.debug('Phone Pumber is None')
        return build_validation_result(False,
                                       'phoneNumber',
                                       'Great. Lastly, I need your phone number so I can send you my findings.')
    elif len(phoneNumber) != 10:
        logger.debug('Invalid Phone Pumber-> {}'.format(phoneNumber))
        return build_validation_result(False,
                                       'phoneNumber',
                                       'Please enter a valid 10-digit phone number.')

    logger.info('Validated all the slots\n')
    return build_validation_result(True, None, None)


""" --- Functions that control the bot's behavior --- """


def dining_suggestions(intent_request):
    """
    Performs dialog management and fulfillment for dining suggestions.
    Beyond fulfillment, the implementation of this intent demonstrates the use of the elicitSlot dialog action
    in slot validation and re-prompting.
    """

    slots = get_slots(intent_request)
    location = slots['location']['value']['interpretedValue'] if slots['location'] is not None else None
    cuisine = slots['cuisine']['value']['interpretedValue'] if slots['cuisine'] is not None else None
    numberOfPpl = slots['numberOfPpl']['value']['interpretedValue'] if slots['numberOfPpl'] is not None else None
    date = slots['date']['value']['interpretedValue'] if slots['date'] is not None else None
    time = slots['time']['value']['interpretedValue'] if slots['time'] is not None else None
    phoneNumber = slots['phoneNumber']['value']['interpretedValue'] if slots['phoneNumber'] is not None else None
    source = intent_request['invocationSource']
    intent_name = intent_request['sessionState']['intent']['name']

    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        
        validation_result = validate_dining_suggestions(location, cuisine, numberOfPpl, date, time, phoneNumber)
        logger.info('Validation Result -> {}'.format(validation_result['isValid']))
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionState'].get('sessionAttributes'),
                                intent_name,
                                slots,
                                validation_result['violatedSlot'],
                                validation_result.get('message'))

        # Pass data back through session attributes to be used in various prompts defined on the bot model.
        output_session_attributes = intent_request['sessionState'].get('sessionAttributes') if intent_request['sessionState'].get('sessionAttributes') is not None else {}

        return delegate(output_session_attributes, intent_name, get_slots(intent_request))

    # Send the slot data to SQS queue
    send_to_sqs(slots)

    # Send the closing response back to the user.
    logger.debug('Closing the intent as its fulfilled')
    return close(intent_request['sessionState']['sessionAttributes'],
                intent_name,
                'Fulfilled',
                {'contentType': 'PlainText',
                 'content': 'You’re all set. Expect my suggestions shortly! Have a good day.'})



""" --- Intents --- """


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    intent_name = intent_request['sessionState']['intent']['name']
    
    logger.info('dispatch sessionId={}, intentName={}'.format(intent_request['sessionId'], intent_name))

    # Dispatch to your bot's intent handlers
    if intent_name == dining_suggestions_intent:
        return dining_suggestions(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.info('event.bot.name={}'.format(event['bot']['name']))
    logger.info(event)

    result = dispatch(event)
    logger.info('Result->\n\n')
    logger.info(result)
    return result

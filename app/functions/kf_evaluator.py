import sys, os
import base64
import json
from datetime import datetime
from itertools import chain

from app.helpers.pubsub import publish

#############################################################################################################################

WEBHOOK_NOGO_TOPIC  = os.getenv('KF_WEBHOOK_NOGO')
WEBHOOK_READY_TOPIC = os.getenv('KF_WEBHOOK_READY')

#############################################################################################################################

def kf_evaluateOCM(data, context):
    """
        Background Cloud Function to be triggered by Pub/Sub.
        Args:
         data (dict): The dictionary with data specific to this type of event.
         context (google.cloud.functions.Context): The Cloud Functions event
         metadata.

         The package pulled out of data has these keys:
            message_id
            action
            payload
            conditions
            webhooks
            processed_timestamp

         From the kingfisher DB
           items queried from the webhook table have:
              0    1        2      3            4                    5
              id   sub_id   name   target_url   object_types(list)   conditions(list of ids)
           items queried from the condition table have:
              0    1        2                3                4          5
              id   sub_id   attribute_uuid   attribute_name   operator   value'
    """
    if not 'data' in data:
        print("Missing top level 'data' element in data parameter, no data published to output topic.")
        return

    package  = json.loads(base64.b64decode(data['data']).decode('utf-8'))
    #print(f'keys for the provided message {repr(list(package.keys()))}')
    message_id = package.get('message_id')
    action     = package.get('action')
    payload    = json.loads(package.get('payload'))
    conditions = json.loads(package.get('conditions'))
    webhooks   = json.loads(package.get('webhooks'))
    object_type = payload['object_type']
    print(f'message_id: {message_id}  action: {action}  object_type: {object_type}')
    #print(f'payload is a {type(payload)}')
    #print(f'payload has these keys {list(payload.keys())}')
    #payload keys: ['action', 'subscription_id', 'ref', 'detail_link', 'object_type', 'changes', 'state', 'project']

    if action.lower() not in ['created', 'updated']:
        print(f'Ignoring OCM action: {action} for message_id: {message_id}')
        return

    print(f'webhooks   -> {webhooks}')
    print(f'conditions -> {conditions}')

    relevant_webhooks = getRelevantWebhooks(webhooks, object_type)
    if not relevant_webhooks:
        print(f'message_id: {message_id} no relevant webhooks for object_type: {object_type}')
        return None
    print(f'message_id: {message_id} relevant_webhooks: {repr(relevant_webhooks)}')

    relevant_conditions = getRelevantConditions(relevant_webhooks, conditions)
    print(f'message_id: {message_id} relevant_conditions: {repr(relevant_conditions)}')

    condition = evaluateItemAgainstConditions(payload, relevant_conditions)

    endpoint = {}
    for webhook in relevant_webhooks:
        disqualified = False
        for cond_id in webhook[-1]:    # all conditions specified by webhook must be true or the webhook is disqualified
            if condition[cond_id]['status'] != True:
                disqualified = True

        message_dict = { "message_id"           : message_id,
                         "action"               : action,
                         "webhook"              : webhook,
                         "payload"              : json.dumps(payload),
                         "processed_timestamp"  : datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                       }

        if disqualified:
            message_dict['conditions'] = condition
            topic_name = WEBHOOK_NOGO_TOPIC
            try:
                future = publish(topic_name, message_dict)
                result = future.result(timeout=10)
                print(f'Published message -- {message_id} topic: WEBHOOK_NOGO result: {result}')
            except Exception as exception:
                print('Encountered error while publishing -- message_id: {message_id} topic: WEBHOOK_NOGO exception: {exception}')
            continue

        if webhook[3] not in endpoint:  # A payload only gets fired on its target once per OCM
            endpoint[webhook[3]] = 1    # to ensure the above statement, cache the target endpoint
            topic_name = WEBHOOK_READY_TOPIC
            try:
                message_dict['attempts'] = 0
                message_dict['eligible'] = 1000 # artificially low timestamp value
                future = publish(topic_name, message_dict)
                result = future.result(timeout=10)
                print('Published message -- {message_id} topic: WEBHOOK_READY result: {result}')
            except Exception as exception:
                print('Encountered error while publishing -- {message_id} topic: WEBHOOK_READY exception: {exception}')

#############################################################################################################################

def getRelevantWebhooks(webhooks, object_type):
    """
        Given a list of webhooks (show structure of a webhook) and a object_type value
        return the set of webhooks where object_type is in the webhook item ix 4 or whose webhook item 4 list is empty
    """
    relevant_webhooks = [wh for wh in webhooks if object_type in wh[4] or len(wh[4]) == 0 ]  # wh[4] is the list of object_types
    return relevant_webhooks

#############################################################################################################################

def getRelevantConditions(webhooks, conditions):
    """
        Given a sequence of webhook items and sequence of conditions
        identify and return the conditions that match the condition ids in each webhook
    """
    conds = [wh[-1]for wh in webhooks] # wh[-1] is a list of integers where each integer is the id value of a condition
    cond_ids = list(set(chain(*conds)))
    relevant_conds = [cond for cond in conditions if cond[0] in cond_ids]
    return relevant_conds

#############################################################################################################################

def evaluateItemAgainstConditions(payload, relevant_conditions):
    """
        Given a payload (dict) in which there is a 'state' key with a sub-dict with attr_name : attr_value pairs
        and a relevant_conditions sequence
    """
    condition = {}
    for cond in relevant_conditions:
        cond_id, sub_id, condition_attr_uuid, condition_attr_name, condition_relation, condition_value = cond
        attribute = payload['state'][condition_attr_uuid]
        #attr_value = payload['state'][condition_attr_uuid]['value']['value']
        attr_value = 'no such value key in attribute'
        if 'value' in attribute:
            attr_value = attribute['value']
            if attr_value and isinstance(attr_value, dict):
                if 'value' in attr_value:
                    attr_value = attr_value['value']
                elif 'name' in attr_value:
                    attr_value = attr_value['name']

        expression = f'{condition_attr_name}({attr_value}) {condition_relation} {condition_value}'
        status = isQualified(payload, cond)
        print(f'{expression} ? {status}')
        condition[cond_id] = {'condition' : expression, 'status' : status}

    return condition

#############################################################################################################################

""" from the Pigeon Webhooks API documentation

Operators
The required fields in an Expression depend on the Operator.

 ------------
The following operators require both a Value and exactly one of AttributeID or AttributeName.

Operator	Description
   =	        Equal
   !=	        Not equal
   <	        Less than
   <=	        Less than or equal
   >	        Greater than
   >=	        Greater than or equal
   changed-to	Value changed to
   changed-from	Value changed from

  ------------
The following operators require an AttributeID or AttributeName, and a Value that is an Array of individual values.

Operator	Description
    ~	    "Equals one of". Matches when the object's value for the attribute 
                             is equal to one of the values given in the Expression
    !~	    "Equals none of". Matches when the object's value for the attribute 
            is not equal to any of the values given in the Expression

  -----------  
The following operators require only an AttributeID or AttributeName (no Value)

Operator	Description
    has	        The object has some (non-null) value for the attribute
    !has	    The object does not have the attribute, or its value is null
    changed	    The value of the attribute was changed on the object
"""


def isEqual(ocm_attr_value, expression_value):
    return ocm_attr_value == expression_value


def isNotEqual(ocm_attr_value, expression_value):
    return ocm_attr_value != expression_value


def isLessThan(ocm_attr_value, expression_value):
    return ocm_attr_value < expression_value


def isLessThanOrEqual(ocm_attr_value, expression_value):
    return ocm_attr_value <= expression_value


def isGreaterThan(ocm_attr_value, expression_value):
    return ocm_attr_value > expression_value


def isGreaterThanOrEqual(ocm_attr_value, expression_value):
    return ocm_attr_value >= expression_value


# def isChangedTo(ocm, ocm_attr_id, expression_value):
#    return False

# def isChangedFrom(ocm, ocm_attr_id, expression_value):
#    return False

def isOneOf(ocm_attr_value, expression_value):
    return ocm_attr_value in expression_value  # "cast" expression_value to a list


def isNotOneOf(ocm_attr_value, expression_value):
    return ocm_attr_value not in expression_value  # "cast" expression_value to a list


# def hasSomeValue(ocm, ocm_attr_id, expression_value):
#    return False

# def hasNoValue(ocm, ocm_attr_id, expression_value):
#    return False


expression_eval = {'='   : isEqual,
                   '!='  : isNotEqual,
                   '<'   : isLessThan,
                   '<='  : isLessThanOrEqual,
                   '>'   : isGreaterThan,
                   '>='  : isGreaterThanOrEqual,
                   # 'changed-to'    : isChangedTo,
                   # 'changed-from'  : isChangedFrom,
                   # expressions that take an attribute_id|name and a list of possible values
                   '~'   : isOneOf,
                   '!~'  : isNotOneOf,
                   # expressions that take just an attribute_id|name
                   # 'has'     : hasSomeValue,
                   # '!has'    : hasNoValue,
                   # 'changed' : valueWasChanged
                  }

def isQualified(ocm, condition):
    #ocm keys: ['action', 'subscription_id', 'ref', 'detail_link', 'object_type', 'changes', 'state', 'project']
    cond_id, sub_id, condition_attr_uuid, condition_attr_name, condition_relation, condition_value = condition
    state   = ocm['state']
    changes = ocm['changes']
    var_info   = state[condition_attr_uuid]
    attr_value = var_info['value']
    if attr_value and isinstance(attr_value, dict):
        if 'value' in attr_value:
            attr_value = attr_value['value']
        elif 'name' in attr_value:
            attr_value = attr_value['name']

    try:
        condition_value = int(condition_value)  # in case condition_value
    except:
        pass
    # alternative to above is to attempt a rough determination of the type of the attr_value and coerce condition_value to same
    #if attr_value and isinstance(attr_value, int)
    #    if condition_value:
    #        try:
    #            condition_value = int(condition_value)
    #        except:
    #            pass
    #elif attr_value and isinstance(attr_value, float)
    #    if condition_value:
    #        try:
    #            condition_value = float(condition_value)
    #        except:
    #            pass

    print(f'{condition_attr_name}({attr_value}) {condition_relation} {condition_value} ?')

    if condition_relation not in ['changed-to', 'changed-from', 'has', '!has', 'changed']:
        if not attr_value:
            return False
        take  = expression_eval[condition_relation](attr_value, condition_value)
        return take

    if condition_relation   == 'changed-to':
        ac = [changes[attr_uuid]['value'] for attr_uuid in changes.keys() if attr_uuid == condition_attr_uuid]
        if not ac:
            return False
        else:
            return ac[0] == condition_value
    elif condition_relation == 'changed-from':
        ac = [changes[attr_uuid]['old_value'] for attr_uuid in changes.keys() if attr_uuid == condition_attr_uuid]
        if not ac:
            return False
        else:
            return ac[0] == condition_value
    elif condition_relation == 'has':
        return attr_value != None
    elif condition_relation == '!has':
        return attr_value == None
    else: # must be 'changed'
        ac = [changes[attr_uuid]['value'] for attr_uuid in changes.keys() if attr_uuid == condition_attr_uuid]
        return len(ac) > 0


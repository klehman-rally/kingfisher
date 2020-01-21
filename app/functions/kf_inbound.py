import sys, os
import json
import datetime
import traceback

#from google.cloud import pubsub_v1

from app.helpers.pgdb    import getQualifiers
from app.helpers.pubsub  import publish

INGESTION_TOPIC = 'kf-blowhole'

###################################################################################################

def kf_inbound(request):
    #print(request.headers)
    payload = json.loads(request.data)
    transaction = payload['value']['transaction']
    message_id = transaction['message_id']

    #payload looks like {'value' : {'transaction' : { ... stuff ...},
    #                               'entities'    : { ... stuff ...} }
    #payload['value']['transaction']
    #'transaction': {'message_id': '47902511-5a2b-4b6a-a118-7fa78c4c7d4c',
    #                'trace_id': 'd3d3af5f-9dc7-4ded-af84-98289f77e408',
    #                'span_id': '9842532a-f9d3-4a91-ad4e-0f1c16135153',
    #                'parent_span_id': 'd0a32084-3f91-4562-8ebd-ebe757969e7f',
    #                'oracle_schema': 'wombat',
    #                'timestamp': 1536079376526,
    #                'user': { 'username': 'ue@test.com', 'email': 'ue@test.com',
    #                          'uuid': '19591e98-5287-46e5-aac2-93e3791abb3a' }
    #               }
    item = payload['value']['entities']
    # item will have a single key in the form of a uuid whose associated value is a dict of:
    #       action, subscription_id, project, object_type, detail_link, ref, state, changes
    #       the state and changes will be keyed by the attribute id
    for item_uuid, info in item.items():
        action  = info['action']
        sub_id  = info['subscription_id']
        project = info['project']['name']
        entity  = info['object_type']
        state   = info['state']
        changes = info['changes']
        state_attrs = {infoblock['name']:infoblock['value'] 
                           for attr_uuid, infoblock in state.items()
                            if infoblock['type'] not in ['Subscription', 'Collection', 'Rating']
                           and infoblock['value'] is not None
                           and infoblock['name'] not in ['Recycled', 'Project', 'RevisionHistory', 'DragAndDropRank']}
        for attr_name in state_attrs:
            if isinstance(state_attrs[attr_name], dict):
                dval = state_attrs[attr_name]
                state_attrs[attr_name] = dval['name'] if 'name' in dval else  dval['value'] if 'value' in dval else dval

        workspace    = state_attrs['Workspace']
        formatted_id = state_attrs['FormattedID']
        print(f'message_id: {message_id}  {sub_id}-{workspace}-{project}-{action}-{entity}-{formatted_id}')
        """
        {
         'ObjectID': 181899,
         'ObjectUUID': 'f51b234a-d248-4069-be68-25ae7e874124', 
         'FormattedID': 'DE1',
         'Name': 'some artifact to get the security token',
         'Description': '',
         'CreationDate': '2018-08-30T22:10:11.568Z',
         'OpenedDate': '2018-08-30T23:00:42.175Z',
         'Ready': False,
         'Notes': '',
         'CreatedBy': {'ref': 'http://stack.local:8999/slm/webservice/v2.x/user/19591e98-5287-46e5-aac2-93e3791abb3a',
                       'detail_link': 'http://stack.local:8999/slm/#/detail/user/164934', 'object_type': 'User',
                       'name': 'ue', 'id': '19591e98-5287-46e5-aac2-93e3791abb3a'},
         'FlowState': {
            'ref': 'http://stack.local:8999/slm/webservice/v2.x/flowstate/dc66d240-1be4-4f19-8ed6-dd767585abd9',
            'detail_link': None, 
            'object_type': 'FlowState', 
            'name': 'Completed',
            'id': 'dc66d240-1be4-4f19-8ed6-dd767585abd9'},
         'FlowStateChangedDate': '2018-09-04T16:42:56.246Z',
            
         'InProgressDate': '2018-08-31T18:15:07.513Z', 
         'AffectsDoc': False, 'TaskStatus': 'NONE', 'LastUpdateDate': '2018-09-04T16:42:56.442Z',
         'PlanEstimate': {'units': 'Points', 'value': 3.0},
         'TaskEstimateTotal': {'units': 'Hours', 'value': 0.0},
         'TaskActualTotal': {'units': 'Hours', 'value': 0.0},
         'TaskRemainingTotal': {'units': 'Hours', 'value': 0.0}, 
         'DisplayColor': '#f9a814',
            
         'Expedite': False, 
         'Workspace': {
            'ref': 'http://stack.local:8999/slm/webservice/v2.x/workspace/c4ace4af-92a5-467d-9f12-62c40a5ae049',
            'detail_link': 'http://stack.local:8999/slm/#/detail/workspace/164973', 'object_type': 'Workspace',
            'name': 'Workspace 1', 'id': 'c4ace4af-92a5-467d-9f12-62c40a5ae049'}, 
         'FormattedIDID': 1,
            
         'ScheduleState': {'ref': 'http://stack.local:8999/slm/webservice/v2.x//43781a87-12a8-4fd0-8ef6-ac87b05a7cc4',
                           'detail_link': None, 'object_type': 'State', 'name': 'Completed',
                           'id': '43781a87-12a8-4fd0-8ef6-ac87b05a7cc4', 'order_index': 3},
         'ScheduleStatePrefix': 'C', 
         'TestCaseStatus': 'NONE', 'Blocked': False, 'ReleaseNote': False, 
         'TestCaseCount': 0,
         'PassingTestCaseCount': 0, 
         'VersionId': 20, 
        
         'FormattedIDPrefix': 'DE', 
        }
        """

        print(f'{repr(state_attrs)}')
        #print(f'state: {state}')
        #print(f'changes: {changes}')

        conditions = getQualifiers('condition', sub_id)
        print("%d conditions for for sub_id %s" % (len(conditions), sub_id))
        #for ix, condition in enumerate(conditions):
        #    print(f'{ix+1} : {condition}')

        webhooks = getQualifiers('webhook', sub_id)
        print("%d webhooks for for sub_id %s" % (len(webhooks), sub_id))
        #for ix, webhook in enumerate(webhooks):
        #    print(f'{ix+1} : {webhook}')

        crate = { "message_id"            : message_id,
                  "action"                : action,
                  "payload"               : json.dumps(info),
                  #"conditions"            : repr(conditions),
                  #"webhooks"              : repr(webhooks),
                  "conditions"            : json.dumps(conditions),
                  "webhooks"              : json.dumps(webhooks),
                  "processed_timestamp"   : datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                }

        try:
            future = publish(INGESTION_TOPIC, crate)
            result = future.result(timeout=10)
            print(f'Published message to INGESTION TOPIC -- message_id: {message_id} topic: {INGESTION_TOPIC} result: {result}')

            #return make_response("Received OCM\n", 202)
        except Exception as exception:
             print(f'Encountered error while publishing to INGESTION TOPIC -- message_id: {message_id} topic: {INGESTION_TOPIC} exception: {exception}')
             #return make_response('Unexpected server error.\n', 500)


#!/usr/local/Cellar/python/3.7.3/bin/python3.7

import sys, os
import json
import time
from random import randint
from pprint import pprint
import ast
import requests

###################################################################################################

GCP_PROJECT = "saas-rally-dev-integrations"
OCM_DATA    = "data/ocm-messages.dat"
SUB_ID_MULT = 100

KF_INGESTION_ENDPOINT = f"https://us-central1-{GCP_PROJECT}.cloudfunctions.net/kf_ingester"
#KF_INBOUND_ENDPOINT   = f"https://us-central1-{GCP_PROJECT}.cloudfunctions.net/kf_inbound"

###################################################################################################

def main(args):
    limit = 100
    if args:
        pseudo_sub_id = args.pop(0)
    if args and args[0] == '-limit' and args[1]:
        limit = int(args[1])

    shipped = 0
    ocms = getOCMItems(OCM_DATA)

    started  = time.time()

    #for ocm in ocms:
    for ocm in ocms[:limit]:
        if not args:
            pseudo_sub_id = randint(1, 100) * SUB_ID_MULT # 1 -> 100, 50 -> 5000, 95 -> 9500
        print(f'pseudo_sub_id: {pseudo_sub_id}')
        #print(ocm)
        #item = json.loads(ocm)
        item_dict = ast.literal_eval(ocm)

        first_item = list(item_dict['value']['entities'].keys())[0]
        item_dict['value']['entities'][first_item]['subscription_id'] = pseudo_sub_id #

        #print(list(item_dict['value']['entities'][first_item].keys()))
        #{'username': 'dfdsfdsf'}

        #pprint(item_dict['value']['entities'][first_key])

        jsonable_string = json.dumps(item_dict)
        #print(jsonable_string)
        headers = {'X-TransitionSpectrum' : "Blue4600a"}
        result = requests.post(KF_INGESTION_ENDPOINT, data=json.dumps(item_dict), headers=headers)
        #result = requests.post(KF_INBOUND_ENDPOINT, data=json.dumps(item_dict), headers=headers)
        print(result)
        shipped += 1
        if shipped >= limit:
            break

    finished = time.time()
    elapsed = round(finished - started)
    print(f"{shipped} messages sent in {elapsed} seconds")

###################################################################################################

def getOCMItems(source_file):
    OCM_SEPARATOR = "-" * 80 + "\n"
    with open(source_file, 'r') as ocmf:
        ocm_blob = ocmf.read()
    return ocm_blob.split(OCM_SEPARATOR)[:-1]

###################################################################################################
###################################################################################################

if __name__ == "__main__":
    main(sys.argv[1:])

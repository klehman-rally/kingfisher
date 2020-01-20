#
# workflood.py - simulate a producer / consumer ecosystem in which there is a single
#                producer and multiple consumers.  The producer supplies a unit of
#                work that is consumed from a common queue from the consumers.
#                The producer is minimally throttled such that the rate of adding work
#                is no more than twice the theoretical rate at which all of the 
#                consumers could handle available work considering that they can
#                only consume a work item after a time period equal to the task_delay.
#     
#                Work is provided as a tuple consisting of a work identifier
#                and a string with raw data:  ("A-n", "sdafkfjdsafkjla;sd")
#
USAGE = """
Usage: workflood.py <total_items> <task_delay> <num_workers> <time_limit_in_seconds>
"""
import sys
import time
from multiprocessing import Process, Queue
from random import randint
import ast
import json
import requests
import urllib3

#########################################################################################

GCP_PROJECT = "saas-rally-dev-integrations"
OCM_DATA    = "data/ocm-messages.dat"
SUB_ID_MULT = 100

LETTERS = [char for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ']
DOUBLE_LETTERS = [f'{letter}{letter}' for letter in LETTERS]
WORKER_CODES = LETTERS + DOUBLE_LETTERS

KF_INGESTION_ENDPOINT = f"https://us-central1-{GCP_PROJECT}.cloudfunctions.net/kf_ingester"
KF_INBOUND_ENDPOINT   = f"https://us-central1-{GCP_PROJECT}.cloudfunctions.net/kf_inbound"

EXAMPLE_HEADERS = {'X-TransitionSpectrum' : "Blue4600a"}

#########################################################################################

def main(args):
    total_items, task_delay, num_workers, time_limit = obtainAndCheckArguments(args)
    task_queue = Queue() # producer (main) injects items into task_queue from _this_ process

    ocm_gen = OCMItemGen(OCM_DATA)

    def endlessGen(item_sequence):
        while True:
            for item in item_sequence:
                yield item

    worker_identifiers = WORKER_CODES[:num_workers]
    workers = getWorkers(worker_identifiers, task_queue, task_delay)
    worker_generator = endlessGen(worker_identifiers)

    work_items_produced = 0
    wi = 0
    started = time.time()
    time_boundary = started + time_limit

    for raw_ocm in ocm_gen:
        if time.time() >= time_boundary:
            break

        worker_ident = next(worker_generator)
        if worker_ident == worker_identifiers[0]:
            wi += 1  # increment the work item index each time we begin the cycle in the worker_identifiers
        task_tag = f'{worker_ident}-{wi}'
        item_dict = shaveAndShine(raw_ocm)
        package = (task_tag, EXAMPLE_HEADERS, json.dumps(item_dict))
        task_queue.put(package)
        work_items_produced += 1
        if work_items_produced >= total_items:
            break

        if work_items_produced % 100 == 0:
            print(f'{work_items_produced} tasks produced')
            sys.stdout.flush()
        if worker_ident == worker_identifiers[-1]:
            time.sleep(task_delay / 2)  # after all workers have seen the current wi, delay before doing another set

    elapsed = round(time.time() - started)
    print(f"task master produced {work_items_produced} task items in {elapsed} seconds, last item label produced: {wi-1}")
    sys.stdout.flush()

    for worker_ident, worker in zip(worker_identifiers, workers):
        end_cap = (f'{worker_ident}-DONE', {}, '')
        task_queue.put(end_cap)
    time.sleep(1)
        
    for worker_ident, worker in zip(worker_identifiers, workers):
        worker.join()

    total_elapsed = round(time.time() - started)
    print(f"all workers joined after {total_elapsed} seconds")

#########################################################################################

def obtainAndCheckArguments(args):

    if len(args) != 4:
        sys.stderr.write("ERROR: bad argument list (not enough or too many)\n\n")
        sys.stderr.write(USAGE)

    try:
        total_items = int(args.pop(0))
    except:
        sys.stderr.write("ERROR: first argument for total_items is not an integer value\n\n")
        sys.stderr.write(USAGE)

    try:
        task_delay = float(args.pop(0))
    except:
        sys.stderr.write("ERROR: second argument for task_delay is not an floating point value\n\n")
        sys.stderr.write(USAGE)
        
    try:
        num_workers = int(args.pop(0))
    except:
        sys.stderr.write("ERROR: third argument for num_workers is not an integer value\n\n")
        sys.stderr.write(USAGE)

    try:
        time_limit = int(args.pop(0))
    except:
        sys.stderr.write("ERROR: fourth argument for num_workers is not an integer value\n\n")
        sys.stderr.write(USAGE)


    return total_items, task_delay, num_workers, time_limit

##################################################################################################

def OCMItemGen(source_file):
    OCM_SEPARATOR = "-" * 80 + "\n"
    with open(source_file, 'r') as ocmf:
        ocm_blob = ocmf.read()
    items = ocm_blob.split(OCM_SEPARATOR)[:-1]
    while True:
        for item in items:
            yield item

#########################################################################################

def shaveAndShine(bloated_ocm):
    item_dict = ast.literal_eval(bloated_ocm)
    first_item = list(item_dict['value']['entities'].keys())[0]

    pseudo_sub_id = randint(1, 100) * SUB_ID_MULT  # 1 -> 100, 50 -> 5000, 95 -> 9500
    item_dict['value']['entities'][first_item]['subscription_id'] = pseudo_sub_id  #

    return item_dict

#########################################################################################

def getWorkers(idents, task_queue, task_delay):
    workers = []
    for worker_ident in idents:
        worker = Process(target=workerProcess, args=(worker_ident, task_queue, task_delay))
        worker.daemon = True
        workers.append(worker)
        worker.start()

    return workers

#########################################################################################

def workerProcess(ident, queue, task_delay):
    ## Read from the queue; this function will be spawned as a separate Process
    slurped = 0
    dropped = 0
    while True:
        msg = queue.get()    # blocking read... no timeouts here
        msg_id, headers, ocm = msg
        if ('-DONE' in msg_id):
            print(f"worker task {ident} received a {msg_id} message, processed {slurped} messages")
            print(f"worker task {ident} had {dropped} messages that could not be posted to the target endpoint")
            break
        slurped += 1
        if slurped % 100 == 0:
            print(f'task-{ident} has processed {slurped} messages')
            sys.stdout.flush()

        # this is where the "work" would happen, ie., consume message, transform, operate, etc.
        #time.sleep(task_delay)
        try:
            result = requests.post(KF_INGESTION_ENDPOINT, data=ocm, headers=headers)
            #result = requests.post(KF_INBOUND_ENDPOINT, data=ocm, headers=headers)
        except urllib3.exceptions.MaxRetryError as exc:
            print(f"task {ident} failed to post an OCM to the GCF endpoint, max retries attempted")
            sys.stdout.flush()
            dropped += 1
        except Exception as exc:
            print(f"task {ident} failed to post an OCM to the GCF endpoint, {exc}")
            sys.stdout.flush()
            dropped += 1

#########################################################################################
#########################################################################################

if __name__=='__main__':
    main(sys.argv[1:])

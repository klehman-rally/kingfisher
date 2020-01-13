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
from multiprocessing import Process, Queue
import time
import sys


#########################################################################################

def main(args):
    total_items, task_delay, num_workers, time_limit = obtainAndCheckArguments(args)
    task_queue = Queue() # producer (main) injects items into task_queue from _this_ process

    worker_identifiers = "ABCDEFGHIKLMNOPQRSTUVWXYZ"[:num_workers]
    workers = getWorkers(worker_identifiers, task_queue, task_delay)

    work_items_produced = 0
    started = time.time()
    wi = 1
    time_boundary = started + time_limit

    while time.time() < time_boundary and work_items_produced < total_items:
        for worker_ident in worker_identifiers:
            task_queue.put((f'{worker_ident}-{wi}', "fictitious fodder for goblins"))
            work_items_produced += 1
        if wi % 100 == 0:
            print(f'{work_items_produced} tasks produced')
            sys.stdout.flush()
        time.sleep(task_delay / 2)
        wi += 1

    elapsed = round(time.time() - started)
    print(f"task master produced {work_items_produced} task items in {elapsed} seconds, last item label produced {wi-1}")
    sys.stdout.flush()

    for worker_ident, worker in zip(worker_identifiers, workers):
        task_queue.put((f'{worker_ident}-DONE', ''))
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
    while True:
        msg = queue.get()    # blocking read... no timeouts here
        msg_id, directive = msg
        if ('-DONE' in msg_id):
            print(f"worker task {ident} received a {msg_id} message, processed {slurped} messages")
            break
        slurped += 1
        if slurped % 100 == 0:
            print(f'task-{ident} has processed {slurped} messages')
            sys.stdout.flush()

        # this is where the "work" would happen, ie., consume message, transform, operate, etc.
        time.sleep(task_delay)

#########################################################################################
#########################################################################################

if __name__=='__main__':
    main(sys.argv[1:])

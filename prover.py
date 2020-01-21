import itertools


OCM_DATA    = "data/ocm-messages.dat"

def getOCMItems(source_file):
    OCM_SEPARATOR = "-" * 80 + "\n"
    with open(source_file, 'r') as ocmf:
        ocm_blob = ocmf.read()
    return ocm_blob.split(OCM_SEPARATOR)

ocms = getOCMItems(OCM_DATA)

count = 0
for raw_ocm in itertools.cycle(ocms):
    count += 1
    if count % 100 == 0:
        print(count)

###############################################

"""

worker_identifiers = "ABCDEFGHIKLMNOPQRSTUVWXYZ"[:4]


def endlessGen(item_sequence):
    while True:
        for item in item_sequence:
             yield item

worker_generator = endlessGen(worker_identifiers)
wi = 0

for thing in range(40):
    worker_ident = next(worker_generator)
    if worker_ident == worker_identifiers[0]:
        wi += 1  # increment the work item index each time we begin the cycle in the worker_identifiers
    task_tag = f'{worker_ident}-{wi}'
    print(f'    {task_tag}')
"""

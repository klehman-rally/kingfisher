#
# puffdata.py - take the n unique lines in ocm-messages-3.raw and produce
#               a new file with 1000 entries  from those original n lines
#               repeated until you hit the 1000 entry limit
#
#########################################################################################
USAGE = "puffdata.py <limit>"

import sys, os

#########################################################################################

ORIG_OCM_DATA_FILE = "data/ocm-messages-3.raw"
BULK_OCM_DATA_FILE = "data/ocm-messages.dat"

#########################################################################################

def main(args):
    limit = 1000
    if args:
        try:
            limit = int(args[0])
        except:
            print(f"bad limit argument: {args[0]}")
            sys.exit(1)

    uniq_data_lines = extractUniqueLines(ORIG_OCM_DATA_FILE, 3)
    mf = open(BULK_OCM_DATA_FILE, 'w')
    emitted = 0
    while emitted < 1000:
        ix = emitted % 3
        mf.write(uniq_data_lines[ix])
        emitted += 1

    mf.close()

#########################################################################################

def extractUniqueLines(target_file, n):
    items = []
    lines = 0
    with open(target_file, "r") as df:
        while lines < n:
            items.append(df.readline())
            lines += 1

    return items

#########################################################################################
#########################################################################################

if __name__ == '__main__':
    main(sys.argv[1:])

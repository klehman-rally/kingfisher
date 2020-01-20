#
# show_message.py - show the n'th message in the reference file in a JSON prettified form
#
#########################################################################################

USAGE = "show_message.py <message_number>"

import sys, os
import json
from pprint import pprint
import ast
from collections import OrderedDict
import textwrap

#########################################################################################

ORIG_OCM_DATA_FILE = "data/ocm-messages-3.raw"

#########################################################################################

def main(args):
    if not args:
        msg_index = 1
    else:
        try:
            msg_index = int(args[0])
        except:
            print(f"bad message number argument: {args[0]}")
            sys.exit(1)

    uniq_data_lines = extractUniqueLines(ORIG_OCM_DATA_FILE, 3)
    target_line = uniq_data_lines[msg_index-1]
    msg_dict = ast.literal_eval(target_line[:-1].rstrip('-'))
    transaction = msg_dict['value']['transaction']
    #pprint(transaction)
    ve_key = list(msg_dict['value']['entities'].keys())[0]
    item = msg_dict['value']['entities'][ve_key]
    #pprint(item)

    vm = OrderedDict()
    vm['message_id']  = transaction['message_id']
    vm['subscription_id'] = item['subscription_id']
    vm['action']      = item['action']
    vm['object_id']   = ve_key
    vm['object_type'] = item['object_type']
    vm['ref']         = item['ref']
    vm['detail_link'] = item['detail_link']
    vm['project']     = item['project']
    vm['transaction'] = {'timestamp' : transaction['timestamp'] ,
                         'trace_id'  : transaction['trace_id'],
                         'user'      : transaction['user']
                        }
    vm['changes'] = item['changes']
    vm['state']   = item['state']
    print("{")
    for key in vm.keys():
        if key in ['message_id', 'action', 'object_id', 'object_type', 'ref', 'detail_link']:
            print('    "%s" : "%s"' % (key, vm[key]))
        elif key == 'subscription_id':
            print('    "%s" : %s' % (key, vm[key]))
        # have to select out the keys that get std treatment vs those with special
        # like project, transaction, changes, state
        elif key == 'project':
            print('    "project" : %s' % (repr(vm[key]).replace("'", '"')))
        elif key == 'transaction':
            print('    "transaction" : %s' % (repr(vm[key]).replace("'", '"')))
        elif key == 'changes':
            print('    "changes" : {')
            for attr_uuid in vm['changes'].keys():
                attr_value_info = vm['changes'][attr_uuid]
                if attr_value_info['type'] in ['Integer', 'Float', 'String', 'Date', 'Rating']:
                    stdized_value = fixKeyOrder(attr_value_info, group='changes')
                    print('                 "%s" : %s' % (attr_uuid, stdized_value))
                else:
                    ml, cvl, ovl = fixComplexFieldKeyOrder(attr_value_info, group='changes')
                #name, display_name, type, ref, added, removed, value, old_value
                    print('%s  "%s" : %s,' % (' ' * 15, attr_uuid, ml[:-1]))
                    print('%s  %s,'   % (' ' * 57, cvl))
                    print('%s  %s },' % (' ' * 57, ovl))
            print('                }')
        elif key == 'state':
            print('    "state" :   {')
            for attr_uuid in vm['state'].keys():
                attr_value_info = vm['state'][attr_uuid]
                #print(attr_value_info)
                if attr_value_info['type'] in ['Integer', 'Float', 'String', 'Date', 'Rating']:
                    stdized_value = fixKeyOrder(attr_value_info, group='state')
                else:
                    ml, cvl, ovl = fixComplexFieldKeyOrder(attr_value_info, group='state')
                    print('%s  "%s" : %s,' % (' ' * 15, attr_uuid, ml[:-1]))
                    value = attr_value_info['value']
                    if value:
                        value = repr(value)
                    print('%s  "value" : %s }' % (' ' * 57, value))
                    #print('%s  %s,'   % (' ' * 57, cvl))
            print('                }')

    print("}")
    #pprint(vm)  # nope, has OrderedDict prefix on output, and has single quoted items

#########################################################################################

def fixKeyOrder(ind, group='changes'):
    correct_order = ['name', 'display_name', 'type', 'ref', 'added', 'removed', 'value', 'old_value']
    if group == 'state':
        correct_order.remove('added')
        correct_order.remove('removed')
        correct_order.remove('old_value')
    cod = OrderedDict()
    [cod.__setitem__(field, ind[field]) for field in correct_order]
    covs = "{%s}" % ", ".join([f'"{key}" : "{value}"' for key, value in cod.items()])
    return covs

def fixComplexFieldKeyOrder(ind, group='changes'):
    correct_order = ['name', 'display_name', 'type', 'ref', 'added', 'removed']
    if group == 'state':
        correct_order.remove('added')
        correct_order.remove('removed')
    cod = OrderedDict()
    [cod.__setitem__(field, ind[field]) for field in correct_order]
    ml = "{%s}" % ", ".join([f'"{key}" : "{value}"' for key, value in cod.items()])

    # put 'value' and  'old_value' on  separate lines
    cvod = OrderedDict()
    correct_value_items_order = ['object_type', 'name', 'order_index', 'id', 'ref', 'detail_link']
    #[cvod.__setitem__(field, ind['value'][field]) for field in correct_value_items_order if field in ind['value']]
    for field in correct_value_items_order:
        if ind['value'] and field in ind['value']:
            cvod.__setitem__(field, ind['value'][field])
    cvl = '"value"     : {%s}' % ", ".join([f'"{key}" : "{value}"' for key, value in cvod.items()])

    if group == 'changes':
        ovod = OrderedDict()
        [ovod.__setitem__(field, ind['old_value'][field]) for field in correct_value_items_order if field in ind['old_value']]
        ovl = '"old_value" : {%s} }' % ", ".join([f'"{key}" : "{value}"' for key, value in ovod.items()])
    else:
        ovl = ''

    return ml, cvl, ovl

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
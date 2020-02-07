import sys, os
import json
import datetime
import traceback


###################################################################################################

def kf_doorman(request):
    print(request.headers)
    payload = json.loads(request.data)



import sys, os
import json
import datetime
import traceback

from os import getenv

from sqlalchemy import Boolean, Column, DateTime, Integer, LargeBinary, String
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
###################################################################################################

def carnivoreChomp(request):
    print("The bear has bitten you")


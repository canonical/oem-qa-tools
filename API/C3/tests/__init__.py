import os
import sys

# Add the path of oem-qa-tools to python path
sys.path.insert(0, os.path.split(os.getcwd())[0])

os.environ['DEBUG_C3'] = 'dev'

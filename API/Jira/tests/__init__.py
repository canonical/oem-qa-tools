import os
import json
import sys

# Add the path of oem-qa-tools to python path
sys.path.insert(0, os.path.split(os.getcwd())[0])

os.environ['DEBUG_JIRA'] = 'dev'

# Check Jira API Token
with open(
    os.path.join(os.getcwd(), 'configs', 'jira_config', 'api_token.json')
) as f:
    api_token = json.load(f)
    if not api_token['email'] or not api_token['api_token']:
        raise Exception('Invalid Jira API token')

# Load testing data
dummy_payload = {}
with open(
    os.path.join(os.getcwd(), 'tests', 'testing_data.json')
) as f:
    dummy_payload = json.load(f)

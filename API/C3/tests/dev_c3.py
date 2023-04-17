import json

from C3.apis.base import C3API

c3 = C3API()
# res = c3.get_dut_by_cid(cid='202208-28154')
# dut_data = json.loads(res.text)
# holder = dut_data['objects'][0]['holder']

res = c3.update_dut_holder(cid='202210-30697', holder_launchpad_id='')
dut_data = json.loads(res.text)
print(json.dumps(dut_data, indent=4))

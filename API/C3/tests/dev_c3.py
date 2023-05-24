import json

from C3.apis.base import C3API, TaipeiLocation

staging_site = 'https://certification.staging.canonical.com/api/v1/hardware'
c3 = C3API(base_url=staging_site)

# Get the holder of specific DUT
res = c3.get_dut_by_cid(cid='202208-28154')
dut_data = json.loads(res.text)
holder = dut_data['objects'][0]['holder']
print(holder)

# Update the holder and location of specific DUT
payload = {
    'holder': '<launchpad_id>',
    'location': TaipeiLocation['TEL_L7'].value
}
res = c3.update_dut(cid='202208-28154', payload=payload)
print(res.status_code)

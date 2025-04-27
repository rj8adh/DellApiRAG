from requests import Session
from pprint import pprint
from bs4 import BeautifulSoup
import json

sesh = Session() # I used a session because it's good practice in case I want to post stuff later

# Cookies Arent Necessary For This Website, But These Are The Ones Present For A Real User:
cookies = {
#    'ak_bmsc': 'FA0AD65B35C10CC1AF54B4E7B203172A~000000000000000000000000000000~YAAQk/fTF2ED0WWWAQAA175dcBuAOO6BnnNWcHWRiucBL4GpOQnpMP9zPPx3VJ1TFjvceKtqYB8KLoSAg1mphFmtjbcMNhQfX8b7SYf+hPLR1NfNQnqA8BP86hCRok6raFnZyIuXvrSiVRaRAYLBXNdMzcJR4w1KKGmAYR6nwVIcmza3+mHoeRNS/PXe5Np5kYcOu5uJmxYNXt+vNYMSAYo7wZGHGjJbMQ/c6hLQxG3kwSuRKPZNQgRsUFy4TJF3b0QxFzP36M/d4y8HRS7D5PIlFtFhOhlRNl3nfD+YBds9veQ2HZecE+qjXIiUGyyyg/wnuLvNS4jAKhDRl1VenGJu62TX6D7XoFcKboRks2/Z/j8MRGuyvti7',
#     's_vnc365': '1777181543262%26vn%3D3',
#     's_ivc': 'true',
#     'kndctr_4DD80861515CAB990A490D45_AdobeOrg_cluster': 'or2',
#     's_ips': '490',
#     's_tp': '718',
#     's_ppv': 'us%257Cen%257Ccorp%257Cdeveloperportal%257C%2C68%2C68%2C68%2C490%2C1%2C1',
#     'bm_sv': '850AC27A42D3FF8005B727F88DD56C81~YAAQk/fTF4mI5mWWAQAAP5GscBvUqzyI5JBXfptnsdOMuxfXiLi6201PGG0R5UUc6bF/4yfsWVf+OaBW3qsXg3IxDJ9ox/ZI95Z+0jSiLPE1m2suNsP7PCIw3aAUiz6oHBJjJT4dAxVtjjxpiAoCR+YjX65V2ummtZrZ315nZvHkiepKhVwKXCbrMGVey7GDvhWRFjQRevw7ZqQlYMfsKmgtUrjM2V6toF3tbOcCVH1Z3Nw46F9mhoYZmEVCrvQ=~1',
}

# To make my request seem like it's from a real computer (isn't necessary)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
}

linksResponse = sesh.get(
    'https://developer.dell.com/api/apis/7ce7d11a-ff9c-47cc-b958-bd30dc9770f0/versions/2.0.0/docs', # The endpoint I found that contains all the URIs before they're converted to js
    cookies=cookies,
    headers=headers,
)

with open("storedData/apiCallData.json", 'w') as linksJson:
    json.dump(linksResponse.json(), linksJson, indent=4)

print("Links Response Json Dumped")

data = linksResponse.json()
# I only need the ID to get the details for the page, but I'm storing URI to point user to relevant webpage later
allUrisAndIds = []

# Getting all the URIs for each item (some were in drop downs)
def extract_uris(items):
    for item in items:
        if item.get("type") == "item" and "uri" in item and "id" in item:
            allUrisAndIds.append((item["uri"], item["id"]))
        if item.get("items"): # if there are sub items (mainly for drop down) recursively keep searching
            extract_uris(item["items"])

# Making sure that there is a toc before extracting the uris from it
if "toc" in data and "items" in data["toc"]:
    extract_uris(data['toc']['items'])
    with open("storedData/linksAndIds.json", 'w') as all:
        json.dump(allUrisAndIds, all, indent=2)

print('ALL URIS:')
pprint(allUrisAndIds)
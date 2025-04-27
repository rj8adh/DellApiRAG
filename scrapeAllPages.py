#TODO Format data with examples and api parameters so it's easier for the AI to understand
from requests import Session
from bs4 import BeautifulSoup
import json
from pprint import pprint

UUID = "7ce7d11a-ff9c-47cc-b958-bd30dc9770f0" # If it changes (unlikely) you can use the value under uuid in the apiCallData.json data
BASEURL = "https://developer.dell.com/apis"

params = {
    'uuid': UUID,
}

def scrapePage(id: int):
    sesh = Session()
    link = f'https://developer.dell.com/api/nodes/{id}/docs'
    response = sesh.get(link, params=params)
    pprint(json.loads(response.content))
    print(f"Response for link: {link}\n")

    # Used to return only the data/main text, but the json format has some other useful stuff
    # return json.loads(response.content).get("data")
    return json.loads(response.content)


def scrapePages(links_and_ids: list):
    allPages = {}
    for pageNum, link in enumerate(links_and_ids, 1):
        allPages[BASEURL + link[0]] = scrapePage(link[1])
        print(f"On Page #{pageNum}/{len(links_and_ids)}")

    with open("storedData/allDocumentation.json", 'w') as docs:
        json.dump(allPages, docs, indent=4)
    return allPages
    

if __name__ == "__main__":
    with open('storedData/linksAndIds.json', 'r') as file:
        allLinksAndIds = json.load(file)
    pprint(scrapePages(allLinksAndIds))

    newVals = {}

    with open('storedData/allDocumentation.json', 'r') as f:
        allData = dict(json.load(f))

    # for dat in allData:
    #     newUrl = str(dat)[:40]
    #     newVals[]

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
from pprint import pprint
from scrapeAllPages import fixUrls

UUID = "7ce7d11a-ff9c-47cc-b958-bd30dc9770f0"
BASEURL = "https://developer.dell.com/apis"

params = {
    'uuid': UUID,
}

async def scrapePage(session: aiohttp.ClientSession, node_id: int):
    url = f'https://developer.dell.com/api/nodes/{node_id}/docs'
    async with session.get(url, params=params) as resp:
        data = await resp.json()
        pprint(data)
        print(f"Response for URL: {url}\n")
        return data

async def scrapePages(links_and_ids: list):
    allPages = {}
    sem = asyncio.Semaphore(10)  # Limiting concurrent requests

    async with aiohttp.ClientSession() as session:
        async def fetch(path: str, node_id: int):
            async with sem:
                result = await scrapePage(session, node_id)
                allPages[BASEURL + path] = result
                print(f"Fetched {path}")

        tasks = [fetch(path, nodeId) for path, nodeId in links_and_ids]
        await asyncio.gather(*tasks)

    # Storing the results
    with open("storedData/allDocumentation.json", 'w') as out:
        json.dump(fixUrls(allPages), out, indent=4)
    return allPages

if __name__ == "__main__":
    with open('storedData/linksAndIds.json', 'r') as f:
        linksAndIds = json.load(f)

    allDocs = asyncio.run(scrapePages(linksAndIds))
    pprint(allDocs)

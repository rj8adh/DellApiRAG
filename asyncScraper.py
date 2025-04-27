import aiohttp
import asyncio
import json
from pprint import pprint
import random
import time
from aiohttp import ClientTimeout

UUID = "7ce7d11a-ff9c-47cc-b958-bd30dc9770f0"  # If it changes (unlikely) you can use the value under uuid in the apiCallData.json data
BASEURL = "https://developer.dell.com/apis"

params = {
    'uuid': UUID,
}

# Configuration for rate limiting and retries
MAX_CONCURRENT_REQUESTS = 5  # Limit concurrent connections
MAX_RETRIES = 3
RETRY_DELAY = 2  # Base seconds to wait between retries
TIMEOUT = ClientTimeout(total=30)  # 30 seconds timeout for requests

async def scrapePage(session, id: int, semaphore):
    link = f'https://developer.dell.com/api/nodes/{id}/docs'
    
    # Use semaphore to limit concurrent requests
    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                async with session.get(link, params=params, timeout=TIMEOUT) as response:
                    content = await response.json()
                    print(f"Response for link: {link}\n")
                    return content
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < MAX_RETRIES - 1:
                    # Add jitter to avoid synchronized retries
                    wait_time = RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1)
                    print(f"Error on {link}, retrying in {wait_time:.2f}s... ({attempt+1}/{MAX_RETRIES})")
                    print(f"Error was: {str(e)}")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"Failed after {MAX_RETRIES} attempts for {link}: {str(e)}")
                    # Return None or some placeholder to indicate failure
                    return {"error": str(e), "status": "failed"}

async def scrapePages(linksAndIds: list):
    allPages = {}
    
    # Create a semaphore to limit concurrent connections
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    # Configure TCP connector with limits
    connector = aiohttp.TCPConnector(
        limit=MAX_CONCURRENT_REQUESTS,
        ssl=False,  # Set to True if you need SSL verification
        force_close=True  # Important for avoiding connection pooling issues
    )
    
    # Create a ClientSession with our configured connector
    async with aiohttp.ClientSession(connector=connector, timeout=TIMEOUT) as session:
        tasks = []
        for link in linksAndIds:
            task = asyncio.create_task(scrapePage(session, link[1], semaphore))
            tasks.append((BASEURL + link[0], task))
        
        # Track progress
        total = len(linksAndIds)
        completed = 0
        
        # Process tasks as they complete
        for url, task in tasks:
            try:
                result = await task
                allPages[url] = result
            except Exception as e:
                print(f"Task failed for {url}: {str(e)}")
                allPages[url] = {"error": str(e), "status": "failed"}
            
            completed += 1
            print(f"On Page #{completed}/{total}")
    
    # Save to file
    with open("storedData/allDocumentation.json", 'w') as docs:
        json.dump(allPages, docs, indent=4)
    
    return allPages

# Process links in batches to avoid memory issues with very large lists
async def process_in_batches(linksAndIds, batch_size=50):
    all_results = {}
    total_batches = (len(linksAndIds) + batch_size - 1) // batch_size
    
    for i in range(0, len(linksAndIds), batch_size):
        batch = linksAndIds[i:i+batch_size]
        print(f"\nProcessing batch {i//batch_size + 1}/{total_batches} (size: {len(batch)})")
        
        # Add a small delay between batches to avoid overwhelming the server
        if i > 0:
            await asyncio.sleep(2)
            
        batch_results = await scrapePages(batch)
        all_results.update(batch_results)
    
    return all_results

async def main(linksAndIds: list):
    return await process_in_batches(linksAndIds)

# To execute the script standalone
if __name__ == "__main__":
    # Replace with your actual linksAndIds list
    with open("storedData/linksAndIds.json", 'r') as f:
        allLinksAndIds = json.load(f)
    
    # Run the async main function
    result = asyncio.run(main(allLinksAndIds))
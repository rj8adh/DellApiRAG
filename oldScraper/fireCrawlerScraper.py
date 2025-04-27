from dotenv import load_dotenv
import os
from firecrawl import FirecrawlApp, ScrapeOptions, JsonConfig
from pprint import pprint
import json

load_dotenv()

CRAWLER_KEY = os.getenv("FIRECRAWL_KEY")
BASEURL = "https://developer.dell.com/apis/7ce7d11a-ff9c-47cc-b958-bd30dc9770f0/versions/2.0.0/docs/"

app = FirecrawlApp(api_key=CRAWLER_KEY)

# Crawl a website:
# crawl_status = app.crawl_url(
#   'https://developer.dell.com/apis/7ce7d11a-ff9c-47cc-b958-bd30dc9770f0/versions/2.0.0/docs/introduction.md', 
#   limit=100, 
#   scrape_options=ScrapeOptions(formats=['markdown', 'html']),
#   poll_interval=30
# )
# pprint(scrape_result.markdown)

scrape_result = app.scrape_url(url='https://developer.dell.com/apis/7ce7d11a-ff9c-47cc-b958-bd30dc9770f0/versions/2.0.0/docs/Create-token.md', formats=['markdown', 'links'])
pprint(scrape_result)
# pprint(f"\n\n\n{scrape_result.markdown}")
print([k for k in scrape_result])
print(scrape_result.markdown)

with open("storedData/introductionPage.md", 'w') as f:
    f.write(str(scrape_result.markdown))
f.close()

with open("storedData/introLinks.json", 'w') as file:
    json.dump(list(scrape_result.links), file)
file.close()

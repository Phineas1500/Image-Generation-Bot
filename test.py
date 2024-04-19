from twitter.account import Account
from twitter.search import Search
from twitter.scraper import Scraper
#import random
#import logging
#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#logger = logging.getLogger(__name__)

ct0 = "79befdd95fc61aaf3b62d11cb8edf20551cf35c839db028abe3ff7b8140d8562fdfa4bcbfe79b58de3c685cce0e65b90738540acf47d972093d0ab52dddfe6847d22a73faf91560540c68f90d162b538"
auth_token = "e61b08456e0ad58388d0ebc1adb2d994c800db99"

# Rat Bot
account = Account(cookies={"ct0": ct0, "auth_token": auth_token})


search = Search(cookies={"ct0": ct0, "auth_token": auth_token})

scraper = Scraper(cookies={"ct0": ct0, "auth_token": auth_token})

res = search.run(
    limit=1,
    retries=30,
    queries=[
        {
            'category': 'Latest',
            'query': '(from:jschlatt) (@RatIsSoCute)'
        },
    ],
)

# checking if account super follows me
subscribes = False
try:
    if (res[0][0]['content']['itemContent']['tweet_results']['result']['core']['user_results']['result']['super_followed_by'] == True):
        print("User super follows me")
        subscribes = True
    else:
        print("User does not super follow me")
        subscribes = False
except:
    print("User does not super follow me")
    subscribes = False
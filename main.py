import json
from twitter.account import Account
from twitter.search import Search
from twitter.scraper import Scraper
#import random
#import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
import requests
import threading
import os
from openai import OpenAI
client = OpenAI()

#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#logger = logging.getLogger(__name__)

ct0 = os.environ.get('CT0')
auth_token = os.environ.get('AUTH_TOKEN')

def load_ids(filename):
    try:
        with open(filename, 'r') as f:
            # Load IDs into a set for efficient lookup
            return set(json.load(f))
    except FileNotFoundError:
        # Return an empty set if file does not exist
        return set()

def save_ids(filename, ids):
    with open(filename, 'w') as f:
        # Convert set to list for JSON compatibility
        json.dump(list(ids), f)

cooldown_users = set()
daily_quota = {}

def add_to_cooldown(username):
    cooldown_users.add(username)
    try:
        threading.Timer(10 * 60, lambda: cooldown_users.remove(username)).start()
    except:
        print("Cooldown failed")
    save_quota()

def check_user_status(username):
    if username in cooldown_users:
        return "cooldown"
    quota = daily_quota.get(username, {'count': 0, 'date': datetime.now().date()})
    if quota['count'] >= 10 and quota['date'] == datetime.now().date():
        return "quota_exceeded"
    return "allowed"

def update_quota(username):
    if username not in daily_quota or daily_quota[username]['date'] != datetime.now().date():
        daily_quota[username] = {'count': 1, 'date': datetime.now().date()}
    else:
        daily_quota[username]['count'] += 1
    save_quota()

def save_quota():
    with open('daily_quota.json', 'w') as f:
        json.dump({user: {'count': daily_quota[user]['count'], 'date': daily_quota[user]['date'].isoformat()} for user in daily_quota}, f)

def load_quota():
    if os.path.exists('daily_quota.json'):
        with open('daily_quota.json', 'r') as f:
            loaded_quota = json.load(f)
            for user, data in loaded_quota.items():
                daily_quota[user] = {'count': data['count'], 'date': datetime.fromisoformat(data['date']).date()}

load_quota()  # Load the quota data when the program starts
        

# Rat Bot
account = Account(cookies={"ct0": ct0, "auth_token": auth_token})


search = Search(cookies={"ct0": ct0, "auth_token": auth_token})

scraper = Scraper(cookies={"ct0": ct0, "auth_token": auth_token})

while True:
    old_ids = load_ids('tweet_ids4.txt')
    approved_users = load_ids('approved_users.txt')
    try:
        res = search.run(
            limit=1,
            retries=30,
            queries=[
                {
                    'category': 'Latest',
                    'query': '"generate" (@RatIsSoCute)'
                },
            ],
        )
    except:
        print("Can't search for tweets")
        time.sleep(55)
        continue
    alsoNow = datetime.now()
    formatted_datetime = alsoNow.strftime("%Y-%m-%d %H:%M")
    print(formatted_datetime)

    new_ids = set()

    for tweet_info in res[0]:
        tweet_id = tweet_info['content']['itemContent']['tweet_results']['result']['rest_id']
        #first_tweet_rest_id = res[0][0]['content']['itemContent']['tweet_results']['result']['rest_id']
        #handle_no_paren = handle[6:-1]  # Remove the '(from:' and ')' from the handle

        if tweet_id in old_ids:
            print("Tweet ID already encountered, checking another tweet.")
            new_ids.add(tweet_id)
            continue  # Check the next tweet
        
        new_ids.add(tweet_id)
        tweet_text_list = []

        # checking if account follows me, if not, skip
        username = tweet_info['content']['itemContent']['tweet_results']['result']['core']['user_results']['result']['legacy']['screen_name']
        try:
            if (tweet_info['content']['itemContent']['tweet_results']['result']['core']['user_results']['result']['legacy']['followed_by']):
                print("User follows me")
            else:
                print("User does not follow me")
                try:
                    account.reply("Follow my account to create images", tweet_id=tweet_id)
                except:
                    print("Can't reply to that tweet")
                continue
        except:
            print("User does not follow me")
            try:
                account.reply("Follow my account to create images", tweet_id=tweet_id)
            except:
                print("Can't reply to that tweet")
            continue
        # check if user has reached quota or cooldown for day
        
        user_status = check_user_status(username)
        if (user_status == "cooldown") and (username not in approved_users):
            print("User is on cooldown")
            try:
                account.reply("You are on cooldown, try again in 10 minutes", tweet_id=tweet_id)
            except:
                print("Can't reply to that tweet")
            continue
        elif (user_status == "quota_exceeded") and (username not in approved_users):
            print("User has exceeded daily quota")
            try:
                account.reply("You have exceeded the daily quota, try again tomorrow", tweet_id=tweet_id)
            except:
                print("Can't reply to that tweet")
            continue

        # checking if account super follows me
        subscribes = False
        try:
            if (tweet_info['content']['itemContent']['tweet_results']['result']['core']['user_results']['result']['super_followed_by'] == True):
                print("User super follows me")
                subscribes = True
            else:
                print("User does not super follow me")
                subscribes = False
        except:
            print("User does not super follow me")
            subscribes = False

        tweet_full_text = tweet_info['content']['itemContent']['tweet_results']['result']['legacy']['full_text']
        print(tweet_id)
        print(tweet_full_text)
        try:
            tweet_full_text = tweet_full_text.lower()
            tweet_full_text = tweet_full_text.replace("@ratissocute", "")
        except:
            print("Can't remove username from tweet")

        #check if text has the word only
        if "only" in tweet_full_text:
            hasOnly = True
            try:
                tweet_full_text = tweet_full_text.lower()
                tweet_full_text = tweet_full_text.replace("only", "")
            except:
                print("Can't remove 'only' from tweet")
        else:
            hasOnly = False

        #check if text has the word also
        if "also" in tweet_full_text:
            hasAlso = True
            try:
                tweet_full_text = tweet_full_text.lower()
                tweet_full_text = tweet_full_text.replace("also", "")
            except:
                print("Can't remove 'also' from tweet")
        else:
            hasAlso = False

        isReply = False
        try:
            print(tweet_info['content']['itemContent']['tweet_results']['result']['legacy']['in_reply_to_status_id_str'])
            tweetBeingRepliedTo = scraper.tweets_details([tweet_info['content']['itemContent']['tweet_results']['result']['legacy']['in_reply_to_status_id_str']])
            isReply = True
        except:
            # tweet is not a reply
            print("Tweet is not a reply")
            isReply = False
        if (isReply):
            for tweet_chain_info in tweetBeingRepliedTo[0]['data']['threaded_conversation_with_injections_v2']['instructions'][0]['entries']:
                try:
                    print(tweet_chain_info['content']['itemContent']['tweet_results']['result']['legacy']['full_text'])
                    tweet_text_list.append(tweet_chain_info['content']['itemContent']['tweet_results']['result']['legacy']['full_text'])
                except:
                    print("This tweet is unavailable")
                    break

        if (hasAlso == True or isReply == False):
            tweet_text_list.append(tweet_full_text)

        if (len(tweet_text_list) == 0):
            # could not access one or more tweets in the chain
            print("Could not access one or more tweets in the chain. An account might be private or have blocked me.")
            try:
                account.reply("Could not access one or more tweets in the chain", tweet_id=tweet_id)
            except:
                print("Can't reply to that tweet")
            continue

        tweetWords = tweet_full_text.lower()
        filterDetect = False
        filter = [
            "groom", "disgust", "piece of", "pathetic", "allegation",
            "don't understand", "manipulat", "ptsd", "this is fake",
            "this isn't true", "victim", "support", "pedo", "harass", "minor",
            "died", "passed away", "devastat", "heart broken", "for your loss",
            "much love", "take as long", "take all the time", "love ya",
            "sorry", "take care", "heartbreaking", "heart goes out",
            "hearts go out", "in fear", "war zone", "daily life",
            "anyone affected", "rest in peace", "rip", "chemo", "cancer",
            "racist", "❤️"
        ]
        for i in filter:
            if i in tweetWords:
                filterDetect = True
        if (filterDetect == False):
            if (isReply == False):
                # PROMPT should only have only tweet in tweet_text_list, not reply
                PROMPT = tweet_text_list[0]
            elif (hasOnly and hasAlso):
                # PROMPT should only have last two tweets
                PROMPT = tweet_text_list[-2] + ", " + tweet_text_list[-1]
            elif (hasOnly and not hasAlso):
                # PROMPT should only have last tweet
                PROMPT = tweet_text_list[-1]
            elif (not hasOnly and hasAlso):
                # PROMPT should have every tweet
                # already added also to list
                PROMPT = ", ".join(tweet_text_list)
            else:
                # PROMPT should have every tweet
                PROMPT = ", ".join(tweet_text_list)

            print(PROMPT)
            #check if username is in approved users
            if ((username in approved_users) or (subscribes)):
                print("User is approved for dall-e-3")
                model = "dall-e-3"
                size="1024x1024"
            else:
                model = "dall-e-2"
                size="512x512"

            try:
                print("Generating image")
                response = client.images.generate(
                    model=model,
                    prompt=PROMPT,
                    size=size,
                    quality="standard",
                    n=1,
                )
            except:
                print("Can't initially generate image")
                # generate a PROMPT that is allowed by safety system
                try:
                    responsePROMPT = client.chat.completions.create(
                        model="gpt-3.5-turbo-0125",
                        response_format={ "type": "json_object" },
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant designed to output JSON. You will clean up the prompt and make it pass DALL-E's safety system without using the word 'generate'."},
                            {"role": "user", "content": PROMPT}
                        ]
                    )
                except:
                    print("Can't generate new prompt")
                    try:
                        account.reply("Could not create image, prompt may not be allowed by safety system", tweet_id=tweet_id)
                    except:
                        print("Can't reply to that tweet")
                    continue
                PROMPT = responsePROMPT.choices[0].message.content
                print(PROMPT)
                try:
                    print("Generating image")
                    response = client.images.generate(
                        model=model,
                        prompt=PROMPT,
                        size=size,
                        quality="standard",
                        n=1,
                    )
                except:
                    print("Can't generate image")
                    try:
                        account.reply("Could not create image, prompt may not be allowed by safety system", tweet_id=tweet_id)
                    except:
                        print("Can't reply to that tweet")
                    continue
            
            image_url = response.data[0].url
            print(image_url)


            # Assuming `image_url` contains the URL to the image you want to download
            response = requests.get(image_url)

            # Check if the request was successful
            if response.status_code == 200:
                with open(Path.cwd() / 'responses/image.png', 'wb') as f:
                    f.write(response.content)
            else:
                print("Failed to download the image.")
                try:
                    print("Replying to tweet with error message")
                    account.reply("Could not create image, request was not successful", tweet_id=tweet_id)
                except:
                    print("Can't reply to that tweet")
                continue
            '''
            # generate a caption based on PROMPT

            response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": "You are a helpful assistant designed to output JSON. You will give a response to the prompt without using the word 'generate'. The response should be related to the prompt."},
                {"role": "user", "content": PROMPT}
            ]
            )
            print(response.choices[0].message.content)
            '''
            # Upload the image to Twitter

            try:
                print("Replying to tweet")
                alsoNow = datetime.now()
                one_minute_later = alsoNow + timedelta(minutes=1)
                formatted_datetime = one_minute_later.strftime("%Y-%m-%d %H:%M")
                print(formatted_datetime)
                account.schedule_reply("", formatted_datetime, tweet_id=tweet_id, media=[
                    {'media': Path.cwd() / 'responses/image.png', 'alt': model + ", Prompt: " + PROMPT},
                ])
                # update quota and add to cooldown
                update_quota(username)
                add_to_cooldown(username)
            except:
                print("Can't reply to that tweet")
        else:
            try:
                account.reply("Not able to reply to this tweet", tweet_id=tweet_id)
            except:
                print("Can't reply to that tweet")

        # Update the list of old tweet IDs
        #old_ids[handle_no_paren] = first_tweet_rest_id
        time.sleep(25)

    # Save the updated list of tweet IDs back to the file outside the for-loop
    save_ids('tweet_ids4.txt', new_ids)
    time.sleep(55)

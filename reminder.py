import smtplib
import time
import os
from email.message import EmailMessage
from tabulate import tabulate
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
import re
import snscrape.modules.twitter as sntwitter
import datetime
import csv
import requests
import feedparser


CSV_FILE = "tweets.csv"
password = os.getenv("PASSWORD")
from_email = os.getenv("FROM_EMAIL")
to_email = os.getenv("TO_EMAIL")
username = os.getenv("USERNAME")
bearer_token = os.getenv("BEARER_TOKEN")

def calculate_days_elapsed(date):
    today = datetime.date.today()
    date_posted = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    days_elapsed = (today - date_posted).days
    return days_elapsed

def infinite_fibonacci():
    a, b = 0, 1
    while True:
        yield b
        a, b = b, a + b

def filter_reminder_tweets(data, fibonacci_sequence):
    return data[data.apply(lambda row: calculate_days_elapsed(row["Date of Post"]) in fibonacci_sequence, axis=1)]

# def fetch_new_tweets(username, latest_tweet_date):
#     new_tweets = []
#     query = f"from:{username} since:{latest_tweet_date.strftime('%Y-%m-%d')}"

#     for tweet in sntwitter.TwitterSearchScraper(query).get_items():
#         hashtags = re.findall(r"#(\w+)", tweet.content)
#         new_tweets.append((tweet.content, tweet.date.date(), ", ".join(hashtags), tweet.url))

#     return new_tweets
# import tweepy

# def fetch_new_tweets(username, latest_tweet_date):
#     consumer_key = os.getenv("API_KEY")
#     consumer_secret = os.getenv("API_KEY_SECRET")
#     access_token = os.getenv("ACCESS_TOKEN")
#     access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

#     auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
#     auth.set_access_token(access_token, access_token_secret)

#     api = tweepy.API(auth)

#     new_tweets = []
#     for tweet in tweepy.Cursor(api.user_timeline, screen_name=username, since_id=latest_tweet_date, tweet_mode="extended").items():
#         hashtags = re.findall(r"#(\w+)", tweet.full_text)
#         new_tweets.append((tweet.full_text, tweet.created_at.date(), ", ".join(hashtags), f"https://twitter.com/{username}/status/{tweet.id}"))

#     return new_tweets
# def fetch_new_tweets(username, latest_tweet_date):
#     new_tweets = []
#     url = "https://api.twitter.com/2/users/by/username/" + username
#     headers = create_twitter_headers()

#     response = requests.get(url, headers=headers)
#     response.raise_for_status()
#     user_id = response.json()["data"]["id"]

#     query = f"from:{user_id} since:{latest_tweet_date.strftime('%Y-%m-%d')}"
#     tweet_fields = "attachments,author_id,context_annotations,created_at,entities,geo,id,in_reply_to_user_id,lang,possibly_sensitive,public_metrics,referenced_tweets,source,text,withheld"
#     url = f"https://api.twitter.com/2/tweets/search/recent?query={query}&tweet.fields={tweet_fields}"

#     response = requests.get(url, headers=headers)
#     response.raise_for_status()
#     tweets_data = response.json()["data"]

#     for tweet in tweets_data:
#         hashtags = [hashtag["tag"] for hashtag in tweet["entities"]["hashtags"]] if "hashtags" in tweet["entities"] else []
#         new_tweets.append((tweet["text"], tweet["created_at"][:10], ", ".join(hashtags), f"https://twitter.com/{username}/status/{tweet['id']}"))

#     return new_tweets

def fetch_new_tweets(username, latest_tweet_date):
    rss_url = f"https://nitter.net/{username}/rss"
    feed = feedparser.parse(rss_url)
    new_tweets = []

    for entry in feed.entries:
        tweet_date = datetime.datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %z").date()
        if tweet_date > latest_tweet_date:
            tweet = {
                'content': entry.title,
                'date': tweet_date,
                'hashtags': ", ".join(re.findall(r"#(\w+)", entry.title)),
                'url': entry.link
            }
            new_tweets.append(tweet)

    return new_tweets

def send_email(subject, content):
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    # Add your table as an HTML content
    html_content = f"""\
    <html>
    <head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #f0f0f0;
        }}
        .header {{
            background-color: #8B4513;
            padding: 15px;
            color: #fff;
            font-size: 24px;
            font-weight: bold;
            text-align: center;
        }}
        .container {{
            width: 80%;
            margin: 20px auto;
            padding: 20px;
            background-color: #fff;
            border: 1px solid #ccc;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        h2 {{ color: #333; }}
        p {{ color: #666; font-size: 16px; }}
        hr {{ border: none; border-top: 1px solid #ccc; margin-top: 20px; margin-bottom: 20px; }}
        a {{ color: #0073e6; text-decoration: none; float: right; }}
        a:hover {{ text-decoration: underline; }}
        em {{ font-style: italic; }}
    </style>
    </head>
    <body>
        <div class="container">
        <div class="header">Idea Reminder</div>
        {content}
        </div>
    </body>
    </html>
    """
    mime_text = MIMEText(html_content, "html")
    msg.attach(mime_text)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(from_email, password)
        server.sendmail(from_email, to_email, msg.as_string())

def update_and_read_csv(new_tweets):
    if os.path.isfile(CSV_FILE):
        data = pd.read_csv(CSV_FILE)
    else:
        columns = ["Tweet", "Date of Post", "Tags", "URL"]
        data = pd.DataFrame(columns=columns)

    existing_tweets = set(data["Tweet"])

    new_rows = []
    for tweet, date, hashtags, url in new_tweets:
        if tweet not in existing_tweets:
            tweet = tweet.replace('\n', ' ')
            new_row = {"Tweet": tweet, "Date of Post": date.strftime("%Y-%m-%d"), "Tags": hashtags, "URL": url}
            new_rows.append(new_row)

    if new_rows:
        new_data = pd.DataFrame(new_rows)
        data = pd.concat([data, new_data], ignore_index=True)
        data.to_csv(CSV_FILE, index=False)

    return data

def main():

    CSV_FILE = "tweets.csv"
    password = os.getenv("PASSWORD")
    from_email = os.getenv("FROM_EMAIL")
    to_email = os.getenv("TO_EMAIL")
    username = os.getenv("USERNAME")


    fibonacci_sequence = set()
    fibonacci_generator = infinite_fibonacci()

    # Add 30 Fibonacci numbers to the sequence
    for _ in range(30):
        fibonacci_sequence.add(next(fibonacci_generator))

    if os.path.isfile(CSV_FILE):
        latest_tweet_date = max([datetime.datetime.strptime(row[1], "%Y-%m-%d").date() for row in csv.reader(open(CSV_FILE, newline="", encoding="utf-8")) if row[1] != "Date of Post"])
    else:
        latest_tweet_date = datetime.datetime.strptime("2023-01-01", "%Y-%m-%d").date()

    new_tweets = fetch_new_tweets(username, latest_tweet_date)
    data = update_and_read_csv(new_tweets)
    print(fibonacci_sequence)
    reminder_tweets = filter_reminder_tweets(data, fibonacci_sequence)

    if not reminder_tweets.empty:
        email_content = ""
        for _, row in reminder_tweets.iterrows():
            tweet, date, hashtags, url = row["Tweet"], row["Date of Post"], row["Tags"], row["URL"]
            email_content += f'<div class="post">\n'
            email_content += f'<h3>{date}</h3>\n'
            email_content += f'<hr>\n'
            email_content += f'<div class="post-text">\n'
            email_content += f'<p>{tweet}</p>\n'
            email_content += f'<p>Tags: {hashtags}</p>\n'
            email_content += f'</div>\n'
            email_content += f'<div class="post-link">\n'
            email_content += f'<p><a href="{url}">Read more</a></p>\n'
            email_content += f'</div>\n'
            email_content += f'</div>\n'
            email_content += f'<br>\n'

        send_email("Your Daily Idea Reminder is Here", email_content)

if __name__ == "__main__":
    main()

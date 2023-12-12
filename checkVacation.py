import feedparser
import sys
import pandas as pd
from datetime import datetime
import os
import json
import ssl, smtplib

resource = ""

feed_list = ["https://www.pelikan.cz/gf3/pelijee-cz/rss/rssfeed",
             "https://cdnapi.levnocestovani.cz/mlomlo/feed?locale=cs_CZ",
             "https://www.planetacestovani.cz/feed/",
             "http://feeds.feedburner.com/Cestujlevne",
             "http://cestujeme-chytre.eu/feed/",
             "http://fly4free.cz/feed/",
             "https://www.vletenky.com/feed",
             "http://www.radicestujeme.eu/rss/akcni-letenky.xml",
             "http://feeds.feedburner.com/akcniletenky?format=xml",
             "https://honzovyletenky.cz/feed/",
             "https://www.svet-letenek.cz/rss",
             "https://www.levneletenky.org/rss.xml",
             "https://zaletsi.cz/feed/"]

def read_resources() -> None:
	try:
		fileName = os.path.abspath(os.path.dirname(sys.argv[0])) +  '/resources.json'
		with open(fileName, 'r') as filehandle:
			global resource
			resource = json.load(filehandle)
                        # print(resource)
	except:
		print("No file: resources.json found!")
		exit(1)

def read_configs(file_path: str) -> dict[str,list[str]]:
	configs = {}
	with open(file_path) as config_file:
		for line in config_file:
			items = line.strip("\n").split(";")
			configs[items[0]] = items[1:]
	return configs

def log_offer(config_name: str, news: feedparser.util.FeedParserDict) -> bool:
	try:
		data = pd.read_csv(f"foundOffers/{config_name}.tsv",sep="\t")
	except:
		data = pd.DataFrame(columns=["detected_date","title","link","price"])
	if news.link in set(data["link"]):
		print("Already found")
		return False
	price_str = "".join([x for x in news.title.replace(".","") if x.isdigit()])
	price = int(price_str) if len(price_str) > 0 else None
	data.loc[len(data)] = [f"{datetime.now().date()}",news.title,news.link,price]
	data.to_csv(f"foundOffers/{config_name}.tsv",sep="\t",index=False)
	return True

def search_offers(config_name: str, config: list[str]) -> list[feedparser.util.FeedParserDict]:
	cities_from = config[0].split(":")
	cities_to = config[1].split(":")
	offers_to_send = []
	for feed in feed_list:
		NewsFeed = feedparser.parse(feed)
		for news in NewsFeed.entries:
			if "title" in news.keys():
				has_from = False
				has_to = False
				for city_from in cities_from:
					if city_from.lower() in news.get("title").lower():
						has_from = True
				for city_to in cities_to:
					if city_to.lower() in news.get("title").lower():
						has_to = True
				if has_from and has_to:
					print(news.get("title"), news.get("link"))
					is_new_offer = log_offer(config_name,news)
					if is_new_offer:
						offers_to_send.append(news)
	return offers_to_send

def send_email(emailText: str, emails: list[str]):
	print(f"{datetime.now()} - Sending E-mail")
	port = 465  # For SSL

        # Create a secure SSL context
	context = ssl.create_default_context()
	sender_email = "rodinne.info@gmail.com"

	with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
		server.login("rodinne.info@gmail.com", resource)
		for email in emails:
			server.sendmail(sender_email, email, emailText.encode('utf-8'))

def send_new_offers(config_name: str, config: list[str], new_offers: feedparser.util.FeedParserDict ) -> None:
	if len(config) == 2:
		print("No email specified for the given configuration!")
		return None
	emails = config[2].split(":")
	if len(resource) == 0:
		read_resources()
	email_text: str = f"Subject: Letenky {config_name}\n\n"
	for offer in new_offers:
		email_text += f"{offer.title} - {offer.link} \n"
	send_email(email_text,emails)

if __name__ == "__main__":
	if len(sys.argv) != 2:
		print("You have to enter search configuration!")
		exit()
	configs: dict[str,list[str]] = read_configs(sys.argv[1])
	for config_name, config in configs.items():
		print(config_name)
		found_offers = search_offers(config_name, config)
		if len(found_offers) != 0:
			send_new_offers(config_name, config, found_offers)

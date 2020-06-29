import link_extractor
from telegram.ext import Updater
import export_to_telegraph
import yaml
import os

with open('credential') as f:
	credential = yaml.load(f, Loader=yaml.FullLoader)
export_to_telegraph.token = credential['telegraph_token']

tele = Updater(credential['bot_token'], use_context=True) # @web_subscription_bot
debug_group = tele.bot.get_chat('@web_record')

existing = set()

def test():
	count = 0
	prefix = 'https://squatting2047.com/page/'
	for page in range(2, 7):
		url = prefix + str(page)
		for link, _ in link_extractor.getLinks(url):
			if link in existing:
				continue
			existing.add(link)
			simplified = export_to_telegraph.export(link, 
				force_cache = True, force=True, toSimplified=True) 
			debug_group.send_message(simplified)
			count += 1
			if count > 20:
				os.system('open %s -g' % simplified)


if __name__ == '__main__':
	test()
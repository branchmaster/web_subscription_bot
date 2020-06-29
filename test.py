import link_extractor

tele = Updater(credential['bot_token'], use_context=True) # @web_subscription_bot
debug_group = tele.bot.get_chat(420074357)

def test():
	prefix = 'https://squatting2047.com/page/'
	for page in range(2, 7):
		url = prefix + str(page)
		for link, _ in link_extractor.getLinks(url):
			print(link)
			simplified = export_to_telegraph.export(link, 
				force_cache = True, force=True, toSimplified=True) 
			debug_group.send_message(simplified)


if __name__ == '__main__':
	test()
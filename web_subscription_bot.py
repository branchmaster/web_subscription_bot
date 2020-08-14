#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram_util import splitCommand, log_on_fail, matchKey
from telegram.ext import Updater, MessageHandler, Filters
import export_to_telegraph
import time
from db import DB
import threading
import yaml
import link_extractor
import web_2_album
import album_sender
import cached_url
from bs4 import BeautifulSoup
import time

with open('credential') as f:
	credential = yaml.load(f, Loader=yaml.FullLoader)
export_to_telegraph.token = credential['telegraph_token']

tele = Updater(credential['bot_token'], use_context=True) # @web_subscription_bot
debug_group = tele.bot.get_chat(420074357)

db = DB()

@log_on_fail(debug_group)
def sendLink(site, link, fixed_channel = None):
	print('sendLink', site, link)
	simplified = None
	telegraph = None
	album_result = None
	for channel, config in db.sub.channels(site, tele.bot):
		if fixed_channel and channel.id != fixed_channel:
			continue 
		if not simplified and 'to_simplify' in config:
			simplified = export_to_telegraph.export(link, 
				force_cache = True, force=True, toSimplified=True) or link
		if '.douban.' in link and '/note/' not in link:
			album_result = web_2_album.get(link, force_cache = True)
		if not telegraph and not album_result and 'to_telegraph' in config:
			print('telegraph in config, link=', link)
			link = link.strip()
			telegraph = export_to_telegraph.export(link, 
				force_cache = True, force=True) or link
			print('telegraph = ', telegraph)
		message = link
		if 'to_simplify' in config:
			message = simplified
		if 'to_telegraph' in config:
			message = telegraph
		print('message =', message)
		try:
			time.sleep(60)
			if album_result:
				album_sender.send_v2(channel, album_result)
			else:
				channel.send_message(message)
		except Exception as e:
			debug_group.send_message('send fail: ' + str(channel.id) 
				+ ' ' + str(e))

@log_on_fail(debug_group)
def loopImp():
	for site in db.sub.subscriptions():
		for link, count in link_extractor.getLinks(site):
			if 'douban.com/explore' in site and count < 120:
				continue
			if not db.existing.add(link):
				continue
			title = ''.join(export_to_telegraph.getTitle(link).split())
			if not db.existing.add(title):
				continue
			sendLink(site, link)
			break # deal with one link per two hour

def backfillSingle(site, chat_id, max_item = 10):
	links = list(link_extractor.getLinks(site))[:max_item]
	for link, _ in links:
		sendLink(site, link, fixed_channel = chat_id)
	return len(links)

def backfill(chat_id):
	for site in db.sub.sub.get(chat_id, {}):
		backfillSingle(site, chat_id)
	tele.bot.get_chat(chat_id).send_message('finished backfill')

def loop():
	loopImp()
	threading.Timer(60 * 60 * 2, loop).start()

def normalizeConfig(config):
	accept_config = set(['to_telegraph', 'to_simplify'])
	config = set(config) & accept_config
	if 'to_simplify' in config:
		return ['to_simplify']
	else:
		return list(config)

@log_on_fail(debug_group)
def handleCommand(update, context):
	print('handleCommand')
	msg = update.effective_message
	if not msg or not msg.text.startswith('/web'):
		return
	command, text = splitCommand(msg.text)
	if 'remove' in command:
		db.sub.remove(msg.chat_id, text)
	elif 'add' in command:
		config = text.split()
		site = config[0]
		config = normalizeConfig(config[1:])
		db.sub.add(msg.chat_id, site, config)
		item_count = backfillSingle(site, msg.chat_id, 1)
		if not item_count:
			msg.chat.send_message('It seems I can not get link from this website')		
			msg.forward(debug_group.id)
		else:
			msg.chat.send_message('Above is an example article you will get in the furture. If this does not look right, feel free to report bug on Github.')
	elif 'backfill' in command:
		backfill(msg.chat_id)
	msg.chat.send_message(db.sub.get(msg.chat_id), disable_web_page_preview=True)

HELP_MESSAGE = '''
Commands:
/web_add - add website, support two additional config flags: to_telegraph, to_simplify
/web_remove - remove website
/web_view - view subscription
/web_backfill - backfill

Example: 
/web_add https://cn.nytimes.com
/web_add https://www.nytimes.com
/web_add https://squatting2047.com to_simplify
/web_add https://whogovernstw.org to_simplify
/web_add https://www.thinkingtaiwan.com to_simplify
/web_add https://matters.news/@Margaux1848 to_simplify
/web_add https://www.bbc.co.uk to_telegraph
/web_add https://www.bbc.com/zhongwen/simp to_telegraph

Can be used in group/channel also.

Github： https://github.com/gaoyunzhi/web_subscription_bot
'''

def handleHelp(update, context):
	update.message.reply_text(HELP_MESSAGE)

def handleStart(update, context):
	if 'start' in update.message.text:
		update.message.reply_text(HELP_MESSAGE)

if __name__ == '__main__':
	threading.Timer(1, loop).start() 
	dp = tele.dispatcher
	dp.add_handler(MessageHandler(Filters.command, handleCommand))
	dp.add_handler(MessageHandler(Filters.private & (~Filters.command), handleHelp))
	dp.add_handler(MessageHandler(Filters.private & Filters.command, handleStart), group=2)
	tele.start_polling()
	tele.idle()
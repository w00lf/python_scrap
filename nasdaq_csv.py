#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lxml import html
import requests
from time import sleep
import json
from random import randint
import csv
import re
import datetime
import smtplib
import urllib3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from subprocess import Popen, PIPE
# Time testing
# from freezegun import freeze_time


def mail(result):
	gmail_user = '<ACCOUNT>@gmail.com'
	gmail_password = '<PASSWORD>'

	sent_from = gmail_user
	to = ['<EMAIL>']
	subject = 'Nasdaq Scraper'
	msg = MIMEMultipart('alternative')
	msg['Subject'] = subject
	msg['From'] = sent_from
	msg['To'] = ', '.join(to)
	# Record the MIME types of both parts - text/plain and text/html.
	part1 = MIMEText(result, 'plain')
	part2 = MIMEText(result, 'html')

	# Attach parts into message container.
	# According to RFC 2046, the last part of a multipart message, in this case
	# the HTML message, is best and preferred.
	msg.attach(part1)
	msg.attach(part2)

	try:
			# server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
			# server.ehlo()
			# server.login(gmail_user, gmail_password)
			# server.sendmail(sent_from, to, msg.as_string())
			# server.close()
			# print 'Email sent!'
			p = Popen(["/usr/sbin/sendmail", "-t", "-oi"], stdin=PIPE)
			p.communicate(msg.as_string())
			print 'Email sent!'
	except Exception as inst:
			print type(inst)     # the exception instance
			print inst.args      # arguments stored in .args
			print inst
			print 'Something went wrong...'

def make_request(url):
	# Adding random delay
	sleep(randint(1, 5))
	headers = {
		"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
		"Accept-Encoding": "gzip, deflate",
		"Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8,ml;q=0.7",
		"Connection": "keep-alive",
		"Host": "www.nasdaq.com",
		"Referer": "http://www.nasdaq.com",
		"Upgrade-Insecure-Requests": "1",
		"User-Agent": "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.1a2pre) Gecko/2008073000 Shredder/3.0a2pre ThunderBrowse/3.2.1.8"
	}

	response = requests.get(
		url, headers=headers, verify=False)  # , cert='cacert.pem'

	if response.status_code != 200:
		raise ValueError("Invalid Response Received From Webserver")
	return response.text

def check_keywords(keywords, text):
	return re.search('|'.join(keywords), text, re.IGNORECASE)

def	find_content(text):
	parser = html.fromstring(text)
	content = ' '.join(parser.xpath('//*[@id="articlebody"]//text()'))
	return content

# Time testing, uncomment to test for date
# @freeze_time("2018-08-30")
def parse_finance_page(symbol, keywords):
	urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
	result = ''
	url = "http://www.nasdaq.com/symbol/%s/press-releases" % (symbol)
	print("Scrapping %s" % (symbol.upper()))
	parser = html.fromstring(make_request(url))
	title = parser.xpath('//*[@id="qwidget_pageheader"]//text()')
	if len(title) == 0:
		return ''
	title = title[0]
	for headline in parser.xpath('//div[@class="news-headlines"]/div'):
		if len(headline.xpath('.//a')) > 0:
			news = headline.xpath('.//a/text()')[0]
			url = headline.xpath('.//a')[0].attrib['href']
			footer = headline.xpath('.//small/text()')
			if len(footer) > 0:
				date = re.findall('\d/\d+/\d+', footer[0])[0]
				if datetime.datetime.now().strftime('%-m/%-d/%Y') == date:
					if check_keywords(keywords, news) or check_keywords(keywords, find_content(make_request(url))):
						result += '<a href="%s">%s (%s)</a><br />%s<br />%s<br /><br /><br />' % (
							url, title, symbol, news, date)
	return result

if __name__ == "__main__":
	result = ''
	keywords = ['crypto', 'blockchain', 'bitcoin']
	symbols = []
	with open('symbols.csv', 'rb') as csvfile:
		symbols_file = csv.reader(csvfile)
		for row in symbols_file:
			symbol = row[0]
			symbols.append(symbol)
			result += parse_finance_page(symbol, keywords)
			if len(result) > 0:
				break
	if len(result) > 0:
		mail(result)
	else:
		mail('No News on These Symbols Checked: %s' % (','.join(symbols)))

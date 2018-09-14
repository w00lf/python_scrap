#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lxml import html
import requests
from time import sleep
import argparse
from random import randint
import csv
import re
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import pytz
import urllib3

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

ORIGIN_URL = "https://cointelegraph.com"
PAGES_URL = "https://cointelegraph.com/api/v1/content/json/_mp"

def mail(text, csv_string=None, csv_name='parsed_links.csv'):
  gmail_user = '<ACCOUNT@gmail.com'
  gmail_password = '<PASSWORD>'
  sent_from = gmail_user
  to = ['<EMAIL>']
  subject = 'Cointelegraph external links scraper'
  msg = MIMEMultipart()
  msg['Subject'] = subject
  msg['From'] = sent_from
  msg['To'] = ', '.join(to)
  text_part = MIMEText(text)
  msg.attach(text_part)
  if csv_string:
    part = MIMEApplication(csv_string, Name=csv_name)
    # After the file is closed
    part['Content-Disposition'] = 'attachment; filename="%s"' % csv_name
    msg.attach(part)
  try:
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.ehlo()
    server.login(gmail_user, gmail_password)
    server.sendmail(sent_from, to, msg.as_string())
    server.close()
    print 'Email sent!'
  except Exception as inst:
    print type(inst)     # the exception instance
    print inst.args      # arguments stored in .args
    print inst
    print 'Something went wrong...'

def get_request(url):
  for retries in range(5):
    try:
      headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "ru,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": ORIGIN_URL,
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.119 Safari/537.36"
      }
      response = requests.get(url, headers=headers, verify=False)
      if response.status_code != 200:
        raise ValueError("Invalid Response Received From Webserver")
      return response.text
    except Exception as e:
      print("Failed to process the request, Exception:%s" % (e))


def json_post_request(url, page, token):
  for retries in range(5):
    try:
      headers = {
          "Accept": "application/json",
          "Accept-encoding": "gzip, deflate",
          "Accept-language": "ru,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6",
          "Cache-Control": "no-cache",
          "Content-type": "application/json;charset=UTF-8",
          "Origin": ORIGIN_URL,
          "Pragma": "no-cache",
          "Referer": ORIGIN_URL,
          "X-Csrf-Token": token,
          "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.119 Safari/537.36"
          }
      json = { "page": page, "lang": "en",
              "_token": token }
      response = requests.post(url, headers=headers, verify=False, json=json)
      if response.status_code != 200:
        raise ValueError("Invalid Response Received From Webserver")
      return response.json()
    except Exception as e:
      print("Failed to process the request, Exception:%s" % (e))

def parse_csrf_token(parser):
  xpath = '//meta[@name="csrf-token"]'
  return parser.xpath(xpath)[0].attrib['content']


def parse_links_urls(parser):
  xpath = '//div[contains(@class,"post-full-text")]//a'
  return filter(lambda n: not re.findall(ORIGIN_URL, n), map(lambda n: n.attrib['href'], parser.xpath(xpath)))

def start(after_date):
  data= []
  main_page_parser = html.fromstring(get_request(ORIGIN_URL))
  csrf_token = parse_csrf_token(main_page_parser)
  page = 1
  while True:
    print("Post page number %s" % (page))
    for post in json_post_request(PAGES_URL, page, csrf_token)['posts']:
      if 'rss_date' in post:
        post_date = date_parser.parse(post['rss_date'])
        print("Article, date creation: %s" % (post_date))
        if post_date < after_date:
          return data
        url = post['url']
        page_parser = html.fromstring(get_request(url))
        for link in parse_links_urls(page_parser):
          data.append([post_date.strftime('%-m/%-d/%Y'),
                      post['category_title'], link, url])
        sleep(randint(1, 3))
      else:
        print("skipping: %s" % (post))
    page += 1

if __name__=="__main__":
  urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
  argparser = argparse.ArgumentParser()
  argparser.add_argument('days', nargs='?', help='Days to parse', type=int, default=10000)
  args = argparser.parse_args()
  days = args.days
  target_after_date = datetime.now(pytz.UTC) - timedelta(days=days)
  print("Fetching from cointelegraph.com post newer than %s" %
        (target_after_date))
  result = start(target_after_date)
  print(result)
  print("Sending result email")
  if len(result) > 0:
    email_text = 'External links after date %s are in the attachment' % (
        target_after_date.strftime('%-m/%-d/%Y'))
    mail(email_text, csv_string="\n".join(map(lambda n: ','.join(n), result)))
  else:
    mail('Have not found any external links for %s' %
         (target_after_date.strftime('%-m/%-d/%Y')))


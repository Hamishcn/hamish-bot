# -*- coding: utf-8 -*-
import json
import os
import re
import time
import hashlib
import datetime

import mwparserfromhell
os.environ['PYWIKIBOT_DIR'] = os.path.dirname(os.path.realpath(__file__))
import pywikibot
from config import config_page_name  # pylint: disable=E0611,W0614

os.environ['TZ'] = 'UTC'
print('Starting at: ' + time.asctime(time.localtime(time.time())))
rec_time = (datetime.datetime.now() + datetime.timedelta(hours = 8)).__format__('%d/%m/%y %H:%M')

site = pywikibot.Site()
site.login()

config_page = pywikibot.Page(site, config_page_name)
cfg = config_page.text
cfg = json.loads(cfg)
print(json.dumps(cfg, indent=4, ensure_ascii=False))
op = False

if not cfg["enable"]:
    exit("disabled\n")

summary_prefix = "[[Wikipedia:机器人/申请/Hamish-bot/2|T2]]："
ewippage = pywikibot.Page(site, cfg["main_page_name"])
text = ewippage.text

rndstr = hashlib.md5(str(time.time()).encode()).hexdigest()
text = re.sub(r'^(===[^=]+===)$', rndstr + r'\1', text, flags=re.M)
text = text.split(rndstr)

mainPageText = text[0].strip()
text = text[1:]

archivelist = {}
count = 0

for section in text:
    section = section.strip()
    if section == '':
        continue
    else:
        title = section.split('\n')[0]
        print(title, end="\t")

    lasttime = datetime(1, 1, 1)
    for m in re.findall(r"(\d{4})年(\d{1,2})月(\d{1,2})日 \(.\) (\d{2}):(\d{2}) \(UTC\)", str(section)):
        d = datetime(int(m[0]), int(m[1]), int(m[2]), int(m[3]), int(m[4]))
        lasttime = max(lasttime, d)
    print(lasttime, end="\t")

    processed = False
    if re.search(cfg["processed_regex"], str(section)) and not re.search(cfg["not_processed_regex"], str(section)):
        processed = True
        print("processed", end="\t")
    else:
        print("not processed", end="\t")

    if (
        (
            (processed and time.time() - lasttime.timestamp() > cfg["time_to_live_for_processed"])
            or (not processed and time.time() - lasttime.timestamp() > cfg["time_to_live_for_not_processed"])
        )
            and lasttime != datetime(1, 1, 1)):
        target = (lasttime.year, lasttime.month)
        if target not in archivelist:
            archivelist[target] = []
        archivelist[target].append(section)
        count += 1
        print("archive to " + str(target), end="\t")
    else:
        mainPageText += '\n\n' + section
        print("not archive", end="\t")
    print()

if count == 0:
    exit("nothing changed")

pywikibot.showDiff(ewippage.text, mainPageText)
ewippage.text = mainPageText
summary = cfg["main_page_summary"].format(count)
print(summary)
ewippage.save(summary=summary_prefix + summary, minor=False)
op = True

for target in archivelist:
    archivepage = pywikibot.Page(site, cfg["archive_page_name"].format(target[0], target[1]))
    text = archivepage.text
    print(archivepage.title())
    if not archivepage.exists():
        text = cfg["archive_page_preload"]
    text += "\n\n" + "\n\n".join(archivelist[target])

    pywikibot.showDiff(archivepage.text, text)
    archivepage.text = text
    summary = cfg["archive_page_summary"].format(len(archivelist[target]))
    print(summary)
    archivepage.save(summary=summary_prefix + summary, minor=False)
    
# Updating task table on user page

user_page = pywikibot.Page(site, "User:Hamish-bot")
user_page_text = user_page.text
user_page_text = re.sub(r'<!-- T2rs -->(.*)<!-- T2re -->', '<!-- T2rs -->' + rec_time + '<!-- T2re -->', user_page_text, flags=re.M)
if op:
    user_page_text = re.sub(r'<!-- T2os -->(.*)<!-- T2oe -->', '<!-- T2os -->' + rec_time + '<!-- T2oe -->', user_page_text, flags=re.M)
pywikibot.showDiff(user_page.text, user_page_text)
user_page.text = user_page_text
user_page.save(summary = "Updating task report", minor = False)

import json
import os
import re
import shutil
import sys
import time
import uuid
from datetime import datetime, timedelta

import mysql
import oss2
import requests
import schedule
from mysql.connector import connection
from selenium import webdriver

sys.path.append('..')

from config.starter_config import StarterConfig

config = StarterConfig.get_config()

options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
driver = webdriver.Chrome(executable_path=config['chromedriver'], options=options)

try:
    driver.implicitly_wait(3)
    driver.get('https://www.instagram.com')
    time.sleep(3)

    login_form = driver.find_element_by_id('loginForm')
    login_form.find_element_by_name('username').send_keys('username')
    time.sleep(1)
    login_form.find_element_by_name('password').send_keys('password')
    time.sleep(1)
    login_form.find_element_by_xpath("//button[@type='submit']").click()
    time.sleep(3)

    notification_dialog = driver.find_element_by_xpath("//div[@role='presentation']/div[@role='dialog']")
    notification_dialog.find_element_by_xpath("//button[text()='以后再说']").click()
    time.sleep(2)
except BaseException as el:
    print(el)
    time.sleep(60)

proxies = config['proxies']
s = requests.Session()
for cookie in driver.get_cookies():
    s.cookies.set(cookie['name'], cookie['value'])


def ins_job():
    urls_file = open(r'./urls.txt', 'r')
    urls = urls_file.readlines()
    urls_file.close()

    cnx = mysql.connector.connect(**config['database'])
    cursor = cnx.cursor()
    latest_time_sql = "SELECT `ins_post_time` FROM `sharp-hook`.`ins_posts` WHERE `user_name` = %s ORDER BY `ins_post_time` DESC LIMIT 1"
    add_post_sql = "INSERT INTO `sharp-hook`.`ins_posts`(`user_name`, `ins_id`, `ins_post_time`, `ins_post_picture_url`) " \
                   "VALUES (%(user_name)s, %(ins_id)s, %(ins_post_time)s, %(ins_post_picture_url)s);"

    add_media_sql = "INSERT INTO `sharp-hook`.`ins_posts_media`(`ins_id`, `ins_post_media_url`) " \
                    "VALUES (%(ins_id)s, %(ins_post_media_url)s);"

    auth = oss2.Auth('your oss access_key_id', 'access_key_secret')
    bucket = oss2.Bucket(auth, 'endpoint', 'bucket_name')

    for page_url in urls:
        try:
            page_url = page_url.strip()
            print('page url >>>>>>>>>>: ' + page_url)
            if pattern := re.search(r"(?<=instagram.com/)[^/]+", page_url):
                user_name = pattern.group()
            else:
                continue

            driver.get(page_url)
            time.sleep(5)

            cursor.execute(latest_time_sql, (user_name,))
            latest_times = cursor.fetchone()
            if latest_times is not None:
                latest_time = latest_times[0]
                is_first_join = False
            else:
                latest_time = datetime.now() - timedelta(2)
                is_first_join = True
            print('latest time >>>>>>>>>>: ' + str(latest_time))

            article_list = driver.find_elements_by_xpath('//article//a')
            for article in article_list:
                post = {'user_name': user_name}

                article_url = article.get_attribute("href")
                ins_id = re.search(r"(?<=instagram.com/p/)[^/]+", article_url).group()
                post['ins_id'] = ins_id
                print('ins_id: ' + ins_id)

                time.sleep(1)
                article.click()
                time.sleep(6)

                label = driver.find_element_by_css_selector(
                    "div[role='dialog'] > article > div > div:nth-child(2) > div:nth-child(2) > div:nth-child(4) > a > time")
                ins_post_time = label.get_attribute("datetime").replace("T", " ").replace(".000Z", "")
                post['ins_post_time'] = ins_post_time
                print('ins_post_time: ' + ins_post_time)

                ins_post_time = datetime.fromisoformat(ins_post_time)
                if ins_post_time > latest_time:
                    post_image = driver.find_element_by_css_selector("div[role='dialog'] > article").screenshot_as_png

                    post_picture_path = 'ins_posts_images/' + user_name + '/' + str(uuid.uuid1()) + '.png'

                    bucket.put_object(post_picture_path, post_image)
                    post['ins_post_picture_url'] = 'https://{bucket_name}.oss-cn-shanghai.aliyuncs.com/' \
                                                   + post_picture_path

                    requests.post(
                        "push channel",
                        json={'msgtype': 'news',
                              'news': {'articles': [
                                  {'title': user_name,
                                   'url': post['ins_post_picture_url'],
                                   'picurl': post['ins_post_picture_url']
                                   }]}})

                    cursor.execute(add_post_sql, post)
                    cnx.commit()

                    response = s.get(article_url + '?__a=1', proxies=proxies)
                    page_json = json.loads(response.text)

                    cache_path = config['cache_path'] + ins_id
                    if not os.path.exists(cache_path):
                        os.makedirs(cache_path)

                    shortcode_media = page_json['graphql']['shortcode_media']
                    if 'video_url' in shortcode_media:
                        r = requests.get(shortcode_media['video_url'], stream=True, proxies=proxies)
                        with open(cache_path + '/' + str(uuid.uuid1()) + '.mp4', 'wb') as f:
                            for chunk in r.iter_content(chunk_size=1024 * 1024):
                                if chunk:
                                    f.write(chunk)

                    if 'edge_sidecar_to_children' in shortcode_media:
                        node_list = shortcode_media['edge_sidecar_to_children']['edges']
                        for item in node_list:
                            if item['node']['__typename'] == 'GraphImage':
                                r = requests.get(item['node']['display_url'], proxies=proxies)
                                with open(cache_path + '/' + str(uuid.uuid1()) + '.jpg', 'wb') as f:
                                    f.write(r.content)

                            if item['node']['__typename'] == 'GraphVideo':
                                r = requests.get(item['node']['video_url'], stream=True, proxies=proxies)
                                with open(cache_path + '/' + str(uuid.uuid1()) + '.mp4', 'wb') as f:
                                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                                        if chunk:
                                            f.write(chunk)

                    if 'display_url' in shortcode_media:
                        r = requests.get(shortcode_media['display_url'], proxies=proxies)
                        with open(cache_path + '/' + str(uuid.uuid1()) + '.jpg', 'wb') as f:
                            f.write(r.content)

                    media_file_path = 'ins_posts_images/' + user_name + '/' + ins_id + '/'
                    os.chdir(cache_path)
                    for file in os.listdir():
                        bucket.put_object_from_file(media_file_path + file, cache_path + '/' + file)
                        requests.post(
                            "translate url",
                            json={'msgtype': 'text',
                                  'text': {'content': 'https://{bucket_name}.oss-cn-shanghai.aliyuncs.com/'
                                                      + media_file_path + file}})
                        media = {'ins_id': ins_id,
                                 'ins_post_media_url': 'https://{bucket_name}.oss-cn-shanghai.aliyuncs.com/'
                                                       + media_file_path + file}
                        cursor.execute(add_media_sql, media)
                    cnx.commit()
                    os.chdir("..")
                    try:
                        shutil.rmtree(cache_path)
                    except OSError as ose:
                        print("Error: %s : %s" % (cache_path, ose.strerror))

                else:
                    break

                time.sleep(1)
                driver.find_element_by_css_selector("svg[aria-label='关闭']").click()

                if is_first_join:
                    break

            time.sleep(10)

        except BaseException as e:
            print(e)
            print('The task was not successfully completed!')
            time.sleep(60)
            continue

    cursor.close()
    cnx.close()


schedule.every(20).seconds.do(ins_job)

while True:
    schedule.run_pending()
    time.sleep(1)

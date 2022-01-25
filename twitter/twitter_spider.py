import hashlib
import json
import re
import sys
import time
import uuid
from datetime import date, datetime, timedelta
from urllib import parse

import mysql
import oss2
import requests
import schedule
import yaml
from mysql.connector import connection
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.tmt.v20180321 import tmt_client, models

sys.path.append('..')

from config.starter_config import StarterConfig

arguments = sys.argv
config = StarterConfig.get_config()

options = webdriver.ChromeOptions()
options.add_argument("window-size=730,1440")
options.add_argument('--ignore-certificate-errors')
driver = webdriver.Chrome(executable_path=config['chromedriver'], options=options)


def twitter_job():
    with open(arguments[1], "r") as f:
        content = yaml.load(f, Loader=yaml.SafeLoader)
        topics = content['topics']

    cnx = mysql.connector.connect(**config['database'])
    cursor = cnx.cursor()
    latest_time_sql = "SELECT `tweet_post_time` FROM `sharp-hook`.`twitter_posts` WHERE `user_name` = %s ORDER BY `tweet_post_time` DESC LIMIT 1"
    add_post_sql = "INSERT INTO `sharp-hook`.`twitter_posts`(`user_name`, `tweet_id`, `tweet_post_time`, `tweet_post_picture_url`) " \
                   "VALUES (%(user_name)s, %(tweet_id)s, %(tweet_post_time)s, %(tweet_post_picture_url)s);"

    auth = oss2.Auth('access_key_id', 'access_key_secret')
    bucket = oss2.Bucket(auth, 'endpoint', 'bucket_name')

    cred = credential.Credential("secret_id", "secret_key")
    httpProfile = HttpProfile()
    httpProfile.endpoint = "tmt.tencentcloudapi.com"

    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    client = tmt_client.TmtClient(cred, "ap-shanghai", clientProfile)

    for item in topics:
        try:
            page_url = item['topic']
            print('page url >>>>>>>>>>: ' + page_url)
            if pattern := re.search(r"(?<=twitter.com/)[^/]+", page_url):
                user_name = pattern.group()
            else:
                continue

            actual_url = get_actual_url(user_name)
            driver.get(actual_url)
            time.sleep(5)

            search_result = driver.find_element_by_css_selector(
                "main > div > div > div > div:nth-child(1) > div > div:nth-child(2) > div > div")
            if "你输入的词没有找到任何结果" in search_result.text:
                continue

            label_outer = driver.find_element_by_css_selector(
                "main > div > div > div > div:nth-child(1) > div > div:nth-child(2) > div > div > section > div > div"
            )
            driver.execute_script("arguments[0].id = 'outer';", label_outer)

            cursor.execute(latest_time_sql, (user_name,))
            latest_times = cursor.fetchone()
            if latest_times is not None:
                latest_time = latest_times[0]
                is_first_join = False
            else:
                latest_time = datetime.now() - timedelta(1)
                is_first_join = True
            print('latest time >>>>>>>>>>: ' + str(latest_time))

            for label_tweet in label_outer.find_elements_by_xpath('//*[@id="outer"]/div'):

                post = {'user_name': user_name}

                try:
                    if label := label_tweet.find_element_by_css_selector(
                            "article > div > div > div > div:nth-child(2) > div:nth-child(2) > div:nth-child(1) > div > div > div:nth-child(1) > a > time"):
                        post['tweet_post_time'] = label.get_attribute("datetime").replace("T", " ").replace(".000Z", "")
                        print('tweet_post_time: ' + post['tweet_post_time'])
                except NoSuchElementException:
                    break

                tweet_post_time = datetime.fromisoformat(post['tweet_post_time'])
                if tweet_post_time > latest_time:
                    if label := label_tweet.find_element_by_css_selector(
                            "article > div > div > div > div:nth-child(2) > div:nth-child(2) > div:nth-child(1) > div > div > div:nth-child(1) > a"):
                        if pattern := re.search("[0-9]+$", label.get_attribute("href")):
                            post['tweet_id'] = pattern.group()
                            print('tweet_id: ' + post['tweet_id'])

                    post_image = label_tweet.screenshot_as_png
                    post_image_base64 = label_tweet.screenshot_as_base64

                    post_picture_path = 'twitter_posts_images/' + user_name + '/' + str(uuid.uuid1()) + '.png'

                    bucket.put_object(post_picture_path, post_image)
                    post['tweet_post_picture_url'] = 'https://{bucket_name}.oss-cn-shanghai.aliyuncs.com/' \
                                                     + post_picture_path

                    for subscriber in item['subscribers']:
                        requests.post(subscriber, json={'msgtype': 'image', 'image': {'base64': post_image_base64,
                                                                                      'md5': hashlib.md5(
                                                                                          post_image).hexdigest()}})
                        time.sleep(1)

                    cursor.execute(add_post_sql, post)
                    cnx.commit()

                    text_en = ''
                    if label := label_tweet.find_element_by_css_selector(
                            "article > div > div > div > div:nth-child(2) > div:nth-child(2) > div:nth-child(2) > div:nth-child(1)"):
                        if "回复" in label.text:
                            if label := label_tweet.find_element_by_css_selector(
                                    "article > div > div > div > div:nth-child(2) > div:nth-child(2) > div:nth-child(2) > div:nth-child(2)"):
                                text_en = label.text
                        else:
                            text_en = label.text

                    if len(text_en) == 0:
                        continue

                    try:
                        req = models.TextTranslateRequest()
                        params = {
                            "SourceText": text_en,
                            "Source": "auto",
                            "Target": "zh",
                            "ProjectId": 0
                        }
                        req.from_json_string(json.dumps(params))

                        resp = client.TextTranslate(req)
                        result = json.loads(resp.to_json_string())

                        translation_text = user_name + "【中文翻译】\n" + result['TargetText']

                        for subscriber in item['subscribers']:
                            requests.post(subscriber,
                                          json={'msgtype': 'markdown', 'markdown': {'content': translation_text}})
                            time.sleep(1)

                    except TencentCloudSDKException as err:
                        print(err)
                        continue

                else:
                    break
                if is_first_join:
                    break
            time.sleep(1)

        except BaseException as e:
            print(e)
            print('The task was not successfully completed!')
            continue

    cursor.close()
    cnx.close()


def get_actual_url(user_name: str) -> str:
    query_sentence = ["from:%s" % user_name, "-filter:retweets"]
    now = datetime.now()
    yesterday = now - timedelta(1)
    tomorrow = now + timedelta(1)
    query_sentence.append("since:%s" % str(date(yesterday.year, yesterday.month, yesterday.day)))
    query_sentence.append("until:%s" % str(date(tomorrow.year, tomorrow.month, tomorrow.day)))
    query = " ".join(query_sentence)
    params = {
        "q": query,
        "f": "live"
    }
    return "https://twitter.com/search?" + parse.urlencode(params)


schedule.every(3).seconds.do(twitter_job)

while True:
    schedule.run_pending()
    time.sleep(1)

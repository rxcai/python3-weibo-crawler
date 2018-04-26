import requests
from postModel import Post, db
import re
from multiprocessing import Pool
import time
import datetime

UID_LIST = [
    ("weibo_name", "weibo_id")  # replace weibo_name and weibo_id yourself
]

REQUEST_HEADERS = {
    "Host": "m.weibo.cn",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X)"
    "AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0"
    "Mobile/15A5370a Safari/604.1"
}

DUPLICATA_CHECK_TIMES = 13

BASE_LIST_URL = "https://m.weibo.cn/api/container/getIndex"
BASE_STATUS_URL = "https://m.weibo.cn/status/"


def get_user_weibo_list(uid_tuple):
    print(f'Run task {uid_tuple[0]}')
    page = 1
    # 这里的 '107603' 是我观察得到的，微博 mobile 不需要通过登陆或者 cookie 的形式来获取信息
    containerid = '107603' + uid_tuple[1]
    weibo_list = []
    source = uid_tuple[0]
    duplicata_check_count = 0

    while True:
        if duplicata_check_count > DUPLICATA_CHECK_TIMES:
            break

        weiboList_params = {
            "containerid": containerid,
            "type": "uid",
            "value": {uid_tuple[1]},
            "page": {page}
        }

        resp = requests.get(
            BASE_LIST_URL,
            params=weiboList_params,
            headers=REQUEST_HEADERS)

        resp.encoding = 'utf-8'
        responseData = resp.json().get('data')
        cards = responseData.get('cards')

        sub_list, duplicata_check_count = get_card_info(
            cards,
            source,
            duplicata_check_count)

        weibo_list.extend(sub_list)

        page += 1
        if page > DUPLICATA_CHECK_TIMES:
            break

    save_data_to_db(weibo_list)
    print(f'{uid_tuple[0]} finished')


def get_card_info(cards, source, duplicata_check_count):
    sub_list = []
    for card in cards:
        if 9 == card['card_type']:
            temp_dict = {}

            mblog = card['mblog']
            temp_dict['id_in_source'] = mblog['idstr']

            if Post.recordExists(temp_dict['id_in_source']):
                duplicata_check_count += 1
                continue

            temp_dict['source'] = source

            temp_dict['date'] = convert_chinese_to_date(mblog['created_at'])

            dirty_text = mblog['text']
            temp_dict['title'] = re.sub(r'<[^>]+>', ' ', dirty_text)
            weibo_link = BASE_STATUS_URL + mblog['idstr']

            temp_dict['desc'] = ("微博链接: " + weibo_link)

            sub_list.append(temp_dict)

    return sub_list, duplicata_check_count


def convert_chinese_to_date(created_at):
    date_result = datetime.datetime.now()
    minute_match = re.match(r'(.+)分钟前', created_at)
    if minute_match:
        minute_before = minute_match.group(1)
        date_result -= datetime.timedelta(minutes=int(minute_before))
        return date_result

    hour_match = re.match(r'(.+)小时前', created_at)
    if hour_match:
        hour_before = hour_match.group(1)
        date_result -= datetime.timedelta(hours=int(hour_before))
        return date_result

    yesterday_match = re.match(r'昨天 (.+):(.+)', created_at)
    if yesterday_match:
        date_result -= datetime.timedelta(days=1)
        return date_result.replace(minute=int(yesterday_match.group(2)), hour=int(yesterday_match.group(1)))

    year_date_match = re.match(r'(.+)-(.+)-(.+)', created_at)
    if year_date_match:
        return datetime.datetime.strptime(created_at, '%Y-%m-%d')

    date_match = re.match(r'(.+)-(.+)', created_at)
    if date_match:
        return datetime.datetime.strptime(str(date_result.year) + '-' + created_at, '%Y-%m-%d')

    return date_result


def save_data_to_db(result_list):
    for data_dict in result_list:
        Post.create(**data_dict)


if __name__ == '__main__':
    with db:
        db.create_tables([Post], safe=True)

    pool = Pool(len(UID_LIST))
    while True:
        for i in range(len(UID_LIST)):
            pool.apply_async(
                get_user_weibo_list,
                args=(UID_LIST[i], ))

        # pool.close()
        # pool.join()
        time.sleep(60*21)

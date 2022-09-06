# 获取网易CC的真实流媒体地址。
# 默认为最高画质

import requests


class CC:

    def __init__(self, rid):
        self.rid = rid

    def get_real_url(self):
        room_url = f'https://api.cc.163.com/v1/activitylives/anchor/lives?anchor_ccid={self.rid}'
        response = requests.get(url=room_url).json()
        data = response.get('data', 0)
        if data:
            channel_id = data.get(f'{self.rid}').get('channel_id', 0)
            if channel_id:
                response = requests.get(f'https://cc.163.com/live/channel/?channelids={channel_id}').json()
                real_url = response.get('data')[0].get('sharefile')
            else:
                raise Exception('live does not exist')
        else:
            raise Exception('input error')
        return real_url


def get_real_url(rid):
    try:
        cc = CC(rid)
        return cc.get_real_url()
    except Exception as e:
        print('Exception：', e)
        return False

import asyncio
import gc
import json
import os
import pickle
import re
import sched
import threading
import time

import config
import aiohttp
import pandas as pd
import pymongo
import requests
import threadpool
from pyquery import PyQuery as pq

# 城市
cn = config.cn
# 多少分钟
a = config.a
# 时间间隔
rr = config.rr


print(f'city:{cn},save_totaltime:{a*rr//60}m,save_solt:{rr}m')


class html_parser():
    city = {"北京": "Beijing1",
            "上海": "Shanghai2",
            "天津": "Tianjin3",
            "重庆": "Chongqing4",
            "大连": "Dalian6",
            "青岛": "Qingdao7",
            "西安": "Xian10",
            "南京": "Nanjing12",
            "苏州": "Suzhou14",
            "杭州": "Hangzhou17",
            "厦门": "Xiamen25",
            "成都": "Chengdu28",
            "深圳": "Shenzhen30",
            "广州": "Guangzhou32",
            "三亚": "Sanya43",
            "台北": "Taipei617",
            "香港": "Hong Kong58",
            "济南": "Jinan144",
            "宁波": "Ningbo375",
            "沈阳": "Shenyang451",
            "武汉": "Wuhan477",
            "郑州": "Zhengzhou559"}

    def __init__(self, cityname="北京"):
        '''
        类初始化
        '''
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.84 Safari/537.36",
        }
        self.cityname = self.city[cityname]
        self.order_data = {}
        # self.order_Tdata = {}

        # 这是所有酒店订单的最新信息
        self.order_base = {}
        self.order_num = 0
        self.datalist = []
        self.tpool = threadpool.ThreadPool(30)
        '''
        连接mongo数据库
        '''
        # self.client = pymongo.MongoClient('localhost', 27017)
        # self.mydb = self.client['mydata']
        # self.mydb_info = self.mydb[self.cityname]

    # def savetomongo(self, startime, endtime, order_num, order_data):
    #     '''
    #     创建全酒店信息字典保存数据到mongoDB中
    #     '''
    #     new = {
    #         "开始记录时间": startime,
    #         "结束记录时间": endtime,
    #         "订单总增量": order_num,
    #         "item": order_data
    #     }
    #     self.mydb_info.insert(new)
    #     print("已成功保存至mongoDB")

    def clear(self):
        self.order_data = {}
        # self.order_Tdata = {}

        # 这是所有酒店订单的最新信息
        self.order_base = {}
        self.order_num = 0
        self.datalist = []

    @staticmethod
    def getime(timeStamp, case1=1):
        '''
        将时间戳转化固定格式的信息
        '''
        timeArray = time.localtime(timeStamp)
        if case1 == 1:
            otherStyleTime = time.strftime("%Y-%m-%d %H:%M:%S", timeArray)
        elif case1 == 2:
            otherStyleTime = time.strftime("%Y%m%d%H%M%S", timeArray)

        return otherStyleTime

    async def __async_requests(self, n):
        '''
        异步爬虫,每次发出50个网页内容请求
        '''
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://hotels.ctrip.com/hotel/{self.cityname}/p{n}", headers=self.headers) as resp:
                # print(resp.status)
                return await resp.text()

    def __get_pagecount(self):
        '''
        获取当前城市酒店网页的总页数
        '''
        html = requests.get(
            f"http://hotels.ctrip.com/hotel/{self.cityname}/p1", headers=self.headers)
        doc = pq(html.text)
        temp = doc(".c_page_num").attr("data-pagecount")
        try:
            if int(temp) > 1:
                self.pagecount = int(temp)
            else:
                self.pagecount = 1
        except:
            print('携程锁IP')
        finally:
            return self.pagecount

    def __add_data(self, id="0", name="NaN", last_book=999999, hotel_value=4.4, hotel_price=999):
        '''
        将网页获取到的关键信息更新到字典中
        '''
        if str(id) in self.order_base:
            # 获取酒店基准信息中的预订时间
            lastbooktime = int(
                self.order_base[str(id)]["hotel_item_last_book"])
            po = int(last_book) / lastbooktime

            if po <= 0.5:
                if str(id) not in self.order_data:
                    self.order_data[str(id)] = {
                        "hotel_name": name,
                        "order_time": [],
                        "total_order": 0,
                        'hotel_value': [],
                        'hotel_price': []
                    }

                gtime = self.getime(time.time())
                setordertime = self.order_data[str(id)]["order_time"]
                if gtime not in setordertime:
                    setordertime.append(gtime)

                    self.order_data[str(id)]["order_time"] = list(
                        set(setordertime))
                    self.order_data[str(id)]["total_order"] = len(
                        self.order_data[str(id)]["order_time"])
                    self.order_data[str(id)]["hotel_value"].append(
                        hotel_value)
                    self.order_data[str(id)]["hotel_price"].append(
                        hotel_price)
                    self.order_num += 1
                    # print(self.order_num)

            if int(last_book) == 0:
                last_book = 0.1
            self.order_base[str(id)]["hotel_item_last_book"] = last_book

        else:
            self.order_base[str(id)] = {
                "hotel_item_last_book": str(last_book),
            }

        # self.order_data = self.order_Tdata.copy()
        return self.order_data

    def __format_lastbook(self, last_book):
        '''
        将获取到的最新预订时间正则抽取出数值(以分钟为计量单位)
        '''
        if last_book == '':
            last_book = 999999
            return last_book
        m = re.search(r".*?(\d+)小", last_book)
        if m != None:
            last_book = int(m.group(1))*60
        else:
            m = re.search(r".*?(\d+)分", last_book)
            last_book = int(m.group(1))
        return last_book

    def __ctrip_parser(self, html):
        '''
        解析网页数据
        酒店[id],
        酒店名字[name],
        酒店最新预订时间[last_book]
        酒店评分[hotel_value]
        '''
        html = pq(html)
        itemlist = html(
            '#hotel_list .hotel_new_list.J_HotelListBaseCell').items()
        try:
            for i in itemlist:
                # 只解释战略合作酒店
                # if i(".hotel_strategymedal") != None:
                hotel_id = i.attr('id')
                hotel_name = i('.hotel_name a').attr('title')

                hotel_lastbook = i('.hotel_item_last_book').text()
                hotel_lastbook = self.__format_lastbook(hotel_lastbook)

                hotel_value = i('.hotel_value').text()
                if hotel_value == '':
                    hotel_value = 0
                hotel_price = i('.J_price_lowList').text()
                if hotel_price == '':
                    hotel_price = 0

                # 更新到字典中
                self.__add_data(hotel_id, hotel_name,
                                hotel_lastbook, hotel_value, hotel_price)
        except:
            # print('无效网页')
            pass

    def main_do(self):
        '''
        主函数:解析网页-数据获取-数据格式化更新进字典
        '''
        # s1 = time.time()
        # print("获取网页开始:%s" % self.getime(time.time()))

        temp = self.__get_pagecount()
        print(temp)
        if temp % 50 == 0:
            temp -= 1
        num = 50
        if temp >= num:
            for i in range(0, temp//num):
                tasks = [asyncio.ensure_future(self.__async_requests(i))
                         for i in range(1+num*i, 51+num*i)]

                loop = asyncio.get_event_loop()
                loop.run_until_complete(asyncio.wait(tasks))
                for i in tasks:
                    self.datalist.append(i.result())
                tasks.clear()

        # s2 = time.time()
        # print("获取网页结束:%s" % self.getime(time.time()))
        tasks = [asyncio.ensure_future(self.__async_requests(
            i)) for i in range(1+num*(temp//num), temp+1)]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.wait(tasks))

        for i in tasks:
            self.datalist.append(i.result())
        tasks3 = threadpool.makeRequests(
            self.__ctrip_parser, [i for i in self.datalist])
        [self.tpool.putRequest(i) for i in tasks3]
        self.tpool.wait()

        self.datalist.clear()
        tasks.clear()
        tasks3.clear()
        gc.collect()
        # s = s2-s1
        # print(f"网页获取时间:{s:.2f}")
        # s = time.time()-s2
        # print("网页解析结束:%s" % self.getime(time.time()))
        # print(f"网页解析时间:{s:.2f}")

    def dump_jsondata(self, startime, endtime, order_num, order_data):
        tempdata = {
            "开始记录时间": startime,
            "结束记录时间": endtime,
            "订单总增量": order_num,
            "item": order_data
        }
        tn = self.getime(time.time(), case1=2)

        with open(f"data/{tn}.json", 'w') as datafile:
            json.dump(tempdata, datafile)
        tempdata.clear()
        self.order_data.clear()

    def load_jsondata(self):
        with open("jsondata.json", 'r') as datafile:
            self.order_jsondata = json.load(datafile)


# *******************************************************************
# 单位时间分钟,


def fun(): print(f"任务执行完成{test.getime(time.time())}")


test = html_parser(cityname=cn)
# 记录开始时间
s = test.getime(time.time())

# 创建一个定时执行计划
st = sched.scheduler(time.time, time.sleep)

# 分发任务
for i in range(a):
    st.enter(i*rr, 3, test.main_do,)
# 分发最后一个任务
st.enter(a*rr, 6, fun,)
# 执行所有计划,直到完成
st.run()

# 记录结束时间
s2 = test.getime(time.time())

# 存入数据库中.
test.dump_jsondata(s, s2, test.order_num, test.order_data)
print(f'订单增量:{test.order_num},记录时长:{a*rr//60}分钟')
del test
time.sleep(2)
os.system('start.bat')

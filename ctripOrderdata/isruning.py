# python -m pip install pypiwin32
import win32com.client
import yagmail
import time
import socket  # 导入方法
import config,os

def check_exsit(process_name):

    WMI = win32com.client.GetObject('winmgmts:')

    processCodeCov = WMI.ExecQuery(
        'select * from Win32_Process where Name="%s"' % process_name)

    if len(processCodeCov) > 0:  # 判断操作 www.iplaypy.com
        # print('%s is exists' % process_name)

        return 1
    else:
        # print('%s is not exists' % process_name)
        return 0


def getime():
    '''
    将时间戳转化固定格式的信息
    '''
    timeArray = time.localtime(time.time())

    otherStyleTime = time.strftime("%Y-%m-%d %H:%M:%S", timeArray)

    return otherStyleTime


def sendemail():
    # 获取本机计算机名称
    hostname = config.cn
    # 获取本机ip
    ip = config.ip
    print(hostname)
    print(ip)
    yag = yagmail.SMTP(user="200610424@qq.com",
                       password='jjakotfhrdqpcacb', host='smtp.qq.com')

    tt = getime()
    doc = f"{tt},检测出现异常,需要登陆查看原因\n{hostname}\n{ip}"
    yag.send('dotangtianwei@163.com', "python-run-info", doc)


isrun = 0
os.system('start.bat')
while True:
    if check_exsit('cmd.exe') == 0:

        for i in range(10):
            if check_exsit('cmd.exe') == 0:
                time.sleep(6)
                isrun += 1
            else:
                isrun = 0
                break
    if isrun >= 10:
        sendemail()
        print("检测到控制台进程被注销")
        os.system('start.bat')
        isrun = 0



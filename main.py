import requests
import time
import datetime
import json
import re

DEBUG = True

with open('config.json', 'r', encoding='utf-8') as f:
    config_data = json.load(f)

session = requests.Session()

data_new = []

def log(message: str):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}")

def login(USERNAME, PASSWORD):
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; HW Build/UKQ1.211100.001; wv) AppleWebKit/530.36 (KHTML, like Gecko) Version/4.0 Chrome/139.0.7204.180 Mobile Safari/538.36 XWEB/1381243 MMWEBSDK/20250404 MMWEBID/9056 MicroMessenger/8.0.40.2600(0x28003130) WeChat/arm64 Weixin Android Tablet NetType/4G Language/zh_CN ABI/arm64"
    })

    if config_data['use_remember_token']:
        token_and_ticket = get_token_and_ticket_by_rme_token(config_data['rme_token'])
        if token_and_ticket == 1:
            log("rme登录失败")
            if config_data['only_use_remember_token']:
                return False
            else:
                token_and_ticket = get_token_and_ticket_by_password(config_data['XMIST_USERNAME'], config_data['XMIST_PASSWORD'], True)
                if token_and_ticket == 1:
                    log("使用账号密码登录失败")
                    return False
                else:
                    log("成功使用账号密码登录")
    else:
        token_and_ticket = get_token_and_ticket_by_password(config_data['XMIST_USERNAME'], config_data['XMIST_PASSWORD'], False)
        if token_and_ticket == 1:
            log("使用账号密码登录失败")
            return False

    access_token = get_access_token_by_oauth(token_and_ticket['token'], token_and_ticket['ticket'])
    if access_token == 1:
        return False

    session.headers.update({
        "Authorization": f"Bearer {access_token}"
    })

    return True

def get_token_and_ticket_by_rme_token(rme):
    try:
        respone = session.post("https://sso.xmist.edu.cn/ssox/auth/token/rme", data={'remember_me': rme}, timeout=config_data['request_timeout'])
    except:
        log("请求token失败, 可能为服务器过载或网络错误")
        return 1
    result = respone.json()

    if result.get('code') == 0 and result.get('data') != None:
        token = result['data']['token']
        ticket = result['data']['ticket']

        session.cookies.set('congress', token)
        session.cookies.set('online_ticket', ticket)

        if DEBUG:
            log(f"[登录 1/5] token: {token}, ticket: {ticket}")
    else:
        return 1

    return {'token': token, 'ticket': ticket}

def get_token_and_ticket_by_password(username, password, use_rme):
    # 不太清楚如何使用python的AES来加密文本, 所以使用api来加密password
    data = {
    "cipherMode": 4,
    "paddingMode": 1,
    "blockSize": 128,
    "keyFormat": 1,
    "key": "hellos,catxcloud",
    "ivFormat": 1,
    "iv": "hellos,catxcloud",
    "nonceDataFormat": 1,
    "nonceData": "",
    "associatedDataFormat": 1,
    "associatedData": "",
    "input": password,
    "encoding": "UTF-8",
    "format": 1
    }
    respone = requests.post("https://www.toolhelper.cn/SymmetricEncryption/AesEncrypt?gts=1762427258662&gv=237&r_=0.7967918398911576", data=data)
    password_encrypt = respone.json()['Data']

    captcha_respone = session.get("https://sso.xmist.edu.cn/ssox/code")
    captcha_result = captcha_respone.json()
    if captcha_result['code'] != 0:
        return 1
    captcha_state = captcha_result['data']['state']
    # 通过api获取验证码
    data = {
        "image": captcha_result['data']['image'],
        "token": "LlyiKwDQdHjd50iZhOQneW1qqxU6rYg2tmj4EYH1HMk",
        "type": 50100
    }
    captcha_sp_result = requests.post("http://api.jfbym.com/api/YmServer/customApi", json=data).json()
    if captcha_sp_result['code'] == 10000:
        captcha_code = captcha_sp_result['data']['data']
    else:
        log("在通过api解析验证码时发生错误")
        return 1

    data = {
        "authType": "normal",
        "state": captcha_state,
        "username": username,
        "password": password_encrypt,
        "captcha": captcha_code,
        "mobile": "",
        "otpCaptcha": "",
        "remeberMe": use_rme
    }

    respone = session.post("https://sso.xmist.edu.cn/ssox/auth/token", data=data)
    result = respone.json()
    if result.get('code') == 0 and result.get('data').get('token') != None:
        token = result.get('data').get('token')
        ticket = result.get('data').get('ticket')
        remeberMe = result.get('data').get('remeberMe')
    else:
        log(f"登录失败, {respone.text}")
        return 1
    
    # 保存rme_token到config.json并更新config_data
    if remeberMe:
        with open('config.json', 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        json_data['rme_token'] = remeberMe
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)
        
        global config_data
        config_data = json_data

    return {'token': token, 'ticket': ticket, 'remeberMe': remeberMe}

def get_access_token_by_oauth(token, ticket):
    """[1/5] 设置token和ticket为cookies和Authorization"""
    session.cookies.set('congress', token)
    session.cookies.set('online_ticket', ticket)

    session.headers.update({
        "Authorization": f"Bearer {token}"
    })

    if DEBUG:
        log(f"[登录 1/5] token: {token}, ticket: {ticket}")
    
    """[2/5] OAuth第一步: 携带token向后端请求登录"""
    try:
        respone = session.get("https://sso.xmist.edu.cn/ssox/authz/oauth/authorize?client_id=77f80a61-4633-4249-9be9-29d90f31899e&response_type=code&redirect_uri=https://app.xmist.edu.cn/xmistmobile/sso&approval_prompt=auto&state=/attendance/student/today-signin", allow_redirects=True, timeout=config_data['request_timeout'])
    except:
        log("OAuth第一步发送请求失败, 可能为服务器过载或网络错误")
        return 1
    
    # 携带token向后端请求之后在返回的网页中寻找 `oauth_approval` token
    oauth_approval_match = re.search(r'oauth_approval=([^&"]+)', respone.text)
    if oauth_approval_match:
        oauth_approval = oauth_approval_match.group(1)
        if DEBUG:
            log(f"[登录 2/5] 成功获取oauth_approval: {oauth_approval}")
    else:
        log("OAuth第一步失败, 无法获取oauth_approval")
        return 1

    """[3/5] OAuth第二步: 审批确认"""
    try:
        respone = session.get(f"https://sso.xmist.edu.cn/ssox/authz/oauth/approval_confirm/get/{oauth_approval}", timeout=config_data['request_timeout'])
    except:
        log("OAuth第二步发送请求失败, 可能为服务器过载或网络错误")
        return 1
    
    result = respone.json()
    if result.get('code') == 0 and result.get('data').get('appName') != None:
        if DEBUG:
            log(f"[登录 3/5] 审批确认成功, 应用名称为\"{result.get('data').get('appName')}\"")
    else:
        log("OAuth第二步失败, 无法进行审批确认")

    """[4/5] OAuth第三步: 获取授权码"""
    try:
        respone = session.post("https://sso.xmist.edu.cn/ssox/authz/oauth/authorize/approval?user_oauth_approval=true", timeout=config_data['request_timeout'])
    except:
        log("OAuth第三步发送请求失败, 可能为服务器过载或网络错误")
        return 1

    result = respone.json()
    if result.get('code') == 0 and result.get('data') != None:
        auth_code_match = re.search(r"(?<=code=)[\w]+", result.get('data'))
        if auth_code_match:
            auth_code = auth_code_match.group()
            if DEBUG:
                log(f"[登录 4/5] 成功获取授权码: {auth_code}")
        else:
            log("OAuth第三步失败, 无法获取授权码")
            return 1
    else:
        log("OAuth第三步失败, 无法获取授权码")
        return 1

    """[5/5] OAuth第四步: 通过授权码换取 access_token"""
    # 不知道为什么请求时要带上这个headers才能成功
    headers = {
        'Authorization': 'Basic Y2F0OmNhdA==',
        'tenant-code': 'xmist_mobile',
        'Connection': 'keep-alive',
        'Content-Length': '0',
    }
    
    try:
        respone = session.post(f"https://app.xmist.edu.cn/gateway/auth/oauth/token?code=XMIST_MOBILE_JST_TYSFRZ-{auth_code}&state=1&grant_type=social&scope=server", headers=headers, timeout=config_data['request_timeout'])
    except:
        log("OAuth第四步发送请求失败, 可能为服务器过载或网络错误")
        return 1
    
    result = respone.json()
    if result.get('access_token') != None:
        access_token = result.get('access_token')
        if DEBUG:
            log(f"[登录 5/5] 登录成功啦, access_token={access_token}")
    else:
        log(f"OAuth第三步失败, 无法获取access_token")
        return 1
    
    return access_token

# False为登录状态正常, True为登录状态异常
def check_login_state():
    i = 0
    while True:
        # 由于服务器总是过载, 于是多次尝试请求
        try:
            respone = session.get(f"https://app.xmist.edu.cn/vcomGateway/vcomXrDtfw/api/sfxx", timeout=config_data['request_timeout'])
            break
        except:
            log("无法请求。可能为服务器过载或网络错误")
            i += i
            if i == 5:
                return True

    try:
        if (respone.status_code != 200):
            return True
        result = respone.json()
        if result.get('code' != 0):
            return True
    except:
        return True
    
    data = result.get('data')
    if data != 'xs':
        return True

    return False

# False为获取失败, True为获取的课表为空, 返回一个字典为成功获取并转换
def get_checkin_data():
    global data_new

    time = datetime.datetime.now().strftime("%Y-%m-%d")
    try:
        respone = session.get(f"https://app.xmist.edu.cn/gateway/xmistWyyService/api/zhxyKqxtQdrwxx/findXsKcb?page=1&size=50&skrq={time}", timeout=config_data['request_timeout'])
    except:
        log("无法请求签到列表。可能为服务器过载或网络错误")
        return False

    try:
        if (respone.status_code != 200):
            log("无法列出签到列表!!!")
            log(respone.text)
            return False
        data = respone.json()
        if data.get('code' != 0):
            log("无法列出签到列表!!!")
            log(respone.text)
            return False
    except:
        log("请求出错!!!")
        log(respone.text)
        return False
    
    content = data.get('data', {}).get('content')
    if content == None:
        log("无法列出签到列表!!!")
        log(respone.text)
        return False
    
    if content == []:
        log("今天的课表为空, 或无法获取课表")
        return True

    data_new = []
    # 计划存储的内容
    #[
    #    {
    #        "id": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX_(index)",
    #        "name": "语文",
    #        "state": "signed_in",   // signed_in已签到, not_signed_in未签到, pending未发起, unknown未知
    #        "start_time": "14:25",
    #        "end_time": "16:00",
    #        "type": "one_click",    // "one_click" (一键签到, 无需密码), "password" (密码签到)
    #        "password": "123456",
    #        "location_info": {
    #            "name": "E201",
    #            "longitude": "118.07279",
    #            "latitude": "24.61582"
    #        },
    #        "sign_in_uuid": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  // 发送签到请求所携带的uuid
    #    }
    #]

    # 转换数据到data_new
    for index, course in enumerate(content):
        data_new.append({})

        data_new[index]['id'] = course['id'] + f"_{index}"
        data_new[index]['name'] = course['kcmc']

        data_new[index]['start_time'] = course['sksj']
        data_new[index]['end_time'] = course['xksj']

        data_new[index]['location_info'] = {}
        data_new[index]['location_info']['name'] = course['jxdd']
        with open('location_info.json', 'r', encoding='utf-8') as f:
            location_data = json.load(f)
        data_new[index]['location_info']['longitude'] = location_data.get(data_new[index]['location_info']['name'], {}).get('longitude', None)
        data_new[index]['location_info']['latitude'] = location_data.get(data_new[index]['location_info']['name'], {}).get('latitude', None)

        if course['zhxyKqxtQdrwxxQueryDTOS'] != []:
            match course['zhxyKqxtQdrwxxQueryDTOS'][0]['qdzt']:
                case "0":
                    data_new[index]['state'] = "not_signed_in"
                case "1":
                    data_new[index]['state'] = "signed_in"
                case _:
                    data_new[index]['state'] = "unknown"
            
            match course['zhxyKqxtQdrwxxQueryDTOS'][0]['qdlx']:
                case "1":
                    data_new[index]['type'] = "one_click"
                case "2":
                    data_new[index]['type'] = "password"
            
            data_new[index]['password'] = course['zhxyKqxtQdrwxxQueryDTOS'][0]['kl']
            data_new[index]['sign_in_uuid'] = course['zhxyKqxtQdrwxxQueryDTOS'][0]['uuid']
        else:
            data_new[index]['state'] = "pending"
            data_new[index]['type'] = None
            data_new[index]['password'] = None
            data_new[index]['sign_in_uuid'] = None
    
    return data_new

# 0代表成功, 1代表失败(原因未知), 2代表失败(因为没有位置信息)
def request_to_sign_in(id):
    for index, course in enumerate(data_new):
        if course['id'] == id:
            if DEBUG:
                log(course)
            index_id = index
            break
    
    if data_new[index_id]['sign_in_uuid'] == None:
        if DEBUG:
            log("没有签到uuid, 无法签到")
        return 1

    match data_new[index_id]['type']:
        case 'one_click':
            type_course = '1'
            password = ''
        case 'password':
            type_course = '2'
            password = data_new[index_id]['password']
        case 'unknown':
            log("警告: 未知签到类型")
            type_course = '1'

    longitude = data_new[index_id]['location_info']['longitude']
    latitude = data_new[index_id]['location_info']['latitude']

    if longitude == None or latitude == None:
        if DEBUG:
            log("没有位置信息, 无法签到")
        return 2
    
    post_data = {
        "qdrwuuid": f"{data_new[index_id]['sign_in_uuid']}",
        "qdlx": f"{type_course}",
        "kl": f"{password}",
        "qdjd": f"{longitude}",
        "qdwd": f"{latitude}"
    }

    if DEBUG == True:
        log(post_data)
    
    try:
        respone = session.post("https://app.xmist.edu.cn/gateway/xmistWyyService/api/zhxyKqxtQdrwxx/qd", json=post_data, timeout=config_data['request_timeout'])
    except:
        log("请求签到失败, 可能为服务器过载或网络错误")
        return 1

    if DEBUG == True:
        log(respone.text)
    
    try:
        data_respone = respone.json()
        if data_respone['code'] == 0:
            return 0
        else:
            return 1
    except:
        return 1

def main_loop():
    if check_login_state():
        log("登录状态已丢失, 尝试重新登录")
        if login(config_data['XMIST_USERNAME'], config_data['XMIST_PASSWORD']):
            log("登录成功")
        else:
            log("登录失败")
            return 2
    
    global data_new
    log("尝试获取签到任务信息")
    data_new = get_checkin_data()
    if DEBUG:
        log(data_new)
    if data_new == False:
        log("获取签到任务信息失败")
        return 3
    if data_new ==  True:
        now = datetime.datetime.now()
        next_6am = datetime.datetime(now.year, now.month, now.day, 6, 0, 0) + datetime.timedelta(days=1)
        next_6am_timedelta = next_6am - now
        log("今天的课表为空, 或无法获取课表, 程序将会在 {next_6am} 继续运行")
        time.sleep(next_6am_timedelta.seconds)
        return 0
    
    # test
    # request_to_sign_in("7287e873df20d9ffd64ba4d517a761dd_3")

    # 检查看有没有已经发起但是还没有签到的签到任务
    for course in data_new:
        if course['state'] == "not_signed_in":
            log(f"发现\"{course['name']}\"课程还没有签到, 将在3秒后尝试签到")
            time.sleep(3)
            request_to_sign_in(course['id'])

    # 获取下一次签到是什么时间, 程序应该休眠多久
    now = datetime.datetime.now()
    for index, course in enumerate(data_new):
        start_time = datetime.datetime.strptime(f"{datetime.datetime.strftime(now, '%Y-%m-%d')} {course['start_time']}", "%Y-%m-%d %H:%M")
        end_time = datetime.datetime.strptime(f"{datetime.datetime.strftime(now, '%Y-%m-%d')} {course['end_time']}", "%Y-%m-%d %H:%M")
        if now < end_time:
            if now < start_time:
                need_sleep_delta = start_time - now
                need_sleep_seconds = need_sleep_delta.seconds - config_data['advance_waiting_time_seconds']
                if need_sleep_seconds > 0:
                    log(f"下一节课是\"{course['name']}\", 在\"{start_time}\"开始, 程序需要休眠{need_sleep_seconds}秒")
                    time.sleep(need_sleep_seconds)
                    if check_login_state():
                        log("登录状态已丢失, 尝试重新登录")
                        if login(config_data['XMIST_USERNAME'], config_data['XMIST_PASSWORD']):
                            log("登录成功")
                        else:
                            log("登录失败")
                        return 2
            log(f"课程\"{course['name']}\"即将开始或已开始, 开始循环检测签到任务是否发起")
            while True:
                # 更新data_new中的数据
                i = 0
                while True:
                    # 由于签到服务器总是过载, 因此多重试几次, 以防止服务器无响应
                    if i == 5:
                        log("多次重试依然无法获取签到任务列表, 放弃重试")
                        return 3

                    data_new = get_checkin_data()
                    if data_new == False:
                        i += 1
                        log("请求签到任务列表出错, 可能为服务器过载或网络错误, 将在1秒后重试")
                        time.sleep(1)
                    else:
                        break
                if data_new[index]['state'] == 'not_signed_in':
                    log(f"\"{course['name']}\"已经可以签到了, 程序将在 5 秒后尝试签到")
                    time.sleep(5)
                    i = 0
                    while request_to_sign_in(course['id']) != 0:
                        log("签到失败, 将在 3 秒后重试")
                        i += 1
                        if i == 5:
                            log(f"签到失败, 跳过\"{course['name']}\"课程签到")
                            return 1
                        time.sleep(3)
                    log("签到成功")
                elif data_new[index]['state'] == 'signed_in':
                    log("此签到任务已完成签到, 切换下一个任务")
                    break
                else:
                    log("签到任务暂未发布, 继续等待...")
                    time.sleep(config_data['CHECK_INTERVAL'])

                    now = datetime.datetime.now()
                    if end_time < now:
                        log(f"已经超过下课时间了, 跳过\"{course['name']}\"课程签到")
                        return 0

    now = datetime.datetime.now()
    next_6am = datetime.datetime(now.year, now.month, now.day, 6, 0, 0) + datetime.timedelta(days=1)
    next_6am_timedelta = next_6am - now
    log(f"似乎今天已经没有课了, 程序将会在 {next_6am} 继续运行")
    time.sleep(next_6am_timedelta.seconds)

def main():
    log("尝试登录中...")
    if login(config_data['XMIST_USERNAME'], config_data['XMIST_PASSWORD']):
        log("登录成功")
    else:
        log("登录失败")
        return False

    while True:
        match main_loop():
            case 0:
                time.sleep(1)
            case 1:
                log("签到失败, 开始检测下一课程签到")
                time.sleep(1)
            case 2:
                log("登录失败, 将在3秒后重试")
                time.sleep(3)
            case 3:
                log("无法获取签到任务信息, 将在15秒后重试")
                time.sleep(15)
            case _:
                log("未知状态...程序退出!!!")
                exit()

main()

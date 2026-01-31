import json
import math
import random
import execjs
import os
from xhs_utils.cookie_util import trans_cookies

# 获取当前文件所在目录 (xhs_utils)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 计算 static 目录的绝对路径 (src/tools/Spider_XHS/static)
static_dir = os.path.join(os.path.dirname(current_dir), 'static')

# 构造 JS 文件的绝对路径
js_path = os.path.join(static_dir, 'xhs_xs_xsc_56.js')
xray_path = os.path.join(static_dir, 'xhs_xray.js')

# ==============================================================================
# 🛠️ 关键修复：动态替换 JS 中的相对路径为绝对路径
# ==============================================================================
def load_js_with_absolute_paths(file_path, base_static_dir):
    """
    读取 JS 文件，并将其中的 ./static 引用替换为绝对路径，
    防止 execjs 在不同目录下运行时找不到依赖。
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 将 Windows 反斜杠路径转换为 JS 认识的正斜杠
    # 例如: D:\Project\static -> D:/Project/static
    abs_static_path = base_static_dir.replace("\\", "/")
    
    # 2. 暴力替换：将 JS 源码里的 relative require 路径修正为 absolute path
    # 错误源码可能长这样: require("./static/xhs_xray_pack1.js")
    # 我们把它变成: require("D:/Project/.../static/xhs_xray_pack1.js")
    content = content.replace("./static", abs_static_path)
    
    # 3. 编译
    return execjs.compile(content)

# 加载 xs.js
try:
    # xs.js 通常没有复杂的 require，直接编译即可，或者为了保险也用处理函数
    # 这里保持原样或统一处理均可，原样通常没问题
    js = execjs.compile(open(js_path, 'r', encoding='utf-8').read())
except Exception as e:
    print(f"Error loading js file: {e}")
    raise e

# 加载 xray.js (这里是报错的源头)
try:
    # 🔥 使用修复函数加载
    xray_js = load_js_with_absolute_paths(xray_path, static_dir)
except Exception as e:
    print(f"Error loading xray js file: {e}")
    raise e
# ==============================================================================

def generate_x_b3_traceid(len=16):
    x_b3_traceid = ""
    for t in range(len):
        x_b3_traceid += "abcdef0123456789"[math.floor(16 * random.random())]
    return x_b3_traceid

def generate_xs_xs_common(a1, api, data='', method='POST'):
    ret = js.call('get_request_headers_params', api, data, a1, method)
    xs, xt, xs_common = ret['xs'], ret['xt'], ret['xs_common']
    return xs, xt, xs_common

def generate_xs(a1, api, data=''):
    ret = js.call('get_xs', api, data, a1)
    xs, xt = ret['X-s'], ret['X-t']
    return xs, xt

def generate_xray_traceid():
    return xray_js.call('traceId')

def get_common_headers():
    return {
        "authority": "www.xiaohongshu.com",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "zh-CN,zh;q=0.9",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "referer": "https://www.xiaohongshu.com/",
        "sec-ch-ua": "\"Chromium\";v=\"122\", \"Not(A:Brand\";v=\"24\", \"Google Chrome\";v=\"122\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

def get_request_headers_template():
    return {
        "authority": "edith.xiaohongshu.com",
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "cache-control": "no-cache",
        "content-type": "application/json;charset=UTF-8",
        "origin": "https://www.xiaohongshu.com",
        "pragma": "no-cache",
        "referer": "https://www.xiaohongshu.com/",
        "sec-ch-ua": "\"Not A(Brand\";v=\"99\", \"Microsoft Edge\";v=\"121\", \"Chromium\";v=\"121\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        "x-b3-traceid": "",
        "x-mns": "unload",
        "x-s": "",
        "x-s-common": "",
        "x-t": "",
        "x-xray-traceid": generate_xray_traceid()
    }

def generate_headers(a1, api, data='', method='POST'):
    xs, xt, xs_common = generate_xs_xs_common(a1, api, data, method)
    x_b3_traceid = generate_x_b3_traceid()
    headers = get_request_headers_template()
    headers['x-s'] = xs
    headers['x-t'] = str(xt)
    headers['x-s-common'] = xs_common
    headers['x-b3-traceid'] = x_b3_traceid
    if data:
        data = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    return headers, data

def generate_request_params(cookies_str, api, data='', method='POST'):
    cookies = trans_cookies(cookies_str)
    a1 = cookies['a1']
    headers, data = generate_headers(a1, api, data, method)
    return headers, cookies, data

def splice_str(api, params):
    url = api + '?'
    for key, value in params.items():
        if value is None:
            value = ''
        url += key + '=' + value + '&'
    return url[:-1]
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 5 19:17:17 2022
Last Edit 10/27/2023
@author: Liyao Zhang

星辰智盈数据自动获取系统 with Streamlit
"""

import io
import time
import base64
import pandas as pd
import streamlit as st
from PIL import Image
from datetime import datetime, timedelta
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
# For W3C actions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput

def main():
    st.set_page_config(
    page_title="星辰数据获取",
    page_icon=Image.open('pages/logo.jpg')
    #initial_sidebar_state="expanded"
    )
    
    st.title("星辰智盈数据自动获取系统")
    
    get_qbl = get_zsxt = get_gplj = get_sqnl = get_lsqt = False
    mode = st.radio('选择算法', options=('全选', '早盘', '临场'), help='全选包括早盘临场5大算法，早盘算法指球伯乐及指数形态，临场算法指公平量价、赛前能量和联赛球探')
    if mode == '全选':
        get_qbl = get_zsxt = get_gplj = get_sqnl = get_lsqt = True
    elif mode == '早盘':
        get_qbl = get_zsxt = True
    elif mode == '临场':
        get_gplj = get_sqnl = get_lsqt = True

    today = datetime.today()
    today_modified = today.replace(minute=0, second=0, microsecond=0)
    with st.form("user_input"):
        col1, col2 = st.columns(2)
        with col1:
            if mode != '临场':
                start_time_qbl = st.slider(
                    "球伯乐开始时间",
                    value=today_modified,
                    min_value=today_modified - timedelta(hours=24),
                    max_value=today_modified + timedelta(hours=8),
                    step=timedelta(minutes=15),
                    format="MM/DD - HH:mm")
                start_time_zsxt = st.slider(
                    "指数形态开始时间",
                    value=today_modified,
                    min_value=today_modified - timedelta(hours=24),
                    max_value=today_modified + timedelta(hours=8),
                    step=timedelta(minutes=15),
                    format="MM/DD - HH:mm")
            if mode != '早盘':
                start_time_gplj = st.slider(
                    "公平量价开始时间",
                    value=today_modified,
                    min_value=today_modified - timedelta(hours=24),
                    max_value=today_modified + timedelta(hours=8),
                    step=timedelta(minutes=15),
                    format="MM/DD - HH:mm")
                start_time_sqnl = st.slider(
                    "赛前能量开始时间",
                    value=today_modified,
                    min_value=today_modified - timedelta(hours=24),
                    max_value=today_modified + timedelta(hours=8),
                    step=timedelta(minutes=15),
                    format="MM/DD - HH:mm")
                start_time_lsqt = st.slider(
                    "联赛球探开始时间",
                    value=today_modified,
                    min_value=today_modified - timedelta(hours=24),
                    max_value=today_modified + timedelta(hours=8),
                    step=timedelta(minutes=15),
                    format="MM/DD - HH:mm")
            reset_app = st.checkbox('以重置应用模式运行', value=False)
        
        with col2:
            if mode != '临场':
                end_time_qbl = st.slider(
                    "球伯乐结束时间",
                    value=today_modified,
                    min_value=today_modified - timedelta(hours=24),
                    max_value=today_modified + timedelta(hours=12),
                    step=timedelta(minutes=15),
                    format="MM/DD - HH:mm")
                end_time_zsxt = st.slider(
                    "指数形态结束时间",
                    value=today_modified,
                    min_value=today_modified - timedelta(hours=24),
                    max_value=today_modified + timedelta(hours=12),
                    step=timedelta(minutes=15),
                    format="MM/DD - HH:mm")
            if mode != '早盘':
                end_time_gplj = st.slider(
                    "公平量价结束时间",
                    value=today_modified,
                    min_value=today_modified - timedelta(hours=24),
                    max_value=today_modified + timedelta(hours=12),
                    step=timedelta(minutes=15),
                    format="MM/DD - HH:mm")
                end_time_sqnl = st.slider(
                    "赛前能量结束时间",
                    value=today_modified,
                    min_value=today_modified - timedelta(hours=24),
                    max_value=today_modified + timedelta(hours=12),
                    step=timedelta(minutes=15),
                    format="MM/DD - HH:mm")
                end_time_lsqt = st.slider(
                    "联赛球探结束时间",
                    value=today_modified,
                    min_value=today_modified - timedelta(hours=24),
                    max_value=today_modified + timedelta(hours=12),
                    step=timedelta(minutes=15),
                    format="MM/DD - HH:mm")
            if mode == '临场':
                combine = st.checkbox('与数据库早盘数据合并', value=False)

        submitted = st.form_submit_button("运行", help='请启动模拟器后再点击运行')
    if submitted:
        caps = {}
        caps["platformName"] = "Android"
        caps["appium:platformVersion"] = "7.1.2"
        caps["appium:deviceName"] = "127.0.0.1:62001"
        caps["appium:appPackage"] = "com.xczy.star_gain"
        caps["appium:appActivity"] = "com.xczy.star_gain.MainActivity"
        caps["appium:ensureWebviewsHavePages"] = True
        caps["appium:nativeWebScreenshot"] = True
        caps["appium:newCommandTimeout"] = 7200
        caps["appium:connectHardwareKeyboard"] = True
        caps["appium:unicodeKeyboard"] = True
        caps["appium:resetKeyboard"] = True
        if not reset_app:
            caps["noReset"] = True
        
        driver = webdriver.Remote("http://127.0.0.1:4723/wd/hub", caps)
        driver.implicitly_wait(10)
        #重置模式
        if reset_app:
            init_login(driver)
        time.sleep(15) #wait for user login/click other info
        init_algo(driver, reset_app)
        st.success('初始化完成！')
        time.sleep(3)
        #遍历每个算法
        qbl_visited = False
        zsxt_visited = False
        gplj_visited = False
        sqnl_visited = False
        lsqt_visited = False
        
        #球伯乐
        if get_qbl:
            algo_list1 = driver.find_elements(AppiumBy.CLASS_NAME, value="android.widget.ImageView")
            i = 0
            while not qbl_visited:
                algo = algo_list1[i]
                if algo.get_attribute('text').split('\n')[0] == '球伯乐':
                    algo_name = ''
                    algo.click()
                    unlock_matches(driver, 7)
                    time.sleep(2)
                    #重置模式
                    if reset_app:
                        init_match(driver) #once only
                        time.sleep(2)
                    with st.spinner("正在获取球伯乐数据..."):
                        df_qbl = get_matches(driver, algo_name, start_time_qbl.strftime('%m-%d %H:%M'), end_time_qbl.strftime('%m-%d %H:%M'))
                    qbl_visited = True
                    st.success('球伯乐数据获取成功！')
                else:
                    i += 1                          
        time.sleep(2)
        #指数形态
        if get_zsxt:
            algo_list2 = driver.find_elements(AppiumBy.CLASS_NAME, value="android.widget.ImageView")
            i = 0
            while not zsxt_visited:
                algo = algo_list2[i]
                if algo.get_attribute('text').split('\n')[0] == '指数形态':
                    algo_name = '指数形态'
                    algo.click()
                    unlock_matches(driver, 7)
                    time.sleep(2)
                    with st.spinner("正在获取指数形态数据..."):
                        df_zsxt = get_matches(driver, algo_name, start_time_zsxt.strftime('%m-%d %H:%M'), end_time_zsxt.strftime('%m-%d %H:%M'))
                    zsxt_visited = True
                    st.success('指数形态数据获取成功！')
                else:
                    i += 1            
        time.sleep(2)
        #公平量价
        if get_gplj:
            #catch exception
            try:
                algo_list3 = driver.find_elements(AppiumBy.CLASS_NAME, value="android.widget.ImageView")
                i = 0
                while not gplj_visited:
                    algo = algo_list3[i]
                    if algo.get_attribute('text').split('\n')[0] == '公平量价':
                        algo_name = '公平量价'
                        algo.click()
                        unlock_matches(driver, 3)
                        time.sleep(2)
                        with st.spinner("正在获取公平量价数据..."):
                            df_gplj = get_matches(driver, algo_name, start_time_gplj.strftime('%m-%d %H:%M'), end_time_gplj.strftime('%m-%d %H:%M'))
                        gplj_visited = True
                        st.success('公平量价数据获取成功！')
                    else:
                        i += 1
            except:
                df_gplj = None

        time.sleep(2)
        #赛前能量
        if get_sqnl:
            #catch exception
            try:
                algo_list4 = driver.find_elements(AppiumBy.CLASS_NAME, value="android.widget.ImageView")
                i = 0
                while not sqnl_visited:
                    algo = algo_list4[i]
                    if algo.get_attribute('text').split('\n')[0] == '赛前能量':
                        algo_name = '赛前能量'
                        algo.click()
                        unlock_matches(driver, 3)
                        time.sleep(2)
                        with st.spinner("正在获取赛前能量数据..."):
                            df_sqnl = get_matches(driver, algo_name, start_time_sqnl.strftime('%m-%d %H:%M'), end_time_sqnl.strftime('%m-%d %H:%M'))
                        sqnl_visited = True
                        st.success('赛前能量数据获取成功！')
                    else:
                        i += 1
            except:
                df_sqnl = None
            
        time.sleep(2)
        #联赛球探
        if get_lsqt:
            #catch exception
            try:
                algo_list5 = driver.find_elements(AppiumBy.CLASS_NAME, value="android.widget.ImageView")
                i = 0
                while not lsqt_visited:
                    algo = algo_list5[i]
                    if algo.get_attribute('text').split('\n')[0] == '联赛球探':
                        algo_name = '联赛球探'
                        algo.click()
                        unlock_matches(driver, 3)
                        time.sleep(2)
                        with st.spinner("正在获取联赛球探数据..."):
                            df_lsqt = get_matches(driver, algo_name, start_time_lsqt.strftime('%m-%d %H:%M'), end_time_lsqt.strftime('%m-%d %H:%M'))
                        lsqt_visited = True
                        st.success('联赛球探数据获取成功！')
                    else:
                        i += 1
            except:
                df_lsqt = None

        #合并数据
        if mode == '全选':                     
            df_final = pd.concat([df_qbl, df_zsxt, df_gplj, df_sqnl, df_lsqt])
        elif mode == '早盘':
            df_final = pd.concat([df_qbl, df_zsxt])
        elif mode == '临场':
            if combine:
                with st.spinner("合并数据中..."):
                    onedrive_link = 'https://1drv.ms/x/s!Ag9ZvloaJitBjy8YIdiLf5Wkr4O6?e=cwBjTO'
                    url = create_onedrive_directdownload(onedrive_link)
                    df = read_file(url)
                    min_time = min(start_time_gplj, start_time_sqnl, start_time_lsqt) #判断最早时间
                    df_selected = df[(df['开球时间']>=min_time.strftime('%m-%d %H:%M'))&(df['年']==2023)] #每年改一次
                    data_selected = pd.concat([df_gplj, df_sqnl, df_lsqt])
                    df_final = pd.concat([df_selected, data_selected])
                st.success('数据合并成功！')
            else:                
                df_final = pd.concat([df_gplj, df_sqnl, df_lsqt])
                
        df_final = df_final.sort_values(by=['开球时间','联赛','比赛'])
        file_name="星辰数据_"+mode+today.strftime('%m-%d')+".xlsx"
        df_final.to_excel(r'C:\Users\张力铫\Desktop\\'+file_name, index=False)

def init_login(driver):
    '''
    进入登录界面
    '''
    #点击【同意】
    el0 = driver.find_element(by=AppiumBy.XPATH, value="/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.Button")
    el0.click()
    
    #点击【使用密码登录】
    el0_1 = driver.find_element(by=AppiumBy.XPATH, value="/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[3]/android.view.View[3]/android.widget.Button")
    el0_1.click()
    
def init_algo(driver, reset_app):
    '''
    进入算法界面
    '''
    #点击【智盈】
    el1 = driver.find_element(by=AppiumBy.XPATH, value="/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[4]/android.widget.ImageView[2]")
    el1.click()
    
    #点击【知道啦】
    if reset_app:
        el1_1 = driver.find_element(by=AppiumBy.XPATH, value="/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[8]")
        el1_1.click()
    time.sleep(3)
    
    #点击【核心算法】
    el2 = driver.find_element(by=AppiumBy.XPATH, value="/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[3]")
    el2.click()
    time.sleep(1)
    
    if reset_app:
        #第一个算法
        el3 = driver.find_element(by=AppiumBy.XPATH, value="/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[5]/android.view.View/android.widget.ImageView[1]")
        el3.click()
        
        #点击【知道啦】
        el3_0 = driver.find_element(by=AppiumBy.XPATH, value="/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[16]")
        el3_0.click()
        
        back = driver.find_element(by=AppiumBy.XPATH, value="/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[1]/android.widget.Button")
        back.click()

def init_match(driver):
    '''
    进入比赛界面
    '''
    #第一场比赛
    el4 = driver.find_element(by=AppiumBy.XPATH, value="/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[13]/android.view.View/android.view.View[1]")
    el4.click()
    time.sleep(1)
    
    #点击【知道啦】
    el4_0 = driver.find_element(by=AppiumBy.XPATH, value="/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[4]")
    el4_0.click()
    
    back_1 = driver.find_element(by=AppiumBy.XPATH, value="/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.Button")
    back_1.click()
    
def unlock_matches(driver, clicks):
    '''
    一键解锁比赛
    '''
    for i in range(0, clicks):
        try:
            driver.find_element(by=AppiumBy.XPATH, value="/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[12]/android.widget.Button")
            unlock = driver.find_element(by=AppiumBy.XPATH, value="/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[12]/android.widget.Button")
            unlock.click()
        except:
            st.error('一键解锁失败')

def clean_leagues(league_name):
    '''
    返回清洗后的联赛名称及是否属于收录的联赛
    '''
    league_dict = {'美职':'美职联','日职':'日职联','冠军杯':'欧冠','智利甲':'智甲','欧霸杯':'欧联','南俱杯':'南球杯','世美预':'南美预选'}

    league_list = ['美职联','日职联','德乙','德甲','西甲','英超','欧冠','阿甲','欧联','法甲','巴甲','意甲','欧国联',
                   '墨超','葡超','荷甲','英冠','解放者杯','欧预赛','南球杯','瑞典超','挪超','世界杯','美洲杯','亚洲预选',
                   '西乙','比甲','智甲','南美预选','世预赛','北美预选','欧洲杯','世俱杯','欧协联']
    
    for key, value in league_dict.items():
        league_name = league_name.replace(key, value)
        
    if league_name in league_list:
        return league_name, True
    else:
        return league_name, False

def clean_teams(home, away, league_name):
    '''
    返回清洗后的球队名称
    '''
    teams_dict = {'日职联':{'鸟栖沙岩':'鸟栖砂岩','清水鼓动':'清水心跳','名古屋鲸八':'名古屋逆戟鲸'},
                  '美职联':{'辛辛那提FC':'辛辛那提','温哥华白帽':'温哥华白浪','堪萨斯城竞技':'堪萨斯城体育','波特兰伐木工':'波特兰伐木者'},
                  '阿甲':{'普拉腾斯':'普拉滕斯竞技','泰格雷':'老虎竞技','竞技俱乐部':'竞技','圣塔菲联':'圣菲联','巴拉卡斯中央队':'巴拉卡斯中央',
                            '科隆竞技':'哥伦布竞技','铁路工场':'塔列雷斯','阿尔多西维':'阿尔多希维','科尔多瓦中央SDE':'科尔多瓦中央','联合队':'科尔多瓦学院',
                            '阿根廷独立':'独立','萨尔米安杜':'萨米恩托','飓风队':'飓风','帕特罗纳图':'天主教青年','防御与正义':'国防与司法','天主教青年会':'天主教青年'},
                  '德甲':{'莱比锡红牛':'RB莱比锡'},
                  '西甲':{'维戈塞尔塔':'塞尔塔','马洛卡':'马略卡','阿尔梅利亚':'阿尔梅里亚','瓦拉多利德':'巴拉多利德','加的斯':'加迪斯'},
                  '英超':{'南安普敦':'南安普顿','曼彻斯特联':'曼联','曼彻斯特城':'曼城','莱切斯特城':'莱斯特城','托特纳姆热刺':'热刺'},
                  '法甲':{'巴黎圣日尔曼':'巴黎圣日耳曼'},
                  '意甲':{'克雷莫纳':'克雷莫内塞','弗洛西诺尼':'弗罗西诺内'},
                  '欧冠':{'比尔森':'比尔森胜利','萨尔茨堡':'萨尔茨堡红牛','格拉斯哥流浪者':'流浪者','年轻人':'伯尔尼年轻人'},
                  '欧联':{'谢里夫':'蒂拉斯波尔警长','LASK林茨':'林茨','帕纳辛纳科斯':'帕纳辛奈科斯','艾里斯利马斯素尔':'阿里斯利马索尔'},
                  '欧协联':{'第聂伯罗特警':'SK第聂伯罗','波兹南':'波兹南莱赫','比尔舒华夏普尔':'贝尔谢巴工人','萨尔格里斯':'扎尔吉里斯',
                             '布加勒斯特星队':'布加勒斯特星','列加斯':'里加足球学校','伊斯坦布':'伊斯坦布尔','利马索尔阿波罗':'阿波罗利马索尔',
                             '奥林比查':'卢布尔雅那奥林匹亚','泰拿华斯巴达':'特纳瓦斯巴达','萨连斯基':'莫斯塔尔兹林斯基','卢甘斯克黎明':'索尔亚','卡拉卡斯维克':'克拉克斯维克',
                             '贝雷达比历克':'布列达布利克'},
                  '德乙':{'不伦瑞克':'布伦瑞克'},
                  '英冠':{'加的夫城':'卡迪夫城','布里斯托城':'布里斯托尔城','西布罗姆维奇':'西布朗'},
                  '西乙':{'格拉纳达GF':'格拉纳达','米兰迪斯':'米兰德斯','安道尔CF':'FC安道尔','阿尔巴切特':'阿尔瓦塞特','特內里费':'特内里费','艾科坎':'阿尔科孔'},
                  '巴甲':{'奥瓦':'阿瓦伊','科里蒂巴':'库里蒂巴','布拉干蒂诺RB':'布拉甘蒂诺红牛','戈伊亚斯':'戈亚斯','福塔雷萨':'福塔莱萨','库亚巴':'奎尔巴'},
                  '墨超':{'老虎大学':'墨西哥老虎','马萨特兰FC':'马萨特兰','蒙特瑞':'蒙特雷','墨西哥美洲':'美洲','阿苏尔':'蓝十字',
                            '拿加沙':'内卡萨','圣路易斯竞技':'圣路易斯','提华纳':'蒂华纳'},
                  '葡超':{'波尔蒂芒尼斯':'波尔蒂芒人','沙维什':'沙维斯','吉维森特':'吉尔维森特','里奥阿维':'阿维河','里斯本竞技':'葡萄牙体育',
                              '卡沙比亞':'卡萨皮亚','维兹拉':'维泽拉','费雷拉':'帕索斯费雷拉','马里迪莫':'马德拉航海','摩雷伦斯':'莫雷拉人','法伦斯':'法鲁人'},
                  '荷甲':{'埃门':'埃蒙','福图纳锡塔德':'锡塔德幸运','PSV埃因霍温':'埃因霍温','维迪斯':'维特斯','赫拉克勒斯':'阿尔梅罗大力神'},
                  '瑞典超':{'韦纳穆':'瓦纳默','IFK哥德堡':'哥德堡','AIK索尔纳':'索尔纳','布鲁马波卡纳':'布洛马波卡纳'},
                  '挪超':{'奥德':'奥特','博德闪耀':'博多格林特','格里姆斯塔':'谢夫','桑纳菲尤尔':'桑德菲杰','萨尔普斯堡':'萨普斯堡'},
                  '比甲':{'奥德赫维里':'奥哈瓦里','聚尔特瓦雷赫姆':'威尔郡','沙勒罗瓦':'沙勒鲁瓦','瑟兰联':'塞莱恩','吉马雷斯':'吉马良斯'},
                  '智甲':{'尤尼昂':'拉卡勒拉联','科金博':'科金博联合','维尼亚德马埃弗顿':'比尼亚德尔马埃弗顿','库里科':'库里科联合','马加拉内斯':'麦哲伦',
                           '塞雷那':'拉塞雷纳','纽夫莱恩斯':'纽布伦斯','希金斯':'奥希金斯','科布雷索':'科布雷萨尔','奥达斯':'奥达科斯意大利人','华奇巴托':'瓦奇巴托'},
                  '解放者杯':{'万卡约':'万卡约体育','巴拉圭国民':'亚松森国民','水晶体育':'水晶竞技','曼特宁独立':'麦德林独立','时刻准备':'时刻准备着','麦罗波利塔诺':'大都会',
                              '蒙得维的亚国民':'乌拉圭民族','国民体育会':'国民竞技','瓜亚基尔':'巴塞罗那SC','佩雷拉':'佩雷拉体育','蒙得维的':'利物浦','亚松森自由':'自由',
                              '亚松森奥林匹亚':'奥林匹亚'},
                  '南球杯':{'德尔瓦耶独立':'山谷独立','卡巴列罗':'卡巴雷罗将军','港发院':'卡贝略港大学','利加大学':'基多大学','德芬':'海豚','奥利恩特':'东方石油',
                            '丹奴比奥':'多瑙河','亚松森瓜拉尼':'巴拉圭瓜拉尼','艾美利亚诺体育':'阿梅利亚诺体育','艾斯图第安特':'梅里达大学生','塔奇拉':'塔齐拉体育',
                            '阿古拉斯多拉达斯':'里奥内格罗老鹰','卡萨大学队':'卡萨大学','普诺双国':'两国竞技','帕马科亚':'棕榈竞技','昆卡':'昆卡体育','托利马体育':'托里马体育',
                            '大学生体育':'秘鲁体育大学'},
                  '世界杯':{'沙特':'沙特阿拉伯'}
                  #Last Edit: 10/27/2023
                  }
    
    for league_key, league_values in teams_dict.items():
        for key, value in league_values.items():
            if home == key:
                home = home.replace(key, value)
            if away == key:
                away = away.replace(key, value)
    return home, away

def decode_scoreline(score_list):
    scoreline = ''
    scoreline_dict = {'[94,842][124,863]':'0-0','[94,904][124,925]':'0-1','[165,904][195,925]':'0-2','[307,904][337,925]':'0-3','[519,904][549,925]':'0-4','[236,965][266,986]':'0-5',
                      '[94,719][124,740]':'1-0','[165,842][195,863]':'1-1','[236,904][266,925]':'1-2','[378,904][408,925]':'1-3','[94,965][124,986]':'1-4','[307,965][337,986]':'1-5',
                      '[165,719][195,740]':'2-0','[236,719][266,740]':'2-1','[236,842][266,863]':'2-2','[449,904][479,925]':'2-3','[165,965][195,986]':'2-4','[378,965][408,986]':'2-5',
                      '[307,719][337,740]':'3-0','[378,719][408,740]':'3-1','[449,719][479,740]':'3-2','[307,842][337,863]':'3-3',
                      '[519,719][549,740]':'4-0','[94,781][124,802]':'4-1','[165,781][195,802]':'4-2',
                      '[236,781][266,802]':'5-0','[307,781][337,802]':'5-1','[378,781][408,802]':'5-2','[449,781][479,802]':'胜其他','[449,965][479,986]':'负其他'}
    for i in range(0,4):
        for key, value in scoreline_dict.items():
            score_list[i] = score_list[i].replace(key, value)
    filteredList = [x for x in score_list if not x.startswith('[')]
    
    if len(filteredList) == 2:
        scoreline = filteredList[0]+' '+filteredList[1]
    elif len(filteredList) == 1:
        scoreline = filteredList[0]+' new'
    return scoreline
            
def get_matches(driver, algo_name, start_time, end_time):
    '''
    获取比赛信息
    '''
    reach_lb = False #遇到指定开始时间的比赛
    reach_ub = False #遇到指定结束时间的比赛
    new_game = True #判断是否还有新比赛
    increase = True #判断是否到达未开赛比赛尽头
    prev_date = '00-00 00:00' #判断开赛时间是否在增长
    games_list = [] #存储比赛信息，用于比赛去重
    df = pd.DataFrame(columns=['开球时间','算法','联赛','比赛','胜','平','负','H','A','让胜','让平','让负','盘口',
                               '注释','比分','进球数','竞彩','批注胜','批注平','批注负','批注让胜','批注让平','批注让负'])
    while new_game:
        num_clicks = 0 #相比上次划动后点击新比赛的次数
        num_duplicates = 0 #相比上次划动后重复比赛的数量
        ImageView_list = driver.find_elements(AppiumBy.CLASS_NAME, value="android.widget.ImageView") #未购买完赛比赛
        View_list = driver.find_elements(AppiumBy.CLASS_NAME, value="android.view.View") #其余所有比赛   
        
        for unbought_match in ImageView_list:
            if num_clicks < 4:
                #判断比赛状态
                status = ''
                goal_distribution = [] #存储进球数概率分布，判断样本大小
                if unbought_match.get_attribute('text').__contains__('已购'):
                    status = '未开赛'
                elif unbought_match.get_attribute('text').__contains__('进行中'):
                    status = '进行中'
                elif unbought_match.get_attribute('text').__contains__('完赛'):
                    status = '已完赛'
                    
                if status != '':
                    #获取比赛基本信息
                    info = unbought_match.get_attribute('text')
                    if info.split('\n')[1].__contains__('竞彩'): #[0]:开球时间 [1]:竞彩编号 [2]:联赛名称 [3]:比赛状态 [4]:主客队及比分
                        jingcai = '是'
                        date = info.split('\n')[0]
                        code = info.split('\n')[1]
                        league = info.split('\n')[2]
                        game = info.split('\n')[4]
                        #print(date, code, league, status, game)
                    else: #[0]:开球时间 [1]:联赛名称 [2]:比赛状态 [3]:主客队及比分
                        jingcai = ''
                        date = info.split('\n')[0]
                        league = info.split('\n')[1]
                        game = info.split('\n')[3]
                        #print(date, league, status, game)
                    #按联赛、时间筛选后收集数据
                    league_name, collect = clean_leagues(league)
                    if game not in games_list and collect and (start_time <= date <= end_time):
                        if game.__contains__('['):
                            home = game.split(' ')[0].split(']')[1]
                            away = game.split(' ')[2].split('[')[0]
                        else:
                            home = game.split(' ')[0]
                            away = game.split(' ')[2]
                        score = game.split(' ')[1]
                        try:
                            H = score.split(':')[0]
                            A = score.split(':')[1]
                        except:
                            st.error('获取比分失败:'+game)
                            H = A = '0'
                        #清洗球队名称
                        home, away = clean_teams(home, away, league_name)
                        games_list.append(game)
                        unbought_match.click()
                        num_clicks += 1
                        
                        WebDriverWait(driver, 20).until(EC.presence_of_element_located((AppiumBy.CLASS_NAME,'android.view.View')))
                        time.sleep(6) # longest wait

                        Item_list = driver.find_elements(AppiumBy.CLASS_NAME, value="android.view.View")
                        goal_flag = False
                        rate_flag = False
                        #是否有年化收益率
                        try:
                            if Item_list[8].get_attribute('text').__contains__('年化收益'):
                                rate_flag = True
                                annual_rate = Item_list[8].get_attribute('text')
                        except:
                            st.error('获取年化收益率失败:'+game)
                        p_win = p_draw = p_loss = num_hand = comment = p_hand_win = p_hand_draw = p_hand_loss = rate_win = rate_draw = rate_loss = rate_hand_win = rate_hand_loss = ''
                        #判断非竞彩比赛让球方
                        try:
                            if jingcai == '':
                                if rate_flag:
                                    sp_home = float(Item_list[12].get_attribute('text').split('sp:')[1])
                                    sp_away = float(Item_list[14].get_attribute('text').split('sp:')[1])
                                else:
                                    sp_home = float(Item_list[11].get_attribute('text').split('sp:')[1])
                                    sp_away = float(Item_list[13].get_attribute('text').split('sp:')[1])
                                #print('主胜概率',sp_home,'客胜概率',sp_away)
                                if sp_home < sp_away:
                                    comment = '-'
                                elif sp_home > sp_away:
                                    comment = '+'
                                else:
                                    comment = 'NA'
                        except:
                            st.error('判断让球方失败:'+game)                        
                                
                        for item in Item_list:
                            info = item.get_attribute('text')
                            #获取胜平负概率
                            if info.__contains__('主胜'):
                                p_win = info
                            elif info.__contains__('平局'):
                                p_draw = info
                            elif info.__contains__('主负'):
                                p_loss = info
                            #获取竞彩让球方及让球胜平负
                            elif jingcai == '是' and info.startswith('主让客') and comment == '':
                                comment = '-'
                            elif jingcai == '是' and info.startswith('主受让') and comment == '':
                                comment = '+'                            
                            elif info.startswith('（') and info.endswith('）'):
                                num_hand = info.split(' ')[1]
                                #注释深盘
                                if num_hand != '-1' and num_hand != '+1':
                                    comment = num_hand
                            elif info.__contains__('让胜'):
                                p_hand_win = info
                            elif info.__contains__('让平'):
                                p_hand_draw = info
                            elif info.__contains__('让负'):
                                p_hand_loss = info
                            #进球数最小概率
                            elif info == '进球数':
                                goal_flag = True
                            if goal_flag and info.split('\n')[0].endswith('%'):
                                goal_distribution.append(info.split('\n')[0])
                        #收录年化收益率
                        if rate_flag and (comment.__contains__('-') or jingcai == '是'):
                            if annual_rate.startswith('(主:'):
                                rate_win = annual_rate.split(':')[1].split(')')[0]
                            elif annual_rate.startswith('(平:'):
                                rate_draw = annual_rate.split(':')[1].split(')')[0]
                            elif annual_rate.startswith('(客:'):
                                rate_loss = annual_rate.split(':')[1].split(')')[0]
                            elif annual_rate.startswith('(让球主:'):
                                rate_hand_win = annual_rate.split(':')[1].split(')')[0]
                            elif annual_rate.startswith('(让球客:'):
                                rate_hand_loss = annual_rate.split(':')[1].split(')')[0]
                        
                        #print(p_win, p_draw, p_loss, p_hand_win, p_hand_draw, p_hand_loss)
                        goals_list = list(map(pct_to_float, goal_distribution))
                        goals_list = [x for x in goals_list if x > 0]
                        try:
                            if (0 < min(goals_list) <= 0.1):
                                small_sample = False
                                print('大样本', min(goals_list))
                            else:
                                small_sample = True
                                print('小样本', min(goals_list))
                        except:
                            small_sample = True
                            st.error('无法确定进球概率最小值:'+game)
                            
                        #【拖动至底部】
                        actions = ActionChains(driver)
                        actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
                        actions.w3c_actions.pointer_action.move_to_location(600, 1261)
                        actions.w3c_actions.pointer_action.pointer_down()
                        actions.w3c_actions.pointer_action.move_to_location(600, 550)
                        actions.w3c_actions.pointer_action.release()
                        actions.perform()
                        
                        #获取比分
                        labels = driver.find_elements(AppiumBy.CLASS_NAME, value="android.widget.ImageView")
                        num_item = len(labels)
                        try:
                            score0 = labels[num_item-4].get_attribute('bounds')
                            score1 = labels[num_item-3].get_attribute('bounds')
                            score2 = labels[num_item-2].get_attribute('bounds')
                            score3 = labels[num_item-1].get_attribute('bounds')
                            scoreline = decode_scoreline([score0, score1, score2, score3])
                        except:
                            st.error('获取比分失败:'+game)
                            scoreline = ''
                        
                        #写入数据表
                        if not small_sample:
                            df = df.append({'开球时间':date,'算法':algo_name,'联赛':league_name,'比赛':home+H+'-'+A+away,
                                            '胜':strip_parent(p_win),'平':strip_parent(p_draw),'负':strip_parent(p_loss),'H':int(H),'A':int(A),
                                            '让胜':strip_parent(p_hand_win),'让平':strip_parent(p_hand_draw),'让负':strip_parent(p_hand_loss),
                                            '注释':comment,'比分':scoreline,'竞彩':jingcai,'批注胜':rate_win,'批注平':rate_draw,'批注负':rate_loss,
                                            '批注让胜':rate_hand_win,'批注让负':rate_hand_loss}, ignore_index=True)
                        back_1 = driver.find_element(by=AppiumBy.XPATH, value="/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.Button")
                        back_1.click()
                        time.sleep(2)
                    else:
                        num_duplicates += 1
                    #判断所处时间位置
                    if start_time >= date:
                        reach_lb = True
                    if date >= end_time:
                        reach_ub = True
                    if date >= prev_date:
                        increase = True
                    else:
                        increase = False
                    prev_date = date
            else:
                pass
            
        for match in View_list:
            if num_clicks < 4:
                #判断比赛状态
                status = ''
                goal_distribution = [] #存储进球数概率分布，判断样本大小
                if match.get_attribute('text').__contains__('已购'):
                    status = '未开赛'
                elif match.get_attribute('text').__contains__('进行中'):
                    status = '进行中'
                elif match.get_attribute('text').__contains__('完赛'):
                    status = '已完赛'
                    
                if status != '':
                    #获取比赛基本信息
                    info = match.get_attribute('text')
                    if info.split('\n')[1].__contains__('竞彩'): #[0]:开球时间 [1]:竞彩编号 [2]:联赛名称 [3]:比赛状态 [4]:主客队及比分
                        jingcai = '是'
                        date = info.split('\n')[0]
                        code = info.split('\n')[1]
                        league = info.split('\n')[2]
                        game = info.split('\n')[4]
                        #print(date, code, league, status, game)
                    else: #[0]:开球时间 [1]:联赛名称 [2]:比赛状态 [3]:主客队及比分
                        jingcai = ''
                        date = info.split('\n')[0]
                        league = info.split('\n')[1]
                        game = info.split('\n')[3]
                        #print(date, league, status, game)
                    #按联赛、时间筛选后收集数据
                    league_name, collect = clean_leagues(league)
                    if game not in games_list and collect and (start_time <= date <= end_time):
                        if game.__contains__('['):
                            home = game.split(' ')[0].split(']')[1]
                            away = game.split(' ')[2].split('[')[0]
                        else:
                            home = game.split(' ')[0]
                            away = game.split(' ')[2]
                        #清洗球队名称
                        home, away = clean_teams(home, away, league_name)
                        games_list.append(game)
                        match.click()
                        num_clicks += 1
                        
                        WebDriverWait(driver, 20).until(EC.presence_of_element_located((AppiumBy.CLASS_NAME,'android.view.View')))
                        time.sleep(6) # longest wait

                        Item_list = driver.find_elements(AppiumBy.CLASS_NAME, value="android.view.View")
                        goal_flag = False
                        rate_flag = False
                        #是否有年化收益率
                        try:
                            if Item_list[8].get_attribute('text').__contains__('年化收益'):
                                rate_flag = True
                                annual_rate = Item_list[8].get_attribute('text')
                        except:
                            st.error('获取年化收益率失败:'+game)
                        p_win = p_draw = p_loss = num_hand = comment = p_hand_win = p_hand_draw = p_hand_loss = rate_win = rate_draw = rate_loss = rate_hand_win = rate_hand_loss = ''
                        #判断非竞彩比赛让球方
                        try:
                            if jingcai == '':
                                if rate_flag:
                                    sp_home = float(Item_list[12].get_attribute('text').split('sp:')[1])
                                    sp_away = float(Item_list[14].get_attribute('text').split('sp:')[1])
                                else:
                                    sp_home = float(Item_list[11].get_attribute('text').split('sp:')[1])
                                    sp_away = float(Item_list[13].get_attribute('text').split('sp:')[1])
                                #print('主胜概率',sp_home,'客胜概率',sp_away)
                                if sp_home < sp_away:
                                    comment = '-'
                                elif sp_home > sp_away:
                                    comment = '+'
                                else:
                                    comment = 'NA'
                        except:
                            st.error('判断让球方失败:'+game)
                                
                        for item in Item_list:
                            info = item.get_attribute('text')
                            #获取胜平负概率
                            if info.__contains__('主胜'):
                                p_win = info
                            elif info.__contains__('平局'):
                                p_draw = info
                            elif info.__contains__('主负'):
                                p_loss = info                                
                            #获取竞彩让球方及让球胜平负
                            elif jingcai == '是' and info.startswith('主让客') and comment == '':
                                comment = '-'
                            elif jingcai == '是' and info.startswith('主受让') and comment == '':
                                comment = '+'                            
                            elif info.startswith('（') and info.endswith('）'):
                                num_hand = info.split(' ')[1]
                                #注释深盘
                                if num_hand != '-1' and num_hand != '+1':
                                    comment = num_hand
                            elif info.__contains__('让胜'):
                                p_hand_win = info
                            elif info.__contains__('让平'):
                                p_hand_draw = info
                            elif info.__contains__('让负'):
                                p_hand_loss = info
                            #进球数最小概率
                            elif info == '进球数':
                                goal_flag = True
                            if goal_flag and info.split('\n')[0].endswith('%'):
                                goal_distribution.append(info.split('\n')[0])
                        #收录年化收益率
                        if rate_flag and (comment.__contains__('-') or jingcai == '是'):
                            if annual_rate.startswith('(主:'):
                                rate_win = annual_rate.split(':')[1].split(')')[0]
                            elif annual_rate.startswith('(平:'):
                                rate_draw = annual_rate.split(':')[1].split(')')[0]
                            elif annual_rate.startswith('(客:'):
                                rate_loss = annual_rate.split(':')[1].split(')')[0]
                            elif annual_rate.startswith('(让球主:'):
                                rate_hand_win = annual_rate.split(':')[1].split(')')[0]
                            elif annual_rate.startswith('(让球客:'):
                                rate_hand_loss = annual_rate.split(':')[1].split(')')[0]                                
                        
                        #print(p_win, p_draw, p_loss, p_hand_win, p_hand_draw, p_hand_loss)
                        goals_list = list(map(pct_to_float, goal_distribution))
                        goals_list = [x for x in goals_list if x > 0]
                        try:
                            if (0 < min(goals_list) <= 0.1):
                                small_sample = False
                                print('大样本', min(goals_list))
                            else:
                                small_sample = True
                                print('小样本', min(goals_list))
                        except:
                            small_sample = True
                            st.error('无法确定进球概率最小值:'+game)
                            
                        #【拖动至底部】
                        actions = ActionChains(driver)
                        actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
                        actions.w3c_actions.pointer_action.move_to_location(600, 1261)
                        actions.w3c_actions.pointer_action.pointer_down()
                        actions.w3c_actions.pointer_action.move_to_location(600, 550)
                        actions.w3c_actions.pointer_action.release()
                        actions.perform()
                        
                        #获取比分
                        labels = driver.find_elements(AppiumBy.CLASS_NAME, value="android.widget.ImageView")
                        num_item = len(labels)
                        try:
                            score0 = labels[num_item-4].get_attribute('bounds')
                            score1 = labels[num_item-3].get_attribute('bounds')
                            score2 = labels[num_item-2].get_attribute('bounds')
                            score3 = labels[num_item-1].get_attribute('bounds')
                            scoreline = decode_scoreline([score0, score1, score2, score3])
                        except:
                            st.error('获取比分失败:'+game)
                            scoreline = ''
                        
                        #写入数据表
                        if not small_sample:
                            df = df.append({'开球时间':date,'算法':algo_name,'联赛':league_name,'比赛':home+'-'+away,
                                            '胜':strip_parent(p_win),'平':strip_parent(p_draw),'负':strip_parent(p_loss),
                                            '让胜':strip_parent(p_hand_win),'让平':strip_parent(p_hand_draw),'让负':strip_parent(p_hand_loss),
                                            '注释':comment,'比分':scoreline,'竞彩':jingcai,'批注胜':rate_win,'批注平':rate_draw,'批注负':rate_loss,
                                            '批注让胜':rate_hand_win,'批注让负':rate_hand_loss}, ignore_index=True)
                        back_1 = driver.find_element(by=AppiumBy.XPATH, value="/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.widget.Button")
                        back_1.click()
                        time.sleep(2)
                    else:
                        num_duplicates += 1
                    #判断所处时间位置
                    if start_time >= date:
                        reach_lb = True
                    if date >= end_time:
                        reach_ub = True
                    if date >= prev_date:
                        increase = True
                    else:
                        increase = False
                    prev_date = date
            else:
                pass        
        
        #结束条件
        if reach_lb and reach_ub and not increase: #当起止时间段都达到，且遇到更早比赛时结束抓取
            new_game = False
        elif reach_lb and reach_ub and increase and num_duplicates == 10: #当起止时间段都达到，但开始时间在最底部时，判断达到底部后结束抓取
            new_game = False
        
        #【划动4场比赛】
        actions = ActionChains(driver)
        actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
        actions.w3c_actions.pointer_action.move_to_location(512, 1242)
        actions.w3c_actions.pointer_action.pointer_down()
        actions.w3c_actions.pointer_action.move_to_location(512, 986)#486
        actions.w3c_actions.pointer_action.release()
        actions.perform()
    
    back = driver.find_element(by=AppiumBy.XPATH, value="/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[1]/android.widget.Button")
    back.click()
    return df

def pct_to_float(pct):
    return float(pct.strip('%'))/100

def strip_parent(string):
    return pct_to_float(string.split('(')[1].split(')')[0])

#用于读取onedrive数据库
def create_onedrive_directdownload(onedrive_link):
    data_bytes64 = base64.b64encode(bytes(onedrive_link, 'utf-8'))
    data_bytes64_String = data_bytes64.decode('utf-8').replace('/','_').replace('+','-').rstrip("=")
    resultUrl = f"https://api.onedrive.com/v1.0/shares/u!{data_bytes64_String}/root/content"
    return resultUrl

def read_file(data):
    df = pd.read_excel(data, sheet_name = 1, converters = {'盘口': str, '竞彩': str, '比分': str})
    df['盘口数字'] = df['盘口'].astype(float)
    df['注释'] = df['注释'].fillna('')
    df['批注胜'] = df['批注胜'].fillna('')
    df['批注平'] = df['批注平'].fillna('')
    df['批注负'] = df['批注负'].fillna('')
    df['批注让胜'] = df['批注让胜'].fillna('')
    df['批注让平'] = df['批注让平'].fillna('')
    df['批注让负'] = df['批注让负'].fillna('')
    return df
    
if __name__ == "__main__":
    main()
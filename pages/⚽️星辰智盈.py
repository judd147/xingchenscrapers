# -*- coding: utf-8 -*-
"""
Created on 12/24/2023
Last Edit 12/26/2023
@author: Liyao Zhang

星辰智盈数据自动获取系统 with Streamlit
"""

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import time
import pandas as pd
import streamlit as st
from stqdm import stqdm
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def main():
    st.set_page_config(
    page_title="星辰数据获取",
    )
    st.title("星辰智盈数据自动获取系统")

    # Mode & Time
    # 全选
    # 早盘-早场 适合前一天23:00左右运行，时间默认为前一天21:00 - 比赛日7:00
    # 早盘-晚场 适合比赛日4:00左右运行，时间默认为比赛日7:00-20:00
    # 临场-普通
    # 临场-预约 用户指定比赛和盘口，根据开球时间自动抓取数据并回测，将结果发送邮箱

    today = datetime.today().replace(minute=0)
    today_modified = today.replace(minute=0, second=0, microsecond=0)
    get_qbl = get_zsxt = get_gplj = get_sqnl = get_lsqt = False
    with st.form("user_input"):
        mode = st.radio('选择模式', options=('全选', '早盘', '临场'), help='全选包括早盘临场5大算法，早盘算法指球伯乐及指数形态，临场算法指公平量价、赛前能量和联赛球探')
        if mode == '全选':
            get_qbl = get_zsxt = get_gplj = get_sqnl = get_lsqt = True
        elif mode == '早盘':
            get_qbl = get_zsxt = True
        elif mode == '临场':
            get_gplj = get_sqnl = get_lsqt = True
        col1, col2 = st.columns(2)
        with col1:
            start_time = st.slider("开始时间", value=today_modified,
                    min_value=today_modified - timedelta(hours=32),
                    max_value=today_modified + timedelta(hours=8),
                    step=timedelta(minutes=30),
                    format="MM/DD - HH:mm").strftime('%m-%d %H:%M')
        with col2:
            end_time = st.slider("结束时间", value=today_modified,
                    min_value=today_modified - timedelta(hours=24),
                    max_value=today_modified + timedelta(hours=12),
                    step=timedelta(minutes=30),
                    format="MM/DD - HH:mm").strftime('%m-%d %H:%M')
            headless = st.toggle('Headless', value=False, help="运行时隐藏浏览器")
        submitted = st.form_submit_button("运行")
    
    if submitted:
        st.write("已选择时间段：{}-{}".format(start_time, end_time))
        driver = init_service(headless)
        login(driver)
        time.sleep(5)
        algos = driver.find_elements(By.CLASS_NAME, 'title')
        st.success('初始化完成！')

        # Iterate through each algo
        for algo in algos:
            text = algo.text
            if text == '球伯乐' and get_qbl:
                algo.click()
                with st.spinner("正在获取球伯乐数据..."):
                    df_qbl = scrape(driver, '', start_time, end_time)
            else:
                pass

        for algo in algos:
            text = algo.text
            if text == '指数形态' and get_zsxt:
                algo.click()
                with st.spinner("正在获取指数形态数据..."):
                    df_zsxt = scrape(driver, text, start_time, end_time)
            else:
                pass
            
        for algo in algos:
            text = algo.text
            if text == '公平量价' and get_gplj:
                algo.click()
                with st.spinner("正在获取公平量价数据..."):
                    df_gplj = scrape(driver, text, start_time, end_time)
            else:
                pass
            
        for algo in algos:
            text = algo.text
            if text == '赛前能量' and get_sqnl:
                algo.click()
                with st.spinner("正在获取赛前能量数据..."):
                    df_sqnl = scrape(driver, text, start_time, end_time)
            else:
                pass
            
        for algo in algos:
            text = algo.text
            if text == '联赛球探' and get_lsqt:
                algo.click()
                with st.spinner("正在获取联赛球探数据..."):
                    df_lsqt = scrape(driver, text, start_time, end_time)
            else:
                pass
            
        # Combine data
        if mode == '全选':                     
            df_final = pd.concat([df_qbl, df_zsxt, df_gplj, df_sqnl, df_lsqt])
        elif mode == '早盘':
            df_final = pd.concat([df_qbl, df_zsxt])
        elif mode == '临场':
            with st.spinner("合并数据中..."):
                onedrive_link = 'https://1drv.ms/x/s!Ag9ZvloaJitBjy8YIdiLf5Wkr4O6?e=cwBjTO'
                url = create_onedrive_directdownload(onedrive_link)
                df = read_file(url)
                min_time = min(start_time_gplj, start_time_sqnl, start_time_lsqt) #判断最早时间
                df_selected = df[(df['开球时间']>=min_time.strftime('%m-%d %H:%M'))&(df['年']==2023)] #每年改一次
                data_selected = pd.concat([df_gplj, df_sqnl, df_lsqt])
                df_final = pd.concat([df_selected, data_selected])
            st.success('数据合并成功！')

        # 下载/上传数据库
        # 方案一：所有读写均通过数据库，管理员定期负责下载最新数据并同步给excel
        # 方案二：读写直接通过调用onedrive，可检查数据重复
        file_name = "星辰数据_{mode}{date}.xlsx".format(mode=mode, date=today.strftime('%m-%d'))
        df_final.to_excel('/Users/zhangliyao/Desktop//'+file_name, index=False)

        st.success('数据获取成功！')
  
def clean_leagues(league_name):
    '''返回清洗后的联赛名称及是否属于收录的联赛'''
    league_dict = {'美职':'美职联','日职':'日职联','冠军杯':'欧冠','智利甲':'智甲','欧霸杯':'欧联','南俱杯':'南球杯','世美预':'南美预选'}

    league_list = ['美职联','日职联','德乙','德甲','西甲','英超','欧冠','阿甲','欧联','法甲','巴甲','意甲','欧国联',
                  '墨超','葡超','荷甲','英冠','解放者杯','欧预赛','南球杯','瑞典超','挪超','世界杯','美洲杯','亚洲预选',
                  '西乙','比甲','智甲','南美预选','世预赛','北美预选','欧洲杯','欧协联']
    
    for key, value in league_dict.items():
        league_name = league_name.replace(key, value)
        
    if league_name in league_list:
        return league_name, True
    else:
        return league_name, False
    
def clean_teams(home, away, league_name):
    '''
    返回清洗后的球队名称
    Last Edit: 11/30/2023
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
                  '欧联':{'谢里夫':'蒂拉斯波尔警长','LASK林茨':'林茨','帕纳辛纳科斯':'帕纳辛奈科斯','利马索尔阿里斯':'阿里斯利马索尔'},
                  '欧协联':{'第聂伯罗特警':'SK第聂伯罗','波兹南':'波兹南莱赫','比尔舒华夏普尔':'贝尔谢巴工人','萨尔格里斯':'扎尔吉里斯',
                            '布加勒斯特星队':'布加勒斯特星','列加斯':'里加足球学校','伊斯坦布':'伊斯坦布尔','利马索尔阿波罗':'阿波罗利马索尔',
                            '奥林比查':'卢布尔雅那奥林匹亚','泰拿华斯巴达':'特纳瓦斯巴达','萨连斯基':'莫斯塔尔兹林斯基','卢甘斯克黎明':'索尔亚','卡拉卡斯维克':'克拉克斯维克',
                            '贝雷达比历克':'布列达布利克'},
                  '德乙':{'不伦瑞克':'布伦瑞克'},
                  '英冠':{'加的夫城':'卡迪夫城','布里斯托城':'布里斯托尔城','西布罗姆维奇':'西布朗'},
                  '西乙':{'格拉纳达GF':'格拉纳达','米兰迪斯':'米兰德斯','安道尔CF':'FC安道尔','阿尔巴切特':'阿尔瓦塞特','特內里费':'特内里费','艾科坎':'阿尔科孔',
                            '费路尔':'费罗尔竞技', '艾尔德斯':'埃登斯'},
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
                  }
    
    for league_key, league_values in teams_dict.items():
        for key, value in league_values.items():
            if home == key:
                home = home.replace(key, value)
            if away == key:
                away = away.replace(key, value)
    return home, away

def pct_to_float(pct):
    return float(pct.strip('%'))/100

def strip_parent(string):
    new_string = string.split('(')[1].split(')')[0]
    if not new_string.startswith('-'):
        new_string = '+' + new_string
    return new_string

def init_service(headless):
    driver_path = '/Users/zhangliyao/Downloads/chromedriver' # use env later

    # Mobile Device
    mobile_emulation = {"deviceName": "iPhone 12 Pro"}

    # Initialize Chrome Driver
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--enable-automation')
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    driver = webdriver.Chrome(service=Service(executable_path=driver_path), options=chrome_options)

    # Open web page
    driver.get("https://xczy.sp1x2.net/xczy-web/") # use env later
    driver.fullscreen_window()
    return driver

def login(driver):
    # Input the phone number
    phone_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
        (By.CLASS_NAME, 'van-field__control'))).send_keys('18566258659') # use env later

    # Input the password
    password_input = driver.find_elements(By.CLASS_NAME, 'van-field__control')[1]
    password_input.send_keys('990311') # use env later

    # Login button
    login_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, 'login-btn')))
    login_button.click()
    
def unlock(driver):
    '''Unlock matches'''
    locked = True
    while locked:
        try:
            driver.find_element(By.CSS_SELECTOR, 'p[class="b-enable"][data-v-308224e0]')
            locked = False
        except:
            unlock_button = driver.find_element(By.CSS_SELECTOR, 'p[class=""][data-v-308224e0]')
            unlock_button.click()
        time.sleep(2)

def back(driver):
    back_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, 'img[class="back"][data-v-5c3272b5]')))
    back_button.click()
    
def get_matches(driver, algo_name, start_time, end_time):
    '''Collect and parse data'''
    df = pd.DataFrame(columns=['开球时间','算法','联赛','比赛','胜','平','负','H','A','让胜','让平','让负','盘口',
                               '注释','比分','进球数','竞彩'])
    match_list = driver.find_element(By.CLASS_NAME, 'matchs-ul')
    matches = match_list.find_elements(By.TAG_NAME, 'li')
    for match in stqdm(matches, algo_name):
        match_info = match.text
        match_context = match_info.split('\n')[0]
        game = match_info.split('\n')[1]
        date = match_context.split(' ')[0] + ' ' + match_context.split(' ')[1]
        league = match_context.split(' ')[2].replace('完赛', '')
        # proceed if league is target
        league_name, isTarget = clean_leagues(league)
        if isTarget and (start_time <= date <= end_time):
            # team names
            if game.__contains__('['):
                home = game.split(' ')[1]
                away = game.split(' ')[3]
            else:
                home = game.split(' ')[0]
                away = game.split(' ')[2]
            home, away = clean_teams(home, away, league_name)
            # scoreline
            if game.__contains__('VS'):
                H = ''
                A = ''
            else:
                part1 = game.split(':')[0]
                part2 = game.split(':')[1]
                H = part1.split(' ')[-1]
                A = part2.split(' ')[0]

            # Match detail
            if match_context.split(' ')[2].__contains__('完赛'):
                show_button = match.find_element(By.CLASS_NAME, 'show.show-end')
            else:
                show_button = match.find_element(By.CLASS_NAME, 'show')
            show_button.click()

            time.sleep(2)

            # jingcai
            detail_context = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div[class="time"][data-v-039f5c22]')))
            if detail_context.text.__contains__('竞彩'):
                jingcai = '是'
            else:
                jingcai = ''

            # probabilities
            prob1 = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                (By.XPATH, '/html/body/div[1]/div/div[1]/div/div[4]/div/div[2]/div[2]/div/div[4]/div/div[2]/div[1]/div/div/div[1]'))).text
            p_win = pct_to_float(prob1.split('\n')[0].split('主胜')[1])
            sp_home = float(prob1.split('\n')[1].replace('sp', ''))

            prob2 = driver.find_element(By.XPATH, '/html/body/div[1]/div/div[1]/div/div[4]/div/div[2]/div[2]/div/div[4]/div/div[2]/div[1]/div/div/div[2]').text
            p_draw = pct_to_float(prob2.split('\n')[0].split('平局')[1])

            prob3 = driver.find_element(By.XPATH, '/html/body/div[1]/div/div[1]/div/div[4]/div/div[2]/div[2]/div/div[4]/div/div[2]/div[1]/div/div/div[3]').text
            p_loss = pct_to_float(prob3.split('\n')[0].split('客胜')[1])
            sp_away = float(prob3.split('\n')[1].replace('sp', ''))

            prob4 = driver.find_element(By.XPATH, '/html/body/div[1]/div/div[1]/div/div[4]/div/div[2]/div[2]/div/div[4]/div/div[2]/div[2]/div/div/div[1]').text
            p_hand_win = pct_to_float(prob4.split('\n')[0].split('让胜')[1])

            prob5 = driver.find_element(By.XPATH, '/html/body/div[1]/div/div[1]/div/div[4]/div/div[2]/div[2]/div/div[4]/div/div[2]/div[2]/div/div/div[2]').text
            p_hand_draw = pct_to_float(prob5.split('\n')[0].split('让平')[1])

            prob6 = driver.find_element(By.XPATH, '/html/body/div[1]/div/div[1]/div/div[4]/div/div[2]/div[2]/div/div[4]/div/div[2]/div[2]/div/div/div[3]').text
            p_hand_loss = pct_to_float(prob6.split('\n')[0].split('让负')[1])

            # handicap
            hand_info = driver.find_element(By.CSS_SELECTOR, 'span[class="h-d"][data-v-039f5c22]').text
            num_hand = strip_parent(hand_info).replace('1', '')

            if jingcai == '是':
                comment = num_hand
            else:
                if sp_home < sp_away:
                    comment = '-'
                elif sp_home > sp_away:
                    comment = '+'
                else:
                    comment = 'NA'

            # sample size
            bar_list = []
            bars = driver.find_elements(By.CSS_SELECTOR, 'span[class="d-s-per"][data-v-039f5c22]')
            for bar in bars:
                bar_list.append(bar.text)
            goals_list = list(map(pct_to_float, bar_list))
            goals_list = [x for x in goals_list if x > 0]
            
            if (min(goals_list) <= 0.1):
                small_sample = False
                #print('大样本', min(goals_list))
            else:
                small_sample = True
                #print('小样本', min(goals_list))

            # recommended scoreline
            top_score = driver.find_elements(By.CSS_SELECTOR, 'div[class="p-b-d-s first-s"][data-v-039f5c22]')[2].text.split('\n')[0]
            sec_score = driver.find_elements(By.CSS_SELECTOR, 'div[class="p-b-d-s second-s"][data-v-039f5c22]')[2].text.split('\n')[0]
            scoreline = top_score.replace(':', '-') + ' ' + sec_score.replace(':', '-')
            
            # append to dataframe
            if not small_sample:
                row_data = {'开球时间':date, '算法':algo_name, '联赛':league_name, '比赛':home+'-'+away,
                            '胜':p_win, '平':p_draw, '负':p_loss, '让胜':p_hand_win,'让平':p_hand_draw,
                            '让负':p_hand_loss, '注释':comment, '比分':scoreline, '竞彩':jingcai}
                df = df.append(row_data, ignore_index=True)

            back_button = driver.find_element(By.CSS_SELECTOR, 'img[class="back"][data-v-039f5c22]')
            back_button.click()
    return df

def scrape(driver, algo_name, start_time, end_time):
    time.sleep(2)
    unlock(driver)
    df = get_matches(driver, algo_name, start_time, end_time)
    back(driver)
    return df

def create_onedrive_directdownload(onedrive_link):
    '''Create onedrive url'''
    data_bytes64 = base64.b64encode(bytes(onedrive_link, 'utf-8'))
    data_bytes64_String = data_bytes64.decode('utf-8').replace('/','_').replace('+','-').rstrip("=")
    resultUrl = f"https://api.onedrive.com/v1.0/shares/u!{data_bytes64_String}/root/content"
    return resultUrl

def read_file(data):
    '''Read excel from onedrive'''
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
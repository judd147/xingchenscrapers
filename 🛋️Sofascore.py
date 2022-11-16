# -*- coding: utf-8 -*-
"""
Created on Wed Nov 16 11:07:58 2022
Last Edit 11/16/2022
@author: zhangliyao
Sofascore scraper with Streamlit
"""

import io
import time
import base64
import pandas as pd
import streamlit as st
from PIL import Image
from datetime import datetime
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException

def main():
    st.set_page_config(
    page_title="Sofascore数据获取",
    page_icon=Image.open('pages/sofascore.jpg')
    #initial_sidebar_state="expanded"
    )
    st.title("Sofascore比分盘口自动获取系统")
    
    with st.form("user_input"):
        source = st.radio("选择设备", ["PC","Company"])
        mode = st.radio('运行模式', ['界面起止点测试','数据获取'])
        if source == 'PC':
            driver_path = r'D:\edgedriver_win64\msedgedriver.exe'
        elif source == 'Company':
            driver_path = r'D:\EdgeDriver\msedgedriver.exe'
        date = st.date_input("选择日期")
        scroll_startpoint = st.number_input('初始位置', min_value=0, max_value=5000, value=0)
        scroll_endpoint = st.number_input('结束位置', min_value=750, max_value=9500, value=3200, step=350)
    
        submitted = st.form_submit_button("运行")
        
    if submitted:
        today = datetime.today()
        today_month = today.strftime('%m')
        select_month = date.strftime('%m')
        select_date = date.strftime('%d')

        driver = webdriver.Edge(service=Service(executable_path=driver_path))
        driver.implicitly_wait(10)
        driver.get("https://www.sofascore.com/")
        
        #显示赔率
        with st.spinner('网页加载中...'):
            showodds = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME,'slider')))
            showodds.click()
        st.success('初始化完成！')
     
        #回到上个月
        if int(select_month)+1 == int(today_month):
            driver.find_element(By.XPATH,'/html/body/div[1]/div/main/div/div[2]/div[1]/div[1]/div[1]/div[1]/button[1]/button').click() #返回上个月
        #切换日期
        switch_date(driver, select_date)
        time.sleep(5)
        
        if mode == '界面起止点测试':
            #初始位置
            if scroll_startpoint != 0:
                driver.refresh() #刷新页面
                ActionChains(driver).scroll_by_amount(0, scroll_startpoint).perform()
                st.info('请查看是否合适，15秒后进行结束位置测试')
                time.sleep(15)
            #结束位置
            driver.refresh() #刷新页面
            ActionChains(driver).scroll_by_amount(0, scroll_endpoint).perform()
            st.info('请查看是否合适，15秒后自动重置')
            time.sleep(15)
            
        elif mode == '数据获取':
            with st.spinner('数据获取中...'):
                df_result = scrape_matches(driver, scroll_startpoint, scroll_endpoint)
                sofascore_result = df_result.drop_duplicates(subset=['主队','客队'])
                sofascore_result = sofascore_result.reset_index()
                del sofascore_result['index']
            st.success('数据获取完成！')
            
            with st.spinner('数据合并中...'):
                onedrive_link = 'https://1drv.ms/x/s!Ag9ZvloaJitBjy_eATdsL7-B6G0m?e=hk8yWv'
                url = create_onedrive_directdownload(onedrive_link)
                df = read_file(url)

                df_selected = df[df['开球时间'].str.startswith(date.strftime('%m-%d'))]
                df_selected = df_selected.reset_index()
                del df_selected['index']
            
                for i in range(len(sofascore_result)):
                    home = sofascore_result.iloc[i, 0]
                    away = sofascore_result.iloc[i, 1]
                    H = sofascore_result.iloc[i, 2]
                    A = sofascore_result.iloc[i, 3]
                    home_name, away_name = map_teams(home, away)
                    sofascore_result.at[i, '主队'] = home_name
                    sofascore_result.at[i, '客队'] = away_name
                    sofascore_result.at[i, '比赛'] = home_name+'-'+away_name
                    sofascore_result.at[i, '赛果'] = home_name+str(H)+'-'+str(A)+away_name
                    
                for k in range(len(df_selected)):
                    game = df_selected.iloc[k, 3]
                    for i in range(len(sofascore_result)):
                        H = sofascore_result.iloc[i, 2]
                        A = sofascore_result.iloc[i, 3]
                        handicap = sofascore_result.iloc[i, 4]
                        sf_game = sofascore_result.iloc[i, 5]
                        sf_result = sofascore_result.iloc[i, 6]
                        if game == sf_game or game == sf_result:
                            df_selected.at[k, '比赛'] = sf_result
                            df_selected.at[k, '盘口'] = handicap
                            df_selected.at[k, 'H'] = H
                            df_selected.at[k, 'A'] = A
            st.success('数据合并完成！')
            
            #下载数据
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_selected.to_excel(writer, index=False)
                writer.save()
                st.download_button(
                    label="下载数据",
                    data=buffer,
                    file_name="Sofascore_"+date.strftime('%m-%d')+".xlsx",
                    mime="application/vnd.ms-excel"
                )
            
#球队字典
def map_teams(home, away):
    '''
    返回清洗后的球队名称
    '''
    teams_dict = {'日乙':{'群马温泉':'群马草津温泉','金泽塞维根':'金泽','琉球FC':'FC琉球'},
                  #✔
                  '美职联':{'FC Cincinnati':'辛辛那提','Vancouver Whitecaps':'温哥华白浪','Sporting Kansas City':'堪萨斯城体育','Portland Timbers':'波特兰伐木者',
                            'Los Angeles FC':'洛杉矶FC','Austin FC':'奥斯汀FC','Philadelphia Union':'费城联合','New York City FC':'纽约城',
                            'Atlanta United FC':'亚特兰大联','DC United':'华盛顿联','Orlando City SC':'奥兰多城','LA Galaxy':'洛杉矶银河','Chicago Fire':'芝加哥火焰',
                            'New England Revolution':'新英格兰革命','Columbus Crew':'哥伦布机员','Inter Miami CF':'迈阿密国际','CF Montreal':'蒙特利尔冲击',
                            'New York Red Bulls':'纽约红牛','Toronto FC':'多伦多FC','Nashville SC':'纳什维尔','Colorado Rapids':'科罗拉多急流','Houston Dynamo':'休斯顿迪纳摩',
                            'Seattle Sounders FC':'西雅图海湾人','Real Salt Lake':'皇家盐湖城','Minnesota United FC':'明尼苏达联','FC Dallas':'达拉斯FC',
                            'Charlotte FC':'夏洛特FC','San Jose Earthquakes':'圣何塞地震'},
                  #✔
                  '日职联':{'Sagan Tosu':'鸟栖砂岩','Shimizu S-Pulse':'清水心跳','Nagoya Grampus Eight':'名古屋逆戟鲸','Cerezo Osaka':'大阪樱花','Yokohama F. Marinos':'横滨水手',
                             'FC Tokyo':'东京FC','Kawasaki Frontale':'川崎前锋','Hokkaido Consadole Sapporo':'札幌冈萨多','Jubilo Iwata':'磐田喜悦',
                             'Kyoto Sanga FC':'京都不死鸟','Kashima Antlers':'鹿岛鹿角','Gamba Osaka':'大阪钢巴','Kashiwa Reysol':'柏太阳神','Vissel Kobe':'神户胜利船',
                             'Shonan Bellmare':'湘南海洋','Sanfrecce Hiroshima':'广岛三箭','Urawa Red Diamonds':'浦和红钻','Avispa Fukuoka':'福冈黄蜂',},
                  '阿甲':{'普拉腾斯':'普拉滕斯竞技','泰格雷':'老虎竞技','竞技俱乐部':'竞技','圣塔菲联':'圣菲联','巴拉卡斯中央队':'巴拉卡斯中央',
                               '科隆竞技':'哥伦布竞技','铁路工场':'塔列雷斯','阿尔多西维':'阿尔多希维','科尔多瓦中央SDE':'科尔多瓦中央',
                               '阿根廷独立':'独立','萨尔米安杜':'萨米恩托','飓风队':'飓风','帕特罗纳图':'天主教青年','防御与正义':'国防与司法'},
                  #✔
                  '德甲':{'Werder Bremen':'云达不莱梅','Hertha BSC':'柏林赫塔','Bayern München':'拜仁慕尼黑','1. FSV Mainz 05':'美因茨','VfL Bochum':'波鸿',
                           'RB Leipzig':'RB莱比锡','Bayer 04 Leverkusen':'勒沃库森','VfB Stuttgart':'斯图加特','FC Augsburg':'奥格斯堡',
                           'VfL Wolfsburg':'沃尔夫斯堡','Eintracht Frankfurt':'法兰克福','Borussia Dortmund':'多特蒙德','FC Schalke 04':'沙尔克04',
                           'SC Freiburg':'弗赖堡','1. FC Köln':'科隆','1899 Hoffenheim':'霍芬海姆','1. FC Union Berlin':'柏林联合',"Borussia M'gladbach":'门兴格拉德巴赫',},
                  #✔
                  '西甲':{'Celta Vigo':'塞尔塔','RCD Mallorca':'马略卡','UD Almería':'阿尔梅里亚','Real Valladolid':'巴拉多利德',
                           'Cádiz CF':'加迪斯','Espanyol':'西班牙人','Atlético Madrid':'马德里竞技','Sevilla':'塞维利亚',
                           'Rayo Vallecano':'巴列卡诺','Valencia':'巴伦西亚','Barcelona':'巴塞罗那','Osasuna':'奥萨苏纳',
                           'Real Madrid':'皇家马德里','Girona FC':'赫罗纳','Athletic Club':'毕尔巴鄂竞技','Villarreal':'比利亚雷亚尔',
                           'Real Sociedad':'皇家社会','Real Betis Balompié':'皇家贝蒂斯','Elche CF':'埃尔切','Getafe CF':'赫塔费'},
                  #✔
                  '英超':{'Leicester City':'莱斯特城','Manchester City':'曼城','AFC Bournemouth':'伯恩茅斯','Tottenham Hotspur':'热刺',
                           'Brentford':'布伦特福德','Wolverhampton':'狼队','Brighton & Hove Albion':'布莱顿','Chelsea':'切尔西',
                           'Crystal Palace':'水晶宫','Southampton':'南安普顿','Newcastle United':'纽卡斯尔','Aston Villa':'阿斯顿维拉',
                           'Liverpool':'利物浦','Leeds United':'利兹联','Arsenal':'阿森纳','Nottingham Forest':'诺丁汉森林',
                           'Manchester United':'曼联','West Ham United':'西汉姆联','Fulham':'富勒姆','Everton':'埃弗顿'},
                  #✔
                  '法甲':{'RC Lens':'朗斯','Toulouse':'图卢兹','Paris Saint-Germain':'巴黎圣日尔曼','Troyes':'特鲁瓦',
                           'RC Strasbourg':'斯特拉斯堡','Olympique de Marseille':'马赛','AJ Auxerre':'欧塞尔','AC Ajaccio':'阿雅克肖',
                           'AS Monaco':'摩纳哥','Angers':'昂热','FC Nantes':'南特','Clermont Foot 63':'克莱蒙',
                           'Stade Brestois 29':'布雷斯特','Stade de Reims':'兰斯','Lorient':'洛里昂','OGC Nice':'尼斯',
                           'Olympique Lyonnais':'里昂','Lille OSC':'里尔','Stade Rennais':'雷恩','Montpellier':'蒙彼利埃'},
                  #✔
                  '意甲':{'Napoli':'那不勒斯','Sassuolo':'萨索洛','Lecce':'莱切','Juventus':'尤文图斯','Udinese':'乌迪内斯',
                           'Inter':'国际米兰','Sampdoria':'桑普多利亚','Empoli':'恩波利','Atalanta':'亚特兰大','Cremonese':'克雷莫内塞',
                           'Spezia':'斯佩齐亚','Fiorentina':'佛罗伦萨','Lazio':'拉齐奥','Salernitana':'萨勒尼塔纳','Torino':'都灵',
                           'Milan':'AC米兰','Hellas Verona':'维罗纳','Roma':'罗马','Monza':'蒙扎','Bologna':'博洛尼亚'},
                  #✔
                  '欧冠':{'Viktoria Plzeň':'比尔森胜利','GNK Dinamo Zagreb':'萨格勒布迪纳摩','Celtic':'凯尔特人','Shakhtar Donetsk':'顿涅茨克矿工',
                           'Red Bull Salzburg':'萨尔茨堡红牛','Rangers':'流浪者','FC København':'哥本哈根','Maccabi Haifa':'海法马卡比'},
                  #✔
                  '欧联':{'FC Sheriff Tiraspol':'蒂拉斯波尔警长','FC Zürich':'苏黎世','Fenerbahçe':'费内巴切','AEK Larnaca':'AEK拉纳卡','Dynamo Kyiv':'基辅迪纳摩',
                           'Ludogorets Razgrad':'卢多戈雷茨','HJK':'赫尔辛基','Omonia Nicosia':'奥莫尼亚','FC Midtjylland':'中日德兰','SK Sturm Graz':'格拉茨风暴',
                           'Qarabağ FK':'卡拉巴赫','Olympiacos':'奥林匹亚科斯','Ferencváros TC':'费伦茨瓦罗斯','Trabzonspor':'特拉布宗体育','FK Crvena zvezda':'贝尔格莱德红星'},
                  #✔
                  '欧协联':{'Başakşehir FK':'伊斯坦布尔','Heart of Midlothian':'哈茨','RFS':'里加足球学校','Silkeborg IF':'锡尔克堡','FCSB':'布加勒斯特星',
                            'Lech Poznań':'波兹南莱赫',"Hapoel Be'er Sheva":'贝尔谢巴工人','Austria Wien':'奥地利维也纳','FK Partizan':'贝尔格莱德游击',
                            '1. FC Slovácko':'斯洛瓦科','SC Dnipro-1':'SK第聂伯罗','Apollon Limassol':'阿波罗利马索尔','FC Vaduz':'瓦杜兹',
                            'Sivasspor':'锡瓦斯体育','Shamrock Rovers':'沙姆洛克流浪','CFR Cluj':'克卢日','Slavia Praha':'布拉格斯拉维亚','FC Basel':'巴塞尔',
                            'KF Ballkani':'巴利卡尼','ŠK Slovan Bratislava':'布拉迪斯拉发','Pyunik Yerevan':'埃里温凤凰','FK Žalgiris':'扎尔吉里斯'},
                  #✔
                  '德乙':{'Eintracht Braunschweig':'布伦瑞克','1. FC Magdeburg':'马格德堡','1. FC Heidenheim':'海登海姆','SpVgg Greuther Fürth':'菲尔特',
                           'Arminia Bielefeld':'比勒费尔德','1. FC Kaiserslautern':'凯泽斯劳滕','1. FC Nürnberg':'纽伦堡','Holstein Kiel':'基尔',
                           'Fortuna Düsseldorf':'杜塞尔多夫','SSV Jahn Regensburg':'雷根斯堡','F.C. Hansa Rostock':'罗斯托克','FC St. Pauli':'圣保利',
                           'Darmstadt 98':'达姆施塔特','Hannover 96':'汉诺威96','Karlsruher SC':'卡尔斯鲁厄','SC Paderborn 07':'帕德博恩',
                           'Hamburger SV':'汉堡','SV Sandhausen':'桑德豪森'},
                  #✔
                  '英冠':{'Cardiff City':'卡迪夫城','Bristol City':'布里斯托尔城','West Bromwich Albion':'西布朗','Birmingham City':'伯明翰',
                           'Queens Park Rangers':'女王公园巡游者','Swansea City':'斯旺西','Sheffield United':'谢菲尔德联','Burnley':'伯恩利',
                           'Reading':'雷丁','Rotherham United':'罗瑟汉姆','Coventry City':'考文垂','Blackpool':'布莱克浦','Millwall':'米尔沃尔',
                           'Huddersfield Town':'哈德斯菲尔德','Hull City':'赫尔城','Blackburn Rovers':'布莱克本','Preston North End':'普雷斯顿',
                           'Norwich City':'诺维奇','Stoke City':'斯托克城','Middlesbrough':'米德尔斯堡','Wigan Athletic':'维冈竞技','Watford':'沃特福德',
                           'Luton Town':'卢顿','Sunderland':'桑德兰'},
                  #✔
                  '西乙':{'Granada':'格拉纳达','Mirandés':'米兰德斯','FC Andorra':'FC安道尔','Albacete Balompié':'阿尔瓦塞特','Tenerife':'特内里费',
                           'Real Zaragoza':'萨拉戈萨','SD Ponferradina':'蓬费拉迪纳','Huesca':'韦斯卡','Las Palmas':'拉斯帕尔马斯','Deportivo Alavés':'阿拉维斯',
                           'Real Oviedo':'皇家奥维耶多','Leganés':'莱加内斯','Racing de Santander':'桑坦德竞技','Burgos':'布尔戈斯','UD Ibiza':'伊维萨',
                           'CD Lugo':'卢戈','FC Cartagena':'卡塔赫纳','Villarreal B':'比利亚雷亚尔B队','Levante UD':'莱万特','Sporting Gijón':'希洪竞技',
                           'Málaga':'马拉加','Eibar':'埃瓦尔'},
                  #✔
                  '巴甲':{'Avaí':'阿瓦伊','Coritiba':'库里蒂巴','Red Bull Bragantino':'布拉甘蒂诺红牛','Goiás':'戈亚斯','Fortaleza':'福塔莱萨',
                           'Cuiabá':'奎尔巴','Ceará':'塞阿拉','Fluminense':'弗鲁米嫩塞','Botafogo':'博塔弗戈','São Paulo':'圣保罗',
                           'Atlético Mineiro':'米内罗竞技','América Mineiro':'米内罗美洲','Internacional':'巴西国际','Athletico':'巴拉纳竞技','Santos':'桑托斯',
                           'Atlético Goianiense':'戈亚尼亚竞技','Juventude':'尤文图德','Flamengo':'弗拉门戈','Corinthians':'科林蒂安','Palmeiras':'帕尔梅拉斯'},
                  #✔
                  '墨超':{'Tigres UANL':'墨西哥老虎','Mazatlán FC':'马萨特兰','Monterrey':'蒙特雷','Club América':'美洲','Cruz Azul':'蓝十字',
                           'Club Necaxa':'内卡萨','Atlético de San Luis':'圣路易斯','Pachuca':'帕丘卡','Toluca':'托卢卡','Puebla':'普埃布拉',
                           'CD Guadalajara':'瓜达拉哈拉','Juárez FC':'华雷斯','Atlas':'阿特拉斯','Pumas UNAM':'美洲狮','Club Tijuana':'蒂华纳',
                           'Club León':'莱昂','Santos Laguna':'桑托斯拉古纳','Querétaro':'克雷塔罗'},
                  #✔
                  '葡超':{'Portimonense':'波尔蒂芒人','GD Chaves':'沙维斯','Gil Vicente FC':'吉尔维森特','Rio Ave':'阿维河','Sporting CP':'葡萄牙体育',
                           'Casa Pia AC':'卡萨皮亚','FC Vizela':'维泽拉','Paços de Ferreira':'帕索斯费雷拉','CS Marítimo':'马德拉航海',
                           'CD Santa Clara':'圣克拉拉','FC Porto':'波尔图','SL Benfica':'本菲卡','Arouca':'阿罗卡','FC Famalicão':'法马利康',
                           'Boavista':'博阿维斯塔','Estoril Praia':'埃斯托里尔','Sporting Braga':'布拉加','Vitória SC':'吉马良斯'},
                  #✔
                  '荷甲':{'FC Emmen':'埃蒙','Fortuna Sittard':'锡塔德幸运','Vitesse':'维特斯','NEC Nijmegen':'奈梅亨','Feyenoord':'费耶诺德',
                           'SC Heerenveen':'海伦芬','FC Utrecht':'乌德勒支','Sparta Rotterdam':'鹿特丹斯巴达','FC Groningen':'格罗宁根',
                           'FC Twente':'特温特','RKC Waalwijk':'瓦尔韦克','PSV Eindhoven':'埃因霍温','AZ Alkmaar':'阿尔克马尔',
                           'FC Volendam':'福伦丹','Go Ahead Eagles':'前进之鹰','Excelsior':'SBV精英','Ajax':'阿贾克斯','SC Cambuur':'坎布尔'},
                  #✔
                  '瑞典超':{'IFK Värnamo':'瓦纳默','IFK Göteborg':'哥德堡','AIK':'索尔纳','Kalmar FF':'卡尔马','IFK Norrköping':'北雪平','Helsingborgs IF':'赫尔辛堡',
                            'Hammarby IF':'哈马比','Varbergs BoIS':'瓦尔贝里','Malmö FF':'马尔默','IF Elfsborg':'埃尔夫斯堡','BK Häcken':'赫根',
                            'Djurgårdens IF':'佐加顿斯','Degerfors IF':'代格福什','GIF Sundsvall':'松兹瓦尔','IK Sirius':'天狼星','Mjällby AIF':'米亚尔比'},
                  #✔
                  '挪超':{'Odds BK':'奥特','Bodø/Glimt':'博多格林特','Jerv':'谢夫','Sandefjord Fotball':'桑德菲杰','Sarpsborg 08':'萨普斯堡','Viking FK':'维京',
                           'Kristiansund BK':'克里斯蒂安松','Aalesunds FK':'奥勒松','Lillestrøm SK':'利勒斯特罗姆','Rosenborg BK':'罗森博格','Molde FK':'莫尔德',
                           'HamKam':'汉坎','Tromsø IL':'特罗姆瑟','Strømsgodset':'斯托姆加斯特','Haugesund':'海于格松','Vålerenga IF':'瓦勒伦加'},
                  #✔
                  '比甲':{'Oud-Heverlee Leuven':'奥哈瓦里','SV Zulte Waregem':'威尔郡','RC Sporting Charleroi':'沙勒鲁瓦','KRC Genk':'亨克',
                           'KV Mechelen':'梅赫伦','Standard Liège':'标准列日','KVC Westerlo':'韦斯特洛','Sint-Truidense VV':'圣图尔登',
                           'KV Kortrijk':'科特赖克','Cercle Brugge':'色格拉布鲁日','Club Brugge':'布鲁日','KV Oostende':'奥斯坦德','Royale Union Saint-Gilloise':'圣吉罗斯',
                           'RSC Anderlecht':'安德莱赫特','KAS Eupen':'欧本','KAA Gent':'根特','RFC Seraing':'塞莱恩','Royal Antwerp FC':'安特卫普'},
                  #✔
                  '智甲':{'Unión La Calera':'拉卡勒拉联','Coquimbo Unido':'科金博联合','Everton de Viña del Mar':'比尼亚德尔马埃弗顿','Curicó Unido':'库里科联合',
                           'Deportes La Serena':'拉塞雷纳','Ñublense':'纽布伦斯',"O'Higgins":'奥希金斯','Cobresal':'科布雷萨尔','Audax Italiano':'奥达科斯意大利人',
                           'Huachipato':'瓦奇巴托','Antofagasta':'安托法加斯塔','Unión Española':'西班牙联合','Colo Colo':'科洛科洛','Universidad Católica':'天主大学',
                           'Palestino':'巴勒斯坦人','Universidad de Chile':'智利大学'},
                  '亚冠':{},#FIXME
                  '解放者杯':{},#FIXME
                  '南球杯':{},#FIXME
                  #✔
                  '中超':{'Guangzhou City':'广州城','Hebei':'河北','Changchun Yatai':'长春亚泰','Meizhou Hakka':'梅州客家','Shanghai Shenhua':'上海申花',
                           'Cangzhou Mighty Lions':'沧州雄狮','Shenzhen':'深圳','Henan Songshan Longmen':'河南嵩山龙门','Beijing Guoan':'北京国安',
                           'Guangzhou FC':'广州队','Wuhan Three Towns':'武汉三镇','Chengdu Rongcheng':'成都蓉城','Tianjin Jinmen Tiger':'天津津门虎',
                           'Zhejiang':'浙江','Dalian Pro':'大连人','Wuhan':'武汉长江','Shandong Taishan':'山东泰山','Shanghai Port':'上海海港'}
                  }

    for league_key, league_values in teams_dict.items():
        for key, value in league_values.items():
            if home == key:
                home = home.replace(key, value)
            if away == key:
                away = away.replace(key, value)
    return home, away

def strip_parent(string):
    return string.split('(')[1]

def switch_date(driver, go_to_date):
    '''
    go_to_date[int]: 要切换到的日期
    '''
    date_xpath = '/html/body/div[1]/div/main/div/div[2]/div[1]/div[1]/div[1]/div[2]/div/div/div/div[2]/button[{num_date}]/div/span'.format(num_date=str(go_to_date))
    date_element = driver.find_element(By.XPATH, date_xpath)
    date = date_element.text
    date_element.click()
    st.write('已切换至',date,'日')
    
def fake_get_match(driver):
    '''
    解决每次刷新后前两场比赛重复的情况
    '''
    element = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/div/main/div/div[2]/div[3]/div/div[1]/div/a/button'))) #Show More Button
    element.send_keys(Keys.CONTROL + Keys.RETURN)
    driver.switch_to.window(driver.window_handles[1])
    time.sleep(1)
    driver.close()
    driver.switch_to.window(driver.window_handles[0])
    
def get_match(driver):
    '''
    获取完场比赛比分及盘口信息
    '''
    home_score = away_score = handicap_H = handicap_A = value_home = value_away = ''
    #打开新标签页获取盘口
    element = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/div/main/div/div[2]/div[3]/div/div[1]/div/a/button'))) #Show More Button
    element.send_keys(Keys.CONTROL + Keys.RETURN)
    driver.switch_to.window(driver.window_handles[1])
    time.sleep(1)
    
    #获取比分及盘口
    try:
        try:
            driver.find_element(By.CLASS_NAME,'sc-eDWCr.jgSsSj') #主比分1
            homescore_class_name = 'sc-eDWCr.jgSsSj'
        except NoSuchElementException:
            driver.find_element(By.CLASS_NAME,'sc-eDWCr.iRYKkj') #主比分2
            homescore_class_name = 'sc-eDWCr.iRYKkj'
    except:
        print('暂无主队比分')
        
    try:
        try:
            driver.find_element(By.CLASS_NAME,'sc-eDWCr.hNUSos') #客比分1
            awayscore_class_name = 'sc-eDWCr.hNUSos'
        except NoSuchElementException:
            driver.find_element(By.CLASS_NAME,'sc-eDWCr.eRrOEk') #客比分2
            awayscore_class_name = 'sc-eDWCr.eRrOEk'
    except:
        print('暂无客队比分')
    
    try:
        try:
            home_score = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, homescore_class_name))).text
            away_score = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, awayscore_class_name))).text
            test_flags = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME,'sc-eDWCr.itJafI')))
            handicap_H = driver.find_elements(By.CLASS_NAME,'sc-eDWCr.itJafI')[0].text #主盘口
            handicap_A = driver.find_elements(By.CLASS_NAME,'sc-eDWCr.itJafI')[1].text #客盘口
            value_home = driver.find_elements(By.CLASS_NAME,'sc-eDWCr.dsMMht')[2].text #主赔
            value_away = driver.find_elements(By.CLASS_NAME,'sc-eDWCr.dsMMht')[3].text #客赔
        except TimeoutException:
            print('请求超时')
    except:
        print('暂无盘口信息')
    
    #回到主页面
    driver.close()
    driver.switch_to.window(driver.window_handles[0])
    return [home_score, away_score, handicap_H, handicap_A, value_home, value_away]

def clean_handicap(handicap_value, value_home, value_away):
    '''
    清洗盘口信息
    '''
    if handicap_value == '0' or handicap_value == '-0':
        if value_home < value_away:
            handicap_value = '-0'
        elif value_away < value_home:
            handicap_value = '+0'
        else:
            handicap_value = '0'
    else:
        if not handicap_value.startswith('-'):
            handicap_value = '+'+handicap_value
    return handicap_value

def create_onedrive_directdownload(onedrive_link):
    '''
    用于读取onedrive数据库
    '''
    data_bytes64 = base64.b64encode(bytes(onedrive_link, 'utf-8'))
    data_bytes64_String = data_bytes64.decode('utf-8').replace('/','_').replace('+','-').rstrip("=")
    resultUrl = f"https://api.onedrive.com/v1.0/shares/u!{data_bytes64_String}/root/content"
    return resultUrl

def read_file(data):
    df = pd.read_excel(data, sheet_name = 1, converters = {'盘口': str, '竞彩': str, '比分': str})
    df['盘口数字'] = df['盘口'].astype(float)
    df['开球时间'] = df['开球时间'].fillna('')
    df['注释'] = df['注释'].fillna('')
    df['批注胜'] = df['批注胜'].fillna('')
    df['批注平'] = df['批注平'].fillna('')
    df['批注负'] = df['批注负'].fillna('')
    df['批注让胜'] = df['批注让胜'].fillna('')
    df['批注让平'] = df['批注让平'].fillna('')
    df['批注让负'] = df['批注让负'].fillna('')
    return df

def scrape_matches(driver, scroll_startpoint, scroll_endpoint):
    #数据存储
    continue_flag = True
    amount_scrolled = scroll_startpoint
    df_result = pd.DataFrame(columns=['主队','客队','H','A','盘口'])
    
    if scroll_startpoint == 0:
        first_scroll_flag = True
    else:
        first_scroll_flag = False
    
    while continue_flag:
        i = 0 #比赛index
        num_clicks = 0 #点击比赛次数
        driver.refresh() #刷新页面
        ActionChains(driver).scroll_by_amount(0, amount_scrolled).perform()
        time.sleep(5) #等待页面元素刷新
        
        try:
            driver.find_element(By.CLASS_NAME,'sc-hKwDye.LFQYO.sc-9199a964-1.bnnDyH') #比赛列表1
            match_class_name = 'sc-hKwDye.LFQYO.sc-9199a964-1.bnnDyH'
        except NoSuchElementException:
            driver.find_element(By.CLASS_NAME,'sc-hLBbgP.dRtNhU.sc-9199a964-1.kusmLq') #比赛列表2
            match_class_name = 'sc-hLBbgP.dRtNhU.sc-9199a964-1.kusmLq'
        matches = driver.find_elements(By.CLASS_NAME, match_class_name) #比赛列表
        
        while num_clicks < 6:
            match = matches[i]
            match.click()        
            if i == 0:
                fake_get_match(driver)
            else:
                num_clicks += 1
                info_list = get_match(driver)
                home_score = info_list[0]
                away_score = info_list[1]
                handicap_H = info_list[2]
                handicap_A = info_list[3]
                value_home = info_list[4]
                value_away = info_list[5]
        
                #显示信息
                try:
                    home_name = handicap_H.split(') ')[1]
                    away_name = handicap_A.split(') ')[1]
                    handicap_value = strip_parent(handicap_H.split(') ')[0])
                    handicap_value = clean_handicap(handicap_value, value_home, value_away)
                    
                    print(home_name+' '+home_score+'-'+away_score+' '+away_name)
                    print('盘口：', handicap_value)
                    df_result = df_result.append({'主队':home_name, '客队':away_name, 'H':home_score, 'A':away_score, '盘口':handicap_value}, ignore_index=True)
                except:
                    print('error parsing handicap info') 
            i += 1
            
        #结束条件
        if amount_scrolled == scroll_endpoint:
            continue_flag = False
        #划动比赛
        if first_scroll_flag:
            ActionChains(driver).scroll_by_amount(0, 750).perform()
            amount_scrolled += 750
            first_scroll_flag = False
        else:
            ActionChains(driver).scroll_by_amount(0, 350).perform()
            amount_scrolled += 350
        print('已划动')
        del matches
    return df_result

if __name__ == "__main__":
    main()
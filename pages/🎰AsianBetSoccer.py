# -*- coding: utf-8 -*-
"""
Last Edit 9/19/2023
@author: zhangliyao
Asian Handicap scraper with Streamlit
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
from selenium.webdriver.safari.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException

def main():
  st.set_page_config(
    page_title="亚盘数据获取"
    )
  st.title("ABS比分盘口自动获取系统")
  st.caption("增加数据检验功能，检查爬虫未识别的队名和合并数据后缺失数据；增加未来比赛盘口")
    
  with st.form("user_input"):
    submitted = st.form_submit_button("运行")
        
  if submitted:
    driver = init_service()
    df_selected = read_db()

    # Scrape matches for each league and save as a df
    frames = []
    league_names = df_selected['联赛'].apply(map_leagues)
    for league_name in league_names.unique():
      select_league(driver, league_name)
      df_result = scrape(driver)
      df_result = clean_result(df_result)
      frames.append(df_result)

    # Combine all dfs to a single df
    final_result = pd.concat(frames)
    final_result['主队'] = final_result['主队'].apply(map_teams)
    final_result['客队'] = final_result['客队'].apply(map_teams)
    final_result['比赛'] = final_result['主队']+'-'+final_result['客队']
    final_result['赛果'] = final_result['主队']+final_result['H']+'-'+final_result['A']+final_result['客队']

    # Combine with original dataset
    for k in range(len(df_selected)):
      game = df_selected.iloc[k, 4].replace(" ", "") #数据库【比赛】列，清除所有空格
      for i in range(len(final_result)):
        H = final_result.iloc[i, 1]
        A = final_result.iloc[i, 2]
        handicap = final_result.iloc[i, 4]
        home_odd = final_result.iloc[i, 5]
        away_odd = final_result.iloc[i, 6]
        sf_game = final_result.iloc[i, 7]
        sf_result = final_result.iloc[i, 8]
        if game == sf_game or game == sf_result:
          df_selected.at[k, '比赛'] = sf_result
          df_selected.at[k, '盘口'] = handicap
          df_selected.at[k, 'H'] = H
          df_selected.at[k, 'A'] = A
          df_selected.at[k, '主赔'] = home_odd
          df_selected.at[k, '客赔'] = away_odd
    df_selected['H'] = df_selected['H'].astype(int)
    df_selected['A'] = df_selected['A'].astype(int)

    # Export dataset
    today = datetime.today()
    file_name="Sofascore_"+today.strftime('%m-%d')+".xlsx"
    df_selected.to_excel('/Users/zhangliyao/Desktop//'+file_name, index=False) # change to download button when needed
    st.success("运行成功！数据已下载至桌面")

def init_service():
  '''
  Connect to the website and choose Bet365 as bookmaker
  '''
  # Initialize
  driver = webdriver.Safari(service=Service())
  driver.implicitly_wait(10)
  driver.get("https://www.asianbetsoccer.com/lastgame.html")
  
  # Select Bookmaker
  buttons = driver.find_elements(By.CLASS_NAME, 'dropdown.element-filter')
  buttons[3].click()
  
  select_element = driver.find_element(By.NAME, 'book_filter')
  select = Select(select_element)
  select.select_by_visible_text('Bet365')
  
  # Submit Bookmaker
  submit_setting = driver.find_element(By.ID, 'setting_submit')
  submit_setting.click()
  time.sleep(2)
  
  return driver

def create_onedrive_directdownload(onedrive_link):
  '''
  用于读取onedrive数据库
  '''
  data_bytes64 = base64.b64encode(bytes(onedrive_link, 'utf-8'))
  data_bytes64_String = data_bytes64.decode('utf-8').replace('/','_').replace('+','-').rstrip("=")
  resultUrl = f"https://api.onedrive.com/v1.0/shares/u!{data_bytes64_String}/root/content"
  return resultUrl

def read_file(data):
  df = pd.read_excel(data, sheet_name=1, converters={'盘口': str, '竞彩': str, '比分': str}, usecols='A:X', skiprows=[1, 50000]) # read last n rows for performance
  df['开球时间'] = df['开球时间'].fillna('')
  df['注释'] = df['注释'].fillna('')
  df['批注胜'] = df['批注胜'].fillna('')
  df['批注平'] = df['批注平'].fillna('')
  df['批注负'] = df['批注负'].fillna('')
  df['批注让胜'] = df['批注让胜'].fillna('')
  df['批注让平'] = df['批注让平'].fillna('')
  df['批注让负'] = df['批注让负'].fillna('')
  return df
    
def select_league(driver, league_name):
  '''
  Filter page content by the league name
  '''
  # Select League
  buttons = driver.find_elements(By.CLASS_NAME, 'dropdown.element-filter')
  buttons[0].click()
  
  select_element = driver.find_element(By.NAME, 'search_filter')
  select = Select(select_element)
  select.select_by_visible_text(league_name)
  
  # Submit League
  submit_league = driver.find_element(By.ID, 'search_submit')
  submit_league.click()
  time.sleep(2)
    
def scrape(driver):
  '''
  The main scaper that collects team names, final scores and handicaps
  '''
  # Collect Match Data
  table1 = driver.find_element(By.ID, 'tablematch1') # locate data stored in table
  rows = table1.find_elements(By.TAG_NAME, 'tr') # locate each row of table
  home_name = away_name = home_score = away_score = ''
  Home = []
  Away = []
  H = []
  A = []
  for row in rows:
    elements = row.find_elements(By.TAG_NAME, 'td') # locate each element of row
    # if first element is H, homescore is [3], if first element is A, awayscore is [2]
    if elements[0].text == 'H':
      home_name = elements[1].text
      home_score = elements[3].text
      while home_name[0].isdigit():
        home_name = home_name[1:]
      Home.append(home_name)
      H.append(home_score)
    elif elements[0].text == 'A':
      away_name = elements[1].text
      away_score = elements[2].text
      while away_name[0].isdigit():
        away_name = away_name[1:]
      Away.append(away_name)
      A.append(away_score)
      
  # Collect Odds Data
  table2 = driver.find_element(By.ID, 'tablematch2') # locate data stored in table
  rows = table2.find_elements(By.TAG_NAME, 'tr') # locate each row of table
  Handicap = []
  HomeOdds = []
  AwayOdds = []
  for row in rows:
    elements = row.find_elements(By.TAG_NAME, 'td') # locate each element of row
    if elements[0].text == 'H':
      home_handicap = elements[1].text
      home_odds = elements[4].text
      #print(home_handicap)
      Handicap.append(home_handicap)
      HomeOdds.append(home_odds)
    elif elements[0].text == 'A':
      away_odds = elements[4].text
      AwayOdds.append(away_odds)
          
  # Create dataframe columns from lists
  df_result = pd.DataFrame()
  df_result['主队'] = Home
  df_result['H'] = H
  df_result['A'] = A
  df_result['客队'] = Away
  df_result['盘口'] = Handicap
  df_result['主赔'] = HomeOdds
  df_result['客赔'] = AwayOdds
  
  return df_result

def clean_result(df_result):
  # Data Cleaning
  df_result.loc[(df_result['盘口']=='0') & (df_result['主赔'] < df_result['客赔']), '盘口'] = '-0'
  df_result.loc[(df_result['盘口']=='0') & (df_result['主赔'] > df_result['客赔']), '盘口'] = '+0'
  df_result.loc[(df_result['盘口']=='0') & (df_result['主赔'] == df_result['客赔']), '盘口'] = '0'
  df_result['盘口'] = df_result['盘口'].apply(clean_handicap)
  
  return df_result
    
def clean_handicap(handicap_value):
  if not handicap_value.startswith('-') and not handicap_value.startswith('+'):
    return '+'+handicap_value
  else:
    return handicap_value
    
def map_leagues(league):
  league_dict = {
    '美职联':'USA Major League Soccer','日职联':'J1 League','德乙':'German Bundesliga 2','德甲':'German Bundesliga','西甲':'Spanish La Liga',
    '英超':'English Premier League','欧冠':'UEFA Champions League','阿甲':'Argentine Division 1','欧联':'','法甲':'France Ligue 1',
    '巴甲':'Brazil Serie A','意甲':'Italian Serie A','欧国联':'','墨超':'Primera Division Liga MX','葡超':'Liga Portugal 1','荷甲':'Holland Eredivisie',
    '英冠':'England Championship','解放者杯':'','欧预赛':'UEFA European Championship','南球杯':'',
    '瑞典超':'Swedish Allsvenskan','挪超':'Norwegian Tippeligaen',
    '世界杯':'','美洲杯':'','亚洲预选':'','西乙':'Spanish La Liga 2','比甲':'Belgian Pro League','智甲':'',
    '南美预选':'FIFA World Cup qualification (CONMEBOL)','世预赛':'','北美预选':'','欧洲杯':'','世俱杯':'','欧协联':''}

  for key, value in league_dict.items():
    if league == key:
      league = league.replace(key, value)
  return league
    
def map_teams(team):
  teams_dict = {
  #1
  '美职联':{'Portland Timbers':'波特兰伐木者','Los Angeles FC':'洛杉矶FC','Minnesota United FC':'明尼苏达联','New England Revolution':'新英格兰革命',
          'DC United':'华盛顿联','San Jose Earthquakes':'圣何塞地震','Inter Miami CF':'迈阿密国际','FC Kansas City':'堪萨斯城体育','Austin FC':'奥斯汀FC',
          'Los Angeles Galaxy':'洛杉矶银河','St. Louis City':'圣路易斯城','Real Salt Lake':'皇家盐湖城','Colorado Rapids':'科罗拉多急流',
          'FC Dallas':'达拉斯FC','Seattle Sounders':'西雅图海湾人','Houston Dynamo':'休斯顿迪纳摩','Charlotte FC':'夏洛特FC','Montreal Impact':'蒙特利尔冲击',
          'Chicago Fire':'芝加哥火焰','Toronto FC':'多伦多FC','Vancouver Whitecaps':'温哥华白浪','Orlando City':'奥兰多城','Columbus Crew':'哥伦布机员',
          'Philadelphia Union':'费城联合','FC Cincinnati':'辛辛那提','Atlanta United':'亚特兰大联','New York City FC':'纽约城','New York Red Bulls':'纽约红牛',
          '':''},
  #✔
  '日职联':{'Urawa Red Diamonds':'浦和红钻','Kyoto Sanga':'京都不死鸟','Yokohama Marinos':'横滨水手','Sagan Tosu':'鸟栖砂岩','Kawasaki Frontale':'川崎前锋',
          'FC Tokyo':'东京FC','Avispa Fukuoka':'福冈黄蜂','Nagoya Grampus':'名古屋逆戟鲸','Consadole Sapporo':'札幌冈萨多','Shonan Bellmare':'湘南海洋',
          'Hiroshima Sanfrecce':'广岛三箭','Vissel Kobe':'神户胜利船','Kashima Antlers':'鹿岛鹿角','Cerezo Osaka':'大阪樱花','Gamba Osaka':'大阪钢巴',
          'Albirex Niigata':'新泻天鹅','Yokohama FC':'横滨FC','Kashiwa Reysol':'柏太阳神'},
  #✔
  '德乙':{'Nurnberg':'纽伦堡','Greuther Furth':'菲尔特','SC Paderborn 07':'帕德博恩','SV Wehen Wiesbaden':'韦恩','Schalke 04':'沙尔克04','Magdeburg':'马格德堡',
        'Hansa Rostock':'罗斯托克','Fortuna Dusseldorf':'杜塞尔多夫','Karlsruher SC':'卡尔斯鲁厄','Kaiserslautern':'凯泽斯劳滕','SV Elversberg':'埃弗斯堡',
        'Hamburger SV':'汉堡','Hannover 96':'汉诺威96','VfL Osnabruck':'奥斯纳布吕克','Hertha Berlin':'柏林赫塔','Eintracht Braunschweig':'布伦瑞克',
        'St. Pauli':'圣保利','Holstein Kiel':'基尔'},
  #✔
  '德甲':{'Bayern Munchen':'拜仁慕尼黑','Bayer Leverkusen':'勒沃库森','VfL Bochum':'波鸿','Eintracht Frankfurt':'法兰克福','FC Koln':'科隆',
        'TSG Hoffenheim':'霍芬海姆','FSV Mainz 05':'美因茨','VfB Stuttgart':'斯图加特','RB Leipzig':'RB莱比锡','Augsburg':'奥格斯堡','SC Freiburg':'弗赖堡',
        'Borussia Dortmund':'多特蒙德','VfL Wolfsburg':'沃尔夫斯堡','Union Berlin':'柏林联合','Darmstadt':'达姆施塔特','Borussia Monchengladbach':'门兴格拉德巴赫',
        'Heidenheimer':'海登海姆','Werder Bremen':'云达不莱梅'},
  #✔
  '西乙':{'Burgos CF':'布尔戈斯','Eibar':'埃瓦尔','Real Oviedo':'皇家奥维耶多','Sporting Gijon':'希洪竞技','Tenerife':'特内里费','Albacete':'阿尔瓦塞特',
        'Leganes':'莱加内斯','SD Huesca':'韦斯卡','Real Valladolid':'巴拉多利德','Elche':'埃尔切','FC Cartagena':'卡塔赫纳','Real Zaragoza':'萨拉戈萨',
        'Mirandes':'米兰德斯','Andorra FC':'FC安道尔','Racing de Ferrol':'费罗尔竞技','Villarreal B':'比利亚雷亚尔B队','Racing Santander':'桑坦德竞技',
        'SD Amorebieta':'亚摩勒比塔','Eldense':'埃登斯','AD Alcorcon':'阿尔科孔','Levante':'莱万特','RCD Espanyol':'西班牙人'},
  #✔
  '西甲':{'Rayo Vallecano':'巴列卡诺','Alaves':'阿拉维斯','FC Barcelona':'巴塞罗那','Real Betis':'皇家贝蒂斯','Celta Vigo':'塞尔塔','Mallorca':'马略卡',
        'Valencia':'巴伦西亚','Atletico Madrid':'马德里竞技','Athletic Bilbao':'毕尔巴鄂竞技','Cadiz':'加迪斯','Real Madrid':'皇家马德里','Real Sociedad':'皇家社会',
        'Sevilla':'塞维利亚','Las Palmas':'拉斯帕尔马斯','Villarreal':'比利亚雷亚尔','Almeria':'阿尔梅里亚','Getafe':'赫塔费','Osasuna':'奥萨苏纳',
        'Granada CF':'格拉纳达','Girona':'赫罗纳'},
  #✔
  '英冠':{'Southampton':'南安普顿','Leicester City':'莱斯特城','Hull City':'赫尔城','Coventry City':'考文垂','Cardiff City':'卡迪夫城','Swansea City':'斯旺西',
        'Blackburn Rovers':'布莱克本','Middlesbrough':'米德尔斯堡','Bristol City':'布里斯托尔城','West Bromwich(WBA)':'西布朗','Huddersfield Town':'哈德斯菲尔德',
        'Rotherham United':'罗瑟汉姆','Norwich City':'诺维奇','Stoke City':'斯托克城','Preston North End':'普雷斯顿','Plymouth Argyle':'普利茅斯',
        'Queens Park Rangers (QPR)':'女王公园巡游者','Sunderland A.F.C':'桑德兰','Sheffield Wednesday':'谢菲尔德星期三','Ipswich Town':'伊普斯维奇',
        'Watford':'沃特福德','Birmingham City':'伯明翰','Millwall':'米尔沃尔','Leeds United':'利兹联'},
  #✔
  '英超':{'Newcastle United':'纽卡斯尔','Brentford':'布伦特福德','Aston Villa':'阿斯顿维拉','Crystal Palace':'水晶宫','Fulham':'富勒姆','Luton Town':'卢顿',
        'Manchester United':'曼联','Brighton Hove Albion':'布莱顿','Tottenham Hotspur':'热刺','Sheffield United':'谢菲尔德联','West Ham United':'西汉姆联',
        'Manchester City':'曼城','Wolves':'狼队','Liverpool':'利物浦','Everton':'埃弗顿','Arsenal':'阿森纳','AFC Bournemouth':'伯恩茅斯','Chelsea':'切尔西',
        'Nottingham Forest':'诺丁汉森林','Burnley':'伯恩利'},

  '欧冠':{'':'哥本哈根','':'加拉塔萨雷','':'萨尔茨堡红牛','Celtic FC':'凯尔特人','Young Boys':'伯尔尼年轻人',
        'Crvena Zvezda':'贝尔格莱德红星','FC Shakhtar Donetsk':'顿涅茨克矿工'},

  '欧联':{'':'奥林匹亚科斯','':'托波拉','':'雅典AEK','':'阿里斯','':'流浪者','':'布拉格斯巴达',
        '':'琴斯托霍瓦','':'格拉茨风暴','':'林茨','':'海法马卡比','':'帕纳辛奈科斯','':'塞尔维特',
        '':'蒂拉斯波尔警长','':'布拉格斯拉维亚','':'卡拉巴赫'},

  '欧协联':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},
  #✔
  '法甲':{'Paris Saint Germain (PSG)':'巴黎圣日耳曼','Nice':'尼斯','Lens':'朗斯','Metz':'梅斯','Rennes':'雷恩','Lille':'里尔','Lyon':'里昂',
        'Le Havre':'勒阿弗尔','Marseille':'马赛','Toulouse':'图卢兹','Clermont':'克莱蒙','Nantes':'南特','Reims':'兰斯','Stade Brestois':'布雷斯特',
        'Strasbourg':'斯特拉斯堡','Montpellier':'蒙彼利埃','Lorient':'洛里昂','Monaco':'摩纳哥'},
  #✔
  '意甲':{'Genoa':'热那亚','Napoli':'那不勒斯','Inter Milan':'国际米兰','AC Milan':'AC米兰','Juventus':'尤文图斯','Lazio':'拉齐奥','AS Roma':'罗马',
        'Empoli':'恩波利','Fiorentina':'佛罗伦萨','Atalanta':'亚特兰大','Frosinone':'弗罗西诺内','Sassuolo':'萨索洛','Monza':'蒙扎','Lecce':'莱切',
        'Cagliari':'卡利亚里','Udinese':'乌迪内斯','Verona':'维罗纳','Bologna':'博洛尼亚','Salernitana':'萨勒尼塔纳','Torino':'都灵'},

  '阿甲':{'Banfield':'班菲尔德','Argentinos Juniors':'阿根廷青年人','Colon de Santa Fe':'哥伦布竞技','Rosario Central':'罗萨里奥中央',
        'Defensa Y Justicia':'国防与司法','Boca Juniors':'博卡青年','Club Atletico Tigre':'老虎竞技','Estudiantes La Plata':'拉普拉塔大学生',
        'Independiente':'独立','CA Huracan':'飓风','Talleres Cordoba':'塔列雷斯','Instituto AC Cordoba':'科尔多瓦学院','Atletico Tucuman':'图库曼竞技',
        'Barracas Central':'巴拉卡斯中央','San Lorenzo':'圣洛伦索','Racing Club':'竞技','Newells Old Boys':'纽维尔老男孩','Club Atlético Unión':'圣菲联',
        'River Plate':'河床','Arsenal de Sarandi':'萨兰迪兵工厂','Godoy Cruz Antonio Tomba':'戈多伊克鲁斯','Belgrano':'贝尔格拉诺','Lanus':'拉努斯',
        'Sarmiento Junin':'萨米恩托','Gimnasia La Plata':'拉普拉塔体操','Central Cordoba SDE':'科尔多瓦中央'},
  #7
  '巴甲':{'Palmeiras':'帕尔梅拉斯','Goias':'戈亚斯','Cuiaba':'奎尔巴','America MG':'米内罗美洲','Bragantino':'布拉甘蒂诺红牛','Gremio (RS)':'格雷米奥',
        'Atletico Mineiro':'米内罗竞技','Botafogo RJ':'博塔弗戈','Vasco da Gama':'瓦斯科达伽马','Fluminense RJ':'弗鲁米嫩塞','Corinthians Paulista (SP)':'科林蒂安',
        'Bahia':'巴伊亚','Santos':'桑托斯','':'','':'','':'','':'','':'','':'','':''},
  #2
  '墨超':{'Club Tijuana':'蒂华纳','Toluca':'托卢卡','Mazatlan FC':'马萨特兰','CDSyC Cruz Azul':'蓝十字','Club America':'美洲','Chivas Guadalajara':'瓜达拉哈拉',
        'Monterrey':'蒙特雷','Club Leon':'莱昂','Necaxa':'内卡萨','FC Juarez':'华雷斯','Atlas':'阿特拉斯','Tigres UANL':'墨西哥老虎','Queretaro FC':'克雷塔罗',
        'Puebla':'普埃布拉','Pumas U.N.A.M.':'美洲狮','Atletico San Luis':'圣路易斯','':'','':''},

  '智甲':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  '解放者杯':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  '南球杯':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},
  #✔
  '荷甲':{'Heracles Almelo':'阿尔梅罗大力神','FC Utrecht':'乌德勒支','PSV Eindhoven':'埃因霍温','NEC Nijmegen':'奈梅亨','Fortuna Sittard':'锡塔德幸运',
        'Volendam':'福伦丹','Vitesse Arnhem':'维特斯','RKC Waalwijk':'瓦尔韦克','Feyenoord':'费耶诺德','SC Heerenveen':'海伦芬','AZ Alkmaar':'阿尔克马尔',
        'Sparta Rotterdam':'鹿特丹斯巴达','Excelsior SBV':'SBV精英','Almere City FC':'阿尔梅勒城','FC Twente Enschede':'特温特','AFC Ajax':'阿贾克斯',
        'PEC Zwolle':'兹沃勒','Go Ahead Eagles':'前进之鹰'},
  #✔
  '葡超':{'Moreirense':'莫雷拉人','Sporting Braga':'布拉加','Estrela da Amadora':'阿马多拉','FC Porto':'波尔图','Vizela':'维泽拉','Benfica':'本菲卡',
        'SC Farense':'法鲁人','Rio Ave':'阿维河','FC Famalicao':'法马利康','Sporting CP':'葡萄牙体育','Vitoria Guimaraes':'吉马良斯','Portimonense':'波尔蒂芒人',
        'FC Arouca':'阿罗卡','Casa Pia AC':'卡萨皮亚','Gil Vicente':'吉尔维森特','Estoril':'埃斯托里尔','Boavista FC':'博阿维斯塔','GD Chaves':'沙维斯'},
  #✔
  '瑞典超':{'Djurgardens':'佐加顿斯','IFK Varnamo':'瓦纳默','IFK Goteborg':'哥德堡','Brommapojkarna':'布洛马波卡纳','IK Sirius FK':'天狼星',
          'Varbergs BoIS FC':'瓦尔贝里','Elfsborg':'埃尔夫斯堡','Kalmar':'卡尔马','Hacken':'赫根','Halmstads':'哈尔姆斯塔德','Hammarby':'哈马比',
          'Malmo FF':'马尔默','AIK Solna':'索尔纳','Degerfors IF':'代格福什','IFK Norrkoping FK':'北雪平','Mjallby AIF':'米亚尔比'},
  #✔
  '挪超':{'Haugesund':'海于格松','Viking':'维京','Molde':'莫尔德','Odd Grenland':'奥特','Sandefjord':'桑德菲杰','Stromsgodset':'斯托姆加斯特',
        'Valerenga':'瓦勒伦加','Aalesund FK':'奥勒松','Rosenborg':'罗森博格','Bodo Glimt':'博多格林特','Sarpsborg 08':'萨普斯堡','Lillestrom':'利勒斯特罗姆',
        'Stabaek':'斯塔贝克','Brann':'布兰','Tromso IL':'特罗姆瑟','Ham-Kam':'汉坎'},
  #✔
  '比甲':{'Westerlo':'韦斯特洛','Royal Antwerp':'安特卫普','Club Brugge':'布鲁日','Charleroi':'沙勒鲁瓦','Saint Gilloise':'圣吉罗斯','Racing Genk':'亨克',
        'Jeunesse Molenbeek':'莫伦贝克','Cercle Brugge':'色格拉布鲁日','Sint-Truidense':'圣图尔登','Mechelen':'梅赫伦','Oud Heverlee':'奥哈瓦里',
        'KAA Gent':'根特','Kortrijk':'科特赖克','Anderlecht':'安德莱赫特','KAS Eupen':'欧本','Standard Liege':'标准列日'},

  'Asia':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  'America':{'Peru':'秘鲁','Brazil':'巴西','Chile':'智利','Colombia':'哥伦比亚','Venezuela':'委内瑞拉','Paraguay':'巴拉圭','Ecuador':'厄瓜多尔',
            'Uruguay':'乌拉圭','Bolivia':'玻利维亚','Argentina':'阿根廷'},

  'Europe':{'Bosnia-Herzegovina':'波黑','Croatia':'克罗地亚','Latvia':'拉脱维亚','Cyprus':'塞浦路斯','Scotland':'苏格兰','Luxembourg':'卢森堡',
          'Iceland':'冰岛','Slovakia':'斯洛伐克','Portugal':'葡萄牙','Turkey':'土耳其','Armenia':'亚美尼亚','Georgia':'格鲁吉亚','Spain':'西班牙',
          'Kosovo':'科索沃','Switzerland':'瑞士','North Macedonia':'马其顿','Italy':'意大利','Romania':'罗马尼亚','Israel':'以色列','Andorra':'安道尔',
          'Belarus':'白俄罗斯','Estonia':'爱沙尼亚','Sweden':'瑞典','Ukraine':'乌克兰','England':'英格兰','Azerbaijan':'阿塞拜疆','Belgium':'比利时',
          'Albania':'阿尔巴尼亚','Poland':'波兰','Greece':'希腊','Ireland':'爱尔兰','Netherlands':'荷兰','Lithuania':'立陶宛','Serbia':'塞尔维亚',
          'Slovenia':'斯洛文尼亚','Faroe Islands':'法罗群岛','Moldova':'摩尔多瓦','Finland':'芬兰','Denmark':'丹麦','Montenegro':'黑山',
          'Bulgaria':'保加利亚','Kazakhstan':'哈萨克斯坦','Northern Ireland':'北爱尔兰','Wales':'威尔士','France':'法国','Norway':'挪威',
          'Austria':'奥地利','Malta':'马耳他'},} #Last Edit: 9/19/2023

  for league_key, league_values in teams_dict.items():
    for key, value in league_values.items():
      if team == key:
        team = team.replace(key, value)
  return team

def read_db():
  # Read excel from onedrive & collect target league names
  onedrive_link = 'https://1drv.ms/x/s!Ag9ZvloaJitBjy8YIdiLf5Wkr4O6?e=cwBjTO'
  url = create_onedrive_directdownload(onedrive_link)
  df = read_file(url)
  df_selected = df[df['盘口'].isnull()]
  df_selected = df_selected.reset_index()
  del df_selected['index']
  
  return df_selected

if __name__ == "__main__":
  main()
# -*- coding: utf-8 -*-
"""
Last Edit 9/16/2023
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
    page_title="亚盘数据获取",
    #page_icon=Image.open('pages/sofascore.jpg')
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
    df_selected.to_excel('/Users/zhangliyao/Desktop//'+file_name, index=False)

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
  counter = 1
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
      if counter % 5 == 0:
        print(home_name, home_score+'-'+away_score, away_name)
      counter += 1
      
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
    '英超':'','欧冠':'','阿甲':'Argentine Division 1','欧联':'','法甲':'France Ligue 1','巴甲':'Brazil Serie A',
    '意甲':'','欧国联':'','墨超':'Primera Division Liga MX','葡超':'Liga Portugal 1','荷甲':'',
    '英冠':'England Championship','解放者杯':'','欧预赛':'UEFA European Championship','南球杯':'','瑞典超':'','挪超':'',
    '世界杯':'','美洲杯':'','亚洲预选':'','西乙':'Spanish La Liga 2','比甲':'Belgian Pro League','智甲':'',
    '南美预选':'FIFA World Cup qualification (CONMEBOL)','世预赛':'','北美预选':'','欧洲杯':'','世俱杯':'','欧协联':''}

  for key, value in league_dict.items():
    if league == key:
      league = league.replace(key, value)
  return league
    
def map_teams(team):
  teams_dict = {
  '葡超':{'Moreirense':'莫雷拉人','Sporting Braga':'布拉加','Estrela da Amadora':'阿马多拉','FC Porto':'波尔图','':'','':'','':'','':'','':'','':''},

  '美职联':{'Portland Timbers':'波特兰伐木者','Los Angeles FC':'洛杉矶FC','Minnesota United FC':'明尼苏达联','New England Revolution':'新英格兰革命',
          'DC United':'华盛顿联','San Jose Earthquakes':'圣何塞地震','Inter Miami CF':'迈阿密国际','FC Kansas City':'堪萨斯城体育',
          'Los Angeles Galaxy':'洛杉矶银河','St. Louis City':'圣路易斯城','':'','':'','':'','':'','':'','':'','':'','':''},

  '日职联':{'Urawa Red Diamonds':'浦和红钻','Kyoto Sanga':'京都不死鸟','Yokohama Marinos':'横滨水手','Sagan Tosu':'鸟栖砂岩','Kawasaki Frontale':'川崎前锋',
          'FC Tokyo':'东京FC','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  '德乙':{'Nurnberg':'纽伦堡','Greuther Furth':'菲尔特','SC Paderborn 07':'帕德博恩','SV Wehen Wiesbaden':'韦恩','':'','':'','':'','':'','':'','':'','':''},

  '德甲':{'Bayern Munchen':'拜仁慕尼黑','Bayer Leverkusen':'勒沃库森','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  '西乙':{'Burgos CF':'布尔戈斯','Eibar':'埃瓦尔','Real Oviedo':'皇家奥维耶多','Sporting Gijon':'希洪竞技','Tenerife':'特内里费','Albacete':'阿尔瓦塞特',
        'Leganes':'莱加内斯','SD Huesca':'韦斯卡','Real Valladolid':'巴拉多利德','Elche':'埃尔切','FC Cartagena':'卡塔赫纳','Real Zaragoza':'萨拉戈萨',
        'Mirandes':'米兰德斯','Andorra FC':'FC安道尔','Racing de Ferrol':'','Villarreal B':'比利亚雷亚尔B队','Racing Santander':'桑坦德竞技',
        'SD Amorebieta':'亚摩勒比塔','Eldense':'埃登斯','AD Alcorcon':'阿尔科孔'},

  '西甲':{'Rayo Vallecano':'巴列卡诺','Alaves':'阿拉维斯','':'','':'','':'','':'','':'','':''},

  '英冠':{'Southampton':'南安普顿','Leicester City':'莱斯特城','Hull City':'赫尔城','Coventry City':'考文垂','':'','':'','':'','':''},

  '英超':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  '欧冠':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  '欧联':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  '欧协联':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  '法甲':{'Paris Saint Germain (PSG)':'巴黎圣日耳曼','Nice':'尼斯','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  '意甲':{'':'','':'','':'','':'','':'','':'','':'','':''},

  '阿甲':{'Banfield':'班菲尔德','Argentinos Juniors':'阿根廷青年人','Colon de Santa Fe':'哥伦布竞技','Rosario Central':'罗萨里奥中央',
        'Defensa Y Justicia':'国防与司法','Boca Juniors':'博卡青年','Club Atletico Tigre':'老虎竞技','Estudiantes La Plata':'拉普拉塔大学生',
        'Independiente':'独立','CA Huracan':'飓风','':'','':'','':'','':'','':''},

  '巴甲':{'Palmeiras':'帕尔梅拉斯','Goias':'戈亚斯','Cuiaba':'奎尔巴','America MG':'米内罗美洲','Bragantino':'布拉甘蒂诺红牛','Gremio (RS)':'格雷米奥',
        '':'','':'','':'','':'','':''},

  '墨超':{'Club Tijuana':'蒂华纳','Toluca':'托卢卡','Mazatlan FC':'马萨特兰','CDSyC Cruz Azul':'蓝十字','':'','':'','':'','':'','':'','':'','':'','':''},

  '荷甲':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  '解放者杯':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  '南球杯':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  '瑞典超':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  '挪超':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

  '比甲':{'Westerlo':'韦斯特洛','Royal Antwerp':'安特卫普','':'','':'','':'','':'','':'','':''},

  '智甲':{'':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':'','':''},

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
          'Austria':'奥地利','Malta':'马耳他'},} #Last Edit: 9/16/2023
    
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
# -*- coding: utf-8 -*-
"""
Last Edit 12/26/2023
@author: zhangliyao
Asian Handicap scraper with Streamlit
"""
import io
import os
import time
import pandas as pd
import streamlit as st
from stqdm import stqdm
from datetime import datetime
from dotenv import load_dotenv
from utils import create_onedrive_directdownload, read_file, map_leagues, map_teams
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
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
  load_dotenv()

  with st.form("user_input"):
    submitted = st.form_submit_button("运行")
        
  if submitted:
    driver = init_service()
    st.success('初始化完成！')
    df_selected = read_db()

    # Scrape matches for each league and save as a df
    frames = []
    league_names = df_selected['联赛'].apply(map_leagues)
    for league_name in stqdm(league_names.unique(), '获取数据中'):
      try:
        select_league(driver, league_name)
        df_result = scrape(driver)
        df_result = clean_result(df_result)
        frames.append(df_result)
      except:
        st.error("获取联赛失败："+league_name)

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
    df_selected['H'] = df_selected['H'].fillna(0)
    df_selected['A'] = df_selected['A'].fillna(0)
    df_selected['H'] = df_selected['H'].astype(int)
    df_selected['A'] = df_selected['A'].astype(int)

    # Export dataset
    today = datetime.today()
    file_name="//Sofascore_"+today.strftime('%m-%d')+".xlsx"
    download_path = os.getenv("DOWNLOAD_PATH")
    df_selected.to_excel(download_path + file_name, index=False) # change to download button when needed
    st.success("运行成功！数据已下载至桌面")

def init_service():
  '''
  Connect to the website and choose Bet365 as bookmaker
  '''
  # Initialize
  driver_path = os.getenv('CHROME_DRIVER_PATH')
  chrome_options = webdriver.ChromeOptions()
  chrome_options.add_argument('--headless')
  driver = webdriver.Chrome(service=Service(executable_path=driver_path), options=chrome_options)

  #driver = webdriver.Safari(service=Service())
  driver.implicitly_wait(10)
  driver.get(os.getenv('HANDICAP_URL'))
  time.sleep(2)

  # Select Bookmaker
  buttons = driver.find_elements(By.CLASS_NAME, 'dropdown-toggle')
  buttons[3].click()
  
  select_element = driver.find_element(By.NAME, 'book_filter')
  select = Select(select_element)
  select.select_by_visible_text('Bet365')
  
  # Submit Bookmaker
  submit_setting = driver.find_element(By.ID, 'setting_submit')
  submit_setting.click()
  time.sleep(2)
  
  return driver
    
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

def read_db():
  '''Read from onedrive and collect target league names'''
  # read from onedrive
  # onedrive_link = os.getenv('ONEDRIVE_DATA_URL')
  # url = create_onedrive_directdownload(onedrive_link)

  # read from local file
  url = os.getenv('LOCAL_DATA_PATH')
  df = read_file(url)
  df_selected = df[df['盘口'].isnull()]
  df_selected = df_selected.reset_index()
  del df_selected['index']
  
  return df_selected

if __name__ == "__main__":
  main()
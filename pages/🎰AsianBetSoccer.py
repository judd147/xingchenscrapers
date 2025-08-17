# -*- coding: utf-8 -*-
"""
Created on 12/26/2023
Last Edit 08/16/2025
@author: Liyao Zhang

Asian Handicap scraper with Streamlit
"""

import os
import time
import pandas as pd
import streamlit as st
from selenium import webdriver
from datetime import datetime
from dotenv import load_dotenv
from utils import contains_lowercase, map_leagues, map_teams
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


def main():
    st.set_page_config(page_title="亚盘数据获取")
    st.title("ABS比分盘口自动获取系统")
    load_dotenv()
    scraper = HandicapScraper()

    with st.form("user_input"):
        mode = st.radio("选择模式", options=("赛前盘口", "终场盘口"), index=1)
        if mode == "赛前盘口":
            mode_text = "next"
        elif mode == "终场盘口":
            mode_text = "last"

        headless = st.toggle("Headless", value=True, help="运行时隐藏浏览器")
        submitted = st.form_submit_button("运行")

    if submitted:
        driver = scraper.init_service(mode_text, headless)
        st.success("初始化完成！")
        df_selected = scraper.read_file()

        # Scrape matches for each league and save as a df
        frames = []
        league_names = df_selected["联赛"].apply(map_leagues)
        for league_name in league_names.unique():
            # for league_name in stqdm(league_names.unique(), '获取数据中'):
            try:
                with st.spinner("正在获取" + league_name + "..."):
                    scraper.select_league(driver, league_name)
                    df_result = scraper.scrape(driver)
                    df_result = scraper.clean_result(df_result)
                    frames.append(df_result)
            except:
                st.error("获取联赛失败：" + league_name)

        # Combine all dfs to a single df
        final_result = pd.concat(frames)
        final_result["主队"] = final_result["主队"].apply(map_teams)
        final_result["客队"] = final_result["客队"].apply(map_teams)
        final_result["比赛"] = final_result["主队"] + "-" + final_result["客队"]
        final_result["赛果"] = (
            final_result["主队"]
            + final_result["H"]
            + "-"
            + final_result["A"]
            + final_result["客队"]
        )
        final_result["error"] = final_result["比赛"].apply(contains_lowercase)

        # Combine with original dataset
        for k in range(len(df_selected)):
            game = df_selected.iloc[k, 4].replace(
                " ", ""
            )  # 数据库【比赛】列，清除所有空格
            for i in range(len(final_result)):
                H = final_result.iloc[i, 1]
                A = final_result.iloc[i, 2]
                handicap = final_result.iloc[i, 4]
                home_odd = final_result.iloc[i, 5]
                away_odd = final_result.iloc[i, 6]
                sf_game = final_result.iloc[i, 7]
                sf_result = final_result.iloc[i, 8]
                if game == sf_game or game == sf_result:
                    if mode_text == "last":
                        df_selected.at[k, "比赛"] = sf_result
                        df_selected.at[k, "H"] = H
                        df_selected.at[k, "A"] = A
                    df_selected.at[k, "盘口"] = handicap
                    df_selected.at[k, "主赔"] = home_odd
                    df_selected.at[k, "客赔"] = away_odd
                    break

        if mode_text == "last":
            df_selected["H"] = df_selected["H"].fillna(0)
            df_selected["A"] = df_selected["A"].fillna(0)
            df_selected["H"] = df_selected["H"].astype(int)
            df_selected["A"] = df_selected["A"].astype(int)

        # Export dataset
        today = datetime.today()
        file_name = "//Sofascore_" + today.strftime("%m-%d") + ".xlsx"
        download_path = os.getenv("DOWNLOAD_PATH")
        df_selected.to_excel(
            download_path + file_name, index=False
        )  # change to download button when needed
        st.success("运行成功！数据已下载至桌面")
        st.dataframe(final_result[final_result["error"]])


class HandicapScraper:
    def __init__(self):
        load_dotenv()

    def init_service(self, mode, headless):
        """
        Connect to the website and choose Bet365 as bookmaker
        """
        # Initialize
        driver_path = os.getenv("CHROME_DRIVER_PATH")
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--enable-automation")
        if headless:
            chrome_options.add_argument("--headless")
        try:
            driver = webdriver.Chrome(
                service=Service(executable_path=ChromeDriverManager().install()),
                options=chrome_options,
            )
        except:
            driver = webdriver.Chrome(
                service=Service(executable_path=driver_path), options=chrome_options
            )

        driver.implicitly_wait(10)
        if mode == "last":
            driver.get(os.getenv("HANDICAP_URL_LAST"))
        elif mode == "next":
            driver.get(os.getenv("HANDICAP_URL_NEXT"))
        time.sleep(2)

        try:
            driver.find_element(
                By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"
            ).click()
        except:
            print("no cookie settings")
            # pass
        time.sleep(1)
        driver.fullscreen_window()
        time.sleep(2)  # allow select bookmaker to catch up

        # Select Bookmaker
        select_element = driver.find_element(By.NAME, "book_filter")
        select = Select(select_element)
        select.select_by_visible_text("Bet365")

        time.sleep(2)
        return driver

    def select_league(self, driver, league_name):
        """
        Filter page content by the league name
        """
        # Select League
        select_element = driver.find_element(By.NAME, "search_filter")
        select = Select(select_element)
        select.select_by_visible_text(league_name)

        time.sleep(2)

    def scrape(self, driver):
        """
        The main scaper that collects team names, final scores and handicaps
        """
        # Collect Match Data
        table1 = driver.find_element(
            By.ID, "tablematch1"
        )  # locate data stored in table
        rows = table1.find_elements(By.TAG_NAME, "tr")  # locate each row of table
        home_name = away_name = home_score = away_score = ""
        Home = []
        Away = []
        H = []
        A = []
        for row in rows:
            elements = row.find_elements(
                By.TAG_NAME, "td"
            )  # locate each element of row
            # if first element is H, homescore is [3], if first element is A, awayscore is [2]
            if elements[0].text == "H":
                home_name = elements[1].text
                home_score = elements[3].text
                while home_name[0].isdigit():
                    home_name = home_name[1:]
                Home.append(home_name)
                H.append(home_score)
            elif elements[0].text == "A":
                away_name = elements[1].text
                away_score = elements[2].text
                while away_name[0].isdigit():
                    away_name = away_name[1:]
                Away.append(away_name)
                A.append(away_score)

        # Collect Odds Data
        table2 = driver.find_element(
            By.ID, "tablematch2"
        )  # locate data stored in table
        rows = table2.find_elements(By.TAG_NAME, "tr")  # locate each row of table
        Handicap = []
        HomeOdds = []
        AwayOdds = []
        for row in rows:
            elements = row.find_elements(
                By.TAG_NAME, "td"
            )  # locate each element of row
            if elements[0].text == "H":
                home_handicap = elements[1].text
                home_odds = elements[4].text
                # print(home_handicap)
                Handicap.append(home_handicap)
                HomeOdds.append(home_odds)
            elif elements[0].text == "A":
                away_odds = elements[4].text
                AwayOdds.append(away_odds)

        # Create dataframe columns from lists
        df_result = pd.DataFrame()
        df_result["主队"] = Home
        df_result["H"] = H
        df_result["A"] = A
        df_result["客队"] = Away
        df_result["盘口"] = Handicap
        df_result["主赔"] = HomeOdds
        df_result["客赔"] = AwayOdds

        return df_result

    def clean_result(self, df_result):
        # Data Cleaning
        df_result.loc[
            (df_result["盘口"] == "0") & (df_result["主赔"] < df_result["客赔"]), "盘口"
        ] = "-0"
        df_result.loc[
            (df_result["盘口"] == "0") & (df_result["主赔"] > df_result["客赔"]), "盘口"
        ] = "+0"
        df_result.loc[
            (df_result["盘口"] == "0") & (df_result["主赔"] == df_result["客赔"]),
            "盘口",
        ] = "0"
        df_result["盘口"] = df_result["盘口"].apply(self.clean_handicap)

        return df_result

    def clean_handicap(self, handicap_value):
        if not handicap_value.startswith("-") and not handicap_value.startswith("+"):
            return "+" + handicap_value
        else:
            return handicap_value

    def read_file(self):
        # read from local file
        url = os.getenv("LOCAL_DATA_PATH")

        df = pd.read_excel(
            url,
            sheet_name=1,
            converters={"盘口": str, "竞彩": str, "比分": str},
            skiprows=[1, 90000],
        )  # read last n rows for performance
        df["开球时间"] = df["开球时间"].fillna("")
        df["注释"] = df["注释"].fillna("")

        df_selected = df[df["盘口"].isnull()]
        df_selected = df_selected.reset_index()
        del df_selected["index"]

        return df_selected


if __name__ == "__main__":
    main()

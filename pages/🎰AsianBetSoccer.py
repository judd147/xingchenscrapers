# -*- coding: utf-8 -*-
"""
Created on 12/26/2023
Last Edit 08/16/2025
@author: Liyao Zhang

Asian Handicap scraper with Streamlit
"""
import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)
import os
import pandas as pd
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from utils import contains_lowercase, map_leagues, map_teams
from models import HandicapScraper


def main():
    st.set_page_config(page_title="亚盘数据获取")
    st.title("ABS比分盘口自动获取系统")
    load_dotenv()
    scraper = HandicapScraper()

    with st.form("user_input"):
        mode = st.radio("选择模式", options=("赛前盘口", "终场盘口", "晚场"), index=1)
        if mode == "赛前盘口":
            mode_text = "next"
        elif mode == "终场盘口":
            mode_text = "last"
        elif mode == "晚场":  # workaround for bug on ABS
            mode_text = "live"

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
                    scraper.select_league(driver, league_name, mode_text)
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


if __name__ == "__main__":
    main()

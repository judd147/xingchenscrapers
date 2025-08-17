# -*- coding: utf-8 -*-
"""
Created on 12/24/2023
Last Edit 08/16/2025
@author: Liyao Zhang

星辰智盈数据自动获取系统 with Streamlit
"""
import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)

import os
import time
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime, timedelta
from utils import pct_to_float, strip_parent, clean_leagues, clean_teams
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def main():
    st.set_page_config(
        page_title="星辰数据获取",
    )
    st.title("星辰智盈数据自动获取系统")
    load_dotenv()

    scraper = XingchenScraper()

    # Mode & Time
    today = datetime.today().replace(minute=0)
    today_modified = today.replace(minute=0, second=0, microsecond=0)
    get_qbl = get_zsxt = get_ohfc = get_gplj = get_sqnl = get_lsqt = False
    with st.form("user_input"):
        mode = st.radio(
            "选择模式",
            options=("全选", "早盘", "临场"),
            help="全选包括早盘临场6大算法；早盘算法指球伯乐、指数形态和欧核方差；临场算法指公平量价、赛前能量和联赛球探",
        )
        if mode == "全选":
            get_qbl = get_zsxt = get_ohfc = get_gplj = get_sqnl = get_lsqt = True
        elif mode == "早盘":
            get_qbl = get_zsxt = get_ohfc = True
        elif mode == "临场":
            get_gplj = get_sqnl = get_lsqt = True
        col1, col2 = st.columns(2)
        with col1:
            start_time = st.slider(
                "开始时间",
                value=today_modified,
                min_value=today_modified - timedelta(hours=30),
                max_value=today_modified + timedelta(hours=10),
                step=timedelta(minutes=30),
                format="MM/DD - HH:mm",
            ).strftime("%m-%d %H:%M")

        with col2:
            end_time = st.slider(
                "结束时间",
                value=today_modified,
                min_value=today_modified - timedelta(hours=24),
                max_value=today_modified + timedelta(hours=16),
                step=timedelta(minutes=30),
                format="MM/DD - HH:mm",
            ).strftime("%m-%d %H:%M")
            headless = st.toggle("Headless", value=True, help="运行时隐藏浏览器")

        submitted = st.form_submit_button("运行")

    if submitted:
        start_clock = time.time()  # 统计时间
        st.info(f"已选择{mode}模式 {start_time}-{end_time}")
        driver = scraper.init_service(headless)
        scraper.login(driver)
        time.sleep(5)
        algos = driver.find_elements(By.CLASS_NAME, "title")
        st.success("初始化完成！")

        # Iterate through each algo
        for algo in algos:
            text = algo.text
            if text == "球伯乐" and get_qbl:
                algo.click()
                with st.spinner("正在获取球伯乐数据..."):
                    df_qbl = scraper.scrape(driver, "", start_time, end_time)
            else:
                pass

        for algo in algos:
            text = algo.text
            if text == "指数形态" and get_zsxt:
                algo.click()
                with st.spinner("正在获取指数形态数据..."):
                    df_zsxt = scraper.scrape(driver, text, start_time, end_time)
            else:
                pass

        for algo in algos:
            text = algo.text
            if text == "欧核方差" and get_ohfc:
                algo.click()
                with st.spinner("正在获取欧核方差数据..."):
                    df_ohfc = scraper.scrape(driver, text, start_time, end_time)
            else:
                pass

        for algo in algos:
            text = algo.text
            if text == "公平量价" and get_gplj:
                algo.click()
                with st.spinner("正在获取公平量价数据..."):
                    df_gplj = scraper.scrape(driver, text, start_time, end_time)
            else:
                pass

        for algo in algos:
            text = algo.text
            if text == "赛前能量" and get_sqnl:
                algo.click()
                with st.spinner("正在获取赛前能量数据..."):
                    df_sqnl = scraper.scrape(driver, text, start_time, end_time)
            else:
                pass

        for algo in algos:
            text = algo.text
            if text == "联赛球探" and get_lsqt:
                algo.click()
                with st.spinner("正在获取联赛球探数据..."):
                    df_lsqt = scraper.scrape(driver, text, start_time, end_time)
            else:
                pass

        # Combine data
        if mode == "全选":
            df_final = pd.concat([df_qbl, df_zsxt, df_ohfc, df_gplj, df_sqnl, df_lsqt])
        elif mode == "早盘":
            df_final = pd.concat([df_qbl, df_zsxt, df_ohfc])
        elif mode == "临场":
            with st.spinner("合并数据中..."):
                url = os.getenv("LOCAL_DATA_PATH")
                df = scraper.read_file(url)
                df_selected = df[
                    (df["开球时间"] >= start_time) & (df["年"] == datetime.now().year)
                ]
                data_selected = pd.concat([df_gplj, df_sqnl, df_lsqt])
                df_final = pd.concat([df_selected, data_selected])

        # 下载/上传数据库现状：读通过onedrive，写通过下载excel表，人工审核后复制粘贴到onedrive
        # 方案一：所有读写均通过MySQL数据库，管理员定期负责下载最新数据并同步给onedrive
        # 方案二：读写直接通过调用onedrive，需要检查数据重复
        df_final = df_final.sort_values(by=["开球时间", "联赛", "比赛"])
        file_name = "//星辰数据_{mode}{date}.xlsx".format(
            mode=mode, date=today.strftime("%m-%d")
        )
        df_final.to_excel(os.getenv("DOWNLOAD_PATH") + file_name, index=False)

        elapsed_time = time.time() - start_clock
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        st.success(f"数据获取成功！耗时: {minutes} 分 {seconds} 秒")


class XingchenScraper:
    def __init__(self):
        load_dotenv()

    def init_service(self, headless):
        driver_path = os.getenv("CHROME_DRIVER_PATH")
        # Mobile Device
        mobile_emulation = {"deviceName": "iPhone 12 Pro"}

        # Initialize Driver
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--enable-automation")
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
        try:
            driver = webdriver.Chrome(
                service=Service(executable_path=ChromeDriverManager().install()),
                options=chrome_options,
            )
        except:
            driver = webdriver.Chrome(
                service=Service(executable_path=driver_path), options=chrome_options
            )

        # Open web page
        driver.get(os.getenv("XINGCHEN_URL"))
        driver.fullscreen_window()
        return driver

    def login(self, driver):
        try:
            driver.find_element(By.CLASS_NAME, "van-dialog__cancel").click()
        except:
            pass
        # Input the phone number
        phone_input = (
            WebDriverWait(driver, 10)
            .until(
                EC.presence_of_element_located((By.CLASS_NAME, "van-field__control"))
            )
            .send_keys(os.getenv("XINGCHEN_NUMBER"))
        )

        # Input the password
        password_input = driver.find_elements(By.CLASS_NAME, "van-field__control")[1]
        password_input.send_keys(os.getenv("XINGCHEN_KEY"))

        # Login button
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "login-btn"))
        )
        login_button.click()

    def unlock(self, driver):
        """Unlock matches"""
        locked = True
        while locked:
            try:
                driver.find_element(
                    By.CSS_SELECTOR, 'p[class="b-enable"][data-v-308224e0]'
                )
                locked = False
            except:
                unlock_button = driver.find_element(
                    By.CSS_SELECTOR, 'p[class=""][data-v-308224e0]'
                )
                unlock_button.click()
            time.sleep(2)

    def back(self, driver):
        back_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'img[class="back"][data-v-5c3272b5]')
            )
        )
        back_button.click()

    def get_matches(self, driver, algo_name, start_time, end_time):
        """Collect and parse data"""
        df = pd.DataFrame(
            columns=[
                "开球时间",
                "算法",
                "联赛",
                "比赛",
                "胜",
                "平",
                "负",
                "H",
                "A",
                "让胜",
                "让平",
                "让负",
                "盘口",
                "注释",
                "比分",
                "进球数",
                "竞彩",
            ]
        )
        match_list = driver.find_element(By.CLASS_NAME, "matchs-ul")
        matches = match_list.find_elements(By.TAG_NAME, "li")
        for match in matches:
            match_info = match.text
            match_context = match_info.split("\n")[0]
            game = match_info.split("\n")[1]
            date = match_context.split(" ")[0] + " " + match_context.split(" ")[1]
            league = (
                match_context.split(" ")[2].replace("完赛", "").replace("进行中", "")
            )
            # proceed if league is target
            league_name, isTarget = clean_leagues(league)
            if isTarget and (start_time <= date <= end_time):
                # team names
                if game.__contains__("["):
                    home = game.split(" ")[1]
                    away = game.split(" ")[3]
                else:
                    home = game.split(" ")[0]
                    away = game.split(" ")[2]
                home, away = clean_teams(home, away, league_name)
                # scoreline
                if game.__contains__("VS"):
                    H = None
                    A = None
                    match_text = home + "-" + away
                else:
                    part1 = game.split(":")[0]
                    part2 = game.split(":")[1]
                    H = part1.split(" ")[-1]
                    A = part2.split(" ")[0]
                    match_text = home + H + "-" + A + away
                    H = int(H)
                    A = int(A)

                # Match detail
                if match_context.split(" ")[2].__contains__("完赛"):
                    show_button = match.find_element(By.CLASS_NAME, "show.show-end")
                else:
                    show_button = match.find_element(By.CLASS_NAME, "show")
                show_button.click()

                time.sleep(2)

                # jingcai
                detail_context = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'div[class="time"][data-v-0a37cbfe]')
                    )
                )
                if detail_context.text.__contains__("竞彩"):
                    jingcai = "是"
                else:
                    jingcai = ""

                # probabilities
                prob1 = (
                    WebDriverWait(driver, 50)
                    .until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "/html/body/div[1]/div/div[1]/div/div[4]/div/div[2]/div[2]/div/div[4]/div/div[2]/div[1]/div/div/div[1]",
                            )
                        )
                    )
                    .text
                )
                p_win = pct_to_float(prob1.split("\n")[0].split("主胜")[1])
                sp_home = float(prob1.split("\n")[1].replace("sp", ""))

                prob2 = driver.find_element(
                    By.XPATH,
                    "/html/body/div[1]/div/div[1]/div/div[4]/div/div[2]/div[2]/div/div[4]/div/div[2]/div[1]/div/div/div[2]",
                ).text
                p_draw = pct_to_float(prob2.split("\n")[0].split("平局")[1])

                prob3 = driver.find_element(
                    By.XPATH,
                    "/html/body/div[1]/div/div[1]/div/div[4]/div/div[2]/div[2]/div/div[4]/div/div[2]/div[1]/div/div/div[3]",
                ).text
                p_loss = pct_to_float(prob3.split("\n")[0].split("客胜")[1])
                sp_away = float(prob3.split("\n")[1].replace("sp", ""))

                prob4 = driver.find_element(
                    By.XPATH,
                    "/html/body/div[1]/div/div[1]/div/div[4]/div/div[2]/div[2]/div/div[4]/div/div[2]/div[2]/div/div/div[1]",
                ).text
                p_hand_win = pct_to_float(prob4.split("\n")[0].split("让胜")[1])

                prob5 = driver.find_element(
                    By.XPATH,
                    "/html/body/div[1]/div/div[1]/div/div[4]/div/div[2]/div[2]/div/div[4]/div/div[2]/div[2]/div/div/div[2]",
                ).text
                p_hand_draw = pct_to_float(prob5.split("\n")[0].split("让平")[1])

                prob6 = driver.find_element(
                    By.XPATH,
                    "/html/body/div[1]/div/div[1]/div/div[4]/div/div[2]/div[2]/div/div[4]/div/div[2]/div[2]/div/div/div[3]",
                ).text
                p_hand_loss = pct_to_float(prob6.split("\n")[0].split("让负")[1])

                # handicap
                hand_info = driver.find_element(
                    By.XPATH,
                    '//*[@id="app"]/div/div[1]/div/div[4]/div/div[2]/div[2]/div/div[4]/div/div[2]/div[2]/p/span[1]',
                ).text
                num_hand = strip_parent(hand_info).replace("1", "")

                if jingcai == "是":
                    comment = num_hand
                else:
                    if sp_home < sp_away:
                        comment = "-"
                    elif sp_home > sp_away:
                        comment = "+"
                    else:
                        comment = "NA"

                # sample size
                bar_list = []
                bars = driver.find_elements(By.CLASS_NAME, "d-s-per")
                for bar in bars:
                    bar_list.append(bar.text)
                goals_list = list(map(pct_to_float, bar_list))
                goals_list = [x for x in goals_list if x > 0]

                if min(goals_list) <= 0.1:
                    small_sample = False
                    # print('大样本', min(goals_list))
                else:
                    small_sample = True
                    # print('小样本', min(goals_list))

                # recommended scoreline
                top_score = driver.find_elements(By.CLASS_NAME, "p-b-d-s.first-s")[
                    -1
                ].text.split("\n")[0]
                sec_score = driver.find_elements(By.CLASS_NAME, "p-b-d-s.second-s")[
                    -1
                ].text.split("\n")[0]
                scoreline = (
                    top_score.replace(":", "-") + " " + sec_score.replace(":", "-")
                )

                # append to dataframe
                if not small_sample:
                    row_data = {
                        "开球时间": date,
                        "算法": algo_name,
                        "联赛": league_name,
                        "比赛": match_text,
                        "胜": p_win,
                        "平": p_draw,
                        "负": p_loss,
                        "H": H,
                        "A": A,
                        "让胜": p_hand_win,
                        "让平": p_hand_draw,
                        "让负": p_hand_loss,
                        "注释": comment,
                        "比分": scoreline,
                        "竞彩": jingcai,
                    }
                    # df = df.append(row_data, ignore_index=True)
                    row_data_df = pd.DataFrame([row_data])
                    df = pd.concat([df, row_data_df], ignore_index=True)

                back_button = driver.find_element(
                    By.XPATH,
                    '//*[@id="app"]/div/div[1]/div/div[4]/div/div[2]/div[2]/div/div[4]/div/div[1]/div/img',
                )
                back_button.click()
        return df

    def scrape(self, driver, algo_name, start_time, end_time):
        time.sleep(2)
        self.unlock(driver)
        df = self.get_matches(driver, algo_name, start_time, end_time)
        self.back(driver)
        return df

    def read_file(self, data):
        df = pd.read_excel(
            data, sheet_name=1, converters={"盘口": str, "竞彩": str, "比分": str}
        )
        df["盘口数字"] = df["盘口"].astype(float)
        df["注释"] = df["注释"].fillna("")
        return df


if __name__ == "__main__":
    main()

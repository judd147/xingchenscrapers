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
from selenium.webdriver.common.by import By
from models import XingchenScraper


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


if __name__ == "__main__":
    main()

import os
import time
import pandas as pd
from dotenv import load_dotenv
from utils import pct_to_float, strip_parent, clean_leagues, clean_teams
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class XingchenScraper:
    def __init__(self):
        load_dotenv()

    def init_service(self, headless):
        """create and return a selenium driver that opens the Xingchen webpage"""
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
        """Login to Xingchen"""
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
                    "//p[@class='p-t' and contains(., '亚洲指数')]//span[@class='h-d']",
                ).text

                # hand_info = driver.find_element(
                #     By.XPATH,
                #     '//*[@id="app"]/div/div[1]/div/div[4]/div/div[2]/div[2]/div/div[4]/div/div[2]/div[2]/p/span[1]',
                # ).text
                num_hand = strip_parent(hand_info)

                if num_hand == "0":
                    if sp_home < sp_away:
                        comment = "-"
                    elif sp_home > sp_away:
                        comment = "+"
                    else:
                        comment = "NA"
                elif num_hand.startswith("-"):
                    comment = "-"
                else:
                    comment = "+"

                # if jingcai == "是":
                #     comment = num_hand
                # else:
                #     if sp_home < sp_away:
                #         comment = "-"
                #     elif sp_home > sp_away:
                #         comment = "+"
                #     else:
                #         comment = "NA"

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

        # dismiss cookie modal
        try:
            driver.find_element(
                By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"
            ).click()
        except:
            print("no cookie settings")

        time.sleep(2)
        driver.fullscreen_window()

        # dismiss new update modal
        try:
            driver.find_element(By.CLASS_NAME, "banner-close").click()
        except:
            print("no new update banner")

        if mode == "next":
            date_input = driver.find_element(By.ID, "value_next")
            date_input.send_keys(Keys.ARROW_RIGHT)  # move to day input
            date_input.send_keys(Keys.ARROW_DOWN)

        # elif mode == "last":
        #     date_input = driver.find_element(By.ID, "value_last")
        #     date_input.send_keys(Keys.ARROW_RIGHT)
        #     date_input.send_keys(Keys.ARROW_DOWN)

        time.sleep(2)  # allow select bookmaker to catch up

        # Select Bookmaker
        select_element = driver.find_element(By.NAME, "book_filter")
        select = Select(select_element)
        select.select_by_visible_text("Bet365")

        time.sleep(2)
        return driver

    def select_league(self, driver, league_name, mode):
        """
        Filter page content by the league name
        """
        # Select League
        select_element = driver.find_element(By.NAME, "search_filter")
        select = Select(select_element)
        select.select_by_visible_text(league_name)

        if mode == "next":
            date_input = driver.find_element(By.ID, "value_next")
            date_input.send_keys(Keys.ARROW_RIGHT)  # move to day input
            date_input.send_keys(Keys.ARROW_DOWN)

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
        """
        Read local excel file for matches that need handicap data
        """
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

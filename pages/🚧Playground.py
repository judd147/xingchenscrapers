# -*- coding: utf-8 -*-
"""
Created on 08/17/2025
@author: Optimized Soccer Data Platform

Streamlit app with background data fetching, SQLite storage, and real-time updates
"""

import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)
import os
import time
import sqlite3
import threading
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor
from models import XingchenScraper, HandicapScraper  # , BacktestEngine


class DatabaseManager:
    """Manages SQLite database operations for caching scraped data"""

    def __init__(self, db_path: str = "soccer_data.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            # Xingchen data table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS xingchen_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    年 INTEGER,
                    开球时间 TEXT,
                    算法 TEXT,
                    联赛 TEXT,
                    比赛 TEXT,
                    胜 REAL,
                    平 REAL,
                    负 REAL,
                    H INTEGER,
                    A INTEGER,
                    让胜 REAL,
                    让平 REAL,
                    让负 REAL,
                    盘口 TEXT,
                    注释 TEXT,
                    比分 TEXT,
                    进球数 INTEGER,
                    竞彩 TEXT,
                    主赔 REAL,
                    客赔 REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(开球时间, 算法, 比赛)
                )
            """
            )

            # Handicap data table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS handicap_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    主队 TEXT,
                    客队 TEXT,
                    H INTEGER,
                    A INTEGER,
                    盘口 TEXT,
                    主赔 REAL,
                    客赔 REAL,
                    比赛 TEXT,
                    联赛 TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(比赛)
                )
            """
            )

            # Backtest results table (placeholder for future ML model)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS backtest_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT,
                    match_id TEXT,
                    比赛 TEXT,
                    开球时间 TEXT,
                    prediction TEXT,
                    confidence REAL,
                    actual_result TEXT,
                    profit_loss REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Data fetch status table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS fetch_status (
                    source TEXT PRIMARY KEY,
                    last_fetch TIMESTAMP,
                    status TEXT,
                    error_message TEXT,
                    records_fetched INTEGER DEFAULT 0
                )
            """
            )

    def insert_xingchen_data(self, df: pd.DataFrame) -> int:
        """Insert Xingchen data with conflict handling, returns number of new records"""
        if df.empty:
            return 0

        initial_count = self.get_xingchen_count()

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Convert DataFrame to list of tuples
                columns = df.columns.tolist()
                values = df.values.tolist()

                # Create placeholders for the query
                placeholders = ",".join(["?"] * len(columns))
                column_names = ",".join(columns)

                # Use INSERT OR IGNORE to handle conflicts
                query = f"INSERT OR IGNORE INTO xingchen_data ({column_names}) VALUES ({placeholders})"

                conn.executemany(query, values)
                conn.commit()

        except Exception as e:
            print(f"Error inserting Xingchen data: {e}")
            return 0

        final_count = self.get_xingchen_count()
        return final_count - initial_count

    def insert_handicap_data(self, df: pd.DataFrame) -> int:
        """Insert handicap data with conflict handling, returns number of new records"""
        if df.empty:
            return 0

        initial_count = self.get_handicap_count()

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Convert DataFrame to list of tuples
                columns = df.columns.tolist()
                values = df.values.tolist()

                # Create placeholders for the query
                placeholders = ",".join(["?"] * len(columns))
                column_names = ",".join(columns)

                # Use INSERT OR IGNORE to handle conflicts
                query = f"INSERT OR IGNORE INTO handicap_data ({column_names}) VALUES ({placeholders})"

                conn.executemany(query, values)
                conn.commit()

        except Exception as e:
            print(f"Error inserting Handicap data: {e}")
            return 0

        final_count = self.get_handicap_count()
        return final_count - initial_count

    def get_xingchen_data(
        self, start_time: str = None, end_time: str = None, algorithms: list = None
    ) -> pd.DataFrame:
        """Retrieve Xingchen data based on time range and algorithms"""
        query = "SELECT * FROM xingchen_data WHERE 1=1"
        params = []

        if start_time and end_time:
            query += " AND 开球时间 BETWEEN ? AND ?"
            params.extend([start_time, end_time])

        if algorithms:
            placeholders = ",".join(["?" for _ in algorithms])
            query += f" AND 算法 IN ({placeholders})"
            params.extend(algorithms)

        query += " ORDER BY 开球时间, 联赛, 比赛"

        try:
            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql_query(query, conn, params=params)
        except Exception as e:
            print(f"Error retrieving Xingchen data: {e}")
            return pd.DataFrame()

    def get_handicap_data(self, matches: list = None) -> pd.DataFrame:
        """Retrieve handicap data for specific matches"""
        try:
            if matches:
                placeholders = ",".join(["?" for _ in matches])
                query = f"SELECT * FROM handicap_data WHERE 比赛 IN ({placeholders})"
                with sqlite3.connect(self.db_path) as conn:
                    return pd.read_sql_query(query, conn, params=matches)
            else:
                with sqlite3.connect(self.db_path) as conn:
                    return pd.read_sql_query("SELECT * FROM handicap_data", conn)
        except Exception as e:
            print(f"Error retrieving Handicap data: {e}")
            return pd.DataFrame()

    def get_latest_match_time(self) -> Optional[str]:
        """Get the latest match time from Xingchen data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT MAX(开球时间) FROM xingchen_data")
                result = cursor.fetchone()[0]
                return result
        except Exception:
            return None

    def get_existing_matches(self, start_time: str, end_time: str) -> set:
        """Get existing match IDs (开球时间 + 比赛) to avoid duplicates"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                    SELECT DISTINCT 开球时间 || '|' || 比赛 as match_id 
                    FROM xingchen_data 
                    WHERE 开球时间 BETWEEN ? AND ?
                """
                cursor = conn.execute(query, (start_time, end_time))
                return {row[0] for row in cursor.fetchall()}
        except Exception:
            return set()

    def get_matches_without_handicap(self) -> List[str]:
        """Get matches that exist in xingchen_data but not in handicap_data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                    SELECT DISTINCT x.比赛 
                    FROM xingchen_data x
                    LEFT JOIN handicap_data h ON x.比赛 = h.比赛
                    WHERE h.比赛 IS NULL
                    AND x.开球时间 >= datetime('now', '-24 hours')
                """
                cursor = conn.execute(query)
                return [row[0] for row in cursor.fetchall()]
        except Exception:
            return []

    def update_fetch_status(
        self,
        source: str,
        status: str,
        error_message: str = None,
        records_fetched: int = 0,
    ):
        """Update fetch status for data sources"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO fetch_status 
                    (source, last_fetch, status, error_message, records_fetched)
                    VALUES (?, datetime('now'), ?, ?, ?)
                """,
                    (source, status, error_message, records_fetched),
                )
        except Exception as e:
            print(f"Error updating fetch status: {e}")

    def get_fetch_status(self) -> Dict[str, Any]:
        """Get status of all data sources"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT * FROM fetch_status")
                return {
                    row[0]: {
                        "last_fetch": row[1],
                        "status": row[2],
                        "error_message": row[3],
                        "records_fetched": row[4] or 0,
                    }
                    for row in cursor.fetchall()
                }
        except Exception:
            return {}

    def get_xingchen_count(self) -> int:
        """Get total count of Xingchen records"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM xingchen_data")
                return cursor.fetchone()[0]
        except Exception:
            return 0

    def get_handicap_count(self) -> int:
        """Get total count of Handicap records"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM handicap_data")
                return cursor.fetchone()[0]
        except Exception:
            return 0

    def reset_database(self):
        """Reset all data tables (admin function)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM xingchen_data")
                conn.execute("DELETE FROM handicap_data")
                conn.execute("DELETE FROM backtest_results")
                conn.execute("UPDATE fetch_status SET records_fetched = 0")
                conn.commit()
        except Exception as e:
            print(f"Error resetting database: {e}")


class BackgroundTaskManager:
    """Handles background data fetching with threading and smart caching"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.xingchen_scraper = XingchenScraper()
        self.handicap_scraper = HandicapScraper()
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.fetch_interval = 300  # 5 minutes
        self.is_running = False
        self.fetch_lock = threading.Lock()

    def start_background_fetch(self):
        """Start background fetching in a separate thread"""
        if not self.is_running:
            self.is_running = True
            threading.Thread(target=self._background_fetch_loop, daemon=True).start()
            print("Background fetch started")

    def stop_background_fetch(self):
        """Stop background fetching"""
        self.is_running = False
        print("Background fetch stopped")

    def _background_fetch_loop(self):
        """Main background fetch loop"""
        while self.is_running:
            try:
                # Acquire lock to prevent concurrent fetching
                with self.fetch_lock:
                    # Fetch Xingchen data first
                    xingchen_records = self._fetch_xingchen_data()

                    # Then fetch Handicap data for matches without it
                    handicap_records = self._fetch_handicap_data()

                    # Future: Run backtest engine here
                    # self._run_backtest()

                print(
                    f"Background fetch completed. Xingchen: {xingchen_records}, Handicap: {handicap_records}"
                )

                # Wait for next interval
                time.sleep(self.fetch_interval)

            except Exception as e:
                print(f"Background fetch error: {e}")
                self.db_manager.update_fetch_status("background", "error", str(e))
                time.sleep(60)  # Wait 1 minute before retrying

    def _fetch_xingchen_data(self) -> int:
        """Fetch Xingchen data in background with smart time range"""
        try:
            self.db_manager.update_fetch_status("xingchen", "fetching")

            # Smart time range calculation
            now = datetime.now()

            # Get the latest match time from database
            latest_time = self.db_manager.get_latest_match_time()

            if latest_time:
                # Parse the latest time and go back a few hours to catch any updates
                try:
                    # Assuming format is "MM-DD HH:MM"
                    latest_dt = datetime.strptime(
                        f"2024-{latest_time}", "%Y-%m-%d %H:%M"
                    )
                    start_time = (latest_dt - timedelta(hours=6)).strftime(
                        "%m-%d %H:%M"
                    )
                except:
                    # Fallback if parsing fails
                    start_time = (now - timedelta(hours=12)).strftime("%m-%d %H:%M")
            else:
                # No data exists, fetch from 12 hours ago
                start_time = (now - timedelta(hours=12)).strftime("%m-%d %H:%M")

            # Fetch for next 24 hours
            end_time = (now + timedelta(hours=24)).strftime("%m-%d %H:%M")

            # Get existing matches to avoid complete duplicates
            existing_matches = self.db_manager.get_existing_matches(
                start_time, end_time
            )

            print(f"Fetching Xingchen data from {start_time} to {end_time}")

            # Fetch data using existing scraper logic
            df_data = self._scrape_xingchen_background(start_time, end_time)

            if not df_data.empty:
                # Filter out existing matches
                df_data["match_id"] = df_data["开球时间"] + "|" + df_data["比赛"]
                df_new = df_data[~df_data["match_id"].isin(existing_matches)]
                df_new = df_new.drop("match_id", axis=1)

                new_records = self.db_manager.insert_xingchen_data(df_new)
                self.db_manager.update_fetch_status(
                    "xingchen", "success", records_fetched=new_records
                )
                return new_records
            else:
                self.db_manager.update_fetch_status("xingchen", "no_data")
                return 0

        except Exception as e:
            self.db_manager.update_fetch_status("xingchen", "error", str(e))
            print(f"Error fetching Xingchen data: {e}")
            return 0

    def _fetch_handicap_data(self) -> int:
        """Fetch Handicap data for matches without it"""
        try:
            self.db_manager.update_fetch_status("handicap", "fetching")

            # Get matches that need handicap data
            matches_needing_handicap = self.db_manager.get_matches_without_handicap()

            if matches_needing_handicap:
                print(
                    f"Fetching handicap data for {len(matches_needing_handicap)} matches"
                )

                df_handicap = self._scrape_handicap_background(matches_needing_handicap)

                if not df_handicap.empty:
                    new_records = self.db_manager.insert_handicap_data(df_handicap)
                    self.db_manager.update_fetch_status(
                        "handicap", "success", records_fetched=new_records
                    )
                    return new_records
                else:
                    self.db_manager.update_fetch_status("handicap", "no_data")
                    return 0
            else:
                self.db_manager.update_fetch_status("handicap", "no_matches")
                return 0

        except Exception as e:
            self.db_manager.update_fetch_status("handicap", "error", str(e))
            print(f"Error fetching Handicap data: {e}")
            return 0

    def _scrape_xingchen_background(
        self, start_time: str, end_time: str
    ) -> pd.DataFrame:
        """Scrape Xingchen data without UI (headless) - all 6 algorithms"""
        try:
            driver = self.xingchen_scraper.init_service(headless=True)
            self.xingchen_scraper.login(driver)
            time.sleep(3)

            # Get all algorithm elements
            algos = driver.find_elements("class name", "title")

            all_data = []
            algo_names = [
                "球伯乐",
                "指数形态",
                "欧核方差",
                "公平量价",
                "赛前能量",
                "联赛球探",
            ]

            for algo in algos:
                text = algo.text
                if text in algo_names:
                    try:
                        algo.click()
                        time.sleep(2)
                        df = self.xingchen_scraper.scrape(
                            driver, text, start_time, end_time
                        )
                        if not df.empty:
                            all_data.append(df)
                        print(f"Scraped {text}: {len(df)} records")
                    except Exception as e:
                        print(f"Error scraping {text}: {e}")

            driver.quit()

            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                combined_df = combined_df.sort_values(by=["开球时间", "联赛", "比赛"])
                return combined_df
            else:
                return pd.DataFrame()

        except Exception as e:
            print(f"Error in Xingchen background scraping: {e}")
            return pd.DataFrame()

    def _scrape_handicap_background(self, matches: List[str]) -> pd.DataFrame:
        """Scrape Handicap data without UI (headless)"""
        try:
            driver = self.handicap_scraper.init_service("last", headless=True)

            # Get the matches data from database to extract leagues
            df_selected = self.db_manager.get_xingchen_data()
            df_matches = df_selected[df_selected["比赛"].isin(matches)]

            if df_matches.empty:
                driver.quit()
                return pd.DataFrame()

            # Import utility functions (you'll need to make sure these are available)
            from utils import map_leagues, map_teams, contains_lowercase

            frames = []
            league_names = df_matches["联赛"].apply(map_leagues)

            for league_name in league_names.unique():
                try:
                    self.handicap_scraper.select_league(driver, league_name)
                    df_result = self.handicap_scraper.scrape(driver)
                    df_result = self.handicap_scraper.clean_result(df_result)
                    if not df_result.empty:
                        frames.append(df_result)
                except Exception as e:
                    print(f"Error scraping handicap for league {league_name}: {e}")

            driver.quit()

            if frames:
                final_result = pd.concat(frames, ignore_index=True)
                final_result["主队"] = final_result["主队"].apply(map_teams)
                final_result["客队"] = final_result["客队"].apply(map_teams)
                final_result["比赛"] = final_result["主队"] + "-" + final_result["客队"]

                # Filter only matches we need
                final_result = final_result[final_result["比赛"].isin(matches)]
                return final_result
            else:
                return pd.DataFrame()

        except Exception as e:
            print(f"Error in Handicap background scraping: {e}")
            return pd.DataFrame()

    def manual_fetch_now(self):
        """Manual fetch trigger for immediate update"""
        if not self.fetch_lock.locked():
            threading.Thread(target=self._manual_fetch, daemon=True).start()
            return True
        return False

    def _manual_fetch(self):
        """Execute manual fetch"""
        try:
            with self.fetch_lock:
                xingchen_records = self._fetch_xingchen_data()
                handicap_records = self._fetch_handicap_data()
                print(
                    f"Manual fetch completed. Xingchen: {xingchen_records}, Handicap: {handicap_records}"
                )
        except Exception as e:
            print(f"Manual fetch error: {e}")


class StreamlitApp:
    """Main Streamlit application with optimized UI"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.background_manager = BackgroundTaskManager(self.db_manager)

        # Initialize session state
        if "background_started" not in st.session_state:
            st.session_state.background_started = False

        if "last_refresh" not in st.session_state:
            st.session_state.last_refresh = datetime.now()

    def run(self):
        """Main application entry point"""
        st.set_page_config(
            page_title="⚽ 智能足球数据平台",
            page_icon="⚽",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        st.title("⚽ 智能足球数据平台")
        st.markdown("*实时数据 • 自动更新 • 智能预测*")

        # Start background fetching
        if not st.session_state.background_started:
            self.background_manager.start_background_fetch()
            st.session_state.background_started = True
            st.success("🔄 后台数据获取已启动")

        # Sidebar for controls
        self._render_sidebar()

        # Main content tabs
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📊 数据查询", "📈 实时监控", "🎯 预测结果", "⚙️ 系统状态"]
        )

        with tab1:
            self._render_data_query()

        with tab2:
            self._render_real_time_monitor()

        with tab3:
            self._render_predictions()

        with tab4:
            self._render_system_status()

    def _render_sidebar(self):
        """Render sidebar controls"""
        st.sidebar.header("🎛️ 控制面板")

        # Manual refresh button
        if st.sidebar.button("🔄 立即刷新数据", key="manual_refresh"):
            if self.background_manager.manual_fetch_now():
                st.sidebar.success("手动刷新已启动...")
            else:
                st.sidebar.warning("数据获取正在进行中，请稍候...")

        # Settings
        st.sidebar.header("⚙️ 设置")
        fetch_interval = st.sidebar.slider(
            "数据获取间隔 (分钟)", min_value=1, max_value=60, value=5
        )
        self.background_manager.fetch_interval = fetch_interval * 60

        # Database management
        st.sidebar.header("🗃️ 数据库管理")
        if st.sidebar.button("🗑️ 重置数据库", type="secondary"):
            self.db_manager.reset_database()
            st.sidebar.success("数据库已重置")

        # Database info
        st.sidebar.header("💾 数据库信息")
        try:
            db_size = os.path.getsize(self.db_manager.db_path) / (1024 * 1024)  # MB
            st.sidebar.metric("数据库大小", f"{db_size:.1f} MB")
        except:
            st.sidebar.metric("数据库大小", "N/A")

        xingchen_count = self.db_manager.get_xingchen_count()
        handicap_count = self.db_manager.get_handicap_count()
        st.sidebar.metric("星辰数据条数", f"{xingchen_count:,}")
        st.sidebar.metric("盘口数据条数", f"{handicap_count:,}")

    def _render_data_query(self):
        """Render data query interface"""
        st.header("📊 数据查询")

        col1, col2 = st.columns(2)
        today = datetime.now().replace(minute=0, second=0, microsecond=0)

        with col1:
            start_date = st.date_input("开始日期", value=today.date())
            start_time_input = st.time_input("开始时间", value=today.time())
        with col2:
            end_date = st.date_input("结束日期", value=today.date())
            end_time_input = st.time_input(
                "结束时间", value=(today + timedelta(hours=8)).time()
            )

        start_time = datetime.combine(start_date, start_time_input).strftime(
            "%m-%d %H:%M"
        )
        end_time = datetime.combine(end_date, end_time_input).strftime("%m-%d %H:%M")

        # Algorithm selection
        algorithms = st.multiselect(
            "选择算法",
            ["球伯乐", "指数形态", "欧核方差", "公平量价", "赛前能量", "联赛球探"],
            default=["球伯乐", "指数形态", "欧核方差"],
        )

        col1, col2 = st.columns([3, 1])
        with col1:
            query_button = st.button("🔍 查询数据", type="primary")
        with col2:
            auto_refresh = st.checkbox("自动刷新", value=False)

        if query_button or auto_refresh:
            with st.spinner("正在查询数据..."):
                # Get Xingchen data
                df_xingchen = self.db_manager.get_xingchen_data(
                    start_time, end_time, algorithms
                )

                if not df_xingchen.empty:
                    # Get corresponding handicap data
                    matches = df_xingchen["比赛"].unique().tolist()
                    df_handicap = self.db_manager.get_handicap_data(matches)

                    # Merge data if handicap data exists
                    if not df_handicap.empty:
                        df_merged = pd.merge(
                            df_xingchen,
                            df_handicap[["比赛", "盘口", "主赔", "客赔"]],
                            on="比赛",
                            how="left",
                            suffixes=("", "_handicap"),
                        )
                        # Use handicap data to update main盘口 if available
                        df_merged["盘口"] = df_merged["盘口_handicap"].fillna(
                            df_merged["盘口"]
                        )
                        df_merged = df_merged.drop(["盘口_handicap"], axis=1)
                    else:
                        df_merged = df_xingchen

                    st.success(f"找到 {len(df_merged)} 条记录")

                    # Display summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("总比赛数", len(df_merged["比赛"].unique()))
                    with col2:
                        st.metric("算法覆盖", len(df_merged["算法"].unique()))
                    with col3:
                        jingcai_count = len(df_merged[df_merged["竞彩"] == "是"])
                        st.metric("竞彩比赛", jingcai_count)
                    with col4:
                        high_conf = df_merged[df_merged["胜"] > 0.7]
                        st.metric("高置信度", len(high_conf))

                    # Data table with filters
                    st.subheader("📋 查询结果")

                    # Filter options
                    filter_col1, filter_col2, filter_col3 = st.columns(3)
                    with filter_col1:
                        league_filter = st.multiselect(
                            "筛选联赛",
                            options=sorted(df_merged["联赛"].unique()),
                            key="league_filter",
                        )
                    with filter_col2:
                        jingcai_filter = st.selectbox(
                            "竞彩筛选",
                            options=["全部", "是", "否"],
                            key="jingcai_filter",
                        )
                    with filter_col3:
                        confidence_filter = st.slider(
                            "最低胜率",
                            min_value=0.0,
                            max_value=1.0,
                            value=0.0,
                            step=0.05,
                            key="confidence_filter",
                        )

                    # Apply filters
                    df_filtered = df_merged.copy()
                    if league_filter:
                        df_filtered = df_filtered[
                            df_filtered["联赛"].isin(league_filter)
                        ]
                    if jingcai_filter != "全部":
                        df_filtered = df_filtered[df_filtered["竞彩"] == jingcai_filter]
                    if confidence_filter > 0:
                        df_filtered = df_filtered[
                            df_filtered["胜"] >= confidence_filter
                        ]

                    st.dataframe(
                        df_filtered,
                        use_container_width=True,
                        column_config={
                            "胜": st.column_config.ProgressColumn(
                                "胜率", min_value=0, max_value=1
                            ),
                            "让胜": st.column_config.ProgressColumn(
                                "让胜率", min_value=0, max_value=1
                            ),
                        },
                    )

                    # Download button
                    csv = df_filtered.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "📥 下载 CSV",
                        csv,
                        f"soccer_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        "text/csv",
                    )
                else:
                    st.warning("未找到符合条件的数据")

    def _render_real_time_monitor(self):
        """Render real-time monitoring dashboard"""
        st.header("📈 实时监控")

        # Auto-refresh controls
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("🔄 刷新监控", key="monitor_refresh"):
                st.rerun()
        with col2:
            auto_monitor = st.checkbox("自动监控", value=False, key="auto_monitor")

        if auto_monitor:
            time.sleep(2)
            st.rerun()

        # Get recent data (last 6 hours to next 12 hours)
        now = datetime.now()
        recent_start = (now - timedelta(hours=6)).strftime("%m-%d %H:%M")
        recent_end = (now + timedelta(hours=12)).strftime("%m-%d %H:%M")

        recent_data = self.db_manager.get_xingchen_data(recent_start, recent_end)

        if not recent_data.empty:
            # Overview metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                total_matches = len(recent_data["比赛"].unique())
                st.metric("📊 总比赛数", total_matches)

            with col2:
                high_conf = recent_data[recent_data["胜"] > 0.7]
                high_conf_matches = len(high_conf["比赛"].unique())
                st.metric("🎯 高置信度比赛", high_conf_matches)

            with col3:
                jingcai = recent_data[recent_data["竞彩"] == "是"]
                jingcai_matches = len(jingcai["比赛"].unique())
                st.metric("🏆 竞彩比赛", jingcai_matches)

            with col4:
                algorithms = recent_data["算法"].nunique()
                st.metric("⚙️ 覆盖算法", algorithms)

            # Time distribution chart
            st.subheader("⏰ 比赛时间分布")

            # Parse time for grouping
            recent_data["hour"] = (
                recent_data["开球时间"].str.split(" ").str[1].str.split(":").str[0]
            )
            time_dist = recent_data.groupby("hour")["比赛"].nunique().reset_index()
            time_dist.columns = ["小时", "比赛数量"]

            st.bar_chart(time_dist.set_index("小时"))

            # League distribution
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("🏟️ 联赛分布")
                league_dist = (
                    recent_data.groupby("联赛")["比赛"].nunique().reset_index()
                )
                league_dist.columns = ["联赛", "比赛数量"]
                league_dist = league_dist.sort_values("比赛数量", ascending=False).head(
                    10
                )
                st.dataframe(league_dist, use_container_width=True)

            with col2:
                st.subheader("🔥 高置信度比赛")
                high_conf_matches = recent_data[recent_data["胜"] > 0.75].sort_values(
                    "胜", ascending=False
                )
                if not high_conf_matches.empty:
                    display_cols = ["开球时间", "联赛", "比赛", "算法", "胜", "竞彩"]
                    st.dataframe(
                        high_conf_matches[display_cols].head(10),
                        use_container_width=True,
                        column_config={
                            "胜": st.column_config.ProgressColumn(
                                "胜率", min_value=0, max_value=1
                            ),
                        },
                    )
                else:
                    st.info("暂无高置信度比赛")

            # Recent updates
            st.subheader("🕐 最近更新")
            recent_updates = recent_data.sort_values(
                "created_at", ascending=False
            ).head(20)
            display_cols = [
                "开球时间",
                "算法",
                "联赛",
                "比赛",
                "胜",
                "平",
                "负",
                "竞彩",
            ]
            st.dataframe(
                recent_updates[display_cols],
                use_container_width=True,
                column_config={
                    "胜": st.column_config.ProgressColumn(
                        "胜率", min_value=0, max_value=1
                    ),
                    "平": st.column_config.ProgressColumn(
                        "平局率", min_value=0, max_value=1
                    ),
                    "负": st.column_config.ProgressColumn(
                        "负率", min_value=0, max_value=1
                    ),
                },
            )

        else:
            st.info("📭 暂无近期数据")
            st.markdown("可能的原因：")
            st.markdown("- 后台数据获取尚未开始")
            st.markdown("- 数据源暂无更新")
            st.markdown("- 网络连接问题")

    def _render_predictions(self):
        """Render predictions interface (placeholder for future ML model)"""
        st.header("🎯 预测结果")

        st.info("🚧 智能预测引擎正在开发中...")

        # Placeholder for BacktestEngine integration
        st.markdown(
            """
        ### 即将推出的功能：
        - 🤖 多算法融合预测模型
        - 📊 实时胜率分析与置信度评分
        - 💰 智能投注建议系统
        - 📈 历史回测结果与性能分析
        - 🎯 个性化策略推荐
        - 📱 实时推送与预警
        """
        )

        # Mock prediction interface for demonstration
        st.subheader("🎲 模拟预测演示")

        col1, col2 = st.columns([2, 1])

        with col1:
            if st.button("🎯 生成模拟预测", type="primary"):
                # Get some recent matches for demo
                recent_matches = self.db_manager.get_xingchen_data()
                if not recent_matches.empty:
                    sample_matches = recent_matches.sample(min(5, len(recent_matches)))

                    # Create mock predictions
                    mock_predictions = []
                    for _, match in sample_matches.iterrows():
                        import random

                        confidence = random.uniform(0.6, 0.95)
                        prediction = random.choice(["主胜", "平局", "客胜"])
                        recommendation = "是" if confidence > 0.8 else "否"

                        mock_predictions.append(
                            {
                                "比赛": match["比赛"],
                                "开球时间": match["开球时间"],
                                "联赛": match["联赛"],
                                "预测结果": prediction,
                                "置信度": confidence,
                                "建议投注": recommendation,
                                "算法来源": match["算法"],
                            }
                        )

                    mock_df = pd.DataFrame(mock_predictions)
                    st.dataframe(
                        mock_df,
                        use_container_width=True,
                        column_config={
                            "置信度": st.column_config.ProgressColumn(
                                "置信度", min_value=0, max_value=1
                            ),
                        },
                    )

                    st.success("✨ 模拟预测已生成！实际预测引擎将基于机器学习模型")
                else:
                    st.warning("暂无数据可用于预测演示")

        with col2:
            st.markdown("**预测说明**")
            st.markdown(
                """
            - 🎯 **置信度**：模型对预测结果的信心程度
            - 💡 **建议投注**：基于风险评估的投注建议
            - 🔄 **多算法融合**：结合多个数据源的预测
            - ⚡ **实时更新**：随数据更新自动刷新预测
            """
            )

        # Future ML model integration placeholder
        st.subheader("🔮 未来集成计划")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**机器学习模型**")
            st.code(
                """
# 预期的集成接口
from models import BacktestEngine

backtest_engine = BacktestEngine()

# 获取预测
predictions = backtest_engine.predict(
    xingchen_data=df_xingchen,
    handicap_data=df_handicap,
    confidence_threshold=0.75
)

# 存储结果
db_manager.insert_backtest_results(predictions)
            """,
                language="python",
            )

        with col2:
            st.markdown("**预测结果存储**")
            st.code(
                """
# 预测结果表结构
CREATE TABLE backtest_results (
    strategy_name TEXT,
    match_id TEXT,
    比赛 TEXT,
    开球时间 TEXT,
    prediction TEXT,
    confidence REAL,
    actual_result TEXT,
    profit_loss REAL,
    created_at TIMESTAMP
)
            """,
                language="sql",
            )

    def _render_system_status(self):
        """Render system status and management interface"""
        st.header("⚙️ 系统状态")

        # Real-time status monitoring
        status_data = self.db_manager.get_fetch_status()

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("📡 数据源状态")

            if status_data:
                for source, info in status_data.items():
                    status = info["status"]
                    last_fetch = info["last_fetch"] or "从未"
                    records_fetched = info["records_fetched"]
                    error_msg = info["error_message"]

                    # Status indicator
                    if status == "success":
                        st.success(f"✅ **{source.upper()}**: 正常运行")
                        st.write(f"   📅 最后更新: {last_fetch}")
                        st.write(f"   📊 获取记录: {records_fetched}")
                    elif status == "fetching":
                        st.info(f"🔄 **{source.upper()}**: 数据获取中...")
                        st.write(f"   📅 开始时间: {last_fetch}")
                    elif status == "error":
                        st.error(f"❌ **{source.upper()}**: 错误")
                        st.write(f"   📅 错误时间: {last_fetch}")
                        st.write(f"   ⚠️ 错误信息: {error_msg}")
                    else:
                        st.warning(f"⚠️ **{source.upper()}**: {status}")
                        st.write(f"   📅 最后检查: {last_fetch}")

                    st.write("---")
            else:
                st.info("暂无数据源状态信息")

        with col2:
            st.subheader("📊 系统统计")

            # Database statistics
            xingchen_count = self.db_manager.get_xingchen_count()
            handicap_count = self.db_manager.get_handicap_count()

            st.metric("🌟 星辰数据", f"{xingchen_count:,} 条")
            st.metric("🎲 盘口数据", f"{handicap_count:,} 条")

            # Database file info
            try:
                db_size = os.path.getsize(self.db_manager.db_path) / (1024 * 1024)
                st.metric("💾 数据库大小", f"{db_size:.2f} MB")
            except:
                st.metric("💾 数据库大小", "N/A")

            # System uptime (mock)
            if st.session_state.background_started:
                uptime = datetime.now() - st.session_state.last_refresh
                hours = int(uptime.total_seconds() // 3600)
                minutes = int((uptime.total_seconds() % 3600) // 60)
                st.metric("⏱️ 运行时间", f"{hours}h {minutes}m")

        # Background task management
        st.subheader("🔧 后台任务管理")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("▶️ 启动后台获取", type="primary"):
                if not self.background_manager.is_running:
                    self.background_manager.start_background_fetch()
                    st.success("✅ 后台数据获取已启动")
                else:
                    st.info("ℹ️ 后台获取已在运行中")

        with col2:
            if st.button("⏸️ 暂停后台获取", type="secondary"):
                if self.background_manager.is_running:
                    self.background_manager.stop_background_fetch()
                    st.warning("⏸️ 后台数据获取已暂停")
                else:
                    st.info("ℹ️ 后台获取未在运行")

        with col3:
            if st.button("🔄 立即手动获取"):
                if self.background_manager.manual_fetch_now():
                    st.success("🚀 手动获取已启动...")
                else:
                    st.warning("⏳ 数据获取进行中，请稍候...")

        # System configuration
        st.subheader("⚙️ 系统配置")

        current_interval = self.background_manager.fetch_interval // 60
        new_interval = st.slider(
            "数据获取间隔 (分钟)",
            min_value=1,
            max_value=60,
            value=current_interval,
            help="设置后台自动获取数据的时间间隔",
        )

        if new_interval != current_interval:
            self.background_manager.fetch_interval = new_interval * 60
            st.success(f"✅ 获取间隔已更新为 {new_interval} 分钟")

        # Database management
        st.subheader("🗄️ 数据库管理")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🗑️ 清空所有数据", type="secondary"):
                self.db_manager.reset_database()
                st.success("🧹 数据库已清空")

        with col2:
            if st.button("📤 导出数据", type="secondary"):
                # Export all data to CSV
                try:
                    xingchen_data = self.db_manager.get_xingchen_data()
                    handicap_data = self.db_manager.get_handicap_data()

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                    if not xingchen_data.empty:
                        xingchen_csv = xingchen_data.to_csv(index=False)
                        st.download_button(
                            "📥 下载星辰数据",
                            xingchen_csv,
                            f"xingchen_data_{timestamp}.csv",
                            "text/csv",
                        )

                    if not handicap_data.empty:
                        handicap_csv = handicap_data.to_csv(index=False)
                        st.download_button(
                            "📥 下载盘口数据",
                            handicap_csv,
                            f"handicap_data_{timestamp}.csv",
                            "text/csv",
                        )

                    if xingchen_data.empty and handicap_data.empty:
                        st.warning("⚠️ 暂无数据可导出")

                except Exception as e:
                    st.error(f"❌ 导出失败: {e}")

        # System logs (placeholder)
        st.subheader("📋 系统日志")

        # Mock recent logs
        with st.expander("查看最近日志", expanded=False):
            mock_logs = [
                f"[{datetime.now().strftime('%H:%M:%S')}] INFO: 后台数据获取服务正常运行",
                f"[{(datetime.now() - timedelta(minutes=5)).strftime('%H:%M:%S')}] SUCCESS: 星辰数据获取完成，新增 {xingchen_count % 100} 条记录",
                f"[{(datetime.now() - timedelta(minutes=8)).strftime('%H:%M:%S')}] SUCCESS: 盘口数据获取完成，新增 {handicap_count % 50} 条记录",
                f"[{(datetime.now() - timedelta(minutes=15)).strftime('%H:%M:%S')}] INFO: 开始定期数据获取任务",
            ]

            for log in mock_logs:
                st.code(log, language="log")

    def _run_backtest_placeholder(self):
        """Placeholder for future backtest engine integration"""
        # TODO: Integrate with BacktestEngine when available
        #
        # from models import BacktestEngine
        #
        # backtest_engine = BacktestEngine()
        #
        # # Get recent data for prediction
        # recent_data = self.db_manager.get_xingchen_data()
        # handicap_data = self.db_manager.get_handicap_data()
        #
        # if not recent_data.empty:
        #     try:
        #         predictions = backtest_engine.predict(
        #             xingchen_data=recent_data,
        #             handicap_data=handicap_data,
        #             confidence_threshold=0.75
        #         )
        #
        #         # Store predictions in database
        #         if not predictions.empty:
        #             with sqlite3.connect(self.db_manager.db_path) as conn:
        #                 predictions.to_sql("backtest_results", conn, if_exists="append", index=False)
        #
        #         self.db_manager.update_fetch_status("backtest", "success", records_fetched=len(predictions))
        #
        #     except Exception as e:
        #         self.db_manager.update_fetch_status("backtest", "error", str(e))
        pass


def main():
    """Application entry point"""
    try:
        app = StreamlitApp()
        app.run()
    except Exception as e:
        st.error(f"应用启动失败: {e}")
        st.info("请检查系统配置和依赖项")
        st.code(f"错误详情: {str(e)}", language="text")


if __name__ == "__main__":
    main()

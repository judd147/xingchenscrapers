import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)
import time
import atexit
import os
import sqlite3
import threading
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from utils import map_leagues, map_teams
from models import XingchenScraper, HandicapScraper
from ML_model import SoccerMLPredictor, predict_upcoming_matches


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
                    H INTEGER,
                    A INTEGER,
                    客队 TEXT,
                    盘口 TEXT,
                    主赔 REAL,
                    客赔 REAL,
                    比赛 TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(比赛)
                )
            """
            )

            # Prediction results table for ML model (requested name: backtest_result)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS backtest_result (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    比赛 TEXT,
                    开球时间 TEXT,
                    联赛 TEXT,
                    算法 TEXT,
                    盘口 TEXT,
                    主赔 REAL,
                    客赔 REAL,
                    model_used TEXT,
                    prediction TEXT,
                    confidence REAL,
                    strength TEXT,
                    prob_upper REAL,
                    prob_lower REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(比赛, 开球时间, 算法)
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

                # Use INSERT OR REPLACE so the latest odds for a given 比赛 overwrite stale ones
                query = f"INSERT OR REPLACE INTO handicap_data ({column_names}) VALUES ({placeholders})"

                conn.executemany(query, values)
                conn.commit()

        except Exception as e:
            print(f"Error inserting Handicap data: {e}")
            return 0

        final_count = self.get_handicap_count()
        return final_count - initial_count

    def update_xingchen_with_handicap(self) -> int:
        """Update xingchen_data with handicap information by joining on 比赛 field"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Update query to join handicap_data with xingchen_data
                update_query = """
                UPDATE xingchen_data 
                SET 盘口 = h.盘口,
                    主赔 = h.主赔,
                    客赔 = h.客赔
                FROM handicap_data h
                WHERE xingchen_data.比赛 = h.比赛
                """

                cursor = conn.execute(update_query)
                updated_records = cursor.rowcount
                conn.commit()

                return updated_records

        except Exception as e:
            print(f"Error updating xingchen data with handicap info: {e}")
            return 0

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

    def insert_backtest_results(self, df: pd.DataFrame) -> int:
        """Insert or replace ML prediction results into backtest_result table."""
        if df is None or df.empty:
            return 0

        # Ensure required columns exist
        required = [
            "比赛",
            "开球时间",
            "联赛",
            "算法",
            "盘口",
            "主赔",
            "客赔",
            "model_used",
            "prediction",
            "confidence",
            "strength",
            "prob_upper",
            "prob_lower",
        ]
        for col in required:
            if col not in df.columns:
                df[col] = None

        try:
            with sqlite3.connect(self.db_path) as conn:
                columns = required
                placeholders = ",".join(["?"] * len(columns))
                column_names = ",".join(columns)
                query = f"INSERT OR REPLACE INTO backtest_result ({column_names}) VALUES ({placeholders})"
                values = df[columns].values.tolist()
                conn.executemany(query, values)
                conn.commit()
                return len(values)
        except Exception as e:
            print(f"Error inserting backtest_result: {e}")
            return 0

    def reset_database(self):
        """Reset all data tables (admin function)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM xingchen_data")
                conn.execute("DELETE FROM handicap_data")
                conn.execute("DELETE FROM backtest_result")
                conn.execute("DELETE FROM fetch_status")
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
        self.stop_event = threading.Event()
        self.thread = None

        # Ensure background thread stops when process exits
        atexit.register(self.stop_background_fetch)

    def start_background_fetch(self):
        """Start background fetching in a separate thread"""
        # Idempotent start: avoid multiple threads after reruns
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.is_running = True
        self.thread = threading.Thread(target=self._background_fetch_loop, daemon=True)
        self.thread.start()
        print("Background fetch started")

    def stop_background_fetch(self):
        """Stop background fetching"""
        # Signal loop to stop and wait briefly
        self.is_running = False
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            try:
                self.thread.join(timeout=5)
            except Exception:
                pass
        print("Background fetch stopped")

    def _background_fetch_loop(self):
        """Main background fetch loop"""
        while not self.stop_event.is_set():
            try:
                # Acquire lock to prevent concurrent fetching
                with self.fetch_lock:
                    # Fetch Xingchen data first
                    xingchen_records = self._fetch_xingchen_data()

                    # Then fetch Handicap data for matches without it
                    handicap_records = self._fetch_handicap_data()

                    # Update Xingchen data with handicap info
                    updated_records = self.db_manager.update_xingchen_with_handicap()
                    print(
                        f"Updated {updated_records} xingchen records with handicap data"
                    )

                    # Run ML predictions on upcoming matches using saved model
                    self._run_ml_predictions()

                print(
                    f"Background fetch completed. Xingchen: {xingchen_records}, Handicap: {handicap_records}"
                )

                # Wait for next interval
                print("Next fetch in", self.fetch_interval // 60, "minutes")
                # Sleep but wake early if stop requested
                if self.stop_event.wait(self.fetch_interval):
                    break

            except Exception as e:
                print(f"Background fetch error: {e}")
                self.db_manager.update_fetch_status("background", "error", str(e))
                time.sleep(60)  # Wait 1 minute before retrying

    def _fetch_xingchen_data(self) -> int:
        """Fetch Xingchen data in background with smart time range"""
        try:
            self.db_manager.update_fetch_status("xingchen", "fetching")

            # Start time is now
            now = datetime.now()
            start_time = (now - timedelta(hours=0)).strftime("%m-%d %H:%M")

            # Fetch for next 12 hours
            end_time = (now + timedelta(hours=12)).strftime("%m-%d %H:%M")

            print(f"Fetching Xingchen data from {start_time} to {end_time}")

            # Fetch data using existing scraper logic
            df_data = self._scrape_xingchen_background(start_time, end_time)

            if not df_data.empty:
                new_records = self.db_manager.insert_xingchen_data(df_data)
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

            # Get matches within next 12 hours
            now = datetime.now()
            start_time = now.strftime("%m-%d %H:%M")
            end_time = (now + timedelta(hours=12)).strftime("%m-%d %H:%M")
            matches_needing_handicap = self.db_manager.get_xingchen_data(
                start_time=start_time, end_time=end_time
            )

            if len(matches_needing_handicap) > 0:
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
                combined_df = combined_df.sort_values(
                    by=["开球时间", "联赛", "比赛", "算法"], kind="mergesort"
                ).reset_index(drop=True)
                return combined_df
            else:
                return pd.DataFrame()

        except Exception as e:
            print(f"Error in Xingchen background scraping: {e}")
            return pd.DataFrame()

    def _scrape_handicap_background(self, df_matches: List[str]) -> pd.DataFrame:
        """Scrape Handicap data without UI (headless)"""
        try:
            driver = self.handicap_scraper.init_service("next", headless=True)

            if df_matches.empty:
                driver.quit()
                return pd.DataFrame()

            frames = []
            league_names = df_matches["联赛"].apply(map_leagues)

            for league_name in league_names.unique():
                try:
                    self.handicap_scraper.select_league(driver, league_name)
                    df_result = self.handicap_scraper.scrape(driver)
                    df_result = self.handicap_scraper.clean_result(df_result)
                    if not df_result.empty:
                        frames.append(df_result)
                except:  # catch the intentional exception when league not found
                    print(f"Skipping {league_name}")

            driver.quit()

            if frames:
                final_result = pd.concat(frames, ignore_index=True)
                final_result["主队"] = final_result["主队"].apply(map_teams)
                final_result["客队"] = final_result["客队"].apply(map_teams)
                final_result["比赛"] = final_result["主队"] + "-" + final_result["客队"]

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

    def _run_ml_predictions(self):
        """Load trained model and run predictions for upcoming matches, then store results."""
        try:
            model_path = os.getenv("ML_MODEL_PATH", "saved_model.pkl")
            if not os.path.exists(model_path):
                print(f"No model found at {model_path}; skipping predictions.")
                return

            predictor = SoccerMLPredictor.load_model(model_path)

            # Time window: now to +12h (same as fetch)
            now = datetime.now()
            start_time = (now - timedelta(hours=0)).strftime("%m-%d %H:%M")
            end_time = (now + timedelta(hours=12)).strftime("%m-%d %H:%M")

            # Query upcoming matches with required fields present
            with sqlite3.connect(self.db_manager.db_path) as conn:
                sql = (
                    "SELECT 开球时间, 联赛, 比赛, 算法, 胜, 平, 负, 让胜, 让平, 让负, 盘口, 竞彩, 主赔, 客赔, H, A "
                    "FROM xingchen_data WHERE 开球时间 BETWEEN ? AND ? "
                    "AND (H IS NULL OR A IS NULL) "
                    "AND 盘口 IS NOT NULL AND 盘口 != '' "
                    "AND 主赔 IS NOT NULL AND 客赔 IS NOT NULL"
                )
                df = pd.read_sql_query(sql, conn, params=[start_time, end_time])

            if df.empty:
                print("No upcoming matches eligible for prediction.")
                return

            # Filter to model's handicap range for prediction consistency
            tmp = df.copy()
            tmp["__handicap_value__"] = tmp["盘口"].apply(predictor.parse_handicap)
            tmp = tmp[
                (tmp["__handicap_value__"] >= predictor.handicap_min)
                & (tmp["__handicap_value__"] <= predictor.handicap_max)
            ].drop(columns=["__handicap_value__"], errors="ignore")

            if tmp.empty:
                print("No matches within handicap range for prediction.")
                return

            # Run predictions
            preds = predict_upcoming_matches(predictor, tmp)
            if preds is None or len(preds) == 0:
                print("Prediction function returned no results.")
                return

            # Merge predictions with source fields
            preds = preds.rename(
                columns={
                    "match": "比赛",
                    "league": "联赛",
                    "handicap": "盘口",
                    "algorithm": "算法",
                    "model": "model_used",
                }
            )
            merged = pd.merge(
                preds,
                tmp[["比赛", "开球时间", "联赛", "算法", "盘口", "主赔", "客赔"]],
                on=["比赛", "联赛", "算法", "盘口"],
                how="left",
            )

            inserted = self.db_manager.insert_backtest_results(merged)
            print(f"Inserted/updated {inserted} ML prediction records.")

        except Exception as e:
            print(f"Error running ML predictions: {e}")

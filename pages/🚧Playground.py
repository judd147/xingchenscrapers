# -*- coding: utf-8 -*-
"""
Created on 08/17/2025
@author: Optimized Soccer Data Platform

Streamlit app with background data fetching, SQLite storage, and real-time updates
"""

import os
import math
from typing import List, Optional

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, time

from managers import DatabaseManager, BackgroundTaskManager
from ML_model import SoccerMLPredictor

HIGH_CONF_THRESHOLD = 0.6

st.set_page_config(
    page_title="⚽ 智能足球数据平台",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner=False)
def load_ml_predictor() -> Optional[SoccerMLPredictor]:
    model_path = os.getenv("ML_MODEL_PATH", "saved_model.pkl")
    if not model_path or not os.path.exists(model_path):
        return None
    try:
        return SoccerMLPredictor.load_model(model_path)
    except Exception as exc:
        st.warning(f"无法加载机器学习模型: {exc}")
        return None


@st.cache_data(show_spinner=False)
def load_backtest_dataset() -> Optional[pd.DataFrame]:
    data_path = os.getenv("LOCAL_DATA_PATH")
    if not data_path or not os.path.exists(data_path):
        return None

    try:
        df = pd.read_excel(
            data_path,
            sheet_name=1,
            converters={
                "年": float,
                "盘口": str,
                "注释": str,
                "竞彩": str,
                "主赔": float,
                "客赔": float,
            },
        )
    except Exception as exc:
        st.warning(f"无法读取历史数据: {exc}")
        return None

    df = df.copy()
    df["算法"] = df["算法"].fillna("球伯乐")
    df["注释"] = df["注释"].fillna("")
    df["主赔"] = pd.to_numeric(df["主赔"], errors="coerce")
    df["客赔"] = pd.to_numeric(df["客赔"], errors="coerce")
    df["H"] = pd.to_numeric(df["H"], errors="coerce")
    df["A"] = pd.to_numeric(df["A"], errors="coerce")
    df["handicap_value"] = pd.to_numeric(df["盘口"], errors="coerce")

    df = df[df["年"].notna() & df["开球时间"].notna()]
    if df.empty:
        return None

    df["年"] = df["年"].astype(int).astype(str)
    df["开球时间"] = df["开球时间"].astype(str).str.strip()
    df["match_datetime"] = pd.to_datetime(
        df["年"] + "-" + df["开球时间"],
        format="%Y-%m-%d %H:%M",
        errors="coerce",
    )
    df = df[df["match_datetime"].notna()]
    if df.empty:
        return None

    df["开球时间_fmt"] = df["match_datetime"].dt.strftime("%Y-%m-%d %H:%M")
    df["week"] = df["match_datetime"].dt.isocalendar().week.astype(int)

    return df


def split_handicap_lines(handicap: float) -> List[float]:
    if math.isclose(handicap % 0.5, 0.0, abs_tol=1e-9):
        return [handicap]
    if handicap > 0:
        base = math.floor(handicap * 2) / 2
        return [base, base + 0.5]
    high = math.ceil(handicap * 2) / 2
    return [high - 0.5, high]


def determine_bet_team(handicap_value: float, prediction: str) -> str:
    if prediction == "上盘":
        return "home" if handicap_value <= 0 else "away"
    return "away" if handicap_value <= 0 else "home"


def calculate_asian_profit(
    handicap_value: float,
    prediction: str,
    home_score: float,
    away_score: float,
    home_odds: Optional[float],
    away_odds: Optional[float],
    stake: float = 100.0,
) -> float:
    if (
        handicap_value is None
        or pd.isna(handicap_value)
        or pd.isna(home_score)
        or pd.isna(away_score)
    ):
        return 0.0

    team = determine_bet_team(handicap_value, prediction)
    team_handicap = handicap_value if team == "home" else -handicap_value
    odds = home_odds if team == "home" else away_odds
    if pd.isna(odds) or odds <= 1.0:
        odds = 1.0

    lines = split_handicap_lines(team_handicap)
    wins = losses = 0

    for line in lines:
        if team == "home":
            diff = home_score + line - away_score
        else:
            diff = away_score + line - home_score
        if diff > 0:
            wins += 1
        elif diff < 0:
            losses += 1

    win_frac = wins / len(lines)
    loss_frac = losses / len(lines)
    profit = stake * (win_frac * (odds - 1) - loss_frac)
    return round(profit, 2)


def derive_handicap_side(handicap_value: float, note: str = "") -> str:
    if isinstance(note, str):
        note = note.strip()
        if "-" in note and "+" not in note:
            return "主让"
        if "+" in note and "-" not in note:
            return "客让"
    if handicap_value < 0:
        return "主让"
    if handicap_value > 0:
        return "客让"
    return "平手"


def format_handicap_display(handicap_value: float) -> str:
    return f"{handicap_value:+.2f}".rstrip("0").rstrip(".")


def format_model_label(strength: str, prediction: str) -> str:
    prefix = {
        "五星级": "新发现！！！五星级",
        "四星级": "新发现！！四星级",
        "三星级": "新发现！三星级",
    }.get(strength, strength or "模型")
    suffix = "上盘模型" if prediction == "上盘" else "下盘模型"
    return f"{prefix}{suffix}"


@st.cache_resource
def get_background_manager():
    db = DatabaseManager()
    mgr = BackgroundTaskManager(db)
    mgr.start_background_fetch()
    return mgr


class StreamlitApp:
    """Main Streamlit application with optimized UI"""

    def __init__(self):
        # Reuse a single background manager across Streamlit reruns
        self.background_manager = get_background_manager()
        self.db_manager = self.background_manager.db_manager

        # Initialize session state
        if "background_started" not in st.session_state:
            st.session_state.background_started = False

        if "last_refresh" not in st.session_state:
            st.session_state.last_refresh = datetime.now()

    def run(self):
        """Main application entry point"""
        st.title("⚽ 智能足球数据平台")
        st.markdown("*实时数据 • 自动更新 • 智能预测*")

        # Start background fetching (idempotent guard inside manager)
        if not st.session_state.background_started:
            self.background_manager.start_background_fetch()
            st.session_state.background_started = True
            st.success("🔄 后台数据获取已启动")

        # Main content tabs
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📊 数据查询", "🎯 预测结果", "📈 历史回测", "⚙️ 系统状态"]
        )

        with tab1:
            self._render_data_query()

        with tab2:
            self._render_predictions()

        with tab3:
            self._render_backtest()

        with tab4:
            self._render_system_status()

    def _render_data_query(self):
        """Render data query interface"""
        st.header("📊 数据查询")

        today = datetime.now().replace(minute=0, second=0, microsecond=0)

        with st.form(key="data_query_form"):
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("开始日期", value=today)
                start_time_input = st.time_input("开始时间", value=today.time())
            with col2:
                end_date = st.date_input("结束日期", value=today + timedelta(days=1))
                end_time_input = st.time_input(
                    "结束时间", value=(today + timedelta(hours=12)).time()
                )

            start_time = datetime.combine(start_date, start_time_input).strftime(
                "%m-%d %H:%M"
            )
            end_time = datetime.combine(end_date, end_time_input).strftime(
                "%m-%d %H:%M"
            )

            # Algorithm selection
            algorithms = st.multiselect(
                "选择算法",
                ["球伯乐", "指数形态", "欧核方差", "公平量价", "赛前能量", "联赛球探"],
                default=[
                    "球伯乐",
                    "指数形态",
                    "欧核方差",
                    "公平量价",
                    "赛前能量",
                    "联赛球探",
                ],
            )

            col1, col2 = st.columns([3, 1])
            with col1:
                query_button = st.form_submit_button("🔍 查询数据", type="primary")
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

                    st.dataframe(
                        df_merged,
                        column_config={
                            "胜": st.column_config.ProgressColumn(
                                "胜率", min_value=0, max_value=1
                            ),
                            "让胜": st.column_config.ProgressColumn(
                                "让胜率", min_value=0, max_value=1
                            ),
                        },
                    )
                else:
                    st.warning("未找到符合条件的数据")

    def _render_predictions(self):
        """Render real-time predictions dashboard"""
        st.header("🎯 预测结果")

        # Auto-refresh controls
        col1, col2 = st.columns([3, 1])
        with col1:
            monitor_refresh = st.button("🔄 刷新")

        if monitor_refresh:
            st.rerun()

        today = datetime.now().replace(minute=0, second=0, microsecond=0)
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", value=today)
            start_time_input = st.time_input("开始时间", value=today.time())
        with col2:
            end_date = st.date_input("结束日期", value=today + timedelta(days=1))
            end_time_input = st.time_input(
                "结束时间", value=(today + timedelta(hours=12)).time()
            )

        start_time = datetime.combine(start_date, start_time_input).strftime(
            "%m-%d %H:%M"
        )
        end_time = datetime.combine(end_date, end_time_input).strftime("%m-%d %H:%M")

        recent_data = self.db_manager.get_prediction_results(start_time, end_time)

        if not recent_data.empty:
            # Overview metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                total_matches = len(recent_data["比赛"].unique())
                st.metric("📊 总比赛数", total_matches)

            with col2:
                high_conf = recent_data[recent_data["confidence"] > 0.57]
                high_conf_matches = len(high_conf["比赛"].unique())
                st.metric("🎯 高置信度比赛", high_conf_matches)

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
                high_conf_matches = recent_data[
                    recent_data["confidence"] > 0.57
                ].sort_values("confidence", ascending=False)
                if not high_conf_matches.empty:
                    display_cols = [
                        "开球时间",
                        "联赛",
                        "比赛",
                        "算法",
                        "盘口",
                        "prediction",
                        "confidence",
                    ]
                    st.dataframe(
                        high_conf_matches[display_cols].head(10),
                        column_config={
                            "confidence": st.column_config.ProgressColumn(
                                "概率", min_value=0, max_value=1
                            ),
                        },
                    )
                else:
                    st.info("暂无高置信度比赛")

            # Recent updates
            st.subheader("🕐 最近更新")
            recent_updates = recent_data.sort_values("created_at", ascending=False)
            display_cols = [
                "开球时间",
                "算法",
                "联赛",
                "比赛",
                "盘口",
                "prediction",
                "confidence",
                "strength",
                "prob_upper",
                "prob_lower",
            ]
            st.dataframe(
                recent_updates[display_cols],
                column_config={
                    "prob_upper": st.column_config.ProgressColumn(
                        "上盘概率", min_value=0, max_value=1
                    ),
                    "prob_lower": st.column_config.ProgressColumn(
                        "下盘概率", min_value=0, max_value=1
                    ),
                },
            )

        else:
            st.info("📭 暂无近期数据")
            st.markdown("可能的原因：")
            st.markdown("- 后台数据获取尚未开始")
            st.markdown("- 数据源暂无更新")
            st.markdown("- 网络连接问题")

    def _render_backtest(self):
        """Run ML backtest against historical data"""
        st.header("📈 历史回测")

        dataset = load_backtest_dataset()
        if dataset is None:
            st.info("无法读取本地历史数据，请检查 LOCAL_DATA_PATH 配置。")
            return

        predictor = load_ml_predictor()
        if predictor is None or not predictor.is_trained:
            st.warning("未检测到已训练的模型，请先训练并保存模型后再回测。")
            return

        min_date = dataset["match_datetime"].min().date()
        max_date = dataset["match_datetime"].max().date()
        default_start = max_date - timedelta(days=30)
        if default_start < min_date:
            default_start = min_date

        algo_options = sorted(dataset["算法"].dropna().unique().tolist())

        with st.form("backtest_form"):
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "开始日期",
                    value=default_start,
                    min_value=min_date,
                    max_value=max_date,
                )
            with col2:
                end_date = st.date_input(
                    "结束日期",
                    value=max_date,
                    min_value=min_date,
                    max_value=max_date,
                )

            selected_algorithms = st.multiselect(
                "算法筛选",
                options=algo_options,
                default=algo_options,
                placeholder="选择需要纳入回测的算法",
            )

            min_confidence = st.slider(
                "最小置信度过滤",
                min_value=0.5,
                max_value=1.0,
                value=0.6,
                step=0.01,
            )

            run_backtest = st.form_submit_button("运行回测", type="primary")

        if not run_backtest:
            return

        if start_date > end_date:
            st.error("开始日期不能晚于结束日期")
            return

        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)

        mask = (dataset["match_datetime"] >= start_dt) & (
            dataset["match_datetime"] <= end_dt
        )
        if selected_algorithms:
            mask &= dataset["算法"].isin(selected_algorithms)

        df_filtered = dataset[mask].copy()
        if df_filtered.empty:
            st.info("所选条件下暂无比赛数据。")
            return

        targets = predictor.create_target_variable(df_filtered)
        valid_mask = targets != -1
        df_valid = df_filtered[valid_mask].copy()
        targets = targets[valid_mask]

        if df_valid.empty:
            st.info("筛选后的比赛缺少完整比分，无法进行回测。")
            return

        per_match_predictions = {}
        conflict_matches = 0

        for (idx, row), actual in zip(df_valid.iterrows(), targets):
            prediction = predictor.predict_single_match(row)
            confidence = prediction.get("confidence", 0.0) or 0.0

            if confidence < min_confidence:
                continue

            predicted_label = prediction.get("prediction", "")
            if predicted_label not in {"上盘", "下盘"}:
                continue

            actual_label = "上盘" if actual == 1 else "下盘"
            is_correct = prediction.get("prediction_numeric") == actual

            handicap_value = row.get("handicap_value")
            if handicap_value is None or pd.isna(handicap_value):
                handicap_value = predictor.parse_handicap(row.get("盘口", ""))

            home_score = row.get("H")
            away_score = row.get("A")
            score_display = (
                f"{int(home_score)}-{int(away_score)}"
                if pd.notna(home_score) and pd.notna(away_score)
                else ""
            )

            profit = calculate_asian_profit(
                handicap_value,
                predicted_label,
                home_score,
                away_score,
                row.get("主赔"),
                row.get("客赔"),
            )

            model_label = format_model_label(
                prediction.get("strength", ""), predicted_label
            )
            handicap_side = derive_handicap_side(handicap_value, row.get("注释", ""))

            entry = {
                "match_datetime": row["match_datetime"],
                "开球时间": row["开球时间_fmt"],
                "联赛": row.get("联赛", ""),
                "比赛": row.get("比赛", ""),
                "算法": row.get("算法", ""),
                "让球方": handicap_side,
                "盘口": (
                    format_handicap_display(handicap_value)
                    if handicap_value is not None and not pd.isna(handicap_value)
                    else row.get("盘口", "")
                ),
                "模型": model_label,
                "平均概率": round(confidence, 4),
                "预测": predicted_label,
                "实际": actual_label,
                "正误": "✔" if is_correct else "✘",
                "比分": score_display,
                "模拟盈亏": round(profit, 2),
                "model_used": prediction.get("model_used", ""),
                "prob_upper": prediction.get("probability_上盘"),
                "prob_lower": prediction.get("probability_下盘"),
                "confidence": confidence,
                "week": int(row.get("week", 0)),
                "predicted_label": predicted_label,
                "actual_label": actual_label,
                "is_correct": bool(is_correct),
            }

            key = (row["match_datetime"], row.get("比赛", ""))
            per_match_predictions.setdefault(key, []).append(entry)

        if not per_match_predictions:
            st.info("没有符合置信度条件的比赛。")
            return

        selected_entries = []
        for key, entries in per_match_predictions.items():
            labels = {e["predicted_label"] for e in entries}
            if len(labels) > 1:
                conflict_matches += 1
                continue

            high_conf_entries = [
                e for e in entries if e["confidence"] >= HIGH_CONF_THRESHOLD
            ]
            chosen = max(high_conf_entries or entries, key=lambda e: e["confidence"])
            selected_entries.append(chosen)

        if not selected_entries:
            st.info("所有符合条件的比赛在不同算法方向冲突，已自动忽略。")
            return

        processed_matches = len(selected_entries)
        total_profit = sum(e["模拟盈亏"] for e in selected_entries)
        total_confidence = sum(e["confidence"] for e in selected_entries)
        correct_predictions = sum(1 for e in selected_entries if e["is_correct"])
        high_conf_matches = sum(
            1 for e in selected_entries if e["confidence"] >= HIGH_CONF_THRESHOLD
        )
        high_conf_correct = sum(
            1
            for e in selected_entries
            if e["confidence"] >= HIGH_CONF_THRESHOLD and e["is_correct"]
        )

        result_df = pd.DataFrame(selected_entries)
        result_df = result_df.sort_values("match_datetime").reset_index(drop=True)
        display_df = result_df.drop(
            columns=["match_datetime", "predicted_label", "actual_label", "is_correct"],
            errors="ignore",
        )

        accuracy = correct_predictions / processed_matches
        avg_confidence = total_confidence / processed_matches
        total_stake = processed_matches * 100
        roi = total_profit / total_stake if total_stake else 0.0

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("样本场次", processed_matches)
        with col2:
            st.metric("命中率", f"{accuracy*100:.1f}%")
        with col3:
            st.metric("累计模拟盈亏", f"{total_profit:.1f}")
        with col4:
            st.metric("平均置信度", f"{avg_confidence:.2f}")

        st.caption(f"资金回报率 (ROI): {roi*100:.1f}%")
        if conflict_matches > 0:
            st.caption(f"{conflict_matches} 场比赛因算法方向冲突被忽略。")

        if high_conf_matches > 0:
            high_conf_accuracy = high_conf_correct / high_conf_matches
            st.caption(
                f"置信度≥{HIGH_CONF_THRESHOLD:.1f} 的比赛: {high_conf_matches} 场，命中率 {high_conf_accuracy*100:.1f}%"
            )

        st.dataframe(
            display_df,
            column_config={
                "平均概率": st.column_config.ProgressColumn(
                    "平均概率", min_value=0.0, max_value=1.0
                ),
                "prob_upper": st.column_config.NumberColumn("上盘概率", format="%.2f"),
                "prob_lower": st.column_config.NumberColumn("下盘概率", format="%.2f"),
                "模拟盈亏": st.column_config.NumberColumn("模拟盈亏", format="%.2f"),
            },
            use_container_width=True,
        )

        csv_data = display_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "下载回测结果 CSV",
            data=csv_data,
            file_name="backtest_results.csv",
            mime="text/csv",
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
            start_fetch = st.button("▶️ 启动后台获取", type="primary")

        with col2:
            pause_fetch = st.button("⏸️ 暂停后台获取", type="secondary")

        with col3:
            manual_fetch = st.button("🔄 立即手动获取")

        if start_fetch:
            if not self.background_manager.is_running:
                self.background_manager.start_background_fetch()
                st.success("✅ 后台数据获取已启动")
            else:
                st.info("ℹ️ 后台获取已在运行中")

        if pause_fetch:
            if self.background_manager.is_running:
                self.background_manager.stop_background_fetch()
                st.warning("⏸️ 后台数据获取已暂停")
            else:
                st.info("ℹ️ 后台获取未在运行")

        if manual_fetch:
            if self.background_manager.manual_fetch_now():
                st.success("🚀 手动获取已启动...")
            else:
                st.warning("⏳ 数据获取进行中，请稍候...")

        # System configuration
        st.subheader("⚙️ 系统配置")

        current_interval = self.background_manager.fetch_interval // 60
        new_interval = st.slider(
            "数据获取间隔 (分钟)",
            min_value=5,
            max_value=60,
            value=15,
            step=5,
            help="设置后台自动获取数据的时间间隔",
        )

        if new_interval != current_interval:
            self.background_manager.fetch_interval = new_interval * 60
            st.success(
                f"✅ 获取间隔已更新为 {self.background_manager.fetch_interval // 60} 分钟"
            )

        # Database management
        st.subheader("🗄️ 数据库管理")

        clear_data = st.button("🗑️ 清空所有数据", type="secondary")

        if clear_data:
            self.db_manager.reset_database()
            st.success("🧹 数据库已清空")


def main():
    """Application entry point"""
    app = StreamlitApp()
    app.run()


if __name__ == "__main__":
    main()

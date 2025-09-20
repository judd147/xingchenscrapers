# -*- coding: utf-8 -*-
"""
Created on 08/17/2025
@author: Optimized Soccer Data Platform

Streamlit app with background data fetching, SQLite storage, and real-time updates
"""

import os
import time
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from managers import DatabaseManager, BackgroundTaskManager
from ML_model import SoccerMLPredictor, predict_upcoming_matches

st.set_page_config(
    page_title="⚽ 智能足球数据平台",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)


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
        tab1, tab2, tab3 = st.tabs(["📊 数据查询", "🎯 预测结果", "⚙️ 系统状态"])

        with tab1:
            self._render_data_query()

        with tab2:
            self._render_predictions()

        with tab3:
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
            recent_updates = recent_data.sort_values(
                "created_at", ascending=False
            ).head(20)
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

# -*- coding: utf-8 -*-
"""
Created on 08/17/2025
@author: Optimized Soccer Data Platform

Streamlit app with background data fetching, SQLite storage, and real-time updates
"""

import io
import os
import time
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from managers import DatabaseManager, BackgroundTaskManager


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
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                        df_filtered.to_excel(writer, index=False)
                    buffer.seek(0)
                    st.download_button(
                        label="下载数据",
                        data=buffer,
                        file_name=f"soccer_data_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.ms-excel",
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
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                            xingchen_data.to_excel(writer, index=False)
                        buffer.seek(0)
                        st.download_button(
                            label="下载星辰数据",
                            data=buffer,
                            file_name=f"xingchen_data_{timestamp}.xlsx",
                            mime="application/vnd.ms-excel",
                        )

                    if not handicap_data.empty:
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                            handicap_data.to_excel(writer, index=False)
                        buffer.seek(0)
                        st.download_button(
                            label="下载盘口数据",
                            data=buffer,
                            file_name=f"handicap_data_{timestamp}.xlsx",
                            mime="application/vnd.ms-excel",
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
    app = StreamlitApp()
    app.run()


if __name__ == "__main__":
    main()

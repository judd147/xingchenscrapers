# -*- coding: utf-8 -*-
"""
Last Edit 12/25/2023
@author: zhangliyao
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
from utils import float_to_pct, pct_to_float, remove_exclamation
from dotenv import load_dotenv

load_dotenv()


def main():
    st.set_page_config(
        layout="wide",
    )

    with st.sidebar:
        st.title("关于")
        st.info(
            """
            GitHub repository: <https://github.com/judd147/xingchenscrapers>
            
            作者: 张力铫
            """
        )
        st.title("Soccer Betting Automated")
        st.caption("")
        st.header("Introduction")
        st.markdown(
            "该项目致力于实现足球赛事的**数据自动获取和自动回测分析**。"
            "目前已经实现全自动化稳定获取星辰智盈5大算法数据；用户在excel表中输入未开赛比赛盘口，系统将按照一套固定算法回测历史数据计算上下盘概率并根据概率判断投资价值。"
            "未来回测算法将使用贝叶斯模型进行全面升级，提升准确率；对于完场赛事，系统将自动抓取AsianBetSoccer的比分和亚盘数据。"
        )

        st.header("Updates and Plans")
        st.checkbox("部署至Streamlit Cloud，实现全天候自动获取数据")
        st.subheader("架构设计")
        st.caption("数据库迁移至SQLlite")
        st.caption("增加后台获取数据功能")
        st.checkbox("增加火线数据获取和回测功能")
        st.subheader("Dashboard")
        st.checkbox("增加模拟盈亏指标展示")
        st.checkbox("保存并使用新模型回测结果")
        st.subheader("星辰智盈数据自动获取系统")
        st.caption("数据源由安卓模拟器改为网页，抓取速度和稳定性获得大幅提升")
        st.subheader("星辰智盈数据自动回测系统")
        st.caption("增加模拟盈亏功能，结合真实赔率数据计算盈利能力")
        st.caption("使用机器学习模型进行回测")
        st.subheader("比分盘口自动获取系统")
        st.caption("数据源由Sofascore改为AsianBetSoccer，抓取速度和稳定性获得大幅提升")

    # Dashboard
    st.title("Performance Dashboard")

    df_history = load_history()
    if df_history is None:
        st.error("该功能暂未开放，请联系作者")
        st.stop()
    worksheet_names = list(df_history.keys())
    worksheet_names.reverse()
    tabs = st.tabs(worksheet_names)
    for i in range(len(tabs)):
        with tabs[i]:
            df_season = df_history[worksheet_names[i]]
            df_season = df_season[df_season["模型"].notnull()]
            df_season = df_season.reset_index()
            del df_season["index"]
            load_dashboard(df_season)

            # 查询球队历史战绩
            with st.form("search_history_{i}".format(i=i)):
                team2search = st.text_input("输入球队名称", help="用于查询球队历史战绩")
                fuzzy = st.checkbox("模糊搜索", value=False)
                submit4search = st.form_submit_button("提交")
                if submit4search:
                    if fuzzy:
                        df_team_history = df_season[
                            df_season["比赛"].str.contains(team2search)
                        ]
                    else:
                        df_metric = clean_history(df_season)
                        df_temp_teams = find_recommend(df_metric)
                        df_team_history = df_temp_teams[
                            df_temp_teams["team"] == (team2search)
                        ].iloc[0:, :14]
                    with st.expander("球队历史战绩", expanded=True):
                        st.dataframe(df_team_history, width=1000)
        i += 1


@st.cache_data
def load_history():
    # read from local file
    url = os.getenv("LOCAL_HISTORY_PATH")
    try:
        df = pd.read_excel(
            url, sheet_name=None, converters={"盘口": str, "week": str}
        )  # read all worksheets
        return df
    except:
        return None


def load_dashboard(df_history):  # TODO 增加模拟盈亏指标计算及展示
    """
    指标计算及可视化
    """
    df_metric = clean_history(df_history)

    # 联赛筛选
    try:
        league_options = st.multiselect(
            "联赛筛选",
            options=df_metric["联赛"].unique(),
            default=["英超", "西甲", "德甲", "意甲", "法甲", "欧冠", "欧联"],
        )
    except:
        league_options = st.multiselect(
            "联赛筛选",
            options=df_metric["联赛"].unique(),
            default=["英超", "西甲", "德甲", "意甲", "法甲"],
        )
    df_metric = df_metric[df_metric["联赛"].isin(league_options)]
    if len(league_options) == 0:
        st.error("请选择至少一个联赛")
        st.stop()

    # 指标1：总体平均胜率
    recent_week = max(df_metric["week"])
    total_avg_success = round(calc_success(df_metric), 3)
    if recent_week == 1:
        total_avg_success_delta = 0
    else:
        df_past = df_metric[df_metric["week"] != recent_week]
        last_week = max(df_past["week"])
        total_avg_success_past = round(calc_success(df_past), 3)
        total_avg_success_delta = round(total_avg_success - total_avg_success_past, 3)

    # 指标2：近期胜率
    df_recent_week = df_metric[df_metric["week"] == recent_week]
    recent_avg_success = round(calc_success(df_recent_week), 3)
    if recent_week == 1:
        recent_avg_success_delta = 0
    else:
        df_last_week = df_metric[df_metric["week"] == last_week]
        last_avg_success = round(calc_success(df_last_week), 3)
        recent_avg_success_delta = round(recent_avg_success - last_avg_success, 3)

    # 指标3：最佳球队
    df_temp_teams = find_recommend(df_metric)
    df_table_team = (
        df_temp_teams.groupby("team")
        .aggregate({"success": "mean", "比赛": "count"})
        .sort_values(by=["success", "比赛"])
        .reset_index()
    )

    # 指标4：最佳联赛
    df_table_league = (
        df_metric.groupby("联赛")
        .aggregate({"success": "mean", "比赛": "count"})
        .sort_values(by="success")
        .reset_index()
    )

    # 指标5：最佳模型
    df_table_model = (
        df_metric.groupby("模型")
        .aggregate({"success": "mean", "比赛": "count"})
        .sort_values(by="success")
        .reset_index()
    )

    # 指标6：最佳盘口
    df_table_handicap = (
        df_metric.groupby("盘口")
        .aggregate({"success": "mean", "比赛": "count"})
        .sort_values(by="success")
        .reset_index()
    )
    df_table_handicap = df_table_handicap[df_table_handicap["比赛"] > 5].reset_index()
    df_table_handicap["盘口"] = "(" + df_table_handicap["盘口"] + ")"
    del df_table_handicap["index"]

    # 指标7：最佳组合
    df_table_combo = (
        df_metric.groupby(["模型", "盘口"])
        .aggregate({"success": "mean", "比赛": "count"})
        .sort_values(by="success", ascending=False)
        .reset_index()
    )

    # 指标展示
    col1, col2, col3 = st.columns(3)
    col1.metric(
        label="总体平均胜率",
        value=float_to_pct(total_avg_success),
        delta=float_to_pct(total_avg_success_delta),
    )
    col2.metric(
        label="近期胜率",
        value=float_to_pct(recent_avg_success),
        delta=float_to_pct(recent_avg_success_delta),
        help="最近一个完整比赛周的胜率，并和再上一周的胜率进行对比",
    )
    col3.metric(
        label="最佳球队",
        value=df_table_team["team"][len(df_table_team) - 1],
        delta=df_table_team["team"][len(df_table_team) - 2],
        delta_color="off",
        help="推荐比赛中赢盘率最高的前两支球队",
    )

    if len(df_table_league["联赛"].unique()) > 1:
        league_delta = df_table_league["联赛"][len(df_table_league) - 2]
    else:
        league_delta = "暂无"
    col1.metric(
        label="最佳联赛",
        value=df_table_league["联赛"][len(df_table_league) - 1],
        delta=league_delta,
        delta_color="off",
        help="胜率最高的前两个联赛",
    )
    try:
        col2.metric(
            label="最佳模型",
            value=df_table_model["模型"][len(df_table_model) - 1],
            delta=df_table_model["模型"][len(df_table_model) - 2],
            delta_color="off",
            help="胜率最高的前两个模型",
        )
    except:
        pass
    try:
        col3.metric(
            label="最佳盘口",
            value=df_table_handicap["盘口"][len(df_table_handicap) - 1],
            delta=df_table_handicap["盘口"][len(df_table_handicap) - 2],
            delta_color="off",
            help="胜率最高的前两个盘口",
        )
    except:
        pass
    col1.metric(
        label="最佳组合",
        value=df_table_combo["模型"][0] + df_table_combo["盘口"][0],
        delta=df_table_combo["模型"][1] + df_table_combo["盘口"][1],
        delta_color="off",
        help="胜率最高的前两个模型盘口组合",
    )

    # 图0：每周胜率折线图
    df_table_weekly_success = (
        df_metric.groupby("week")
        .aggregate({"success": "mean", "比赛": "count"})
        .reset_index()
        .round(decimals=2)
    )
    fig0 = px.line(
        df_table_weekly_success,
        x="week",
        y="success",
        hover_name="比赛",
        markers=True,
        text="success",
        line_shape="spline",
    )
    fig0.add_hline(
        y=total_avg_success,
        line_dash="dot",
        line_color="green",
        annotation_text="总体平均胜率",
        annotation_position="top left",
        annotation_font_size=10,
        annotation_font_color="green",
    )
    fig0.update_traces(textposition="top center")
    fig0.update_layout(hovermode="x")
    with st.expander("赛季胜率走势", expanded=True):
        st.plotly_chart(fig0)

    # #组合条件筛选
    # cond_col1, cond_col2, cond_col3 = st.columns(3)
    # league_select = cond_col1.selectbox('联赛', options=df_metric['联赛'].sort_values().unique())
    # model_select = cond_col2.selectbox('模型', options=df_metric['模型'].sort_values().unique())
    # handicap_select = cond_col3.selectbox('盘口', options=df_metric['盘口'].sort_values(ascending=False).unique())

    # 球队比赛数量筛选
    threshold = st.slider(
        "球队比赛数量筛选",
        value=int(len(df_temp_teams) / 150),
        max_value=max(df_table_team["比赛"]),
    )
    df_table_team = df_table_team[df_table_team["比赛"] >= threshold].reset_index()
    del df_table_team["index"]

    figcol1, figcol2 = st.columns(2)
    with figcol1:
        # 图1：各联赛胜率柱状图
        fig1 = px.bar(
            df_table_league,
            x="success",
            y="联赛",
            color="success",
            hover_name="比赛",
            range_x=[0, 1],
            orientation="h",
            text_auto=".2f",
        )
        fig1.update_layout(hovermode="y")
        with st.expander("最新联赛胜率", expanded=True):
            st.plotly_chart(fig1)

        # 图2：各模型胜率柱状图
        fig2 = px.bar(
            df_table_model,
            x="success",
            y="模型",
            color="success",
            hover_name="比赛",
            range_x=[0, 1],
            orientation="h",
            text_auto=".2f",
        )
        fig2.update_layout(hovermode="y")
        with st.expander("最新模型胜率", expanded=True):
            st.plotly_chart(fig2)

    with figcol2:
        # 图3：最佳球队柱状图
        df_table_team_top = df_table_team.iloc[-20:]
        fig3 = px.bar(
            df_table_team_top,
            x="success",
            y="team",
            color="success",
            hover_name="比赛",
            range_x=[0, 1],
            orientation="h",
            text_auto=".2f",
        )
        fig3.update_layout(hovermode="y")
        with st.expander("最佳球队Top20", expanded=True):
            st.plotly_chart(fig3)

        # 图4：各盘口胜率柱状图
        fig4 = px.bar(
            df_table_handicap,
            x="success",
            y="盘口",
            color="success",
            hover_name="比赛",
            range_x=[0, 1],
            orientation="h",
            text_auto=".2f",
        )
        fig4.update_layout(hovermode="y")
        with st.expander("最新盘口胜率", expanded=True):
            st.plotly_chart(fig4)

    # 表0：组合红黑榜
    with st.expander("组合红黑榜", expanded=True):
        df_table_combo = df_table_combo[
            df_table_combo["比赛"] >= threshold
        ].reset_index()
        del df_table_combo["index"]
        st.dataframe(df_table_combo, width=1000)

    # 表1：球队红黑榜
    df_table_team = df_table_team.sort_values(
        by=["success", "比赛"], ascending=False
    ).reset_index()
    del df_table_team["index"]
    with st.expander("球队红黑榜", expanded=True):
        st.dataframe(df_table_team, width=1000)


# *** 工具类函数 *** #
def clean_history(df_history):
    """
    历史回测结果字段处理
    """
    df_metric = df_history.copy()
    df_metric["平均概率"] = df_metric["平均概率"].apply(pct_to_float)
    df_metric["模型"] = df_metric["模型"].apply(remove_exclamation)
    df_metric["week"] = df_metric["week"].astype(float)
    df_metric.loc[(df_metric["正误"] == "\u2714"), "success"] = 1
    df_metric.loc[(df_metric["正误"] == "\u2716"), "success"] = 0
    return df_metric


def find_recommend(df_metric):
    """
    判断每场比赛的推荐球队
    """
    df_temp_teams = df_metric.copy()
    df_temp_teams["盘口"] = df_temp_teams["盘口"].astype(float)
    df_temp_teams = df_temp_teams[abs(df_temp_teams["盘口"]) < 1.5]
    df_temp_teams[["Home", "Away"]] = df_temp_teams["比赛"].str.split("-", expand=True)
    df_temp_teams["H"] = df_temp_teams["Home"].str[-1:]
    df_temp_teams["A"] = df_temp_teams["Away"].str[:1]
    df_temp_teams["Home"] = df_temp_teams["Home"].str[:-1]
    df_temp_teams["Away"] = df_temp_teams["Away"].str[1:]

    # 判断推荐的球队(team)
    df_temp_teams.loc[
        (df_temp_teams["让球方"] == "主让")
        & (df_temp_teams["模型"].str.contains("上盘")),
        "team",
    ] = df_temp_teams["Home"]
    df_temp_teams.loc[
        (df_temp_teams["让球方"] == "主让")
        & (df_temp_teams["模型"].str.contains("下盘")),
        "team",
    ] = df_temp_teams["Away"]
    df_temp_teams.loc[
        (df_temp_teams["让球方"] == "客让")
        & (df_temp_teams["模型"].str.contains("上盘")),
        "team",
    ] = df_temp_teams["Away"]
    df_temp_teams.loc[
        (df_temp_teams["让球方"] == "客让")
        & (df_temp_teams["模型"].str.contains("下盘")),
        "team",
    ] = df_temp_teams["Home"]
    return df_temp_teams


def calc_success(df):
    """
    传入dataframe后计算并返回该df内的准确率
    """
    num_success = len(df[df["正误"] == "\u2714"])
    return float(num_success / (len(df)))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
Liyao Zhang

Start Date 4/4/2022
Last Edit 9/19/2023

星辰智盈自动回测系统 with Streamlit
"""

import re
import io
import base64
import pandas as pd
import streamlit as st
import plotly.express as px
from numpy import mean
from collections import Counter

def main():
    st.set_page_config(
    page_title="星辰数据回测",
    page_icon="📊",
    #initial_sidebar_state="expanded"
    )
    st.title("星辰智盈数据自动回测系统")
    st.caption("增加历史赛季胜率数据；增加模拟盈亏计算")
    
    source = st.sidebar.radio("选择数据源", ["OneDrive","本地文件"])
    file = None
    if source == '本地文件':
        file = st.sidebar.file_uploader("上传数据库文件", type='xlsx')
        opt1 = st.sidebar.checkbox("统计历史胜率", value=False)
    elif source == 'OneDrive':
        num_show = st.sidebar.number_input('数据显示行数', min_value=1, max_value=100, value=20, key='show')
    run = st.sidebar.button('运行')

    #加载历史回测数据仪表盘
    df_history = load_history()
    load_dashboard(df_history)
    
    #查询球队历史战绩
    with st.form("search_history"):
        team2search = st.text_input('输入球队名称', help='用于查询球队历史战绩')
        fuzzy = st.checkbox('模糊搜索', value=False)
        submit4search = st.form_submit_button('提交')
        if submit4search:
            if fuzzy:
                df_team_history = df_history[df_history['比赛'].str.contains(team2search)]
            else:
                df_metric = clean_history(df_history)
                df_temp_teams = find_recommend(df_metric)
                df_team_history = df_temp_teams[df_temp_teams['team']==(team2search)].iloc[0:,:12]
            with st.expander('球队历史战绩', expanded=True):
                st.dataframe(df_team_history, width=1000)
    
    #运行回测
    if source == 'OneDrive' and run:
        onedrive_link = 'https://1drv.ms/x/s!Ag9ZvloaJitBjy8YIdiLf5Wkr4O6?e=cwBjTO'
        with st.spinner("加载数据中..."):
            url = create_onedrive_directdownload(onedrive_link)
            df = read_file(url)
        st.write(df.tail(num_show))
        dfb = search(df, False)
        st.dataframe(dfb)
        st.success('运行成功！')
        #下载数据
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            dfb.to_excel(writer, index=False)
            writer.save()
            st.download_button(
                label="下载数据",
                data=buffer,
                file_name="result.xlsx",
                mime="application/vnd.ms-excel"
            )
    elif file and run:
        with st.spinner("加载数据中..."):
            df = read_file(file)
        dfb = search(df, opt1)
        st.dataframe(dfb)
        st.success('运行成功！')        

# *** 工具类函数 *** #
def clean_history(df_history):
    '''
    历史回测结果字段处理
    '''
    df_metric = df_history.copy()
    df_metric['平均概率'] = df_metric['平均概率'].apply(pct_to_float)
    df_metric['模型'] = df_metric['模型'].apply(remove_exclamation)
    df_metric['week'] = df_metric['week'].astype(float)
    df_metric.loc[(df_metric['正误'] == '\u2714'), 'success'] = 1
    df_metric.loc[(df_metric['正误'] == '\u2716'), 'success'] = 0
    return df_metric

def find_recommend(df_metric):
    '''
    判断每场比赛的推荐球队
    '''
    df_temp_teams = df_metric.copy()
    df_temp_teams['盘口'] = df_temp_teams['盘口'].astype(float)
    df_temp_teams = df_temp_teams[abs(df_temp_teams['盘口']) < 1.5]
    df_temp_teams[['Home', 'Away']] = df_temp_teams['比赛'].str.split('-', expand=True)
    df_temp_teams['H'] = df_temp_teams['Home'].str[-1:]
    df_temp_teams['A'] = df_temp_teams['Away'].str[:1]
    df_temp_teams['Home'] = df_temp_teams['Home'].str[:-1]
    df_temp_teams['Away'] = df_temp_teams['Away'].str[1:]
    
    #判断推荐的球队(team)
    df_temp_teams.loc[(df_temp_teams['让球方']=='主让')&(df_temp_teams['模型'].str.contains('上盘')), 'team'] = df_temp_teams['Home']    
    df_temp_teams.loc[(df_temp_teams['让球方']=='主让')&(df_temp_teams['模型'].str.contains('下盘')), 'team'] = df_temp_teams['Away']
    df_temp_teams.loc[(df_temp_teams['让球方']=='客让')&(df_temp_teams['模型'].str.contains('上盘')), 'team'] = df_temp_teams['Away']
    df_temp_teams.loc[(df_temp_teams['让球方']=='客让')&(df_temp_teams['模型'].str.contains('下盘')), 'team'] = df_temp_teams['Home']
    return df_temp_teams

def load_dashboard(df_history):
    '''
    指标计算及可视化
    '''
    df_metric = clean_history(df_history)
    
    #指标1：总体平均胜率
    recent_week = max(df_metric['week'])
    total_avg_success = round(calc_success(df_metric), 3)
    if recent_week == 1:
        total_avg_success_delta = 0
    else:
        df_past = df_metric[df_metric['week']!=recent_week]
        last_week = max(df_past['week'])
        total_avg_success_past = round(calc_success(df_past), 3)
        total_avg_success_delta = round(total_avg_success-total_avg_success_past, 3)
        
    #指标2：近期胜率
    df_recent_week = df_metric[df_metric['week']==recent_week]
    recent_avg_success = round(calc_success(df_recent_week), 3)
    if recent_week == 1:
        recent_avg_success_delta = 0
    else:
        df_last_week = df_metric[df_metric['week']==last_week]
        last_avg_success = round(calc_success(df_last_week), 3)
        recent_avg_success_delta = round(recent_avg_success-last_avg_success, 3)
    
    #指标3：最佳球队
    df_temp_teams = find_recommend(df_metric)
    
    df_table_team = df_temp_teams.groupby('team').aggregate({'success': 'mean', '比赛':'count'}).sort_values(by=['success', '比赛']).reset_index()
    threshold = int(len(df_temp_teams)/150)
    df_table_team = df_table_team[df_table_team['比赛']>=threshold].reset_index()
    del df_table_team['index']
    
    #指标4：最佳联赛
    df_table_league = df_metric.groupby('联赛').aggregate({'success': 'mean', '比赛':'count'}).sort_values(by='success', ascending=False).reset_index()
    
    #指标5：最佳模型
    df_table_model = df_metric.groupby('模型').aggregate({'success': 'mean', '比赛':'count'}).sort_values(by='success', ascending=False).reset_index()

    #指标6：最佳盘口
    df_table_handicap = df_metric.groupby('盘口').aggregate({'success': 'mean', '比赛':'count'}).sort_values(by='success').reset_index()
    df_table_handicap = df_table_handicap[df_table_handicap['比赛'] > 5].reset_index()
    del df_table_handicap['index']

    #指标展示
    col1, col2, col3 = st.columns(3)
    col1.metric(label="总体平均胜率", value=float_to_pct(total_avg_success), delta=float_to_pct(total_avg_success_delta))
    col2.metric(label="近期胜率", value=float_to_pct(recent_avg_success), delta=float_to_pct(recent_avg_success_delta), help='最近一个完整比赛周的胜率，并和再上一周的胜率进行对比')
    col3.metric(label="最佳球队", value=df_table_team['team'][len(df_table_team)-1], delta=df_table_team['team'][len(df_table_team)-2], delta_color='off', help='推荐比赛中赢盘率最高的前两支球队')

    col4, col5, col6 = st.columns(3)
    col4.metric(label="最佳联赛", value=df_table_league['联赛'][0], delta=df_table_league['联赛'][1], delta_color='off', help='胜率最高的前两个联赛')
    col5.metric(label="最佳模型", value=df_table_model['模型'][0], delta=df_table_model['模型'][1], delta_color='off', help='胜率最高的前两个模型')
    col6.metric(label="最佳盘口", value=df_table_handicap['盘口'][len(df_table_handicap)-1], delta=df_table_handicap['盘口'][len(df_table_handicap)-2], delta_color='off', help='胜率最高的前两个盘口')
    
    st.metric(label='最佳组合', value='敬请期待')

    #图0：每周胜率折线图
    df_table_weekly_success = df_metric.groupby('week').aggregate({'success': 'mean', '比赛':'count'}).reset_index().round(decimals=2)
    fig0 = px.line(df_table_weekly_success, x="week", y="success", hover_name='比赛', markers=True, text='success', line_shape='spline')
    fig0.add_hline(y=total_avg_success, line_dash="dot", line_color="green", annotation_text="总体平均胜率",
                   annotation_position="top left",
                   annotation_font_size=10,
                   annotation_font_color="green")
    fig0.update_traces(textposition='top center')
    fig0.update_layout(hovermode="x")
    with st.expander("23-24赛季胜率走势", expanded=True): # Change me once a year
        st.plotly_chart(fig0)
        
    figcol1, figcol2 = st.columns(2)
    with figcol1:
        #图1：各联赛胜率柱状图
        fig1 = px.bar(df_table_league, x="success", y="联赛", color='success', hover_name='比赛', range_x=[0,1], orientation='h', text_auto='.2f')
        fig1.update_layout(hovermode="y")
        with st.expander("最新联赛胜率", expanded=True):
            st.plotly_chart(fig1)    
            
        #图2：各模型胜率柱状图
        fig2 = px.bar(df_table_model, x="success", y="模型", color='success', hover_name='比赛', range_x=[0,1], orientation='h', text_auto='.2f')
        fig2.update_layout(hovermode="y")
        with st.expander("最新模型胜率", expanded=True):
            st.plotly_chart(fig2)
            
    with figcol2:
        #图3：最佳球队柱状图
        df_table_team_top = df_table_team.iloc[-20:]
        fig3 = px.bar(df_table_team_top, x="success", y="team", color='success', hover_name='比赛', range_x=[0,1], orientation='h', text_auto='.2f')
        fig3.update_layout(hovermode="y")
        with st.expander("最佳球队Top20", expanded=True):
            st.plotly_chart(fig3)
            
        #图4：各盘口胜率柱状图
        fig4 = px.bar(df_table_handicap, x="success", y="盘口", color='success', hover_name='比赛', range_x=[0,1], orientation='h', text_auto='.2f')
        fig4.update_layout(hovermode="y")
        with st.expander("最新盘口胜率", expanded=True):
                st.plotly_chart(fig4)      
        
    #表1：球队红黑榜
    df_table_team = df_table_team.sort_values(by=['success', '比赛'], ascending=False).reset_index()
    del df_table_team['index']
    with st.expander('球队红黑榜', expanded=True):
        st.dataframe(df_table_team, width=1000)

def calc_success(df):
    '''
    传入dataframe后计算并返回该df内的准确率
    '''
    num_success = len(df[df['正误']=='\u2714'])
    return float(num_success/(len(df)))

def float_to_pct(floatpoint):
    return str(round(floatpoint*100, 3))+'%'

def pct_to_float(pct):
    return float(pct.strip('%'))/100

def remove_exclamation(text):
    text = text.replace('！','').split('新发现')[1]
    text = text.replace('模型','')
    return text

# *** 连接层函数 *** #
#onedrive
@st.cache_data
def load_history():
    onedrive_link = 'https://1drv.ms/x/s!Ag9ZvloaJitBkDvM3TVDY7HffBxS'
    url = create_onedrive_directdownload(onedrive_link)
    df = pd.read_excel(url, sheet_name=1, converters = {'盘口': str, 'week': str}) # Change me once a year
    df = df[df['模型'].notnull()]
    df = df.reset_index()
    del df['index']
    return df

def create_onedrive_directdownload(onedrive_link):
    data_bytes64 = base64.b64encode(bytes(onedrive_link, 'utf-8'))
    data_bytes64_String = data_bytes64.decode('utf-8').replace('/','_').replace('+','-').rstrip("=")
    resultUrl = f"https://api.onedrive.com/v1.0/shares/u!{data_bytes64_String}/root/content"
    return resultUrl

def read_file(data):
    df = pd.read_excel(data, sheet_name = 1, converters = {'盘口': str, '竞彩': str, '比分': str})
    df['盘口数字'] = df['盘口'].astype(float)
    df['算法'] = df['算法'].fillna('球伯乐')
    df['注释'] = df['注释'].fillna('')
    df['批注胜'] = df['批注胜'].fillna('')
    df['批注平'] = df['批注平'].fillna('')
    df['批注负'] = df['批注负'].fillna('')
    df['批注让胜'] = df['批注让胜'].fillna('')
    df['批注让平'] = df['批注让平'].fillna('')
    df['批注让负'] = df['批注让负'].fillna('')
    return df
    
# *** 核心层函数 *** #
# 计算概率、判断上下盘及遗漏提示
def calc_prob(home, away, deep, result, total):        
    p_win = (len(result[result['H'] >result['A']])/total)*100
    p_tie = (len(result[result['H']==result['A']])/total)*100
    p_los = (len(result[result['H'] <result['A']])/total)*100
    if home and deep:
        p_h2 = (len(result[(result['H']-result['A']) > 1])/total)*100
        st.write("主胜占比:",round(p_win,2),'%',"平局占比:",round(p_tie,2),'%',"客胜占比:",round(p_los,2),'%',"主队赢得两球及以上占比:",round(p_h2,2),'%')
    elif away and deep:
        p_a2 = (len(result[(result['A']-result['H']) > 1])/total)*100
        st.write("主胜占比:",round(p_win,2),'%',"平局占比:",round(p_tie,2),'%',"客胜占比:",round(p_los,2),'%',"客队赢得两球及以上占比:",round(p_a2,2),'%')
    else:
        st.write("主胜占比:",round(p_win,2),'%',"平局占比:",round(p_tie,2),'%',"客胜占比:",round(p_los,2),'%')
    #主让上盘方向    
    if home and not deep and p_win > (p_tie+p_los):
        miss = 0
        if p_win >= 60:
            for index, row in result.iterrows():
                if row['H'] <= row['A']:
                    miss += 1
                else:
                    miss = 0
            if miss > 1:
                st.write("提示：主队赢盘遗漏",miss,"场")
        return p_win, 'home', miss
    #主让下盘方向
    elif home and not deep and p_win <= (p_tie+p_los):
        miss = 0
        if (p_tie+p_los) >= 60:
            for index, row in result.iterrows():
                if row['H'] > row['A']:
                    miss += 1
                else:
                    miss = 0
            if miss > 1:
                st.write("提示：客队赢盘遗漏",miss,"场")
        return p_tie+p_los, 'away', miss
    #客让上盘方向
    elif away and not deep and p_los > (p_tie+p_win):
        miss = 0
        if p_los >= 60:
            for index, row in result.iterrows():
                if row['H'] >= row['A']:
                    miss += 1
                else:
                    miss = 0
            if miss > 1:
                st.write("提示：客队赢盘遗漏",miss,"场")
        return p_los, 'away', miss
    #客让下盘方向
    elif away and not deep and p_los <= (p_tie+p_win):
        miss = 0
        if (p_tie+p_win) >= 60:
            for index, row in result.iterrows():
                if row['H'] < row['A']:
                    miss += 1
                else:
                    miss = 0
            if miss > 1:
                st.write("提示：主队赢盘遗漏",miss,"场")
        return p_win+p_tie, 'home', miss
    #深盘主让上盘方向
    elif home and deep and p_h2 > 50:
        miss = 0
        if p_h2 >= 60:
            for index, row in result.iterrows():
                if (row['H']-1) <= row['A']:
                    miss += 1
                else:
                    miss = 0
            if miss > 1:
                st.write("提示：主队赢盘遗漏",miss,"场")
        return p_h2, 'home', miss
    #深盘主让下盘方向
    elif home and deep and p_h2 <= 50:
        miss = 0
        if p_h2 <= 40:
            for index, row in result.iterrows():
                if (row['H']-1) > row['A']:
                    miss += 1
                else:
                    miss = 0
            if miss > 1:
                st.write("提示：客队赢盘遗漏",miss,"场")
        return 100-p_h2, 'away', miss        
    #深盘客让上盘方向
    elif away and deep and p_a2 > 50:
        miss = 0
        if p_a2 >= 60:
            for index, row in result.iterrows():
                if (row['H']+1) >= row['A']:
                    miss += 1
                else:
                    miss = 0
            if miss > 1:
                st.write("提示：客队赢盘遗漏",miss,"场")
        return p_a2, 'away', miss
    #深盘客让下盘方向
    elif away and deep and p_a2 <= 50:
        miss = 0
        if p_a2 <= 40:
            for index, row in result.iterrows():
                if (row['H']+1) < row['A']:
                    miss += 1
                else:
                    miss = 0
            if miss > 1:
                st.write("提示：主队赢盘遗漏",miss,"场")
        return 100-p_a2, 'home', miss

# 对预估概率进行修正
def laplace(temp, total):
    num = (temp/100)*total
    est_prob = (num+1)/(total+2)
    return est_prob*100
    
# 储存每一步筛选的上/下盘概率
def decision(home, away, uppr, down, temp, signal):
    if home:
        if signal == 'home':
            uppr.append(temp)
            down.append(100-temp)
        elif signal == 'away':
            down.append(temp)
            uppr.append(100-temp)
    elif away:
        if signal == 'away':
            uppr.append(temp)
            down.append(100-temp)
        elif signal == 'home':
            down.append(temp)
            uppr.append(100-temp)
    return uppr, down

# 储存60%(拉普拉斯修正后约57%)/70%/80%概率的算法数
def analysis(best_prob, count):
    if 57 < best_prob < 70:
        count[0] += 1
    elif 70 <= best_prob < 80:
        count[1] += 1
    elif best_prob >= 80:
        count[2] += 1
    return count

#判断历史比赛正误
def judge(new_score, hand, home, away, deep, signal):
    if home and not deep:
        if signal == 'uppr':
            if new_score[0] > new_score[1]:
                return True
            elif hand == 0 and new_score[0] >= new_score[1]:
                return True
            else:
                return False
        elif signal == 'down':
            if new_score[0] <= new_score[1]:
                return True
            elif hand >= 1 and (new_score[0]-1) <= new_score[1]:
                return True
            else:
                return False
    elif home and deep:
        if signal == 'uppr':
            if (new_score[0]+hand) >= new_score[1]:
                return True
            else:
                return False
        elif signal == 'down':
            if (new_score[0]+hand) <= new_score[1]:
                return True
            else:
                return False
    elif away and not deep:
        if signal == 'uppr':
            if new_score[0] < new_score[1]:
                return True
            elif hand == 0 and new_score[0] <= new_score[1]:
                return True
            else:
                return False
        elif signal == 'down':
            if new_score[0] >= new_score[1]:
                return True
            elif hand >= 1 and (new_score[0]+1) >= new_score[1]:
                return True
            else:
                return False
    elif away and deep:
        if signal == 'uppr':
            if (new_score[0]+hand) <= new_score[1]:
                return True
            else:
                return False
        elif signal == 'down':
            if (new_score[0]+hand) >= new_score[1]:
                return True
            else:
                return False
            
# 计算出现频率最高的比分            
def score_freq(score):
    line = ''
    freq = 0
    L = Counter(score).most_common(1)
    score_L = [X[0] for X in L]
    freqc_L = [X[1] for X in L]
    for Y in score_L:
        line = Y
    for Z in freqc_L:
        freq = Z
    return line, freq
    
# 回测主函数
def search(df, opt1):
    history = False
    if opt1:
        history = True
    dfb = pd.DataFrame(columns=['联赛','比赛','让球方','盘口','模型','平均概率','最长遗漏','高频比分','频率','算法数量','正误','注释'])
    
    #储存每一行信息的变量
    liga = '中甲'
    prev = 'nmsl' #上一行比赛名称
    hand = 'mlgb' #上一行盘口
    num_hand = 69 #上一行盘口数字
    home = False #主让
    away = False #客让
    deep = False #深盘
    
    #储存每一场比赛信息的变量
    uppr_count = [0,0,0] #上盘三星级 四星级 五星级算法结果数量
    down_count = [0,0,0] #下盘三星级 四星级 五星级算法结果数量
    avg_uppr = [] #各算法上盘最优概率
    avg_down = [] #各算法下盘最优概率
    upprmiss = [] #上盘遗漏数量
    downmiss = [] #下盘遗漏数量
    algo = 1      #每场比赛算法数量
    score = ()    #每场比赛推荐比分
    comment = []  #每场比赛注释和批注
    
    for index, row in df[df['H'].isnull() & df['盘口'].notnull()].iterrows():
        flag = False #非竞彩客让
        rare = False #竞彩客让
        roll = False #继续筛选
        skip = False #跳过让负
        best_prob = 0 #当前算法最优概率
        temp_miss = []#当前算法遗漏数量
        uppr = [] #每次筛选后的上盘概率
        down = [] #每次筛选后的下盘概率
        
        #旧比赛
        if row['比赛'] == prev:
            algo += 1
        #新比赛
        else:
            if prev != 'nmsl':
                #计算最高频比分
                line, freq = score_freq(score)
            #上盘
            if sum(uppr_count)/algo > 0.5 and algo > 1:
                #注释和批注
                com_str = ''
                if comment:
                    for item in comment:
                        item = str(item)
                        com_str += str(item + ",")
                    com_str = com_str[:-1]
                #写入上盘信息
                avg_best = mean(avg_uppr)
                if home:
                    side = '主让'
                elif away:
                    side = '客让'
                if upprmiss:
                    num_miss = max(upprmiss)
                else:
                    num_miss = 0
            
                if history:
                    TF = judge(new_score, num_hand, home, away, deep, 'uppr')
                    if TF:
                        outcome = '\u2714'
                    else:
                        outcome = '\u2716'
                else:
                    outcome = ''
                
                if avg_best >= 60 and uppr_count[2] > 0:
                    model = '新发现！！！五星级上盘模型'
                    st.write('新发现！！！五星级上盘模型：',prev,'平均概率',round(avg_best,2),'%')
                elif avg_best >= 60 and uppr_count[1] > 0:
                    model = '新发现！！四星级上盘模型'
                    st.write('新发现！！四星级上盘模型：',prev,'平均概率',round(avg_best,2),'%')
                elif (avg_best >= 50) and ((uppr_count[0] > 1) or (uppr_count[1] > 0) or (uppr_count[2] > 0)):
                    model = '新发现！三星级上盘模型'
                    st.write('新发现！三星级上盘模型：',prev,'平均概率',round(avg_best,2),'%')
                else:
                    model = ''
                dfb = dfb.append({'联赛': liga, '比赛': prev, '让球方': side, '盘口': hand, '模型': model, '平均概率': str(round(avg_best,2))+'%', '最长遗漏': num_miss, '高频比分': line, '频率': freq, '算法数量': str(sum(uppr_count))+'/'+str(algo), '正误': outcome, '注释': com_str}, ignore_index=True)
            #下盘
            elif sum(down_count)/algo > 0.5 and algo > 1:
                #注释和批注
                com_str = ''
                if comment:
                    for item in comment:
                        item = str(item)
                        com_str += str(item + ",")
                    com_str = com_str[:-1]
                #写入下盘信息
                avg_best = mean(avg_down)
                if home:
                    side = '主让'
                elif away:
                    side = '客让'
                if downmiss:
                    num_miss = max(downmiss)
                else:
                    num_miss = 0
                    
                if history:
                    TF = judge(new_score, num_hand, home, away, deep, 'down')
                    if TF:
                        outcome = '\u2714'
                    else:
                        outcome = '\u2716'
                else:
                    outcome = ''
                    
                if avg_best >= 60 and down_count[2] > 0:
                    model = '新发现！！！五星级下盘模型'                    
                    st.write('新发现！！！五星级下盘模型：',prev,'平均概率',round(avg_best,2),'%')
                elif avg_best >= 60 and down_count[1] > 0:
                    model = '新发现！！四星级下盘模型'
                    st.write('新发现！！四星级下盘模型：',prev,'平均概率',round(avg_best,2),'%')
                elif (avg_best >= 50) and ((down_count[0] > 1) or (down_count[1] > 0) or (down_count[2] > 0)):
                    model = '新发现！三星级下盘模型'
                    st.write('新发现！三星级下盘模型：',prev,'平均概率',round(avg_best,2),'%')
                else:
                    model = ''
                dfb = dfb.append({'联赛': liga, '比赛': prev, '让球方': side, '盘口': hand, '模型': model, '平均概率': str(round(avg_best,2))+'%', '最长遗漏': num_miss, '高频比分': line, '频率': freq, '算法数量': str(sum(down_count))+'/'+str(algo), '正误': outcome, '注释': com_str}, ignore_index=True)
            st.write('=============================================')
            #重置上一场比赛信息
            algo = 1
            score = []
            comment = []
            uppr_count = [0,0,0]
            down_count = [0,0,0]
            avg_uppr = []
            avg_down = []
            upprmiss = []
            downmiss = []
        #清空上一行信息并更新
        liga = row['联赛']
        prev = row['比赛']
        hand = row['盘口']
        num_hand = row['盘口数字']
        home = False
        away = False
        deep = False
        
        #判断让球方
        if row['盘口'].__contains__('-'):
            if (row['盘口']=='-0.25') and (row['让胜'] <= row['平']+row['胜']+0.03) and (row['让胜'] >= row['平']+row['胜']-0.03) and (0 < (row['胜']+row['平']) < 1):
                away = True
            elif (row['盘口']=='-0') and (row['让胜'] <= row['平']+row['胜']+0.03) and (row['让胜'] >= row['平']+row['胜']-0.03) and (0 < (row['胜']+row['平'])) and (row['竞彩'] == '是'):
                away = True
            else:
                home = True

        elif row['盘口'].__contains__('+'):
            if (row['竞彩'] == '是') and (row['让负'] <= row['平']+row['负']+0.03) and (row['让负'] >= row['平']+row['负']-0.03):
                home = True
            else:
                away = True
        #深盘比赛
        if (row['盘口数字'] < -1.25) or (row['盘口数字'] > 1.25):
            deep = True

        if home:
            st.write("正在分析:",row['联赛'],row['比赛'],row['算法'],'主队让球:',row['盘口'],"\n")
        elif away:
            st.write("正在分析:",row['联赛'],row['比赛'],row['算法'],'客队让球:',row['盘口'],"\n")
            
        #第0轮筛选 胜平负
        result0 = df[(df['H'].notnull()) & (df['胜'] == row['胜']) & (df['平'] == row['平'])]
        total = len(result0)
        if total < 2:
            st.write("历史样本不足:",total,'场')
        elif total >= 2 and total < 8:
            temp = df[(df['H'].notnull()) & (df['胜'] == row['负']) & (df['平'] == row['平'])]
            mixed = pd.concat([result0, temp], axis=0)
            mix_total = len(mixed)
            temp_home = mixed[mixed['盘口'].str.contains('\-')]
            temp_away = mixed[mixed['盘口'].str.contains('\+')]
            if deep:
                p_uppr = ((len(temp_home[(temp_home['H']-temp_home['A']) > 1])+len(temp_away[(temp_away['A']-temp_away['H']) > 1])+1)/(mix_total+2))*100
                p_down = 100-p_uppr
            else:
                p_uppr = ((len(temp_home[temp_home['H'] > temp_home['A']])+len(temp_away[temp_away['H'] < temp_away['A']])+1)/(mix_total+2))*100
                p_down = 100-p_uppr
            if mix_total >= 5:
                uppr.append(p_uppr)
                down.append(p_down)
                
            if len(temp)==0:
                st.write("按胜平负匹配历史比赛",total,"场")
                calc_prob(home, away, deep, result0, total)
            else:
                st.write("按双向胜平负匹配历史比赛",mix_total,"场")
                st.write("上盘概率:",round(p_uppr,2),'%',"下盘概率:",round(p_down,2),'%')
                
            if mix_total >= 8:
                m_result1 = mixed[(mixed['盘口数字'] <= row['盘口数字']+0.25) & (mixed['盘口数字'] >= row['盘口数字']-0.25)]
                m_result2 = mixed[(mixed['盘口数字'] <= row['盘口数字']*(-1)+0.25) & (mixed['盘口数字'] >= row['盘口数字']*(-1)-0.25)]
                m_result = pd.concat([m_result1, m_result2], axis=0)
                m_result.drop_duplicates(subset=['比赛'], keep='first', inplace=True)
                total = len(m_result)
                if total > 0:
                    st.write("按双向模糊盘口匹配历史比赛",total,"场")
                    temp_home = m_result[m_result['盘口'].str.contains('\-')]
                    temp_away = m_result[m_result['盘口'].str.contains('\+')]
                    if deep:
                        p_uppr = ((len(temp_home[(temp_home['H']-temp_home['A']) > 1])+len(temp_away[(temp_away['A']-temp_away['H']) > 1])+1)/(total+2))*100
                        p_down = 100-p_uppr
                    else:
                        p_uppr = ((len(temp_home[temp_home['H'] > temp_home['A']])+len(temp_away[temp_away['H'] < temp_away['A']])+1)/(total+2))*100
                        p_down = 100-p_uppr
                    st.write("上盘概率:",round(p_uppr,2),'%',"下盘概率:",round(p_down,2),'%')
                    if total >= 5:
                        uppr.append(p_uppr)
                        down.append(p_down)
                
                if total >= 8:
                    m_result3 = m_result[(m_result['盘口数字'] == row['盘口数字']) | (m_result['盘口数字'] == row['盘口数字']*(-1))]
                    total = len(m_result3)
                    if total > 0:
                        st.write("按双向精确盘口匹配历史比赛",total,"场")
                        temp_home = m_result3[m_result3['盘口'].str.contains('\-')]
                        temp_away = m_result3[m_result3['盘口'].str.contains('\+')]
                        if deep:
                            p_uppr = ((len(temp_home[(temp_home['H']-temp_home['A']) > 1])+len(temp_away[(temp_away['A']-temp_away['H']) > 1])+1)/(total+2))*100
                            p_down = 100-p_uppr
                        else:
                            p_uppr = ((len(temp_home[temp_home['H'] > temp_home['A']])+len(temp_away[temp_away['H'] < temp_away['A']])+1)/(total+2))*100
                            p_down = 100-p_uppr
                        st.write("上盘概率:",round(p_uppr,2),'%',"下盘概率:",round(p_down,2),'%')
                        if total >= 5:
                            uppr.append(p_uppr)
                            down.append(p_down)
              
        else:
            roll = True
            st.write("按胜平负匹配历史比赛",total,"场")
            temp, signal, num_miss = calc_prob(home, away, deep, result0, total)
            temp_miss.append(num_miss)
            temp = laplace(temp, total)
            uppr, down = decision(home, away, uppr, down, temp, signal)
            if away and (row['让负'] <= row['平']+row['负']+0.03) and (row['让负'] >= row['平']+row['负']-0.03):
                flag = True
            elif away and (row['让胜'] <= row['平']+row['胜']+0.03) and (row['让胜'] >= row['平']+row['胜']-0.03):
                rare = True

        #第1轮筛选 让球方向
        if roll:
            roll = False
            if home:
                result1 = result0[result0['盘口'].str.contains('\-', na=True)]
            elif away:
                result1 = result0[result0['盘口'].str.contains('\+', na=True)]
            total = len(result1)
            if total > 0:
                st.write("按让球方匹配历史比赛",total,"场")
                temp, signal, num_miss = calc_prob(home, away, deep, result1, total)
                temp_miss.append(num_miss)
                temp = laplace(temp, total)
                if total >= 5:
                    uppr, down = decision(home, away, uppr, down, temp, signal)
                
            if total >= 8:
                roll = True
                if deep or flag or rare:
                    roll = False
                    skip = True
                    result2 = result1
                            
        #第2轮筛选 让负/让胜
        if roll:
            result2 = result1[result1['让负'] == row['让负']]
            total = len(result2)
            if total >= 5:
                st.write("按让负匹配历史比赛",total,"场")
                temp, signal, num_miss = calc_prob(home, away, deep, result2, total)
                temp_miss.append(num_miss)
                temp = laplace(temp, total)
                uppr, down = decision(home, away, uppr, down, temp, signal)
            else:
                result2 = result1

        elif rare:
            result2 = result1[result1['让胜'] == row['让胜']]
            total = len(result2)
            if total >= 5:
                st.write("按让胜匹配历史比赛",total,"场")
                temp, signal, num_miss = calc_prob(home, away, deep, result2, total)
                temp_miss.append(num_miss)
                temp = laplace(temp, total)
                uppr, down = decision(home, away, uppr, down, temp, signal)
            else:
                result2 = result1
                
        #第3轮筛选 盘口±0.25    
        if roll or skip:
            roll = False
            result3 = result2[(result2['盘口数字'] >= row['盘口数字']-0.25) & (result2['盘口数字'] <= row['盘口数字']+0.25)]
            total = len(result3)
            if total > 0:
                st.write("按模糊盘口匹配历史比赛",total,"场")
                temp, signal, num_miss = calc_prob(home, away, deep, result3, total)
                temp_miss.append(num_miss)
                temp = laplace(temp, total)
                if total >= 5:
                    uppr, down = decision(home, away, uppr, down, temp, signal)
                
            if total >= 8:
                roll = True
                
        #第4轮筛选 盘口
        if roll:
            result4 = result3[result3['盘口数字'] == row['盘口数字']]
            total = len(result4)
            if total > 0:
                st.write("按精确盘口匹配历史比赛",total,"场")
                temp, signal, num_miss = calc_prob(home, away, deep, result4, total)
                temp_miss.append(num_miss)
                temp = laplace(temp, total)
                if total >= 5:
                    uppr, down = decision(home, away, uppr, down, temp, signal)
                
        #收敛与计数
        if mean(uppr) > mean(down):
            best_prob = max(uppr)
            if temp_miss:
                upprmiss.append(temp_miss[uppr.index(best_prob)])
            avg_uppr.append(best_prob)
            avg_down.append(100-best_prob)
            uppr_count = analysis(best_prob, uppr_count)
            st.write('综合分析看好上盘获胜，概率：',round(best_prob,2),'%')
        elif mean(down) > mean(uppr):
            best_prob = max(down)
            if temp_miss:
                downmiss.append(temp_miss[down.index(best_prob)])
            avg_down.append(best_prob)
            avg_uppr.append(100-best_prob)
            down_count = analysis(best_prob, down_count)
            st.write('综合分析看好下盘获胜，概率：',round(best_prob,2),'%')
        else:
            st.write('建议放弃')
        st.write('\n')
        
        #收集推荐比分
        temp_score = row['比分'].split(' ')
        temp_score = tuple(temp_score)
        score += temp_score
        
        #收集注释和批注
        if row['算法'] == '球伯乐' and row['注释']:
            comment.append(row['注释'])
        if row['批注胜']:
            comment.append('胜:'+row['批注胜'])
        if row['批注平']:
            comment.append('平:'+row['批注平'])
        if row['批注负']:
            comment.append('负:'+row['批注负'])
        if row['批注让胜']:
            comment.append('让胜:'+row['批注让胜'])
        if row['批注让平']:
            comment.append('让平:'+row['批注让平'])
        if row['批注让负']:
            comment.append('让负:'+row['批注让负'])
        
        #处理最后一行        
        if index == df[df['H'].isnull() & df['盘口'].notnull()].index[-1]:
            line, freq = score_freq(score)
            #上盘
            if sum(uppr_count)/algo > 0.5 and algo > 1:
                #注释和批注
                com_str = ''
                if comment:
                    for item in comment:
                        item = str(item)
                        com_str += str(item + ",")
                    com_str = com_str[:-1]
                #写入上盘信息
                avg_best = mean(avg_uppr)
                if home:
                    side = '主让'
                elif away:
                    side = '客让'
                if upprmiss:
                    num_miss = max(upprmiss)
                else:
                    num_miss = 0
            
                if history:
                    TF = judge(new_score, num_hand, home, away, deep, 'uppr')
                    if TF:
                        outcome = '\u2714'
                    else:
                        outcome = '\u2716'
                else:
                    outcome = ''
                
                if avg_best >= 60 and uppr_count[2] > 0:
                    model = '新发现！！！五星级上盘模型'
                    st.write('新发现！！！五星级上盘模型：',prev,'平均概率',round(avg_best,2),'%')
                elif avg_best >= 60 and uppr_count[1] > 0:
                    model = '新发现！！四星级上盘模型'
                    st.write('新发现！！四星级上盘模型：',prev,'平均概率',round(avg_best,2),'%')
                elif (avg_best >= 50) and ((uppr_count[0] > 1) or (uppr_count[1] > 0) or (uppr_count[2] > 0)):
                    model = '新发现！三星级上盘模型'
                    st.write('新发现！三星级上盘模型：',prev,'平均概率',round(avg_best,2),'%')
                else:
                    model = ''
                dfb = dfb.append({'联赛': liga, '比赛': prev, '让球方': side, '盘口': hand, '模型': model, '平均概率': str(round(avg_best,2))+'%', '最长遗漏': num_miss, '高频比分': line, '频率': freq, '算法数量': str(sum(uppr_count))+'/'+str(algo), '正误': outcome, '注释': com_str}, ignore_index=True)
            #下盘
            elif sum(down_count)/algo > 0.5 and algo > 1:
                #注释和批注
                com_str = ''
                if comment:
                    for item in comment:
                        item = str(item)
                        com_str += str(item + ",")
                    com_str = com_str[:-1]
                #写入下盘信息
                avg_best = mean(avg_down)
                if home:
                    side = '主让'
                elif away:
                    side = '客让'
                if downmiss:
                    num_miss = max(downmiss)
                else:
                    num_miss = 0
                    
                if history:
                    TF = judge(new_score, num_hand, home, away, deep, 'down')
                    if TF:
                        outcome = '\u2714'
                    else:
                        outcome = '\u2716'
                else:
                    outcome = ''
                    
                if avg_best >= 60 and down_count[2] > 0:
                    model = '新发现！！！五星级下盘模型'                    
                    st.write('新发现！！！五星级下盘模型：',prev,'平均概率',round(avg_best,2),'%')
                elif avg_best >= 60 and down_count[1] > 0:
                    model = '新发现！！四星级下盘模型'
                    st.write('新发现！！四星级下盘模型：',prev,'平均概率',round(avg_best,2),'%')
                elif (avg_best >= 50) and ((down_count[0] > 1) or (down_count[1] > 0) or (down_count[2] > 0)):
                    model = '新发现！三星级下盘模型'
                    st.write('新发现！三星级下盘模型：',prev,'平均概率',round(avg_best,2),'%')
                else:
                    model = ''
                dfb = dfb.append({'联赛': liga, '比赛': prev, '让球方': side, '盘口': hand, '模型': model, '平均概率': str(round(avg_best,2))+'%', '最长遗漏': num_miss, '高频比分': line, '频率': freq, '算法数量': str(sum(down_count))+'/'+str(algo), '正误': outcome, '注释': com_str}, ignore_index=True)
            st.write('=============================================')
        #提取赛果并储存
        if history:
            scoreline = re.findall('[0-9]+', row['比赛'])
            new_score = [int(s) for s in scoreline]
            df.loc[index, 'H'] = new_score[0]
            df.loc[index, 'A'] = new_score[1]
    return dfb
    
if __name__ == "__main__":
    main()

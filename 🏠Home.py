# -*- coding: utf-8 -*-
"""
Last Edit 12/25/2023
@author: zhangliyao
"""

import streamlit as st

def main():
    st.sidebar.title("关于")
    st.sidebar.info(
    """
    GitHub repository: <https://github.com/judd147/xingchenscrapers>
    
    作者: 张力铫
    """
    )
    st.title('Soccer Betting Automated')
    st.caption('')
    st.header('Introduction')
    st.markdown('该项目致力于实现足球赛事的**数据自动获取和自动回测分析**。'
                '目前已经实现全自动化稳定获取星辰智盈5大算法数据；用户在excel表中输入未开赛比赛盘口，系统将按照一套固定算法回测历史数据计算上下盘概率并根据概率判断投资价值。'
                '未来回测算法将使用贝叶斯模型进行全面升级，提升准确率；对于完场赛事，系统将自动抓取AsianBetSoccer的比分和亚盘数据。')

    st.header('Updates and Plans')
    st.subheader('架构设计')
    st.checkbox('数据库从OneDrive迁移至MySQL')
    st.checkbox('Deploy to Streamlit Cloud & Auth0')
    st.write("https://github.com/conradbez/streamlit-auth0")
    st.subheader('星辰智盈数据自动获取系统')
    st.checkbox('数据源由安卓模拟器改为网页，抓取速度和稳定性获得大幅提升', value=True)
    st.checkbox('增加直播火线数据')
    st.subheader('星辰智盈数据自动回测系统')
    st.checkbox('增加组合查询功能', value=True)
    st.checkbox('🚧 增加模拟盈亏功能，结合真实赔率数据计算盈利能力')
    st.checkbox('🚧 升级算法提高预测成功率（方差法，伯努利抽样分布，提高数量门槛等）')
    st.checkbox('增加历史赛季胜率数据展示')
    st.subheader('比分盘口自动获取系统')
    st.checkbox('数据源由Sofascore改为AsianBetSoccer，抓取速度和稳定性获得大幅提升', value=True)
    st.checkbox('比赛日结束后自动获取')
    
if __name__ == "__main__":
    main()
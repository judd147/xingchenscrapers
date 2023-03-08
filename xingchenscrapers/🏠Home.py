# -*- coding: utf-8 -*-
"""
Last Edit 2/4/2023
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
    st.title('足球比赛自动化项目')
    st.caption('')
    st.header('Introduction')
    st.markdown('该项目致力于实现足球赛事的**数据自动获取和自动回测分析**。'
                '目前已经实现全自动化稳定获取星辰智盈5大算法数据；用户在excel表中输入未开赛比赛盘口，系统将按照一套固定算法回测历史数据计算上下盘概率并根据概率判断投资价值。'
                '未来回测算法将使用贝叶斯模型进行全面升级，提升准确率；对于完场赛事，系统将自动抓取sofascore的比分和亚盘数据，目前完整率接近100%。')

    st.header('Updates and Plans')
    st.subheader('星辰智盈数据自动获取系统')
    st.checkbox('修复了临场模式的起始时间bug')
    st.subheader('星辰智盈数据自动回测系统')
    st.checkbox('已增加查询指定球队历史战绩功能')
    st.subheader('Sofascore比分盘口自动获取系统')
    st.checkbox('已更新2023赛季阿甲球队字典')
    
if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 20 09:55:50 2022

@author: zhangliyao
"""

import streamlit as st

def main():
    st.sidebar.title("关于")
    st.sidebar.info(
    """
    GitHub repository: <https://github.com/judd147>
    """
    )

if __name__ == "__main__":
    main()
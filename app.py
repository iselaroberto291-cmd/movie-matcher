import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz

st.set_page_config(page_title="影视内容高精度自动匹配工具", layout="wide")

# UI 样式
st.markdown("""
    <style>
    .warning-box { background-color: #fffbe6; border: 1px solid #ffe58f; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
    .blue-header { background-color: #3498db; color: white; padding: 10px 20px; border-radius: 5px 5px 0 0; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("李阳专属工具！")

st.markdown('<div class="warning-box"><b>🚀 高精度模式已开启</b><br>'
            '当前支持：片名 + 年份 + 导演 + 演员 四维度交叉匹配。</div>', unsafe_allow_html=True)

st.markdown('<div class="blue-header">文件上传与管理</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    base_file = st.file_uploader("上传影视底库 (主表)", type=["xlsx", "csv"], key="u_base")
with col2:
    target_file = st.file_uploader("上传待匹配表", type=["xlsx", "csv"], key="u_target")

if base_file and target_file:
    df_base = pd.read_excel(base_file) if base_file.name.endswith('xlsx') else pd.read_csv(base_file)
    df_target = pd.read_excel(target_file) if target_file.name.endswith('xlsx') else pd.read_csv(target_file)
    
    st.divider()
    st.subheader("⚙️ 匹配列名设置")
    base_cols = df_base.columns.tolist()
    target_cols = df_target.columns.tolist()

    # 动态选择匹配列
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        b_name = st.selectbox("底库：片名列", base_cols, key="bn")
        t_name = st.selectbox("目标：片名列", target_cols, key="tn")
    with c2:
        b_year = st.selectbox("底库：年份列", base_cols, key="by")
        t_year = st.selectbox("目标：年份列", target_cols, key="ty")
    with c3:
        b_dir = st.selectbox("底库：导演列", base_cols, key="bd")
        t_dir = st.selectbox("目标：导演列", target_cols, key="td")
    with c4:
        b_act = st.selectbox("底库：演员列", base_cols, key="ba")
        t_act = st.selectbox("目标：演员列", target_cols, key="ta")

    threshold = st.slider("匹配敏感度 (推荐85)", 50, 100, 85, key="slider")

    if st.button("开始高精度全维度匹配", type="primary", key="go"):
        results = []
        bar = st.progress(0)
        
        for i, row in df_target.iterrows():
            # 提取目标数据
            t_val = f"{row[t_name]} {row[t_dir]} {row[t_act]}"
            t_y = row[t_year]
            
            # 1. 年份硬过滤：锁定在同一年份的影视中寻找
            candidates = df_base[df_base[b_year] == t_y]
            
            if not candidates.empty:
                # 2. 构建底库对比字符串：片名 + 导演 + 演员
                choices = (candidates[b_name].astype(str) + " " + 
                           candidates[b_dir].astype(str) + " " + 
                           candidates[b_act].astype(str)).tolist()
                
                # 3. 模糊语义算法比对
                res = process.extractOne(t_val, choices, scorer=fuzz.token_sort_ratio)
                
                if res and res[1] >= threshold:
                    match_idx = candidates.index[choices.index(res[0])]
                    match_row = df_base.loc[match_idx]
                    results.append({"匹配结果": res[0], "置信度": round(res[1],1), "底库ID": match_row.get('ID', '成功')})
                else:
                    results.append({"匹配结果": "无匹配", "置信度": res[1] if res else 0, "底库ID": "N/A"})
            else:
                results.append({"匹配结果": "年份无对应", "置信度": 0, "底库ID": "N/A"})
            
            if i % 100 == 0:
                bar.progress(i / len(df_target))

        final_df = pd.concat([df_target, pd.DataFrame(results)], axis=1)
        st.success("匹配完成！")
        st.dataframe(final_df.head(100))
        st.download_button("下载完整报告", final_df.to_csv(index=False).encode('utf-8-sig'), "movie_match_result.csv")
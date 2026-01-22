import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz

st.set_page_config(page_title="影视内容自动匹配工具", layout="wide")

# UI 样式
st.markdown("""
    <style>
    .warning-box { background-color: #fffbe6; border: 1px solid #ffe58f; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
    .blue-header { background-color: #3498db; color: white; padding: 10px 20px; border-radius: 5px 5px 0 0; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("李阳专属影视匹配工具")

st.markdown('<div class="warning-box"><b>💡 使用说明：</b><br>'
            '1. 分别上传两个表格。<br>'
            '2. 在“关联字段”中选择用于识别影视剧的列。<br>'
            '3. 在“返回列设置”中勾选匹配成功后你需要的反馈结果。</div>', unsafe_allow_html=True)

st.markdown('<div class="blue-header">第一步：上传文件</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    base_file = st.file_uploader("上传原文件 (底库)", type=["xlsx", "csv"], key="u_base")
with c2:
    target_file = st.file_uploader("上传待匹配文件", type=["xlsx", "csv"], key="u_target")

if base_file and target_file:
    # 加载数据
    df_base = pd.read_excel(base_file) if base_file.name.endswith('xlsx') else pd.read_csv(base_file)
    df_target = pd.read_excel(target_file) if target_file.name.endswith('xlsx') else pd.read_csv(target_file)
    
    base_cols = df_base.columns.tolist()
    target_cols = df_target.columns.tolist()

    st.markdown('<div class="blue-header">第二步：配置匹配逻辑</div>', unsafe_allow_html=True)
    
    col_config_1, col_config_2 = st.columns([2, 1])
    
    with col_config_1:
        st.write("### 🔗 关联字段设置 (用于识别比对)")
        sub_c1, sub_c2 = st.columns(2)
        with sub_c1:
            st.info("原文件字段")
            b_name = st.selectbox("片名列", base_cols, key="bn")
            b_year = st.selectbox("年份列", base_cols, key="by")
            b_dir = st.selectbox("导演列", base_cols, key="bd")
        with sub_c2:
            st.info("待匹配文件字段")
            t_name = st.selectbox("片名列", target_cols, key="tn")
            t_year = st.selectbox("年份列", target_cols, key="ty")
            t_dir = st.selectbox("导演列", target_cols, key="td")

    with col_config_2:
        st.write("### 📋 返回结果设置")
        # 核心功能：选择匹配成功后需要反馈哪些列的数据
        result_cols = st.multiselect("匹配成功后，需要反馈的字段：", target_cols, help="勾选后，匹配到的这些列数据会合并到结果中")
        threshold = st.slider("匹配敏感度", 50, 100, 85)

    if st.button("开始匹配并导出指定结果", type="primary"):
        results = []
        bar = st.progress(0)
        
        # 预处理：统一转为字符串并清洗
        df_base[b_year] = df_base[b_year].astype(str).str.strip()
        df_target[t_year] = df_target[t_year].astype(str).str.strip()

        # 遍历原文件进行匹配
        for i, row in df_base.iterrows():
            current_y = row[b_year]
            # 1. 年份硬过滤提高效率
            candidates = df_target[df_target[t_year] == current_y]
            
            # 初始化反馈数据
            match_feedback = {f"匹配_{col}": "未找到" for col in result_cols}
            match_feedback["相似度得分"] = 0
            
            if not candidates.empty:
                # 2. 构建模糊匹配池：片名 + 导演
                choices = (candidates[t_name].astype(str) + " " + candidates[t_dir].astype(str)).tolist()
                target_str = f"{row[b_name]} {row[b_dir]}"
                
                # 3. 模糊比对
                res = process.extractOne(target_str, choices, scorer=fuzz.token_sort_ratio)
                
                if res and res[1] >= threshold:
                    matched_row = candidates.iloc[choices.index(res[0])]
                    for col in result_cols:
                        match_feedback[f"匹配_{col}"] = matched_row[col]
                    match_feedback["相似度得分"] = round(res[1], 1)
            
            results.append(match_feedback)
            if i % 100 == 0:
                bar.progress(i / len(df_base))

        # 合并并展示
        final_df = pd.concat([df_base, pd.DataFrame(results)], axis=1)
        st.success("✅ 匹配任务完成！")
        st.write("预览前 100 行结果：")
        st.dataframe(final_df.head(100))
        
        # 导出
        csv_data = final_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 点击下载匹配结果表", csv_data, "匹配反馈结果.csv", "text/csv")

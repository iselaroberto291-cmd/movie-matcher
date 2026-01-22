import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz

st.set_page_config(page_title="影视内容自动比对工具", layout="wide")

st.markdown("""
    <style>
    .blue-header { background-color: #3498db; color: white; padding: 10px 20px; border-radius: 5px; font-weight: bold; margin-bottom: 15px; }
    .stMultiSelect div div div div { background-color: #e3f2fd; }
    </style>
    """, unsafe_allow_html=True)

st.title("李阳专属：多维比对与差异反馈工具")

# 1. 文件上传
st.markdown('<div class="blue-header">1. 上传文件</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    base_file = st.file_uploader("上传原文件 (底库表)", type=["xlsx", "csv"], key="u_base")
with c2:
    target_file = st.file_uploader("上传待匹配文件 (目标表)", type=["xlsx", "csv"], key="u_target")

if base_file and target_file:
    # 加载数据
    df_base = pd.read_excel(base_file) if base_file.name.endswith('xlsx') else pd.read_csv(base_file)
    df_target = pd.read_excel(target_file) if target_file.name.endswith('xlsx') else pd.read_csv(target_file)
    
    base_cols = df_base.columns.tolist()
    target_cols = df_target.columns.tolist()

    # 2. 匹配参数配置
    st.markdown('<div class="blue-header">2. 匹配参数配置</div>', unsafe_allow_html=True)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("### 🔍 设定多维比对字段 (数量需一致)")
        m_base_cols = st.multiselect("底库表参与比对的列 (多选无限制)", base_cols, key="m_base")
        m_target_cols = st.multiselect("目标表对应的比对比列", target_cols, key="m_target")
        
    with col_b:
        st.write("### 📋 设定返回与反馈项")
        feedback_cols = st.multiselect("匹配成功后，需从目标表反馈的列：", target_cols, key="f_cols")
        threshold = st.slider("匹配容错阈值 (100为完全一致)", 50, 100, 95)

    if st.button("开始自动执行比对", type="primary"):
        if len(m_base_cols) != len(m_target_cols):
            st.error("❌ 错误：两表选中的比对列数量必须相等！")
        elif len(m_base_cols) == 0:
            st.warning("⚠️ 请至少选择一个比对字段。")
        else:
            results = []
            bar = st.progress(0)
            
            # 构建目标表的比对池
            choices = []
            for _, t_row in df_target.iterrows():
                choices.append(" ".join([str(t_row[c]).strip() for c in m_target_cols]))
            
            # 执行匹配逻辑
            for i, row in df_base.iterrows():
                base_str = " ".join([str(row[c]).strip() for c in m_base_cols])
                
                # 模糊比对计算
                res = process.extractOne(base_str, choices, scorer=fuzz.token_sort_ratio)
                
                row_feedback = {f"反馈_{col}": "NULL" for col in feedback_cols}
                row_feedback["匹配状态"] = "未找到"
                row_feedback["差异列标记"] = ""
                
                if res and res[1] >= threshold:
                    matched_idx = choices.index(res[0])
                    target_row = df_target.iloc[matched_idx]
                    
                    # 1. 提取反馈列数据
                    for col in feedback_cols:
                        row_feedback[f"反馈_{col}"] = target_row[col]
                    
                    # 2. 标记不一致字段 (精准核对)
                    diffs = []
                    for bc, tc in zip(m_base_cols, m_target_cols):
                        if str(row[bc]).strip() != str(target_row[tc]).strip():
                            diffs.append(f"{bc}≠{tc}")
                    
                    row_feedback["匹配状态"] = "已对齐" if not diffs else "内容有差异"
                    row_feedback["差异列标记"] = " | ".join(diffs)
                
                results.append(row_feedback)
                if i % 100 == 0:
                    bar.progress(i / len(df_base))

            # 合并展示结果
            final_df = pd.concat([df_base, pd.DataFrame(results)], axis=1)
            st.success("✅ 比对完成！")
            st.dataframe(final_df.head(100))
            
            # 导出 CSV
            csv = final_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下载完整比对报告", csv, "match_report.csv", "text/csv")

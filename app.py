import streamlit as st
import pandas as pd
import re
from rapidfuzz import process, fuzz

# 1. 科技感 UI 配置
st.set_page_config(page_title="🐇黎小独特匹配小工具🔧", layout="wide")

# 自定义 CSS：深色背景、荧光线条、毛玻璃效果
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stApp { background: radial-gradient(circle, #1b2735 0%, #090a0f 100%); }
    
    /* 科技感卡片 */
    .tech-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid #00f2ff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 0 15px rgba(0, 242, 255, 0.2);
        margin-bottom: 20px;
    }
    
    /* 标题特效 */
    .tech-title {
        font-family: 'Courier New', monospace;
        color: #00f2ff;
        text-shadow: 0 0 10px #00f2ff;
        text-align: center;
        border-bottom: 2px solid #00f2ff;
        padding-bottom: 10px;
        margin-bottom: 30px;
    }

    /* 按钮美化 */
    .stButton>button {
        background: linear-gradient(45deg, #00f2ff, #0072ff);
        color: white;
        border: none;
        box-shadow: 0 0 10px #00f2ff;
        width: 100%;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<h1 class="tech-title">LI YANG DATA MATCHING SYSTEM v2.0</h1>', unsafe_allow_html=True)

# 2. 核心逻辑函数
def split_text(text):
    """支持多种符号切分内容"""
    if pd.isna(text): return []
    return set(re.split(r'[ /／,，;；|]+', str(text).strip()))

# 3. 文件上传区
st.markdown('<div class="tech-card"><h3>📂 数据矩阵导入</h3>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    base_file = st.file_uploader("上传原文件 (BASE DATA)", type=["xlsx", "csv"], key="u_base")
with c2:
    target_file = st.file_uploader("上传待匹配表 (TARGET DATA)", type=["xlsx", "csv"], key="u_target")
st.markdown('</div>', unsafe_allow_html=True)

if base_file and target_file:
    df_base = pd.read_excel(base_file) if base_file.name.endswith('xlsx') else pd.read_csv(base_file)
    df_target = pd.read_excel(target_file) if target_file.name.endswith('xlsx') else pd.read_csv(target_file)
    
    base_cols = df_base.columns.tolist()
    target_cols = df_target.columns.tolist()

    # 4. 参数配置区
    st.markdown('<div class="tech-card"><h3>⚙️ 逻辑参数协议</h3>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.write("#### 🔗 字段映射对齐")
        m_base_cols = st.multiselect("底库参与比对字段", base_cols, key="m_base")
        m_target_cols = st.multiselect("目标表对应比对字段", target_cols, key="m_target")
        
    with col_b:
        st.write("#### 📊 输出反馈配置")
        feedback_cols = st.multiselect("匹配成功后返回字段", target_cols, key="f_cols")
        # 针对长内容的最小匹配要求
        hit_min = st.number_input("最小命中元素数 (只要匹配到一个就填1)", min_value=1, value=1)

    if st.button("EXECUTE MATCHING / 执行深度匹配"):
        if len(m_base_cols) != len(m_target_cols):
            st.error("SYSTEM ERROR: 比对字段数量不匹配！")
        elif not m_base_cols:
            st.warning("SYSTEM WARNING: 请设定比对参数。")
        else:
            results = []
            bar = st.progress(0)
            
            # 构建目标池
            choices = []
            for _, t_row in df_target.iterrows():
                choices.append(" ".join([str(t_row[c]) for c in m_target_cols]))
            
            # 迭代比对
            for i, b_row in df_base.iterrows():
                best_idx, max_hits = -1, 0
                
                for t_idx, t_row in df_target.iterrows():
                    current_hits = 0
                    for bc, tc in zip(m_base_cols, m_target_cols):
                        b_elements = split_text(b_row[bc])
                        t_elements = split_text(t_row[tc])
                        current_hits += len(b_elements.intersection(t_elements))
                    
                    if current_hits > max_hits:
                        max_hits = current_hits
                        best_idx = t_idx
                
                # 反馈逻辑
                row_res = {f"反馈_{col}": "NULL" for col in feedback_cols}
                if best_idx != -1 and max_hits >= hit_min:
                    target_match = df_target.iloc[best_idx]
                    for col in feedback_cols:
                        row_res[f"反馈_{col}"] = target_match[col]
                    row_res["STATUS"] = "SUCCESS"
                    row_res["HIT_COUNT"] = f"命中{max_hits}项"
                else:
                    row_res["STATUS"] = "FAILED"
                    row_res["HIT_COUNT"] = "0"
                
                results.append(row_res)
                if i % 100 == 0: bar.progress(i / len(df_base))

            # 展示结果
            final_df = pd.concat([df_base, pd.DataFrame(results)], axis=1)
            st.success("ANALYSIS COMPLETE / 分析任务已完成")
            st.dataframe(final_df.head(100))
            st.download_button("DOWNLOAD REPORT / 下载数据报告", final_df.to_csv(index=False).encode('utf-8-sig'), "tech_match_report.csv")
    st.markdown('</div>', unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import re
from rapidfuzz import process, fuzz

st.set_page_config(page_title="影视多维匹配工具", layout="wide")

st.markdown("""
    <style>
    .blue-header { background-color: #3498db; color: white; padding: 10px 20px; border-radius: 5px; font-weight: bold; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🐰黎小专属匹配工具🔧")

# 1. 文件上传
st.markdown('<div class="blue-header">1. 上传文件</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    base_file = st.file_uploader("上传原文件 (底库表)", type=["xlsx", "csv"], key="u_base")
with c2:
    target_file = st.file_uploader("上传待匹配文件 (目标表)", type=["xlsx", "csv"], key="u_target")

def split_text(text):
    """通用的文本切分函数，支持空格、斜杠、逗号、分号"""
    if pd.isna(text): return []
    return set(re.split(r'[ /／,，;；|]+', str(text).strip()))

if base_file and target_file:
    df_base = pd.read_excel(base_file) if base_file.name.endswith('xlsx') else pd.read_csv(base_file)
    df_target = pd.read_excel(target_file) if target_file.name.endswith('xlsx') else pd.read_csv(target_file)
    
    base_cols = df_base.columns.tolist()
    target_cols = df_target.columns.tolist()

    st.markdown('<div class="blue-header">2. 自定义字段映射与逻辑</div>', unsafe_allow_html=True)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("### 🔍 设定比对字段")
        m_base_cols = st.multiselect("底库表比对列 (如：导演/演员)", base_cols, key="m_base")
        m_target_cols = st.multiselect("目标表对应列 (数量须一致)", target_cols, key="m_target")
        
    with col_b:
        st.write("### 📋 结果反馈设置")
        feedback_cols = st.multiselect("需从目标表反馈的附加列：", target_cols, key="f_cols")
        # 针对主片名比对的敏感度（非切分字段使用）
        threshold = st.slider("非切分字段匹配敏感度", 50, 100, 90)

    if st.button("执行高精度拆分匹配", type="primary"):
        if len(m_base_cols) != len(m_target_cols):
            st.error("❌ 错误：两表选中的比对列数量必须相等！")
        elif not m_base_cols:
            st.warning("⚠️ 请选择比对字段")
        else:
            results = []
            bar = st.progress(0)
            
            # 遍历底库执行比对
            for i, b_row in df_base.iterrows():
                best_match_idx = -1
                max_hit_count = -1
                final_diffs = []
                
                # 为了性能，建议至少有一个关键比对项（如片名）
                # 这里执行全量搜索以保证“只要匹配到一个就算”
                for t_idx, t_row in df_target.iterrows():
                    current_hit_count = 0
                    current_diffs = []
                    
                    for bc, tc in zip(m_base_cols, m_target_cols):
                        b_elements = split_text(b_row[bc])
                        t_elements = split_text(t_row[tc])
                        
                        # 交集计算：匹配到了几个相同项
                        hits = b_elements.intersection(t_elements)
                        if hits:
                            current_hit_count += len(hits)
                        else:
                            # 如果该字段一个都没对上，记录差异
                            current_diffs.append(f"{bc}不匹配")
                    
                    # 记录命中数最多的那一行
                    if current_hit_count > max_hit_count:
                        max_hit_count = current_hit_count
                        best_match_idx = t_idx
                        final_diffs = current_diffs
                
                # 组装结果
                row_feedback = {f"反馈_{col}": "NULL" for col in feedback_cols}
                if best_match_idx != -1 and max_hit_count > 0:
                    matched_target_row = df_target.iloc[best_match_idx]
                    for col in feedback_cols:
                        row_feedback[f"反馈_{col}"] = matched_target_row[col]
                    
                    row_feedback["匹配状态"] = "已对齐"
                    row_feedback["命中个数"] = f"命中{max_hit_count}个元素"
                    row_feedback["差异标记"] = " | ".join(final_diffs) if final_diffs else "全对齐"
                else:
                    row_feedback["匹配状态"] = "未找到"
                    row_feedback["命中个数"] = "命中0个"
                    row_feedback["差异标记"] = "无重合内容"
                
                results.append(row_feedback)
                if i % 100 == 0:
                    bar.progress(i / len(df_base))

            final_df = pd.concat([df_base, pd.DataFrame(results)], axis=1)
            st.success("✅ 拆分匹配完成！")
            st.dataframe(final_df.head(100))
            st.download_button("📥 下载差异反馈报告", final_df.to_csv(index=False).encode('utf-8-sig'), "split_match_report.csv")


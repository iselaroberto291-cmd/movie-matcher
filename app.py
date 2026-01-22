import streamlit as st
import pandas as pd
import re

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
    """通用的文本切分函数，确保始终返回 set 以支持 intersection 操作"""
    if pd.isna(text) or str(text).strip() == "": 
        return set()
    # 使用正则切分并过滤掉空字符串
    elements = re.split(r'[ /／,，;；|]+', str(text).strip())
    return {e for e in elements if e}

if base_file and target_file:
    # 读取数据
    try:
        df_base = pd.read_excel(base_file) if base_file.name.endswith('xlsx') else pd.read_csv(base_file)
        df_target = pd.read_excel(target_file) if target_file.name.endswith('xlsx') else pd.read_csv(target_file)
    except Exception as e:
        st.error(f"文件读取失败: {e}")
        st.stop()

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
        threshold = st.slider("匹配权重阈值 (命中多少个元素算有效)", 1, 10, 1)

    if st.button("执行高精度拆分匹配", type="primary"):
        if len(m_base_cols) != len(m_target_cols):
            st.error("❌ 错误：两表选中的比对列数量必须相等！")
        elif not m_base_cols:
            st.warning("⚠️ 请选择比对字段")
        else:
            results = []
            bar = st.progress(0)
            
            # 预处理目标表数据，提高匹配速度
            target_data = []
            for idx, t_row in df_target.iterrows():
                # 预先切分好每一行的目标字段
                t_fields = [split_text(t_row[tc]) for tc in m_target_cols]
                target_data.append((idx, t_row, t_fields))

            # 遍历底库执行比对
            total_rows = len(df_base)
            for i, b_row in df_base.iterrows():
                best_match_idx = -1
                max_hit_count = 0
                final_diffs = []
                
                # 获取当前底库行的切分集合
                b_fields = [split_text(b_row[bc]) for bc in m_base_cols]
                
                for t_idx, t_row, t_fields in target_data:
                    current_hit_count = 0
                    current_diffs = []
                    
                    # 比对每一对映射字段
                    for idx, (b_elements, t_elements) in enumerate(zip(b_fields, t_fields)):
                        # 核心修复：此时 b_elements 和 t_elements 均为 set
                        hits = b_elements.intersection(t_elements)
                        if hits:
                            current_hit_count += len(hits)
                        else:
                            current_diffs.append(f"{m_base_cols[idx]}不匹配")
                    
                    # 记录命中数最多的那一行
                    if current_hit_count > max_hit_count:
                        max_hit_count = current_hit_count
                        best_match_idx = t_idx
                        final_diffs = current_diffs
                
                # 组装结果
                row_feedback = {f"反馈_{col}": "NULL" for col in feedback_cols}
                if best_match_idx != -1 and max_hit_count >= threshold:
                    matched_target_row = df_target.iloc[best_match_idx]
                    for col in feedback_cols:
                        row_feedback[f"反馈_{col}"] = matched_target_row[col]
                    
                    row_feedback["匹配状态"] = "已对齐"
                    row_feedback["命中总数"] = max_hit_count
                    row_feedback["差异详情"] = " | ".join(final_diffs) if final_diffs else "全对齐"
                else:
                    row_feedback["匹配状态"] = "未找到"
                    row_feedback["命中总数"] = 0
                    row_feedback["差异详情"] = "无重合内容"
                
                results.append(row_feedback)
                
                # 更新进度条
                if i % 10 == 0 or i == total_rows - 1:
                    bar.progress((i + 1) / total_rows)

            # 合并结果并显示
            final_df = pd.concat([df_base.reset_index(drop=True), pd.DataFrame(results)], axis=1)
            st.success("✅ 拆分匹配完成！")
            st.dataframe(final_df.head(100))
            
            # 下载报表
            csv = final_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下载差异反馈报告", csv, "split_match_report.csv", "text/csv")

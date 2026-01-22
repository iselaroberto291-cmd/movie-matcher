import streamlit as st
import pandas as pd
import re
import io

# 1. 霓虹极客 UI 样式
st.set_page_config(page_title="影视数据高精度比对系统", layout="wide")

st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #050b18 0%, #0c111d 100%); color: #e0e0e0; }
    .cyber-card {
        background: rgba(13, 22, 38, 0.7);
        border: 1px solid rgba(0, 242, 255, 0.3);
        border-radius: 15px;
        padding: 30px;
        box-shadow: 0 0 20px rgba(0, 242, 255, 0.1);
        margin-bottom: 25px;
        backdrop-filter: blur(10px);
    }
    .cyber-title {
        font-family: 'Segoe UI', sans-serif;
        font-weight: 800;
        background: linear-gradient(to right, #00f2ff, #7000ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        font-size: 2.5rem;
        margin-bottom: 40px;
    }
    .stButton>button {
        background: linear-gradient(45deg, #00f2ff, #7000ff);
        color: white !important;
        border-radius: 10px;
        box-shadow: 0 0 15px rgba(0, 242, 255, 0.4);
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<h1 class="cyber-title">DATA MATCHING SYSTEM v7.0</h1>', unsafe_allow_html=True)

# 2. 核心函数
def split_text(text):
    if pd.isna(text): return set()
    return set(re.split(r'[ /／,，;；|]+', str(text).strip()))

# 3. 数据载入
st.markdown('<div class="cyber-card"><h3>🛸 矩阵载入 / DATA INPUT</h3>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    base_file = st.file_uploader("底库原文件", type=["xlsx", "csv"], key="u_base")
with c2:
    target_file = st.file_uploader("目标待匹配表", type=["xlsx", "csv"], key="u_target")
st.markdown('</div>', unsafe_allow_html=True)

if base_file and target_file:
    df_base = pd.read_excel(base_file) if base_file.name.endswith('xlsx') else pd.read_csv(base_file)
    df_target = pd.read_excel(target_file) if target_file.name.endswith('xlsx') else pd.read_csv(target_file)
    
    base_cols = df_base.columns.tolist()
    target_cols = df_target.columns.tolist()

    # 4. 配置协议
    st.markdown('<div class="cyber-card"><h3>⚡ 匹配协议与导出设置 / PROTOCOL</h3>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        m_base_cols = st.multiselect("原文件比对字段", base_cols, key="m_base")
        m_target_cols = st.multiselect("目标表对应字段", target_cols, key="m_target")
    with col_b:
        feedback_cols = st.multiselect("需反馈的列", target_cols, key="f_cols")
        hit_min = st.slider("最小命中阈值", 1, 10, 1)
        export_mode = st.radio("导出模式", ["单行拼接 (适合快速查看)", "多行平铺 (适合底库同步)"], index=1)

    if st.button("RUN DEEP MATCHING / 启动深度匹配"):
        if len(m_base_cols) != len(m_target_cols):
            st.error("字段映射数量不匹配。")
        else:
            final_rows = []
            progress_bar = st.progress(0)
            
            # 预处理目标表
            target_data_split = []
            for _, t_row in df_target.iterrows():
                target_data_split.append([split_text(t_row[tc]) for tc in m_target_cols])
            
            for i, b_row in df_base.iterrows():
                matched_entries = []
                b_split = [split_text(b_row[bc]) for bc in m_base_cols]
                
                for t_idx, t_splits in enumerate(target_data_split):
                    current_hits = 0
                    for b_s, t_s in zip(b_split, t_splits):
                        current_hits += len(b_s.intersection(t_s))
                    if current_hits >= hit_min:
                        matched_entries.append((t_idx, current_hits))
                
                # 排序
                matched_entries.sort(key=lambda x: x[1], reverse=True)

                if not matched_entries:
                    # 未匹配成功
                    new_row = b_row.to_dict()
                    for f in feedback_cols: new_row[f"反馈_{f}"] = "NULL"
                    new_row.update({"STATUS": "FAILED", "命中统计": "0", "差异标记": "无匹配内容"})
                    final_rows.append(new_row)
                else:
                    if export_mode == "单行拼接 (适合快速查看)":
                        new_row = b_row.to_dict()
                        for f in feedback_cols:
                            new_row[f"反馈_{f}"] = " | ".join([str(df_target.iloc[idx][f]) for idx, _ in matched_entries])
                        new_row.update({"STATUS": "SUCCESS", "命中统计": f"匹配到{len(matched_entries)}个结果", "差异标记": "见多重结果"})
                        final_rows.append(new_row)
                    else:
                        # 多行平铺逻辑
                        for rank, (t_idx, hits) in enumerate(matched_entries):
                            new_row = b_row.to_dict()
                            t_row = df_target.iloc[t_idx]
                            for f in feedback_cols:
                                new_row[f"反馈_{f}"] = t_row[f]
                            # 差异检查
                            diffs = [f"{bc}≠{tc}" for bc, tc in zip(m_base_cols, m_target_cols) 
                                     if str(b_row[bc]).strip() != str(t_row[tc]).strip()]
                            new_row.update({
                                "STATUS": "SUCCESS" if not diffs else "WARNING",
                                "命中统计": f"命中{hits}项 (排名:{rank+1})",
                                "差异标记": " | ".join(diffs) if diffs else "完全一致"
                            })
                            final_rows.append(new_row)
                
                if i % 100 == 0: progress_bar.progress(i / len(df_base))

            output_df = pd.DataFrame(final_rows)
            st.success("ANALYSIS COMPLETED")
            st.dataframe(output_df.head(100), use_container_width=True)

            # --- 生成带颜色的 Excel ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                output_df.to_excel(writer, index=False, sheet_name='比对结果')
                workbook  = writer.book
                worksheet = writer.sheets['比对结果']
                
                # 定义格式
                red_fmt = workbook.add_format({'font_color': '#FF4B4B', 'bg_color': '#FFEBEB'})
                orange_fmt = workbook.add_format({'font_color': '#FF9D00', 'bg_color': '#FFF5E6'})
                blue_fmt = workbook.add_format({'font_color': '#0072FF'})

                # 获取 STATUS 列索引
                status_col_idx = output_df.columns.get_loc("STATUS")
                
                # 遍历行应用格式 (这里对 STATUS 列进行条件格式化示例)
                worksheet.conditional_format(1, status_col_idx, len(output_df), status_col_idx, {
                    'type':     'cell',
                    'criteria': '==',
                    'value':    '"FAILED"',
                    'format':   red_fmt
                })
                worksheet.conditional_format(1, status_col_idx, len(output_df), status_col_idx, {
                    'type':     'cell',
                    'criteria': '==',
                    'value':    '"WARNING"',
                    'format':   orange_fmt
                })

            st.download_button(
                label="📥 下载彩色 Excel 报告 (多行平铺版)",
                data=output.getvalue(),
                file_name="cyber_match_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    st.markdown('</div>', unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import re

# 初始化用户可配置的雷达图归一化参数 (在脚本顶部或首次使用前)
if 'user_normalization_params' not in st.session_state:
    st.session_state.user_normalization_params = {
        '德育': {'min': 12.0, 'max': 15.0},
        '智育': {'min': 0, 'max': 105.0},
        '体测成绩': {'min': 0, 'max': 120.0},
        '附加分': {'min': -1.0, 'max': 10.0},
        '综测总分': {'min': 0, 'max': 110.0}
    }

# 页面配置
st.set_page_config(
    page_title="航空工程学院学生数据分析系统",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS样式
st.markdown("""
<style>
.main-header {
    background: #28a745;
    color: white;
    padding: 1rem;
    margin-bottom: 1rem;
    text-align: center;
}

.card {
    padding: 1rem;
    margin-bottom: 1rem;
    background: transparent;
    border: none;
    box-shadow: none;
}

.card::before {
    display: none;
}

.info-row {
    display: flex;
    padding: 0.5rem 0;
    border-bottom: 1px solid #f3f4f6;
}

.info-label {
    color: #6b7280;
    font-weight: 500;
    width: 50%;
    text-align: left;
}

.info-value {
    font-weight: 600;
    color: #1f2937;
    width: 50%;
    text-align: center;
}

.status-badge {
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
}

.status-help {
    background-color: #fee2e2;
    color: #dc2626;
}

.status-no-help {
    background-color: #dcfce7;
    color: #16a34a;
}

.status-scholarship {
    background-color: #fef3c7;
    color: #d97706;
}

.status-none {
    background-color: #f3f4f6;
    color: #6b7280;
}

.psych-level-3 {
    background-color: #dcfce7;
    color: #16a34a;
}

.psych-level-2 {
    background-color: #fef3c7;
    color: #d97706;
}

.psych-level-1 {
    background-color: #fee2e2;
    color: #dc2626;
}

.metric-card {
    text-align: center;
    padding: 1rem;
    margin: 0.5rem;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.gpa-summary {
    color: #1f2937;
    padding: 0.8rem;
    text-align: center;
    margin: 0.5rem 0;
    background: transparent;
    border: none;
    box-shadow: none;
}

div.block-container {
    padding-top: 1rem !important;
}

.element-container {
    margin-bottom: 0.5rem !important;
}

.js-plotly-plot {
    border: none;
    box-shadow: none;
    background-color: transparent;
    padding: 0;
}
</style>
""", unsafe_allow_html=True)

# 工具函数：处理空值显示
def format_value(value):
    """将空值、NaN、None等转换为'无'，并处理纯空格字符串"""
    if pd.isna(value) or value is None:
        return '无'
    # 检查字符串表示形式
    # strip()移除前后空格，lower()转小写，再检查是否为空或特定代表"无"的词
    s_value_stripped = str(value).strip()
    if not s_value_stripped or s_value_stripped.lower() in ['nan', 'none']: # '' also handled by not s_value_stripped
        return '无'
    return str(value) # 如果数据有效，则返回原始字符串形式

chinese_to_num_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
def get_year_sort_key(year_str_input):
    # Extracts the Chinese numeral part if present e.g. "一" from "第一学年"
    year_str = str(year_str_input).replace("第","").replace("学年","")
    return chinese_to_num_map.get(year_str, int(year_str) if year_str.isdigit() else 999)

def extract_semester_gpa_data(student_data):
    """动态提取学期绩点数据"""
    gpa_data = []
    gpa_pattern = re.compile(r'第([一二三四五六七八九十\d]+)学期绩点')
    
    # 检查是否在列中（对应行数据）
    for column in student_data.index:
        match = gpa_pattern.match(str(column))
        if match:
            value = student_data.get(column)
            if pd.notna(value) and value is not None:
                try:
                    float_value = float(value)
                    semester_num_str = match.group(1)
                    sort_key = get_year_sort_key(semester_num_str)
                    gpa_data.append({
                        'semester': f'第{semester_num_str}学期',
                        'gpa': float_value,
                        'sort_key': sort_key
                    })
                except (ValueError, TypeError):
                    continue
    
    # 检查是否在列名中（对应DataFrame列）
    if not gpa_data and isinstance(student_data, pd.Series):
        for column in student_data.keys():
            match = gpa_pattern.match(str(column))
            if match:
                value = student_data.get(column)
                if pd.notna(value) and value is not None:
                    try:
                        float_value = float(value)
                        semester_num_str = match.group(1)
                        sort_key = get_year_sort_key(semester_num_str)
                        gpa_data.append({
                            'semester': f'第{semester_num_str}学期',
                            'gpa': float_value,
                            'sort_key': sort_key
                        })
                    except (ValueError, TypeError):
                        continue
    
    gpa_data.sort(key=lambda x: x['sort_key'])
    return gpa_data

def extract_academic_year_data(student_data):
    """动态提取学年综测数据"""
    academic_years = {}
    year_patterns = {
        '德育': re.compile(r'第([一二三四五六七八\\d]+)学年德育'),
        '智育': re.compile(r'第([一二三四五六七八\\d]+)学年智育'),
        '体测成绩': re.compile(r'第([一二三四五六七八\\d]+)学年体测成绩'),
        '体测评级': re.compile(r'第([一二三四五六七八\\d]+)学年体测评级'),
        '附加分': re.compile(r'第([一二三四五六七八\\d]+)学年附加分'),
        '综测总分': re.compile(r'第([一二三四五六七八\\d]+)学年综测总分')
    }
    for column in student_data.index:
        for field_type, pattern in year_patterns.items():
            match = pattern.match(str(column))
            if match:
                year_num_str = match.group(1)
                value = student_data.get(column)
                if year_num_str not in academic_years:
                    academic_years[year_num_str] = {}
                academic_years[year_num_str][field_type] = value
    return academic_years

def extract_yearly_scholarship_data(student_data):
    """动态提取学年奖学金数据"""
    scholarship_data = {}
    # Define the keys to extract and use for storing data. These should align with app.py's general fields.
    scholarship_keys_to_extract = {
        "人民奖学金": "人民奖学金",
        "助学奖学金": "助学奖学金", # Keyword to search for in column name, and key for storing data
        "助学金": "助学金",
        "奖项": "奖项" # Keyword for "奖项" or "获得奖项" columns. Stored with key "奖项".
    }
    
    year_pattern_generic = re.compile(r'第([一二三四五六七八\\d]+)学年(.+)')

    for col_name in student_data.index:
        match = year_pattern_generic.match(str(col_name))
        if match:
            year_num_str = match.group(1)
            field_name_in_col = match.group(2) # e.g., "人民奖学金", "助学金", "奖项"
            
            for data_key, keyword_to_match in scholarship_keys_to_extract.items():
                if keyword_to_match in field_name_in_col:
                    if year_num_str not in scholarship_data:
                        scholarship_data[year_num_str] = {}
                    scholarship_data[year_num_str][data_key] = student_data.get(col_name)
                    break # Found a match for this column for one of our defined keys

    return scholarship_data

def extract_yearly_poverty_level_data(student_data):
    """动态提取学年贫困等级数据"""
    poverty_data = {}
    poverty_pattern = re.compile(r'第([一二三四五六七八\\d]+)学年困难等级')
    for column in student_data.index:
        match = poverty_pattern.match(str(column))
        if match:
            year_num_str = match.group(1)
            value = student_data.get(column)
            poverty_data[year_num_str] = value
    return poverty_data

def extract_yearly_psychological_level_data(student_data):
    """动态提取学年心理评测等级数据"""
    psych_data = {}
    psych_pattern = re.compile(r'第([一二三四五六七八九十\\d]+)学年心理[评测]*等级')
    for column in student_data.index:
        match = psych_pattern.match(str(column))
        if match:
            year_num_str = match.group(1)
            value = student_data.get(column)
            psych_data[year_num_str] = value
    return psych_data

def create_radar_chart(year_data, year_name):
    """创建单个学年的雷达图"""
    # Check for '综测总分' validity first
    comprehensive_score_value = year_data.get('综测总分')
    
    is_invalid_score = False
    if pd.isna(comprehensive_score_value) or comprehensive_score_value is None:
        is_invalid_score = True
    else:
        try:
            float(comprehensive_score_value) # Check if it's a number
        except (ValueError, TypeError):
            is_invalid_score = True # Not a number (e.g. empty string, "无")
            
    if is_invalid_score:
        return None, None # Do not display radar chart if '综测总分' is invalid

    normalization_params = {
        '德育': (st.session_state.user_normalization_params['德育']['min'], 
                st.session_state.user_normalization_params['德育']['max']),
        '智育': (st.session_state.user_normalization_params['智育']['min'], 
               st.session_state.user_normalization_params['智育']['max']),
        '体测成绩': (st.session_state.user_normalization_params['体测成绩']['min'], 
                  st.session_state.user_normalization_params['体测成绩']['max']),
        '附加分': (st.session_state.user_normalization_params['附加分']['min'], 
                st.session_state.user_normalization_params['附加分']['max']),
        '综测总分': (st.session_state.user_normalization_params['综测总分']['min'], 
                  st.session_state.user_normalization_params['综测总分']['max'])
    }
    def normalize_value(value, min_val, max_val):
        if pd.isna(value) or value is None: return 0
        try:
            return max(0, min(100, ((float(value) - min_val) / (max_val - min_val)) * 100))
        except (ValueError, TypeError): return 0
    def get_display_value(value):
        if pd.isna(value) or value is None: return 0
        try: return float(value)
        except (ValueError, TypeError): return 0
    
    radar_items = []
    for field in ['德育', '智育', '体测成绩', '附加分', '综测总分']:
        if field in year_data:
            min_val, max_val = normalization_params.get(field, (0,100))
            radar_items.append((field, normalize_value(year_data[field], min_val, max_val), get_display_value(year_data[field])))
    
    if not radar_items: return None, None
    
    categories = [item[0] for item in radar_items]
    values = [item[1] for item in radar_items]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values, theta=categories, fill='toself', name=f'{year_name}综合评分',
        line_color='#3b82f6', fillcolor='rgba(59, 130, 246, 0.3)'
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100],gridcolor='#e5e7eb'), angularaxis=dict(gridcolor='#e5e7eb')),
        showlegend=False, height=400, margin=dict(t=50,b=50,l=50,r=50), title=f"{year_name}综合素质雷达图"
    )
    return fig, radar_items

# 初始化session state
if 'students_data' not in st.session_state:
    st.session_state.students_data = None
if 'selected_student_index' not in st.session_state:
    st.session_state.selected_student_index = 0

# 主标题
st.markdown("""
<div class="main-header">
    <h1>✈️ 航空工程学院学生数据分析系统</h1>
</div>
""", unsafe_allow_html=True)

# 文件上传区域
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### 📊 数据上传")

st.info("""
💡 **上传说明：**
- 系统会自动识别并动态适应不同数量的学期和学年数据        
- 支持包含多个学期绩点数据的Excel文件（如：第一学期绩点、第二学期绩点...第五学期绩点等）
- 支持包含多个学年综测数据的Excel文件（如：第一学年德育、第二学年德育等）
- 支持包含多个学年贫困等级数据的Excel文件（如：第一学年困难等级、第二学年困难等级等）
- 支持包含多个学年奖学金数据的Excel文件（如：第一学年人民奖学金、第二学年人民奖学金等）
""")

uploaded_file = st.file_uploader(
    "选择Excel文件上传学生数据",
    type=['xlsx', 'xls'],
    help="支持Excel格式文件，系统会自动适应不同的数据结构"
)

if uploaded_file is not None:
    try:
        # 读取Excel文件
        df = pd.read_excel(uploaded_file)
        st.session_state.students_data = df
        st.success(f"✅ 成功加载 {len(df)} 名学生的数据")
        
        # 显示数据结构信息
        with st.expander("📋 数据结构预览", expanded=False):
            st.write(f"**总行数:** {len(df)}")
            st.write(f"**总列数:** {len(df.columns)}")
            
            # 显示绩点相关列
            gpa_cols = [col for col in df.columns if '绩点' in str(col)]
            if gpa_cols:
                st.write(f"**绩点相关列 ({len(gpa_cols)}个):** {', '.join(gpa_cols)}")
            
            # 显示综测相关列
            comp_cols = [col for col in df.columns if any(keyword in str(col) for keyword in ['德育', '智育', '体测', '附加', '综测'])]
            if comp_cols:
                st.write(f"**综测相关列 ({len(comp_cols)}个):** {', '.join(comp_cols[:10])}{'...' if len(comp_cols) > 10 else ''}")

    except Exception as e:
        st.error(f"❌ 文件读取失败: {str(e)}")
        st.session_state.students_data = None

st.markdown('</div>', unsafe_allow_html=True)

# 如果没有数据，显示欢迎界面
if st.session_state.students_data is None:
    st.markdown("""
    <div class="card" style="text-align: center; padding: 3rem;">
        <h3>🎯 欢迎使用学生数据分析系统</h3>
        <p style="color: #6b7280; margin: 1rem 0;">请上传Excel文件开始分析学生数据</p>
        <p style="color: #9ca3af; font-size: 0.9rem;">支持动态识别不同数量的学期绩点和学年综测数据</p>
    </div>
    """, unsafe_allow_html=True)
else:
    df = st.session_state.students_data
    
    # 学生选择器
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🔍 学生选择器")
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        # 搜索功能
        search_term = st.text_input("🔍 搜索学生", placeholder="输入姓名、学号或班级进行搜索...")
        
        # 过滤学生数据
        if search_term:
            # 创建搜索条件，支持多种可能的列名
            search_columns = ['姓名', '学号']
            # 添加可能的班级列名
            possible_class_cols = ['班级', '新班级', '原班级', '班级_基本信息', '班 级', '班 级_基本信息']
            for col in possible_class_cols:
                if col in df.columns:
                    search_columns.append(col)
            
            mask = pd.Series([False] * len(df))
            for col in search_columns:
                if col in df.columns:
                    mask |= df[col].astype(str).str.contains(search_term, case=False, na=False)
            
            filtered_df = df[mask]
        else:
            filtered_df = df
    
    with col2:
        st.metric("总学生数", len(df))
    
    with col3:
        st.metric("筛选结果", len(filtered_df))
    
    if len(filtered_df) > 0:
        # 学生选择下拉框
        student_options = []
        for idx, row in filtered_df.iterrows():
            # 获取班级值，尝试多种可能的列名
            班级值 = '未知'
            for col in ['新班级', '班级', '原班级', '班级_基本信息', '班 级', '班 级_基本信息']:
                if col in filtered_df.columns and pd.notna(row.get(col)):
                    班级值 = row.get(col)
                    break
                    
            student_options.append(f"{format_value(row.get('姓名', '未知'))} - {format_value(row.get('学号', '未知'))} - {班级值}")
        
        selected_student = st.selectbox(
            "选择学生",
            options=range(len(student_options)),
            format_func=lambda x: student_options[x],
            key="student_selector"
        )
        
        # 导航按钮
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("⬅️ 上一个", disabled=selected_student == 0):
                selected_student = max(0, selected_student - 1)
        with col3:
            if st.button("下一个 ➡️", disabled=selected_student >= len(student_options) - 1):
                selected_student = min(len(student_options) - 1, selected_student + 1)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 获取选中的学生数据
        student_data = filtered_df.iloc[selected_student]
        
        # 个人信息卡片
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 👤 个人信息")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div class="info-row">
                <span class="info-label">姓名：</span>
                <span class="info-value">{format_value(student_data.get('姓名'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">分流专业：</span>
                <span class="info-value">{format_value(student_data.get('分流专业'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">新班级：</span>
                <span class="info-value">{format_value(student_data.get('新班级') or student_data.get('班级_基本信息') or student_data.get('班 级_基本信息') or student_data.get('班级') or student_data.get('班 级'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">辅导员：</span>
                <span class="info-value">{format_value(student_data.get('辅导员'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">民族：</span>
                <span class="info-value">{format_value(student_data.get('民族'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">是否积极分子：</span>
                <span class="info-value">{format_value(student_data.get('是否积极分子'))}</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="info-row">
                <span class="info-label">学号：</span>
                <span class="info-value">{format_value(student_data.get('学号'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">原专业：</span>
                <span class="info-value">{format_value(student_data.get('原专业'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">原班级：</span>
                <span class="info-value">{format_value(student_data.get('原班级', student_data.get('班级')))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">政治面貌：</span>
                <span class="info-value">{format_value(student_data.get('政治面貌'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">性别：</span>
                <span class="info-value">{format_value(student_data.get('性别'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">是否递交入党申请书：</span>
                <span class="info-value">{format_value(student_data.get('是否递交入党申请书'))}</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        # 帮助需求卡片
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🆘 帮助需求")
        
        help_needed_value = student_data.get('有无需要学院协助解决的困难')
        help_needed = (
            help_needed_value and 
            not pd.isna(help_needed_value) and
            str(help_needed_value).lower() not in ['无', 'nan', 'none', '']
        )
        
        if help_needed:
            st.markdown(f"""
            <div style="background: #fee2e2; padding: 1rem; border-radius: 8px; border: 1px solid #fecaca;">
                <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                    <div style="width: 12px; height: 12px; background: #dc2626; border-radius: 50%; margin-right: 0.5rem;"></div>
                    <span style="font-weight: 600; color: #dc2626;">需要帮助</span>
                </div>
                <p style="color: #dc2626; margin: 0; font-size: 0.9rem;">
                    困难详情: {format_value(student_data.get('有何困难', '未详述'))}
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: #dcfce7; padding: 1rem; border-radius: 8px; border: 1px solid #bbf7d0;">
                <div style="display: flex; align-items: center;">
                    <div style="width: 12px; height: 12px; background: #16a34a; border-radius: 50%; margin-right: 0.5rem;"></div>
                    <span style="font-weight: 600; color: #16a34a;">无需帮助</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        # 心理评测等级模块
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 💖 心理评测等级")
        
        # 获取学年心理评测等级数据
        yearly_psych_data = extract_yearly_psychological_level_data(student_data)
        html_lines_for_psych = []  # 存储需要显示的HTML行
        
        # 处理每个学年的心理评测数据
        if yearly_psych_data:
            # 按学年顺序排序
            sorted_psych_years = sorted(yearly_psych_data.keys(), key=get_year_sort_key)
            # 最多显示4年数据
            for year_num_str in sorted_psych_years[:4]:
                year_label = f"第{year_num_str}学年"
                raw_value = yearly_psych_data[year_num_str]
                
                # 处理该学年的数值
                psych_value = format_value(raw_value)
                
                # 根据心理等级设置不同的样式和描述
                if psych_value in ['3级', '3', 'III级', 'III', '三级', '良好']:
                    status_class = "psych-level-3"
                    description = "心理健康状况良好"
                elif psych_value in ['2级', '2', 'II级', 'II', '二级', '一般']:
                    status_class = "psych-level-2"
                    description = "存在轻微心理问题"
                elif psych_value in ['1级', '1', 'I级', 'I', '一级', '较差', '差']:
                    status_class = "psych-level-1"
                    description = "存在严重心理问题"
                else:
                    status_class = "status-none"
                    description = "暂无心理评测数据" if psych_value == '无' else f"数据: {psych_value}"
                
                # 添加HTML内容
                html_lines_for_psych.append(f"""
                <div style="background: #f0f4f8; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border: 1px solid #e2e8f0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span style="color: #4b5563; font-weight: 600;">{year_label}心理评测等级：</span>
                        <span class="status-badge {status_class}">{psych_value if psych_value != "无" else "暂无"}</span>
                    </div>
                    <div style="color: #4b5563; font-size: 0.95rem; margin-top: 0.5rem;">
                        {description}
                    </div>
                </div>
                """)
        
        # 如果没有学年数据，则显示综合心理评测等级（兼容旧数据）
        if not html_lines_for_psych:
            psychological_level = student_data.get('心理评测等级', student_data.get('最新心理等级', student_data.get('心理等级')))
            psych_value = format_value(psychological_level)
            
            # 根据心理等级设置不同的样式和描述
            if psych_value in ['3级', '3', 'III级', 'III', '三级', '良好']:
                status_class = "psych-level-3"
                description = "心理健康状况良好"
            elif psych_value in ['2级', '2', 'II级', 'II', '二级', '一般']:
                status_class = "psych-level-2"
                description = "存在轻微心理问题"
            elif psych_value in ['1级', '1', 'I级', 'I', '一级', '较差', '差']:
                status_class = "psych-level-1"
                description = "存在严重心理问题"
            else:
                status_class = "status-none"
                description = "暂无心理评测数据" if psych_value == '无' else f"数据: {psych_value}"
            
            # 添加综合心理评测等级的HTML内容
            html_lines_for_psych.append(f"""
            <div style="background: #f0f4f8; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border: 1px solid #e2e8f0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <span style="color: #4b5563; font-weight: 600;">心理评测等级：</span>
                    <span class="status-badge {status_class}">{psych_value if psych_value != "无" else "暂无"}</span>
                </div>
                <div style="color: #4b5563; font-size: 0.95rem; margin-top: 0.5rem;">
                    {description}
                </div>
            </div>
            """)
        
        # 显示所有心理评测等级的HTML内容
        st.markdown("".join(html_lines_for_psych), unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 新增：贫困等级模块
        yearly_poverty_data = extract_yearly_poverty_level_data(student_data)
        html_lines_for_poverty = [] # Store HTML for lines that should be displayed

        if yearly_poverty_data: 
            sorted_poverty_years = sorted(yearly_poverty_data.keys(), key=get_year_sort_key)
            for year_num_str in sorted_poverty_years:
                year_label = f"第{year_num_str}学年困难等级"
                raw_value = yearly_poverty_data[year_num_str]

                # Determine if this year's poverty level should be displayed
                should_display_line = False
                if isinstance(raw_value, str) and raw_value == "无":
                    # If the raw value is literally the string "无", display it
                    should_display_line = True
                elif pd.notna(raw_value) and raw_value is not None:
                    # If it's not NA/None, check if it's a non-empty string or non-string type
                    if isinstance(raw_value, str):
                        if raw_value.strip() != "": # Display if non-empty string
                            should_display_line = True
                    else: # Display if it's a number or other non-string, non-NA/None type
                        should_display_line = True
                
                if should_display_line:
                    formatted_value_to_display = format_value(raw_value) # Use format_value for consistency in output ("无" or actual)
                    status_class_poverty = "status-help" if formatted_value_to_display != '无' else "status-none"
                    html_lines_for_poverty.append(f"""
                    <div style="background:#f8fafc; padding: 0.75rem; border-radius: 8px; margin: 0.5rem 0;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color:#6b7280;">{year_label}：</span>
                            <span class="status-badge {status_class_poverty}">{formatted_value_to_display}</span>
                        </div>
                    </div>
                    """)
        
        if html_lines_for_poverty: # Only show the card if there are actual lines to display
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 💜 贫困等级")
            st.markdown("".join(html_lines_for_poverty), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        # If no lines were generated (e.g., all columns were missing or contained only truly blank data),
        # the entire card is skipped.
        
        # 学业成绩趋势图（动态适应）
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📈 学业成绩分析")
        
        # 动态提取绩点数据
        gpa_data = extract_semester_gpa_data(student_data)
        
        # 如果未找到绩点数据，尝试从DataFrame直接提取
        if not gpa_data and isinstance(student_data, pd.Series):
            semester_pattern = re.compile(r'第([一二三四五六七八九十\d]+)学期绩点')
            
            # 从学生数据的键中提取绩点
            for col in student_data.keys():
                match = semester_pattern.match(str(col))
                if match:
                    value = student_data.get(col)
                    if pd.notna(value) and value is not None:
                        try:
                            float_value = float(value)
                            semester_num_str = match.group(1)
                            sort_key = get_year_sort_key(semester_num_str)
                            gpa_data.append({
                                'semester': f'第{semester_num_str}学期',
                                'gpa': float_value,
                                'sort_key': sort_key
                            })
                        except (ValueError, TypeError):
                            continue
            
            # 如果正则表达式匹配失败，尝试直接匹配列名
            if not gpa_data:
                # 直接查找可能的列名
                semester_names = ["第一学期绩点", "第二学期绩点", "第三学期绩点", "第四学期绩点", "第五学期绩点", 
                                "第六学期绩点", "第七学期绩点", "第八学期绩点"]
                
                for i, col_name in enumerate(semester_names):
                    if col_name in student_data:
                        value = student_data.get(col_name)
                        if pd.notna(value) and value is not None:
                            try:
                                float_value = float(value)
                                sort_key = i + 1
                                gpa_data.append({
                                    'semester': col_name.replace("绩点", ""),
                                    'gpa': float_value,
                                    'sort_key': sort_key
                                })
                            except (ValueError, TypeError):
                                continue
            
            # 按学期排序
            if gpa_data:
                gpa_data.sort(key=lambda x: x['sort_key'])
        

        
        if gpa_data:
            semesters = [item['semester'] for item in gpa_data]
            gpas = [item['gpa'] for item in gpa_data]
            
            # 创建折线图
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=semesters,
                y=gpas,
                mode='lines+markers',
                name='绩点',
                line=dict(color='#8b5cf6', width=3),
                marker=dict(size=8, color='#8b5cf6')
            ))
            
            fig.update_layout(
                title=f"学期绩点趋势图 (共{len(gpa_data)}个学期)",
                xaxis_title="学期",
                yaxis_title="绩点",
                yaxis=dict(range=[1.5, 4.5]),
                height=400,
                margin=dict(t=50, b=30, l=30, r=30),
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 显示各学期绩点和统计信息
            st.markdown("#### 📊 学期绩点详情")
            
            # 计算统计信息
            max_gpa = max(gpas) if gpas else 0
            min_gpa = min(gpas) if gpas else 0
            num_semesters = len(gpa_data)

            # 尝试获取总绩点，如果不存在则使用计算的平均值
            overall_gpa_value = student_data.get('总绩点', student_data.get('平均学分绩点'))
            gpa_label = "总绩点"
            if pd.isna(overall_gpa_value) or overall_gpa_value is None:
                overall_gpa_value = np.mean(gpas) if gpas else 0
                gpa_label = "总绩点 (计算均值)"
            else:
                try:
                    overall_gpa_value = float(overall_gpa_value)
                except ValueError:
                    overall_gpa_value = np.mean(gpas) if gpas else 0 # Fallback if conversion fails
                    gpa_label = "总绩点 (转换失败，计算均值)"

            # 第一行：统计卡片
            stat_cols = st.columns(4)
            with stat_cols[0]:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-weight: 600; color: #374151; margin-bottom: 0.25rem;">{gpa_label}</div>
                    <div style="color: #8b5cf6; font-weight: bold; font-size: 1.5rem;">{overall_gpa_value:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with stat_cols[1]:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-weight: 600; color: #374151; margin-bottom: 0.25rem;">最高绩点</div>
                    <div style="color: #16a34a; font-weight: bold; font-size: 1.5rem;">{max_gpa:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with stat_cols[2]:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-weight: 600; color: #374151; margin-bottom: 0.25rem;">最低绩点</div>
                    <div style="color: #dc2626; font-weight: bold; font-size: 1.5rem;">{min_gpa:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with stat_cols[3]:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-weight: 600; color: #374151; margin-bottom: 0.25rem;">学期总数</div>
                    <div style="color: #3b82f6; font-weight: bold; font-size: 1.5rem;">{num_semesters}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # 第二行：学期绩点 1-4
            sem_row2_cols = st.columns(4)
            for i in range(4):
                if i < len(gpa_data):
                    data = gpa_data[i]
                    with sem_row2_cols[i]:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div style="font-weight: 600; color: #374151; margin-bottom: 0.25rem;">{data['semester']}</div>
                            <div style="color: #8b5cf6; font-weight: bold; font-size: 1.2rem;">{data['gpa']:.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    with sem_row2_cols[i]: # Placeholder for empty slots if less than 4 semesters
                        st.markdown("<div class=\"metric-card\" style=\"opacity:0; pointer-events:none;\">&nbsp;</div>", unsafe_allow_html=True)

            # 第三行：学期绩点 5-8
            if len(gpa_data) > 4:
                sem_row3_cols = st.columns(4)
                for i in range(4):
                    data_index = i + 4
                    if data_index < len(gpa_data):
                        data = gpa_data[data_index]
                        with sem_row3_cols[i]:
                            st.markdown(f"""
                            <div class="metric-card">
                                <div style="font-weight: 600; color: #374151; margin-bottom: 0.25rem;">{data['semester']}</div>
                                <div style="color: #8b5cf6; font-weight: bold; font-size: 1.2rem;">{data['gpa']:.2f}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        with sem_row3_cols[i]: # Placeholder for empty slots
                            st.markdown("<div class=\"metric-card\" style=\"opacity:0; pointer-events:none;\">&nbsp;</div>", unsafe_allow_html=True)
        else:
            st.info("📊 暂无绩点数据")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 综合素质雷达图（动态适应多个学年）
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📊 综合素质评价")
        
        # 动态提取学年数据
        academic_years = extract_academic_year_data(student_data)
        
        if academic_years:
            # 按学年顺序排序
            sorted_years = sorted(academic_years.keys(), key=get_year_sort_key)
            
            # 为每个学年创建雷达图
            for year_num in sorted_years:
                year_data = academic_years[year_num]
                year_name = f"第{year_num}学年"
                
                fig, radar_data = create_radar_chart(year_data, year_name)
                
                if fig is not None:
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 显示该学年的详细数据
                    with st.expander(f"📋 {year_name}详细数据", expanded=False):
                        detail_cols = st.columns(3)
                        
                        # Display radar_data items (德育, 智育, 体测成绩, 附加分, 综测总分)
                        for i, (field, normalized_val, actual_val) in enumerate(radar_data):
                            col_idx = i % 3
                            # Determine color for this field's value display
                            if field == '德育': color = '#16a34a'
                            elif field == '智育': color = '#3b82f6'
                            elif field == '体测成绩': color = '#f59e0b'
                            elif field == '附加分': color = '#8b5cf6'
                            else: color = '#dc2626' # For 综测总分 or any other

                            with detail_cols[col_idx]:
                                if field == '综测总分' or field == '附加分': # Modified condition
                                    st.markdown(f"""
                                    <div class="metric-card">
                                        <div style="font-weight: 600; color: #374151; margin-bottom: 0.25rem;">{field}</div>
                                        <div style="color: {color}; font-weight: bold; font-size: 1.2rem;">{actual_val:.1f}</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else: # For '德育', '智育', '体测成绩'
                                    st.markdown(f"""
                                    <div class="metric-card">
                                        <div style="font-weight: 600; color: #374151; margin-bottom: 0.25rem;">{field}</div>
                                        <div style="color: {color}; font-weight: bold; font-size: 1.2rem;">{actual_val:.1f}</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                        
                        # Display '体测评级' as a metric card in the next available column
                        if '体测评级' in year_data and pd.notna(year_data['体测评级']):
                            col_idx_for_rating = len(radar_data) % 3 # Calculate column index after radar items
                            rating_value = format_value(year_data['体测评级'])
                            rating_text_color = '#0369a1' # Blue color for rating text
                            
                            with detail_cols[col_idx_for_rating]:
                                st.markdown(f"""
                                <div class="metric-card">
                                    <div style="font-weight: 600; color: #374151; margin-bottom: 0.25rem;">体测评级</div>
                                    <div style="color: {rating_text_color}; font-weight: bold; font-size: 1.2rem;">{rating_value}</div>
                                </div>
                                """, unsafe_allow_html=True)
            # 添加归一化细则说明
            with st.expander("ℹ️ 雷达图评分归一化细则", expanded=False):
                st.markdown(f"""
                雷达图中的各项评分均已通过以下方式进行归一化处理，以便在统一的0-100范围内进行比较：
                **各维度具体归一化参数 (预设最小值 / 预设最大值)：**
                *   `德育`: {st.session_state.user_normalization_params['德育']['min']} / {st.session_state.user_normalization_params['德育']['max']}
                *   `智育`: {st.session_state.user_normalization_params['智育']['min']} / {st.session_state.user_normalization_params['智育']['max']}
                *   `体测成绩`: {st.session_state.user_normalization_params['体测成绩']['min']} / {st.session_state.user_normalization_params['体测成绩']['max']}
                *   `附加分`: {st.session_state.user_normalization_params['附加分']['min']} / {st.session_state.user_normalization_params['附加分']['max']}
                *   `综测总分`: {st.session_state.user_normalization_params['综测总分']['min']} / {st.session_state.user_normalization_params['综测总分']['max']}
                
                归一化公式: `score = (原始值 - 最小值) / (最大值 - 最小值) * 100`
                """)
            
        else:
            st.info("📊 暂无综合素质评价数据")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 奖学金信息 (Replaces "奖助学金与特殊情况")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🏆 奖学金信息")
        yearly_scholarship_data = extract_yearly_scholarship_data(student_data)

        has_any_yearly_data_to_show_header_for = False
        if yearly_scholarship_data:
            # First, check if there's anything at all to warrant printing year headers
            for year_num_str_check in sorted(yearly_scholarship_data.keys(), key=get_year_sort_key):
                year_s_data_check = yearly_scholarship_data[year_num_str_check]
                scholarship_items_for_check = [
                    year_s_data_check.get("人民奖学金"),
                    year_s_data_check.get("助学奖学金"),
                    year_s_data_check.get("助学金"),
                    year_s_data_check.get("奖项")
                ]
                if any(format_value(val) != '无' for val in scholarship_items_for_check):
                    has_any_yearly_data_to_show_header_for = True
                    break
        
            if has_any_yearly_data_to_show_header_for:
                sorted_scholarship_years = sorted(yearly_scholarship_data.keys(), key=get_year_sort_key)
                for year_num_str in sorted_scholarship_years:
                    year_s_data = yearly_scholarship_data[year_num_str]
                    
                    # Define items for this year based on app.py structure
                    scholarship_items_for_this_year = [
                        ("人民奖学金", year_s_data.get("人民奖学金")),
                        ("助学奖学金", year_s_data.get("助学奖学金")),
                        ("助学金", year_s_data.get("助学金")),
                        ("获得奖项", year_s_data.get("奖项")) # Label "获得奖项", data key "奖项"
                    ]
                    
                    # Check if this specific year has any data to display its header
                    if any(format_value(item[1]) != '无' for item in scholarship_items_for_this_year):
                        st.markdown(f"#### {format_value(f'第{year_num_str}学年')}")
                        for label, raw_value in scholarship_items_for_this_year: # Iterate all defined items
                            value = format_value(raw_value) # format_value handles None -> '无'
                            status_class_schol = "status-scholarship" if value != '无' else "status-none"
                            st.markdown(f'''
                            <div style="background:#fffbeb; padding:0.75rem; border-radius:8px; margin:0.5rem 0;">
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <span style="color:#6b7280;">{label}：</span>
                                    <span class="status-badge {status_class_schol}">{value}</span>
                                </div>
                            </div>''', unsafe_allow_html=True)
            else: # No year had any displayable scholarship data, force fallback
                 yearly_scholarship_data = {} # Clear it to trigger fallback

        # Fallback to general scholarship items if no yearly data was processed or found worth displaying headers for
        if not yearly_scholarship_data or not has_any_yearly_data_to_show_header_for:
            st.markdown(f"#### 通用奖学金记录") # Header for general records
            
            fallback_scholarship_items = [
                ("人民奖学金", student_data.get('人民奖学金')),
                ("助学奖学金", student_data.get('助学奖学金')),
                ("助学金", student_data.get('助学金', student_data.get('助学金.1'))), # Specific app.py fallback
                ("获得奖项", student_data.get('奖项')) # Label "获得奖项", data key "奖项"
            ]
            
            # Check if there's any actual data in fallback items to avoid printing "暂无奖学金数据" if there is data.
            has_any_fallback_data_content = any(format_value(item[1]) != '无' for item in fallback_scholarship_items)

            if not has_any_fallback_data_content and not has_any_yearly_data_to_show_header_for:
                 st.info("📊 暂无奖学金数据")
            else: # Display all fallback items, showing '无' where applicable
                for label, raw_value in fallback_scholarship_items:
                    value = format_value(raw_value) # format_value handles None -> '无'
                    status_class_schol = "status-scholarship" if value != '无' else "status-none"
                    st.markdown(f'''
                    <div style="background:#fffbeb; padding:0.75rem; border-radius:8px; margin:0.5rem 0;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="color:#6b7280;">{label}：</span>
                            <span class="status-badge {status_class_schol}">{value}</span>
                        </div>
                    </div>''', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
        
        
    else:
        st.warning("🔍 没有找到匹配的学生数据，请调整搜索条件")

# 页脚
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6b7280; padding: 1rem;">
    <p>✈️ 航空工程学院学生数据分析系统</p>
</div>
""", unsafe_allow_html=True)
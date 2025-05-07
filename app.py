import streamlit as st
import io
import tempfile
import os
from docx import Document
from openai import OpenAI
import base64
import re
import json
from stqdm import stqdm
import requests

# 页面配置
st.set_page_config(
    page_title="AIGC文本降重修改工具",
    page_icon="✍️",
    layout="wide"
)

# 初始化会话状态
if 'doc' not in st.session_state:
    st.session_state.doc = None
if 'paragraphs' not in st.session_state:
    st.session_state.paragraphs = []
if 'modified_paragraphs' not in st.session_state:
    st.session_state.modified_paragraphs = []
if 'ai_probabilities' not in st.session_state:
    st.session_state.ai_probabilities = []
if 'selected_text' not in st.session_state:
    st.session_state.selected_text = ""
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""

# 自定义样式
st.markdown("""
<style>
    .main {
        padding: 1rem;
    }
    .stTextArea textarea {
        min-height: 200px;
    }
    .color-red {
        color: red;
    }
    .color-orange {
        color: orange;
    }
    .color-purple {
        color: purple;
    }
    .color-black {
        color: black;
    }
    .color-green {
        color: green;
    }
    .doc-viewer {
        border: 1px solid #ddd;
        padding: 10px;
        height: 600px;
        overflow-y: auto;
        background-color: white;
        color: black;
    }
    .doc-viewer p {
        color: black;
    }
</style>
""", unsafe_allow_html=True)

# 页面标题
st.title("AIGC 文本降重修改工具")
st.markdown("基于 **DeepSeek AI** 分析文本的 **AIGC生成概率**，自动优化内容，降低AI检测风险")

# DeepSeek API 调用函数
def analyze_text_with_deepseek(text, api_key, ai_probability=50):
    """使用DeepSeek API分析文本的AI生成概率并提供优化建议，传入用户选择的AI率"""
    try:
        # 直接使用requests库调用API而不是OpenAI客户端
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 根据用户选择的AI率构建不同的提示词
        system_prompt = f"""
        你是一个专业的文本优化助手，请对以下文本进行分析并基于{ai_probability}%的AI率进行优化：

        请基于以下降重核心策略进行针对性处理：
        1. 物理删除法：
          - 识别最明显的AI生成特征段落，适当情况下可考虑删除非核心内容
          - 针对高风险句子进行重写或缩减
        
        2. 引用大法：
          - 适当添加学术引用和交叉引用，提高文本可信度
          - 通过正确的引用格式，降低被判定为AI生成的概率
          - 将AI生成风险较高的内容改写为引用他人观点的形式
        
        3. 分段法：
          - 将风险较高的长段落分成多个较短的段落，避免"连坐"效应
          - 根据内容逻辑，将一个大段落拆分为2-3个小段落
          - 在段落之间添加过渡句，保持逻辑连贯性
        
        4. 同义词替换与句式变化：
          - 替换明显的AI风格词汇为更口语化的表达
          - 引入语气词和口语化表达（如"其实"、"说实话"、"值得一提的是"等）
          - 适当打破句式规律性，引入句长变化和思维跳跃
          - 以个人视角重构部分论述（如"我认为"、"从这个角度看"）

        根据文本的AI概率{ai_probability}%，请采用以下优化策略：
        """
        
        # 根据不同AI率范围添加具体优化策略
        if ai_probability > 70:
            system_prompt += """
            【深度优化】需要进行的改变：
              * 优先考虑分段法，将较长段落拆分为多个短段落
              * 积极添加学术引用，为高风险内容寻找合适的引用支持
              * 彻底打破句式结构规律性，引入自然起伏的句长变化
              * 加入口语化但学术上可接受的表述（"其实"、"说实话"、"值得一提的是"等）
              * 适度引入转折（"不过"、"然而"、"但话说回来"）和小范围跳跃性思考
              * 以个人视角重构部分论述（"我认为"、"从这个角度看"）
              * 保持原意的前提下，用不那么"完美"的解释替换过于教科书式的表述
              * 对非核心内容考虑精简或物理删除
            """
        elif 60 <= ai_probability <= 70:
            system_prompt += """
            【适度调整】需要进行的改变：
              * 应用分段法，将风险较高的段落适当分割
              * 在关键点添加1-2处恰当的学术引用
              * 保留部分原始结构，但有针对性地调整过于规则的段落
              * 增加少量个人见解和口语化连接词，但不影响学术严谨性
              * 在保持主要论点的同时，稍微调整论证路径，使其更自然
              * 使用同义词替换法，将明显的AI特征词汇替换为更人性化的表达
            """
        elif 50 <= ai_probability < 60:
            system_prompt += """
            【轻微优化】需要进行的改变：
              * 对个别明显AI特征句子应用分段法
              * 主要保留原文，只对最明显的AI特征进行微调
              * 替换1-2个过于标准化的表达，增加人性化语气
              * 微调个别句子的结构，但整体保持原貌
              * 适当添加口语化表达，如"其实"、"值得一提的是"等
            """
        else:
            system_prompt += """
            【保持原文】AI概率低于50%：
              * 文本已经具有较好的人类写作特征
              * 无需大量修改，可以保持原貌
              * 如有需要，只对个别明显机器化的表达进行调整
              * 可以考虑增加1-2处个人观点表达
            """
        
        # 添加通用要求
        system_prompt += """
        所有优化均应：
        - 保持学术写作基本规范和专业性以及严谨性
        - 确保术语使用的准确性不变
        - 在引入口语化元素的同时不失专业严谨
        - 避免过度调整导致内容失真
        - 适当添加个人视角的表述，但不破坏原有专业性

        请直接输出优化后的文本，不要解释你的修改。
        """
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]
        }
        
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        # 检查响应状态
        if response.status_code == 200:
            response_data = response.json()
            optimized_text = response_data["choices"][0]["message"]["content"]
            return optimized_text
        else:
            st.error(f"API调用失败，状态码: {response.status_code}, 响应: {response.text}")
            return text
            
    except Exception as e:
        st.error(f"调用DeepSeek API时发生错误: {str(e)}")
        return text  # 出错时返回原文本

# 处理Word文档上传
def process_docx_upload(uploaded_file):
    """处理上传的Word文档，并保留原有格式"""
    try:
        # 创建临时文件保存上传的文档
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        # 读取文档
        doc = Document(tmp_path)
        os.unlink(tmp_path)  # 删除临时文件
        
        # 提取段落及其格式
        paragraphs = []
        styles = []  # 存储每个段落的样式信息

        for para in doc.paragraphs:
            if para.text.strip():  # 只处理非空段落
                paragraphs.append(para.text)
                
                # 保存段落样式信息
                para_style = {
                    'style_name': para.style.name,
                    'alignment': para.alignment,
                    'runs': []
                }
                
                # 保存每个run的格式信息
                for run in para.runs:
                    # 处理字体颜色
                    has_color = False
                    color_rgb = None
                    
                    # 安全地获取颜色信息
                    if hasattr(run, 'font') and hasattr(run.font, 'color'):
                        try:
                            font_color = run.font.color
                            if font_color and hasattr(font_color, 'rgb') and font_color.rgb:
                                has_color = True
                                # 获取颜色值，可能是整数或其他类型
                                color_rgb = font_color.rgb
                        except:
                            pass
                    
                    run_style = {
                        'text': run.text,
                        'bold': run.bold,
                        'italic': run.italic,
                        'underline': run.underline,
                        'font_size': run.font.size if run.font.size else None,
                        'font_name': run.font.name if run.font.name else None,
                        'has_color': has_color,
                        'color_rgb': color_rgb
                    }
                    para_style['runs'].append(run_style)
                
                styles.append(para_style)
        
        st.session_state.doc = doc
        st.session_state.paragraphs = paragraphs
        st.session_state.modified_paragraphs = paragraphs.copy()
        st.session_state.paragraph_styles = styles
        st.session_state.ai_probabilities = [50] * len(paragraphs)  # 默认概率值
        
        return True
    except Exception as e:
        st.error(f"处理文档时发生错误: {str(e)}")
        return False

# 获取文本的颜色标记
def get_color_class(ai_probability):
    """根据AI生成概率返回相应的颜色类名"""
    if ai_probability > 70:
        return "color-red"
    elif 60 <= ai_probability <= 70:
        return "color-orange"
    elif 50 <= ai_probability < 60:
        return "color-purple"
    else:
        return "color-black"

# 获取段落原始格式的HTML样式
def get_paragraph_style_html(para_idx):
    """根据保存的段落样式信息生成HTML样式"""
    if not hasattr(st.session_state, 'paragraph_styles') or para_idx >= len(st.session_state.paragraph_styles):
        return ""
    
    style = st.session_state.paragraph_styles[para_idx]
    style_str = ""
    
    # 添加对齐方式
    if style['alignment'] == 1:  # 居中
        style_str += "text-align: center; "
    elif style['alignment'] == 2:  # 右对齐
        style_str += "text-align: right; "
    elif style['alignment'] == 3:  # 两端对齐
        style_str += "text-align: justify; "
    
    # 如果段落有runs，使用第一个run的格式作为默认格式
    if style['runs'] and len(style['runs']) > 0:
        first_run = style['runs'][0]
        
        if first_run['bold']:
            style_str += "font-weight: bold; "
        if first_run['italic']:
            style_str += "font-style: italic; "
        if first_run['underline']:
            style_str += "text-decoration: underline; "
        if first_run['font_size'] is not None:
            # 将磅转换为像素（大致转换）
            pt_size = first_run['font_size'] / 12700  # 将EMU转换为磅
            px_size = pt_size * 1.33  # 磅转像素的大致转换
            style_str += f"font-size: {px_size}px; "
        if first_run['font_name'] is not None:
            style_str += f"font-family: '{first_run['font_name']}', sans-serif; "
        
        # 使用原始文本颜色，如果有
        if first_run['has_color'] and first_run['color_rgb']:
            try:
                # 简化颜色处理逻辑
                rgb = first_run['color_rgb']
                if isinstance(rgb, int):
                    # 如果是整数值，直接处理
                    r = rgb & 0xFF
                    g = (rgb >> 8) & 0xFF
                    b = (rgb >> 16) & 0xFF
                    style_str += f"color: rgb({r}, {g}, {b}); "
                elif hasattr(rgb, '_rgb'):
                    # 处理某些颜色对象
                    color_value = rgb._rgb
                    if color_value is not None:
                        style_str += f"color: #{color_value:06x}; "
                else:
                    # 默认使用黑色
                    style_str += "color: black; "
            except Exception as e:
                # 如果解析颜色出错，使用默认黑色
                style_str += "color: black; "
    
    return style_str

# 导出修改后的文档
def export_modified_doc():
    """导出修改后的Word文档，保留原格式"""
    try:
        if st.session_state.doc is None:
            st.error("没有可导出的文档")
            return None
        
        # 创建新文档
        doc = Document()
        
        # 获取修改后的文本段落
        modified_paragraphs = st.session_state.modified_paragraphs
        
        # 复制原文档的段落和格式
        for para_idx, para in enumerate(st.session_state.doc.paragraphs):
            if para.text.strip() and para_idx < len(modified_paragraphs):  # 只处理非空段落
                # 创建新段落并设置文本
                new_para = doc.add_paragraph()
                
                # 应用原段落的样式
                new_para.style = para.style
                
                # 判断是否有保存的样式信息
                if hasattr(st.session_state, 'paragraph_styles') and para_idx < len(st.session_state.paragraph_styles):
                    # 添加修改后的文本内容（不处理复杂格式，只添加纯文本）
                    new_para.add_run(modified_paragraphs[para_idx])
                else:
                    # 没有保存的样式信息，直接添加文本
                    new_para.add_run(modified_paragraphs[para_idx])
        
        # 创建内存中的字节流
        doc_bytes = io.BytesIO()
        doc.save(doc_bytes)
        doc_bytes.seek(0)
        
        return doc_bytes
    except Exception as e:
        st.error(f"导出文档时发生错误: {str(e)}")
        return None

# 创建下载链接
def get_download_link(doc_bytes, filename="modified_document.docx"):
    """生成文档下载链接"""
    b64 = base64.b64encode(doc_bytes.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,{b64}" download="{filename}">点击下载修改后的文档</a>'
    return href

# 主界面
col1, col2 = st.columns(2)

# 左侧面板 - 上传和文档查看
with col1:
    st.subheader("文档上传与编辑区")
    
    # API密钥输入
    api_key = st.text_input("请输入您的DeepSeek API密钥", 
                            value=st.session_state.api_key,
                            type="password",
                            help="需要DeepSeek API密钥才能分析和优化文本")
    
    if api_key != st.session_state.api_key:
        st.session_state.api_key = api_key
    
    # 文件上传
    uploaded_file = st.file_uploader("上传Word文档", type=["docx"], 
                                    help="仅支持.docx格式的Word文档")
    
    if uploaded_file is not None:
        if process_docx_upload(uploaded_file):
            st.success(f"成功加载文档: {uploaded_file.name}")
    
    # 显示可编辑的文档内容
    if st.session_state.paragraphs:
        st.markdown("### 文档内容 (点击段落进行编辑)")
        
        selected_para_index = st.selectbox(
            "选择要编辑的段落", 
            options=list(range(len(st.session_state.paragraphs))),
            format_func=lambda x: f"段落 {x+1}: {st.session_state.paragraphs[x][:50]}..."
        )
        
        # 显示选定段落的AI概率和颜色标记
        prob = st.session_state.ai_probabilities[selected_para_index]
        color_class = get_color_class(prob)
        
        # 手动选择AI生成概率
        st.markdown("### 手动设置AI生成概率（AI率越高改写程度越大，本AI率是指原文本的AI率")
        selected_prob = st.slider(
            "AI生成概率", 
            min_value=0, 
            max_value=100, 
            value=prob,
            step=5,
            help="手动设置文本的AI生成概率，用于决定改写程度"
        )
        
        # 更新AI生成概率
        if selected_prob != prob:
            st.session_state.ai_probabilities[selected_para_index] = selected_prob
            prob = selected_prob
            color_class = get_color_class(prob)
        
        st.markdown(f"<p>AI生成概率: <span class='{color_class}'>{prob}%</span></p>", unsafe_allow_html=True)
        
        # 编辑区域
        st.session_state.selected_text = st.text_area(
            "编辑选定的段落", 
            value=st.session_state.modified_paragraphs[selected_para_index],
            height=200
        )
        
        # 更新修改后的段落
        if st.session_state.selected_text != st.session_state.modified_paragraphs[selected_para_index]:
            st.session_state.modified_paragraphs[selected_para_index] = st.session_state.selected_text
        
        # AI优化按钮
        if st.button("使用DeepSeek AI优化此段落"):
            if not st.session_state.api_key:
                st.error("请输入DeepSeek API密钥")
            else:
                with st.spinner("正在优化文本..."):
                    text = st.session_state.selected_text
                    # 将用户选择的AI概率值传递给API调用函数
                    ai_prob = st.session_state.ai_probabilities[selected_para_index]
                    optimized_text = analyze_text_with_deepseek(text, st.session_state.api_key, ai_prob)
                    
                    # 显示优化结果
                    st.markdown("### 优化结果")
                    st.markdown(f"<p class='color-green'>{optimized_text}</p>", 
                                unsafe_allow_html=True)
                    
                    if st.button("应用AI优化建议"):
                        st.session_state.modified_paragraphs[selected_para_index] = optimized_text
                        st.session_state.selected_text = optimized_text
                        st.experimental_rerun()

# 右侧面板 - 修改前后对比
with col2:
    st.subheader("文本对比与导出区")
    
    if st.session_state.paragraphs:
        # 创建两列以便并排显示
        orig_col, mod_col = st.columns(2)
        
        with orig_col:
            st.markdown("### 原始文本")
            
            # 原始文本显示区域，保留原格式
            original_text_html = "<div class='doc-viewer'>"
            for idx, para in enumerate(st.session_state.paragraphs):
                # 获取段落原始样式
                para_style = get_paragraph_style_html(idx)
                
                # 应用原始样式，确保文本为黑色
                if "color:" not in para_style:
                    para_style += " color: black;"
                original_text_html += f"<p style='{para_style}'>{para}</p>"
            original_text_html += "</div>"
            
            st.markdown(original_text_html, unsafe_allow_html=True)
        
        with mod_col:
            st.markdown("### 修改后文本")
            
            # 修改后文本显示区域，保留原格式并添加AI概率指示器
            modified_text_html = "<div class='doc-viewer'>"
            for idx, para in enumerate(st.session_state.modified_paragraphs):
                # 获取段落原始样式
                para_style = get_paragraph_style_html(idx)
                
                # 确保文本为黑色
                if "color:" not in para_style:
                    para_style += " color: black;"
                
                # 获取AI概率的颜色类
                ai_prob = st.session_state.ai_probabilities[idx]
                color_class = get_color_class(ai_prob)
                
                # 应用原始样式，并添加AI概率指示器
                modified_text_html += f"<p style='{para_style}'>{para} <span class='{color_class}'>({ai_prob}%)</span></p>"
            modified_text_html += "</div>"
            
            st.markdown(modified_text_html, unsafe_allow_html=True)
        
        # 批量处理按钮
        if st.button("批量分析所有段落"):
            if not st.session_state.api_key:
                st.error("请输入DeepSeek API密钥")
            else:
                progress_bar = stqdm(enumerate(st.session_state.paragraphs))
                for idx, para in progress_bar:
                    progress_bar.set_description(f"正在分析段落 {idx+1}/{len(st.session_state.paragraphs)}")
                    # 将每个段落的AI概率值传递给API调用函数
                    ai_prob = st.session_state.ai_probabilities[idx]
                    optimized_text = analyze_text_with_deepseek(para, st.session_state.api_key, ai_prob)
                    
                    # 根据当前设置的AI概率决定是否修改
                    if ai_prob > 50:
                        st.session_state.modified_paragraphs[idx] = optimized_text
                
                st.success("批量分析完成!")
                st.experimental_rerun()
        
        # 导出按钮
        if st.button("导出低AIGC文档"):
            doc_bytes = export_modified_doc()
            if doc_bytes:
                st.markdown(get_download_link(doc_bytes), unsafe_allow_html=True)
                st.success("文档已准备好下载!")

# 页脚
st.markdown("---")
st.markdown("#### 🎯 **AIGC文本降重修改工具** - 让AI生成文本更接近人类写作，轻松通过检测工具！")
st.markdown("""
- 🔴 **红色 (>70% AI概率)**: 需要深度改写
- 🟠 **橙色 (60%-70%)**: 适度优化
- 🟣 **紫色 (50%-60%)**: 轻微调整
- ⚫ **黑色 (<50%)**: 保留原文
""") 

st.markdown("""
#### 降重核心策略:
- 📝 **物理删除法**: 识别并删除高风险非核心内容
- 📚 **引用大法**: 添加学术引用，降低AI检测风险
- 📋 **分段法**: 将长段落分割，避免"连坐"效应
- 🔄 **同义词替换**: 用口语化表达替代机器化语言
""") 

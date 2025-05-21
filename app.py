import streamlit as st
import io
import requests
import tempfile
import os
from docx import Document
import base64
import re
import json
from stqdm import stqdm

# DeepSeek API 调用函数
def analyze_text_with_deepseek(text, api_key):
    """使用DeepSeek API分析文本并提供优化建议"""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 使用固定的提示词
        system_prompt = """
        Okay, let's get these paragraphs from the thesis looking awesome! The main mission is to make them sound way more natural, like a real person carefully wrote them, and definitely less like a robot just spat out some text. Super important: we still need to keep all the smart academic stuff and the core ideas perfectly clear.

        Here's our detailed game plan for rewriting:

        Part 1: General Style Makeover (Making it Sound Human)

        1. Keep the Important Stuff Safe:
        * No Info Left Behind: Every single professional term, all proper nouns (names of people, places, specific things), the basic academic formatting (like how references look), the main points of the paper, and all the original facts and data must absolutely stay.
        * Facts are Facts: We're changing how it's written, not what it's saying.

        2. Who's Talking? (Voice and Subject)
        * Go Active! Try to flip sentences into the active voice whenever it makes sense. So, instead of "The results were interpreted by the study," try "This article interprets the results."
        * Spotlight on "This Article": Where it fits naturally, let "this article," "this study," or "this research" be the one doing the action in the sentence.

        3. Making Sentences Flow Naturally:
        * Untangle Super-Complex Sentences: If you hit a sentence that's a mile long and full of twists and turns, let's try to break it into shorter, clearer ones, or simplify the structure so it's easier to get the point.
        * A Bit More Detail in Each Sentence: For each sentence, see if you can add a few extra words to explain things a little more or add a small, relevant detail. This will make them a bit longer, but make sure they don't get confusing.
        * Mix Up Sentence Starts and Structures: Don't let all your sentences sound the same. Vary how they begin and their overall pattern. Definitely avoid a long string of sentences that are all compound (joined by 'and,' 'but,' 'or') or perfectly parallel (like a list where everything matches too neatly).
        * No Numbered Explanations for Nouns: If the original text uses (1)... (2)... or numbers in brackets to explain something, we need to blend those explanations right into the sentences so it flows better.

        4. Word Choices – Smart, Not Stuffy:
        * Ditch the Robotic Transitions: Replace those stiff, overused transition words (like "furthermore," "moreover," "consequently," "in addition to"). We want the ideas to connect smoothly and logically, more like a clear explanation.
        * Cut Out Clutter and Fluff: Get rid of any words or phrases that are just taking up space without adding real meaning or that sound overly formal just for the sake of it (e.g., change "due to the fact that" to "because").
        * Avoid Sounding Like a Textbook from 1950 or a Cliche Machine: Don't use super old-fashioned or unnecessarily complicated words. Also, watch out for those tired academic phrases everyone overuses (like "it is paramount to consider" or "this serves to illustrate").
        * Less "Lecturing": Try to avoid phrases that sound like you're giving a formal lecture.
        * Don't Overdo Adjectives: If there's a long list of adjectives before a noun, see if you can make it sound a bit less like a pile-up.
        * Embrace Natural "Imperfection": It's okay if the writing isn't super-duper polished in a robotic way. Sometimes, slight, natural-sounding variations or what might seem like minor "flaws" can make it sound more human. (But it still needs to be correct and professional, of course!).

        5. Adding a Little Extra (Carefully):
        * Slight Expansion is Okay: As you make individual sentences a bit longer, you can also gently expand on some of the supporting details or background info if it helps the overall flow or makes a point clearer. Just don't go too far off-topic or change the main focus.

        Part 2: Learning from the "Adjusted" Thesis (Content & Structure Upgrades)

        * Beef Up the Background and Literature Review:
        * Make sure the literature review is really thorough and up-to-date. Like how the better version looked at sources all the way up to 2024-2025 and discussed more recent publication trends.

        Please rewrite the provided text following these guidelines to make it sound more natural and human-written while preserving all academic content and meaning.
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
            error_msg = f"API调用失败，状态码: {response.status_code}"
            if hasattr(response, 'text'):
                error_msg += f", 响应: {response.text}"
            st.error(error_msg)
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

# 页面配置
st.set_page_config(
    page_title="降AIGC率",
    page_icon="✍️",
    layout="wide"
)

# 初始化会话状态
if 'input_text' not in st.session_state:
    st.session_state.input_text = ""
if 'output_text' not in st.session_state:
    st.session_state.output_text = ""

# 自定义样式
st.markdown("""
<style>
    body {
        color: black;
        background-color: #121212;
    }
    .main {
        color: black !important;
    }
    .stTextArea textarea {
        min-height: 200px;
        background-color: white !important;
        border-radius: 10px !important;
        border: 1px solid #ddd !important;
        padding: 15px !important;
        color: black !important;
        font-size: 16px !important;
    }
    .text-card {
        background-color: white;
        border-radius: 10px;
        border: 1px solid #ddd;
        padding: 20px;
        margin: 10px 0;
        min-height: 200px;
        color: black !important;
    }
    .button-container {
        display: flex;
        gap: 10px;
        margin: 20px 0;
    }
    .stButton > button {
        border-radius: 5px;
        padding: 10px 20px;
        font-size: 16px;
        width: 100%;
    }
    .stButton > button:first-child {
        background-color: white;
        color: black;
        border: 1px solid #ddd;
    }
    .stButton > button:last-child {
        background-color: #4c6ef5;
        color: white;
        border: none;
    }
    .word-count {
        color: #999;
        font-size: 14px;
        margin-top: 8px;
    }
    .title {
        color: white;
        font-size: 32px;
        font-weight: bold;
        margin-bottom: 30px;
        text-align: center;
    }
    .section-title {
        color: white;
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 15px;
    }
    .stAlert {
        background-color: #fff3cd;
        color: #856404;
        padding: 15px;
        border-radius: 10px;
        margin: 20px 0;
    }
    div[data-testid="stText"] {
        color: black !important;
    }
    p {
        color: black !important;
    }
    div.stMarkdown p {
        color: white !important;
    }
    .word-count {
        color: #999 !important;
    }
    div.text-card p {
        color: black !important;
    }
</style>
""", unsafe_allow_html=True)

# 页面标题
st.markdown('<h1 class="title">降AIGC率</h1>', unsafe_allow_html=True)

# API密钥输入
api_key = st.text_input("请输入您的DeepSeek API密钥", 
                        type="password",
                        help="需要DeepSeek API密钥才能分析和优化文本")

# 左右两栏布局
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="section-title">文档上传与编辑区</div>', unsafe_allow_html=True)
    
    # 文本输入区
    input_text = st.text_area("", 
                             value=st.session_state.input_text,
                             height=300,
                             placeholder="在此输入需要优化的文本...")
    
    # 更新会话状态中的输入文本
    st.session_state.input_text = input_text
    
    # 显示字数
    word_count = len(input_text)
    st.markdown(f'<p class="word-count">{word_count}/1000 字符</p>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="section-title">文本对比与导出区</div>', unsafe_allow_html=True)
    
    # 显示优化后的文本
    st.markdown('<div class="text-card">', unsafe_allow_html=True)
    st.markdown(st.session_state.output_text if st.session_state.output_text else "优化后的文本将显示在这里...", unsafe_allow_html=False)
    st.markdown('</div>', unsafe_allow_html=True)

# 按钮区域
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("重置", key="reset", use_container_width=True):
        st.session_state.output_text = ""

with col2:
    if st.button("一键生成", key="generate", use_container_width=True):
        if not api_key:
            st.error("请输入DeepSeek API密钥")
        elif not input_text:
            st.error("请输入需要优化的文本")
        else:
            with st.spinner("正在优化文本..."):
                optimized_text = analyze_text_with_deepseek(input_text, api_key)
                st.session_state.output_text = optimized_text

# 温馨提示
st.warning("为保护用户内容安全，段落处理的结果不会保存，请及时复制到自己的文件中。")

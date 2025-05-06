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
def analyze_text_with_deepseek(text, api_key):
    """使用DeepSeek API分析文本的AI生成概率并提供优化建议"""
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        
        # 根据AI检测原理优化提示词
        messages = [
            {"role": "system", "content": """
            你是一个专业的文本优化助手，请对以下文本进行分析并完成两项任务：
            
            1. 分析该文本由AI生成的概率（以百分比表示），基于以下三大核心技术的检测原理：
               - 语言模型分析：评估文本与大型语言模型生成内容的"指纹"相似度
               - 文本特征提取：分析语言多样性、句长变化、词汇丰富度（AI文本往往过于规律化）
               - 语篇连贯性分析：检测是否过于条理化、缺乏人类写作中常见的思维跳跃和逻辑断层
            
            2. 根据AI概率，提供优化建议使其更像人类所写：
               - 如果AI概率>70%（深度改写）：
                 * 打破过于规整的段落结构，增加句长变化
                 * 增加个性化表达和口语化元素
                 * 适当加入转折、跳跃或小偏题，模拟人类思维流动
                 * 使用更多人类常用但非最优的词汇选择
                 * 偶尔使用不那么严密的逻辑关系
               
               - 如果AI概率在60%-70%（适度优化）：
                 * 调整部分句式和衔接方式
                 * 增加适量的主观表达和个人感受
                 * 减少过于完美的段落结构
               
               - 如果AI概率在50%-60%（轻微调整）：
                 * 微调词汇选择，避免过于正式的学术感
                 * 调整极少数过于机械的表达方式
               
               - 如果AI概率<50%：
                 * 完全保留原文，无需修改
            
            请确保修改后的文本保持原意，但更具人类写作特色。
            
            请按以下格式回复：
            {"ai_probability": 数字, "optimized_text": "优化后的文本"}
            """},
            {"role": "user", "content": text}
        ]
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )
        
        response_text = response.choices[0].message.content
        
        # 提取JSON格式的响应
        json_pattern = r'\{.*\}'
        json_match = re.search(json_pattern, response_text, re.DOTALL)
        
        if json_match:
            result = json.loads(json_match.group())
            return result.get("ai_probability", 0), result.get("optimized_text", text)
        else:
            # 如果无法解析JSON，从文本中尝试提取概率
            prob_pattern = r'ai_probability":\s*(\d+)'
            prob_match = re.search(prob_pattern, response_text)
            prob = int(prob_match.group(1)) if prob_match else 50
            
            # 提取优化文本
            opt_pattern = r'optimized_text":\s*"([^"]+)'
            opt_match = re.search(opt_pattern, response_text)
            opt_text = opt_match.group(1) if opt_match else text
            
            return prob, opt_text
    except Exception as e:
        st.error(f"调用DeepSeek API时发生错误: {str(e)}")
        return 50, text  # 返回默认值

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
        
        # AI分析按钮
        if st.button("使用DeepSeek AI分析和优化此段落"):
            if not st.session_state.api_key:
                st.error("请输入DeepSeek API密钥")
            else:
                with st.spinner("正在分析文本..."):
                    text = st.session_state.selected_text
                    ai_prob, optimized_text = analyze_text_with_deepseek(text, st.session_state.api_key)
                    
                    st.session_state.ai_probabilities[selected_para_index] = ai_prob
                    
                    # 显示AI分析结果
                    st.markdown(f"### AI分析结果")
                    st.markdown(f"<p>AI生成概率: <span class='{get_color_class(ai_prob)}'>{ai_prob}%</span></p>", 
                                unsafe_allow_html=True)
                    
                    if ai_prob > 50:
                        st.markdown("### 优化建议")
                        st.markdown(f"<p class='color-green'>{optimized_text}</p>", 
                                    unsafe_allow_html=True)
                        
                        if st.button("应用AI优化建议"):
                            st.session_state.modified_paragraphs[selected_para_index] = optimized_text
                            st.session_state.selected_text = optimized_text
                            st.experimental_rerun()
                    else:
                        st.success("此段落的AI生成概率较低，无需修改。")

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
                progress_bar = stqdm(st.session_state.paragraphs)
                for idx, para in enumerate(progress_bar):
                    progress_bar.set_description(f"正在分析段落 {idx+1}/{len(st.session_state.paragraphs)}")
                    ai_prob, optimized_text = analyze_text_with_deepseek(para, st.session_state.api_key)
                    st.session_state.ai_probabilities[idx] = ai_prob
                    
                    # 根据AI概率决定是否修改
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

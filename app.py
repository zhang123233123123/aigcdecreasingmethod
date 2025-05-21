import streamlit as st
import requests

# 页面配置
st.set_page_config(page_title="降AIGC率", page_icon="✍️", layout="wide")

# 初始化会话状态
if 'input_text' not in st.session_state:
    st.session_state.input_text = ""
if 'output_text' not in st.session_state:
    st.session_state.output_text = ""

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
        return text

# 自定义样式
st.markdown("""
<style>
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
    div.text-card p {
        color: black !important;
    }
</style>
""", unsafe_allow_html=True)

# 页面标题
st.title("降AIGC率")

# API密钥输入
api_key = st.text_input("请输入您的DeepSeek API密钥", type="password")

# 左右两栏布局
col1, col2 = st.columns(2)

with col1:
    st.subheader("文档上传与编辑区")
    
    # 文本输入区
    input_text = st.text_area("", 
                             value=st.session_state.input_text,
                             height=300,
                             placeholder="在此输入需要优化的文本...")
    
    # 更新会话状态中的输入文本
    st.session_state.input_text = input_text
    
    # 显示字数
    word_count = len(input_text)
    st.text(f"{word_count}/1000 字符")

with col2:
    st.subheader("文本对比与导出区")
    
    # 显示优化后的文本
    st.markdown('<div class="text-card">', unsafe_allow_html=True)
    st.write(st.session_state.output_text if st.session_state.output_text else "优化后的文本将显示在这里...")
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
                if optimized_text:
                    st.session_state.output_text = optimized_text

# 温馨提示
st.warning("为保护用户内容安全，段落处理的结果不会保存，请及时复制到自己的文件中。")

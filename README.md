# AIGC 文本降重修改工具

这是一个基于 Streamlit 和 DeepSeek AI 的文本降重修改工具，专为优化 AI 生成内容而设计，降低 AI 检测风险。

## 核心功能

- **智能降AIGC率**：基于 DeepSeek AI 分析文本的 AIGC 生成概率，自动优化内容
- **用户可控修改**：允许手动调整 AI 修改后的文本，确保语义通顺
- **颜色标记风险等级**：
  - 🔴 **红色（>70% AI概率）→ 深度改写**
  - 🟠 **橙色（60%-70%）→ 适度优化**
  - 🟣 **紫色（50%-60%）→ 轻微调整**
  - ⚫ **黑色（<50%）→ 保留原文**
- **一键应用修改**：将优化后的文本整合并导出为 .docx 文件

## 使用方法

1. 安装依赖：
```
pip install -r requirements.txt
```

2. 运行应用：
```
streamlit run app.py
```

3. 使用流程：
   - 输入您的 DeepSeek API 密钥
   - 上传 Word (.docx) 文档
   - 选择段落进行编辑或批量分析
   - 查看和应用 AI 优化建议
   - 导出优化后的文档

## 技术实现

- 使用 Streamlit 构建 Web 界面
- 集成 DeepSeek API 进行 AI 文本分析和优化
- 使用 python-docx 处理 Word 文档
- 提供直观的文本比对和编辑功能

## 部署

应用已部署在 Streamlit Share 平台，可以通过以下链接访问：
[AIGC 文本降重修改工具](https://share.streamlit.io)

## 注意事项

- 使用前需准备 DeepSeek API 密钥
- 仅支持 .docx 格式的 Word 文档
- 建议在 AI 优化后进行人工微调，确保内容质量 
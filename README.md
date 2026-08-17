# AI Product Technical Operations Portfolio

两个可运行的个人实践项目，面向 AI 产品技术运营、技术支持和 ToB 客户成功岗位。

## 1. AI Knowledge Base Support Assistant

功能：知识库检索、引用来源、问题反馈记录、可选 OpenAI 兼容 API 问答增强。

```powershell
cd knowledge-base-assistant
python app.py
```

访问 `http://127.0.0.1:8765`。默认是本地检索模式。配置以下环境变量后可启用大模型回答：

```powershell
$env:OPENAI_API_KEY = "your_key"
$env:OPENAI_MODEL = "gpt-4o-mini"
python app.py
```

## 2. AI Technical Support Workbench

功能：客户问题提交、规则化诊断建议、优先级、状态流转、客户到研发的信息整理。

```powershell
cd support-workbench
python app.py
```

访问 `http://127.0.0.1:8766`。工单数据保存在本地 `tickets.db`，不会上传。

## GitHub 发布建议

公开前先运行两个项目、录制 1 分钟演示、补充截图并完成自己的 README。简历应描述为“个人项目，使用 Python 标准库与开源 AI API 协议实现”，不要写成自研大模型或生产系统。

建议仓库结构：一个仓库保存两个应用，或拆成两个独立仓库。发布时保留本 README、`.gitignore` 和 `LICENSE`。

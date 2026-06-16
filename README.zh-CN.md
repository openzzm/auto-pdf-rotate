# PDF 页面方向自动修正

[English](README.md)

这是一个本地运行的 Windows PDF 页面方向修正工具，可识别扫描 PDF 中横倒或上下颠倒的页面，并在源文件旁生成修正副本。

程序完全在本机处理文件，不上传文档、不提供下载接口，也不会修改源 PDF。

## 功能

- 使用 RapidOCR 和 ONNX Runtime 检测页面方向。
- 保留源 PDF，在同目录生成修正副本。
- 支持点击选择 PDF，也支持将 PDF 拖拽到选择区域。
- 使用保守的置信度阈值，方向不明确的页面保持原样。
- 对难以判断的页面使用更高分辨率重试。
- 显示处理进度、已用时间、平均每页耗时和预计剩余时间。
- 提供英语和简体中文界面及文档，默认使用英语。
- 支持浏览器模式和 Windows 便携桌面版。
- 关闭程序时清理工作线程、任务信息和临时文件。

## 输出文件

选择：

```text
document.pdf
```

将在同目录生成：

```text
document_已修正方向版.pdf
```

源文件不会被修改。

## 环境要求

- Windows 10 或 Windows 11
- 推荐使用 Python 3.12

## 从源码运行

```powershell
git clone https://github.com/openzzm/auto-pdf-rotate.git
cd auto-pdf-rotate
python -m pip install -r requirements.txt
python app.py
```

服务启动后，请访问 `http://127.0.0.1:8765`。

Windows 下也可以双击 `start-browser.bat` 启动浏览器模式。在便携桌面版中，可以将 PDF 拖拽到选择区域，也可以点击选择文件。普通浏览器拖拽无法可靠暴露源文件目录，因此浏览器模式保留点击选择作为兜底。

## 构建便携版

安装构建依赖：

```powershell
python -m pip install -r requirements-build.txt
```

构建 PyInstaller `onedir` 便携版：

```powershell
.\build-portable.ps1 -PythonExecutable "C:\Path\To\Python312\python.exe"
```

构建结果：

```text
release\AutoPDFRotate-Portable\AutoPDFRotate.exe
```

迁移到其他电脑时，需要复制整个 `AutoPDFRotate-Portable` 目录。

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试覆盖旋转判断、输出命名、同目录自动保存、关闭清理和桌面桥接。

## 工作原理

1. 使用轻量分析分辨率渲染每个页面。
2. 检测文字区域并判断文字方向。
3. 仅在投票数量、置信度和领先幅度达到阈值时旋转。
4. 对文字稀少或结果冲突的页面使用更高分辨率重试。
5. 保存修正后的 PDF 和内部分析报告。
6. 服务关闭时删除临时任务数据。

## 项目结构

```text
app.py                  Flask 服务、PDF 处理和桌面启动
templates/index.html    应用界面
static/app.js           界面行为和语言资源加载
static/locales/         英语和简体中文界面文案
static/style.css        界面样式
tests/                  自动化回归测试
portable.spec           PyInstaller 配置
build-portable.ps1      便携版构建脚本
```

## 隐私说明

所有 PDF 均在本机处理。应用运行期间，临时分析报告保存在 `jobs` 目录，正常关闭时会自动删除。修正后的 PDF 会保留在源文件同目录。

## 已知限制

- 无文字页面或特殊排版可能无法提供足够的方向判断依据。
- 桌面便携版面向 Windows x64。
- 强制终止进程可能导致关闭清理无法执行。

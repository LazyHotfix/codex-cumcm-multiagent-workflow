# Windows PowerShell 中文编码说明

## 适用场景

当在 Windows PowerShell、Codex 终端或脚本输出中看到中文乱码、`��`、JSON 解析异常，或文件路径/论文标题显示异常时，先按本说明判断是显示层编码问题还是文件内容已经损坏。

## 常见原因

项目内 Markdown、JSON、OCR 文本和样例索引默认按 UTF-8 保存；但 Windows PowerShell 5.1、传统控制台代码页、系统 ANSI 编码和终端桥接层可能使用 GBK、OEM 936 或其他编码解释 stdout。

这会导致同一份 UTF-8 文件在 Python 中可正常读取和解析，但用 PowerShell `Get-Content`、`ConvertFrom-Json` 或普通终端预览时显示乱码，甚至因被错误解码而解析失败。

## 判断原则

- 优先用 Python 显式 `encoding="utf-8"` 读取、写入和解析文件。
- 如果 Python UTF-8 读取正常，而 PowerShell 显示乱码，通常视为终端显示层问题。
- 如果 Python UTF-8 也无法读取、JSON 无法解析或文本本身已经包含乱码字符，再判断为文件内容可能已损坏。
- 不要因为 PowerShell 预览乱码就直接重写、删除或替换样例库文件。

## 推荐读取方式

优先使用 Python：

```python
from pathlib import Path
import json

p = Path("path/to/file.json")
data = json.loads(p.read_text(encoding="utf-8"))
```

写入 JSON 时保留中文：

```python
p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
```

## PowerShell 临时设置

在当前 PowerShell 会话中可尝试：

```powershell
chcp 65001
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
```

读取文件时显式指定 UTF-8：

```powershell
Get-Content -Encoding UTF8 -LiteralPath "path\to\file.md"
```

## PowerShell 长期设置

可把下面内容加入 `$PROFILE`：

```powershell
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
```

若 `$PROFILE` 不存在：

```powershell
New-Item -ItemType File -Force -Path $PROFILE
```

PowerShell 7 通常比 Windows 自带 PowerShell 5.1 更稳定，配合 Windows Terminal 更适合处理 UTF-8 中文项目。

## 开源提示

开源后如果其他用户报告中文乱码，先要求对方说明：

- 使用的是 Windows PowerShell 5.1、PowerShell 7、Windows Terminal、CMD 还是其他终端。
- 文件是否能用 Python `encoding="utf-8"` 正常读取。
- 乱码只出现在终端显示，还是已经写入到文件内容中。

只有确认文件内容已被错误编码写坏时，才需要从备份、原始样例或重新生成流程恢复。

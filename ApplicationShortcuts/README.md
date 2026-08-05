# application shortcuts · v2

在原始 "application shortcuts" 工作流基础上重做：**保留全部有效热键**，
删掉死节点，终端/浏览器改为**可配置**，并用 `app` 菜单消除黑盒。

## 画布结构

双列排版，分类纵向分组（热键在左、动作在右，连线都是短横线）：

```
 热键 (x=40)              动作 (x=280)
 ──────────────           ─────────────────
 Hyper+1        ──────►   ChatGPT            ← AI
 Hyper+C        ──────►   Claude
 (留白)
 Hyper+2        ──────►   launch.sh          ← 终端/浏览器（共享）
 Hyper+B        ──────►   launch.sh
 app 关键词      ──────►   launch.sh          ← 菜单也走同一出口
 (留白)
 Hyper+M        ──────►   WeChat             ← 聊天
 Hyper+D        ──────►   Discord
 (留白)
 Hyper+N        ──────►   Obsidian           ← 笔记
 Hyper+W        ──────►   workbook 脚本
 (留白)
 Hyper+Z        ──────►   Zed                ← 开发/系统
 Hyper+F        ──────►   Finder
 (留白)
 ⌥⇧S            ──────►   easydict 脚本      ← 查询
```

## 脚本说明

| 文件 | 角色 | 说明 |
| --- | --- | --- |
| `launch.sh` | 共享启动器 | 终端/浏览器热键和 `app` 菜单的共同出口，实现启动或切换（toggle） |
| `filter.py` | `app` 菜单 | 输出 Alfred Script Filter JSON，只列已配置项，**不搜索全部应用** |
| `build_plist.py` | 构建工具 | 生成 `info.plist`（唯一事实来源），含热键、画布布局、内置 readme |
| `pack.sh` | 打包工具 | 重新生成 plist → 压缩成 `.alfredworkflow` → 校验 +x 和 plist |

### launch.sh 参数协议

`$1` 取值（`app` 菜单和热键共用同一协议）：

| 参数 | 效果 |
| --- | --- |
| `terminal` | 读环境变量 `TERMINAL_APP`（Configure Workflow… 下拉框的值），启动该终端 |
| `browser` | 读 `BROWSER_APP`，启动该浏览器 |
| `<应用名>` | 直接启动，如 `ChatGPT`、`Easydict` |
| `<应用名>\|<路径>` | 带文件/文件夹启动，如 `Obsidian\|~/data/note/workbook`（`~` 会自动展开） |

**行为**：目标应用已在前台 → 用 System Events 隐藏（首次会弹一次
「Alfred 想控制 System Events」授权）；否则 `open -a` 启动/聚焦。

**环境变量**：`TERMINAL_APP` / `BROWSER_APP` 由工作流变量注入，默认值
iTerm / Google Chrome，在 Configure Workflow… 里修改。

### 画布上的其他动作节点

- **Launch Apps/Files × 7**（ChatGPT、Claude、Discord、Finder、WeChat、
  Obsidian、Zed）：Alfred 内置启动器，带 toggle，零权限。
- **内联 AppleScript × 2**（写在 plist 里，不是独立文件）：
  - Hyper+W：`open -a "Obsidian" ~/data/note/workbook` → 打开工作笔记 vault
  - ⌥⇧S：把**选中文本**拼进 `easydict://query?text=…` 传给 Easydict

### 改哪里？

| 想改… | 改这里 |
| --- | --- |
| 终端/浏览器候选列表、默认值 | `build_plist.py` 的 `userconfigurationconfig`（popupbutton pairs） |
| Obsidian 工作笔记 vault 路径 | `build_plist.py` 的 `add_script('open -a "Obsidian" …')` |
| `app` 菜单的文案/图标 | `filter.py` 的 `ROWS` |
| 画布分组/位置 | `build_plist.py` 的 `BLOCKS` 和 `HX/TX` |
| 新增一个快捷键 | 在 `build_plist.py` 加一行热键 + 动作 + 连线，重新 `./pack.sh` |

改完统一执行 `./pack.sh` 重新打包。

## 快捷键

| 按键 | 分类 | 打开 |
| --- | --- | --- |
| Hyper+1 | AI | ChatGPT |
| Hyper+2 | 终端 | 可配置（默认 iTerm） |
| Hyper+B | 浏览器 | 可配置（默认 Google Chrome） |
| Hyper+C | AI | Claude |
| Hyper+D | 聊天 | Discord |
| Hyper+F | 系统 | Finder |
| Hyper+M | 聊天 | WeChat |
| Hyper+N | 笔记 | Obsidian |
| Hyper+W | 笔记 | Obsidian（工作笔记 vault） |
| Hyper+Z | 开发 | Zed |
| ⌥⇧S | 查询 | Easydict（选中文本查询） |

> Hyper = ⌃⌥⇧⌘（Karabiner 配置）。Hyper+3 原本是空目标，已删除；
> 想用新键：在 `build_plist.py` 加一行，或复制画布热键块改键。

## 与 v1 的差异

- 画布从 31 个对象精简到 22 个，删除死节点（3 个未设置热键的触发、
  2 个空 Launch、1 个孤儿脚本、1 个孤儿 Launch）
- Hyper+2 / Hyper+B 改为 Configure Workflow… 下拉框配置
- 新增 `app` 菜单：查看每个快捷键对应什么，回车直接启动

## 发布

```bash
./pack.sh   # 生成 info.plist + 打包 Application Shortcuts.alfredworkflow + 校验
```

导入时 bundle id 与旧工作流相同（`com.srq.application`），Alfred 会直接替换。
**注意：导入前先删除已安装的 App Launcher 工作流**（它注册了同样的 Hyper
热键，会导致按键冲突）。

# App Launcher

Hyper-key 应用启动器：**36 个静态 Alfred 热键**（Hyper+0-9 / Hyper+A-Z）全部触发
同一个启动脚本，按键通过热键的 `argumenttext` 传入；键→应用映射存在一个
**JSON 注册表**里，运行时随时增删 —— 添加应用只需一条命令，**无需打开
工作流编辑器、无需改 plist、无需重启 Alfred**。

> Hyper = ⌃⌥⇧⌘（你在 Karabiner 里配置的 Hyper 键），与旧工作流完全一致。

## 为什么是 36 个静态热键？

Alfred 无法在运行时动态注册全局热键（热键组合写死在 info.plist 里）。
本工作流把「热键集合」与「键→应用映射」解耦：

- **热键集合固定**：36 个 Hyper+单键触发，一次性生成在 info.plist 里（覆盖
  10 个数字 + 26 个字母，你的旧映射 10 个键全部在内）；
- **映射动态**：按下 Hyper+1 → 脚本查 `apps.json` → 启动对应应用。
  `app add` 只是写 JSON，**立即生效**。

## 安装 & 首次运行

1. 双击导入 `App Launcher.alfredworkflow`；
2. 按任意 Hyper+键（或输入 `app`）；
3. **自动迁移**：首次运行会解析旧的 "application shortcuts" 工作流
   （如果还在），导入全部有效映射：Hyper+1 ChatGPT、Hyper+2 kitty、
   Hyper+B Chrome、Hyper+C Claude、Hyper+D Discord、Hyper+F Finder、
   Hyper+M WeChat、Hyper+N Obsidian、Hyper+W Obsidian(workbook)、
   Hyper+Z Zed，以及 **⌥⇧S → Easydict 选中文本查询**。
   死节点（未设热键的触发、空 Launch、孤儿脚本）自动丢弃。

## 使用

| 输入 | 效果 |
| --- | --- |
| `app add 4 Slack` | 绑定 Hyper+4 → Slack（自动解析应用路径） |
| `app add w Obsidian ~/data/note/workbook` | 带启动参数绑定 |
| `app 4 slack` | 一步绑定（键在前的两词形式） |
| `app rm 4` / `app rm Slack` | 解除绑定 |
| `app slack` | 启动任意应用（注册或未注册都行） |
| `app` | 全部已注册应用 + 用法提示，Alfred 内模糊过滤 |
| 按未绑定的 Hyper+键 | 提示通知，附精确的添加命令 |
| ⌥⇧S | 选中文本 → Easydict 查询 |

## 行为细节

- **Toggle（默认开启）**：应用在前台时再按一次热键则隐藏（与旧工作流一致）。
  前台检测用 `lsappinfo`（无需权限）；隐藏用 System Events —— 首次使用会弹
  一次「Alfred 想要控制 System Events」的授权，允许后静默。不想用 toggle 可在
  Configure Workflow… 里关掉（变纯 launch-or-focus）。
- **查询模式**：⌥⇧S 触发器和 `"mode": "query"` 的条目把选中文本代入 URL scheme。
- 未绑定按键的提示通知可在 Configure Workflow… 里关闭。

## 注册表

`apps.json` 位于 Alfred 的 Workflow Data 目录（本 bundle id）：
`~/Library/Application Support/Alfred/Workflow Data/com.yitiansong.applauncher/apps.json`

```json
{
  "1": {"name": "ChatGPT", "path": "/Applications/ChatGPT.app", "toggle": true},
  "w": {"name": "Obsidian", "path": "/Applications/Obsidian.app",
        "args": ["~/data/note/workbook"], "toggle": true},
  "s": {"name": "Easydict", "mode": "query",
        "scheme": "easydict://query?text={query}"}
}
```

## 已知冲突

**Hyper+R / Hyper+S 被 "Writing Assistant" 工作流占用** —— 网格里这两个键
故意未绑定，`app add r …` 会收到提示。若你改了 Writing Assistant 的快捷键，
这两个键自动可用。

## 重新构建

```bash
python3 build_plist.py   # 重新生成 info.plist（改网格/修饰键/关键词在此）
./pack.sh                # 打包 ../App Launcher.alfredworkflow 并校验
```

运行时文件：`app.py`（引擎）、`launch.sh`（热键/管理入口）、
`launchq.sh`（⌥⇧S 选中文本入口）、`filter.sh`（`app` 脚本过滤器入口）。

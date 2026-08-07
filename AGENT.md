# AGENT.md — Alfred Workflow 项目记忆

> 本文件是给 AI agent 看的项目记忆，记录用户偏好、最终方案、实测 ground truth 和**踩过的坑**。
> 任何 agent 在本目录开发 Alfred workflow 前，**必须**先读本文件。

---

## 项目结构

```
/Users/yitiansong/data/code/alfred/
├── AGENT.md                        ← 本文件，先读
├── Settings.alfredworkflow         ← Settings workflow 打包产物（最新）
├── System Settings/                ← Settings workflow 源目录（唯一编辑目标）
│   ├── info.plist                  ← 43 keyword + 43 Arg&Vars + 1 Open URL
│   ├── icon.png                    ← workflow 图标（系统设置齿轮）
│   └── <对象UID>.png               ← 每个 keyword 对象的专属图标（共 43 个）
├── Homebrew Manager/               ← 其他项目（勿动）
├── netease-music-controls/         ← 其他项目（勿动）
└── pi-agent/                       ← 其他项目（勿动）
```

---

## Settings workflow：用户需求（最终版，已确认）

用户要的是一个**输入即打开**的系统设置 workflow，**没有关键字前缀、没有参数、没有空格、没有 fallback 两步、没有快捷键**。

### 最终方案（用户拍板）

**43 个独立 keyword，每个对应一个设置面板，输入即打开，一步到位。**

| 输入 | 打开 |
| ------ | ------ |
| `wifi` / `wi-fi` | Wi‑Fi |
| `battery` | 电池 |
| `login items` / `login` | 登录项 |
| `privacy` / `security` | 隐私与安全性 |
| `dock` / `desktop` | 桌面与程序坞 |
| …（共 43 个） | … |

- 对象结构：`keyword → Arg&Vars(完整 x-apple.systempreferences: URL) → Open URL(url 留空)`
- keyword 支持 `||` 多别名（如 `"wifi||wi-fi"`、`"desktop||dock"`）
- keyword config：`argumenttype: 2`、`withspace: false`、`subtext: "System Settings → <名称>"`

### 用户明确否决的方案（不要再提）

| ❌ 否决 | 原因（用户原话） |
| --------- | ----------------- |
| Script Filter + 关键字 + 参数 | "你这个脚本只能通过关键字，先输入关键字，然后空格，然后再输入参数。你这不是闹呢吗" |
| Fallback Search（两步） | "搜索 WiFi，它出来的是 system system 然后跟着 WiFi，我需要回车才能看到真正的 WiFi，多此一举" |
| 快捷键 Hotkey | "我不要快捷键" |
| 中文/拼音搜索 | 未要求，不要自作主张加 |

**核心教训：用户要的是「输入设置名 → 直接打开」，任何需要第二个步骤的方案都是错的。**

---

## 开发流程约定（用户明确要求）

1. **只改源目录** `/Users/yitiansong/data/code/alfred/System Settings/`
2. **打包产物**：`python3 ~/.agents/skills/skills/alfred-workflow/scripts/package.py "System Settings"` → `Settings.alfredworkflow`
3. **绝对不要**直接编辑/同步安装目录 `~/data/sync/alfred/Alfred.alfredpreferences/workflows/user.workflow.*`（用户原话："你别在那个目录改了行吗"）
4. **绝对不要**重启 Alfred、不要用 `open` 触发导入覆盖（用户原话："别再帮我重启覆盖了"）
5. Alfred 会 ~15-20s 自动加载 workflow 文件变化，**让用户自己导入、自己重启**
6. 打包前清理 `.ruff_cache` 等垃圾文件

### 标准操作流程（每次改完代码必做，按顺序执行）

1. **改源目录**：只修改 `/Users/yitiansong/data/code/alfred/System Settings/` 下的文件
   （info.plist、图标 png 等；如新增/删除 keyword 对象，同步增删对应 `<对象UID>.png`）
2. **校验 plist**：`plutil -lint 'System Settings/info.plist'` 确认无语法错误
3. **清理垃圾**：删除源目录里的 `.ruff_cache`、`.DS_Store` 等（`rm -rf 'System Settings/.ruff_cache'`）
4. **重新打包**：

   ```bash
   cd /Users/yitiansong/data/code/alfred
   python3 ~/.agents/skills/skills/alfred-workflow/scripts/package.py "System Settings"
   ```

   产物：`Settings.alfredworkflow`（覆盖旧包）
5. **验证打包内容**（防打包过期，曾踩过“源改了包没更新”的坑）：

   ```bash
   unzip -l Settings.alfredworkflow            # 文件数/图标数量正确
   unzip -p Settings.alfredworkflow info.plist | python3 -c "import sys,plistlib; pl=plistlib.loads(sys.stdin.buffer.read()); print(len(pl['objects']))"  # 对象数正确
   ```

   并对比包内 info.plist 与源目录 info.plist 的关键内容（keyword 列表、URL 列表）是否一致
6. **不动安装目录**：不复制到 `~/data/sync/alfred/.../user.workflow.*/`，不重启 Alfred，不用 `open` 触发导入
7. **告诉用户**：包已更新到 `Settings.alfredworkflow`，由用户自行双击导入验证

---

### 发布新版：让 Pulse 检测到更新的完整流程（通用，所有工作流）

Pulse（关键词 `update`）每次触发都**实时** curl 拉取
`raw.githubusercontent.com/<repo>/main/versions.json`，按 bundle id 扫描已装
工作流目录，比较版本：**manifest.version 严格大于已装 info.plist 的 version**
才算「可更新」。无 TTL 缓存；`cache.json`（Workflow Data 下）只在拉取失败时
兜底，**不需要手动清**。

发布顺序（每次发布新版必做）：

1. **升版本号**：改源 `info.plist` 的 `version`（生成式 plist 如 Glide，改
   `build_plist.py` 里的 `"version"` 再重新生成）。⚠️ 必须**严格递增**：同号
   修复（1.8.0 → 1.8.0）Pulse 不会检测到。格式随意（`1.8.0` / `v1.2.3-beta`），
   比较时数字按数值、字母按字典序、忽略前缀 v
2. **重新打包**：各工作流自己的 `./pack.sh`（需要重编引擎时 `./pack.sh --universal`）
3. **重新生成清单**：`bash scripts/gen-manifest.sh` —— 从源 info.plist 读
   name/bundleid/version，哈希根目录 `.alfredworkflow` 写 sha256，输出
   `versions.json`（缺失的包打印 SKIP 跳过）
4. **提交 + 推送**：工作流改动与 `versions.json` 一起 commit 并 push 到 main。
   ⚠️ **不 push 就永远检测不到**（Pulse 只认 main 分支的 raw 地址）

用户侧：**无需任何操作**，重新输 `update` 即实时生效；唯一延迟是 GitHub raw
CDN 缓存（push 后通常几十秒内）。替换导入后已装版本 = manifest 版本，
`update` 自动显示「已最新」。

---

## Alfred 5.7.3 实测 ground truth（血泪经验）

### Script Filter `argumenttype` 枚举（与直觉相反！）

| 值 | 含义 | 后果 |
| ---- | ------ | ------ |
| `0` | Argument **Required**（必需参数） | 无输入不显示列表 |
| `1` | Argument **Optional**（可选参数） | 边输入边过滤 ✅ |
| `2` | **No Argument**（无参数） | **脚本只跑一次，后续输入全被忽略** ← 大坑 |

> 曾把 `argumenttype=2` 当"可选参数"用，导致"输入 wifi 没反应"——用户手动改成 1 后好了，又被我改回 2 改坏了。**永远记住：2 = 忽略输入。**

### `withspace`

- `true`：keyword 后必须有空格才运行
- `false` + argumenttype=1：常驻列表，但 query 可能带**前导空格**，脚本必须 `strip()`

### Fallback Search（用户已否决此方案，但机制要知道）

- fallback 必须在 Alfred UI 的 **Features → Default Results → "Setup fallback results"** 里添加，**光写 prefs.plist 无效**
- Alfred 自己写入的注册格式是**字符串**：`user.workflow.<工作流目录UID>.<对象UID>`（不是 dict）
- 触发器对象类型：`alfred.workflow.trigger.fallback`，config 只有 `text`（可含 `{query}`）
- 触发条件：默认结果（应用/文件/联系人）**无匹配**时才触发

### keyword 对象图标

- 对象图标 = workflow 目录下 `<对象UID>.png` 文件，Alfred 自动使用
- 从系统扩展提取图标：**swift + NSWorkspace**（pyobjc 不可用；JXA 的 NSData 写入方法会报错）
- 提取脚本参考：`/tmp/extract_icon.swift`（icon(forFile:) → tiffRepresentation → NSBitmapImageRep → PNG），再用 `sips -Z 256` 缩放
- 图标源：`/System/Library/ExtensionKit/Extensions/<扩展>.appex`（对应面板的 Settings 扩展）

### 其他坑

- 导入 `.alfredworkflow` 会丢失脚本可执行权限（chmod +x 需重设）
- 重新导入**不会覆盖**安装目录已有脚本文件——改完脚本要显式同步
- keyword 对象 config 参考（Vítor 版实测）：`{argumenttype: 2, keyword: "...", skipuniversalaction: true, subtext: "...", text: "...", withspace: false}`，version 1
- Arg&Vars config：`{argument: "x-apple.systempreferences:<pane_id>", passthroughargument: false, variables: {}}`
- Open URL config：`{browser: "", skipqueryencode: false, skipvarencode: false, spaces: "", url: ""}`（url 留空 = 用传入的 argument）

---

## 常用设置面板 ID 速查

```text
Wi‑Fi:      com.apple.wifi-settings-extension
Battery:    com.apple.Battery-Settings.extension*BatteryPreferences
Bluetooth:  com.apple.BluetoothSettings
Login Items: com.apple.LoginItems-Settings.extension
Sound:      com.apple.Sound-Settings.extension
Displays:   com.apple.Displays-Settings.extension
Keyboard:   com.apple.Keyboard-Settings.extension
Trackpad:   com.apple.Trackpad-Settings.extension
Network:    com.apple.Network-Settings.extension
Privacy:    com.apple.settings.PrivacySecurity.extension
Notifications: com.apple.Notifications-Settings.extension
General:    com.apple.systempreferences.GeneralSettings
Wallpaper:  com.apple.Wallpaper-Settings.extension
Screen Time: com.apple.Screen-Time-Settings.extension
Users:      com.apple.Users-Groups-Settings.extension
Lock Screen: com.apple.Lock-Screen-Settings.extension
Time Machine: com.apple.Time-Machine-Settings.extension
Startup Disk: com.apple.Startup-Disk-Settings.extension
```

完整 43 面板列表在 `System Settings/info.plist` 里（keyword → Arg&Vars 连接）。

---

## 用户沟通风格提醒

- 用户要什么直接给什么，**不要解释太多，不要自创方案**
- 用户指出的问题就是问题，先承认再修，不要争辩
- 用户不喜欢反复导入/重启/覆盖——一次做对，让用户自己验证
- 发现方案方向可能错了时，先停下来问清楚，别埋头做完再被推翻

# application shortcuts · v2

在原始 "application shortcuts" 工作流基础上重做：**保留全部有效热键**，
删掉死节点，终端/浏览器改为**可配置**，并用 `app` 菜单消除黑盒。

## 和旧版（v1）的差异

| | v1（原始） | v2（本版） |
| --- | --- | --- |
| 画布 | 31 个对象，3 个未设置热键的死触发、2 个空 Launch、1 个孤儿脚本（Obsidian notebook）、1 个孤儿 Launch（kitty） | 22 个对象，按 AI / 终端 / 浏览器 / 聊天 / 笔记 / 开发 / 系统 / 查询分类排列，无死节点 |
| Hyper+2（终端） | 写死 iTerm | **Configure Workflow… 下拉框可选**：iTerm / kitty / Alacritty / WezTerm / Ghostty / Warp / Terminal |
| Hyper+B（浏览器） | 写死 Google Chrome | **下拉框可选**：Chrome / Safari / Arc / Edge / Firefox / Brave / Orion / Vivaldi |
| 查看映射 | 只能打开编辑器数 | 输入 `app`：列出每个快捷键对应的应用（终端/浏览器显示当前配置值），回车直接启动 |
| 行为 | Launch Apps/Files（toggle） | 保持不变：启动或切换（前台再按一次隐藏）；终端/浏览器由 launch.sh 实现同等 toggle |

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
> 想用 Hyper+3 之类的新键，在编辑器里复制任意热键块改键即可。

## 文件

- `build_plist.py` — 生成 `info.plist`（唯一事实来源）
- `launch.sh` — 终端/浏览器/`app` 菜单的共享启动脚本（launch-or-toggle）
- `filter.py` — `app` 关键词的脚本过滤器（只列已配置项，不搜索全部应用）
- `pack.sh` — 打包 `Application Shortcuts.alfredworkflow`

## 发布

```bash
./pack.sh   # 生成 info.plist + 打包 + 校验
```

导入时 bundle id 与旧工作流相同（`com.srq.application`），Alfred 会直接替换。
注意：**导入前先删除已安装的 App Launcher 工作流**（它注册了同样的 Hyper
热键，会导致按键冲突）。

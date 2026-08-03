# AGENTS.md — 本仓库的 agent 工作规则

## 绝对禁止：不要修改 Alfred 的同步目录

- **`~/data/sync/alfred/` 下的一切文件都不可改动**（包括
  `Alfred.alfredpreferences/workflows/` 里的任何工作流目录）。
- 那是 Alfred 管理的活跃工作流位置，直接改会被 Alfred 覆盖、产生
  用户无法追踪的差异，并且绕过了正常的导入流程。
- 工作流**源码**只存在于本仓库（`Glide/`、`PiHop/` 等目录），是唯一的
  source of truth。

## 正确的发布/更新流程

1. 修改仓库内的工作流源码（`info.plist`、脚本、图标等）。
2. 打包：`zip` 或仓库内自带的 `pack.sh`，生成 `.alfredworkflow` 到仓库根目录。
3. **交付给用户自行双击导入**，或推送后由用户下载导入。
4. 永远不要为了"让 Alfred 立即生效"而去拷贝文件进同步目录。

## 其他规则

- 根目录的 `*.alfredworkflow` 是打包产物，随源码一起提交。
- `prefs.plist`（用户配置）永不提交（已在 .gitignore）。
- 未完成/不属于当前任务的工作流改动（如 Homebrew Manager、
  netease-music-controls、Settings、System Settings 的历史改动）不要混入
  当前任务的提交。

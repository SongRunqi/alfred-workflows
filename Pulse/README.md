# Pulse

给 Alfred 工作流**号脉**：检查仓库里**已安装**的工作流有没有新版本，有就
下载、校验并交给 Alfred 导入替换。关键词 `update`，热键 Hyper+U。

## 用法

| 操作 | 效果 |
| --- | --- |
| `update` | 输入即见列表（读缓存秒开），边输入边过滤 |
| 列表里回车 | 下载 → sha256 校验 → `open -a "Alfred 5"` → 弹窗点「替换」 |
| ⌘回车 | 仅下载，不导入 |
| `↻ 重新检查` | 强制联网刷新（缓存超 10 分钟才自动联网） |
| `全部更新` | 逐个下载并交给 Alfred 确认 |
| Hyper+U | 静默检查 → 通知摘要 |

## 设计要点

- **缓存秒开**：列表打开直接读本地缓存，不联网；缓存超过 10 分钟
  （或点「↻ 重新检查」）才拉取清单，避免每次输入都等网络。
- **只检查已安装的工作流**：本机按 bundle id 扫描 Alfred 工作流目录，
  与仓库 `versions.json` 清单取交集。未安装的不出现——更新是更新，
  搜索是搜索（装应用是 `app` / 搜索的活）。
- **安装走 Alfred 官方导入流程**（方案 A）：Pulse 绝不写 Alfred 的
  工作流目录；每次更新在 Alfred 弹窗确认一次「替换」，prefs.plist
  用户配置由 Alfred 保留。
- **清单驱动**：仓库根目录 `versions.json`（`scripts/package-all.sh`
  打包时自动生成并随提交进 main）：

  ```json
  {"repo": "SongRunqi/alfred-workflows", "branch": "main", "updated": "…",
   "workflows": [{"name": "PiHop", "bundleid": "com.yt.pi-agent",
     "version": "1.1.1", "file": "PiHop.alfredworkflow",
     "sha256": "…", "url": "https://raw.githubusercontent.com/…"}]}
  ```

  Pulse 只下载这一个几百字节的 JSON，对比版本，只对"有更新"的下载 zip
  并校验 sha256。
- **可迁移**：Configure Workflow… 的 `PULSE_REPO` / `PULSE_BRANCH`（或
  Workflow Data 的 `config.json`）可指向任何仓库——只要对方提供同格式
  的 `versions.json`。将来要单开仓库/开源，搬走本目录改一行配置即可。
- **自更新**：Pulse 自己也进清单，新版发布后在 `update` 里同样出现。

## 文件

- `pulse.py` — 核心：扫描已安装 / 拉清单 / 版本比较 / 过滤器 JSON /
  通知 / 下载校验导入
- `filter.sh` — `pulselist` 列表入口（完整更新列表，经 go-list 外部触发器进入）
- `update.sh` — 更新入口（`name|url|sha256` / `all` / `dl|…`）
- `notify.sh` — Hyper+U 入口（静默检查 → 通知）
- `build_plist.py` / `make_icon.py` / `pack.sh` — 构建与打包

## 发布

```bash
./pack.sh            # 生成 info.plist/icon.png + 打包 Pulse.alfredworkflow
scripts/package-all.sh   # 全量打包（含 Pulse），并生成根目录 versions.json
```

注意：`versions.json` 要随提交进 main（Pulse 从 raw.githubusercontent 拉取），
CI 的 release.yml 打包步骤同样会生成它。

## 测试

```bash
PULSE_MANIFEST_URL=file:///tmp/versions.json PULSE_SCAN_DIRS=/tmp/fakewf \
  PULSE_DATA=/tmp/pulse-test ./pulse.py filter   # 本地清单 + 假安装目录
PULSE_DRY=1 ./pulse.py update all                # dry：只打印动作
```

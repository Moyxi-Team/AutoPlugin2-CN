# AutoPlugin II 国内网络补丁（防覆盖版）

让 **AutoPlugin II（AP2）2.20** 在中国大陆网络环境下能正常加载在线插件列表、正常下载插件，并且**不会被 AP2 自带的在线更新还原**。

- 上游项目（Upstream）：AutoPlugin II 2.20，作者 TheHeroeGAC / ONElua
- 补丁版本：v2（2026-11-24）
- 安装包：见 [Releases](https://github.com/Moyxi-Team/AutoPlugin2-CN/releases) 中的 `AutoPlugin2_2.20_CN_v2.vpk`

> 本项目仅为网络层补丁，不含对 AP2 功能逻辑的改动，不收集任何数据。

---

## 一、为什么需要这个补丁

AP2 的在线列表、插件下载、脚本更新全部硬编码指向 `raw.githubusercontent.com` / `github.com`，且**没有自定义源（custom source）设置**，国内网络下基本都是空列表或一直转圈。

更麻烦的是：AP2 打开"在线插件列表"时会做三件事，会把任何静态改动顶掉。

| 序号 | AP2 的行为 | 只改文本的后果 |
|---|---|---|
| 1 | 下载 `scripts/psvita/autoplugin.lua`，`files.move` 覆盖本地后 `dofile` 加载 | 已镜像化的脚本被官方原版顶掉 |
| 2 | 下载 `plugins/plugins.lua`，`files.move` 覆盖本地 | 大量已镜像的 URL 被还原 |
| 3 | 上述文件同样来自 `raw.githubusercontent.com` | 网络一断，更新逻辑本身也跑不动 |

所以只做 URL 替换（v1 方案）没用，触发一次在线更新就回到原样。v2 解决的就是这个"被还原"问题。

## 二、v2 的三层设计

```text
L1 静态镜像    18 个 lua、190 处 GitHub URL 统一前置 https://gh-proxy.com/
L2 运行时 Hook  script.lua 最前端劫持 http.get / http.download，出口统一改写
L3 覆盖拦截     plugins_online.lua 中两处 files.move 覆盖动作全部改道
```

### L1 静态镜像

遍历 AP2 内部全部 `*.lua`，把 `https://raw.githubusercontent.com/`、`https://github.com/`、`https://api.github.com/`、`https://objects.githubusercontent.com/`、`https://codeload.github.com/` 开头的 URL 统一前置镜像前缀，形如：

```text
https://gh-proxy.com/https://raw.githubusercontent.com/xxx/yyy/main/zzz.lua
```

已带前缀的不会二次叠加。

### L2 运行时 Hook（核心）

注入位置：`script.lua` 第 23 行，**早于** `dofile("git/shared.lua")` 与所有业务脚本加载。

```lua
if not __CN_MIRROR_HOOK then
    __CN_MIRROR_HOOK = true
    local __MIRROR = "https://gh-proxy.com/"
    local __PFX = { "https://raw.githubusercontent.com/", "https://github.com/", ... }
    -- 包装 http.get / http.download：命中 GitHub 域名 → 前置镜像；其他域名原样放行
end
```

特性：

- 整个 AP2 进程内**所有** http 出站请求都会经过这一层，包括官方后来下载的新脚本里写死的原始域名；
- 已带镜像前缀的 URL 不叠加；
- `devdavisnunez.x10.mx` 等非 GitHub 域名不动；
- 整段包在 `pcall` 内，即使掌机环境的 `http` 表不可写，也不会导致 AP2 启动失败（此时退化为 L1 + L3）。

### L3 覆盖动作改道

`scripts/psvita/plugins_online.lua` 第 219 / 238 行：

| 原行为 | v2 行为 |
|---|---|
| `files.move(tmp, "scripts/psvita/")` 覆盖 `autoplugin.lua` | 改为 `files.delete(tmp)`：官方下载内容直接丢弃，继续 `dofile` 本地已镜像化脚本 |
| `files.move(tmp, "plugins/")` 覆盖 `plugins.lua` | 改为写入 `plugins/plugins_online_cache.lua` 并加载该缓存，`plugins/plugins.lua` 本体永不被动 |

效果：在线更新只更新"在线列表数据"，不再触碰任何已打补丁的脚本。

## 三、安装

### 方式 A：整包覆盖安装（推荐）

1. 把 `AutoPlugin2_2.20_CN_v2.vpk` 拷到记忆卡任意目录；
2. VitaShell 里选中安装，装到与原 AP2 相同的分区（原装 `ux0` 就装 `ux0`，原装 `ur0` 就装 `ur0`）；
3. 覆盖安装会保留 `ux0:data/AUTOPLUGIN2/` 下的配置与插件备份。

### 方式 B：FTP 手工覆盖（不重装）

1. 先确认 AP2 的安装位置：`ux0:app/AUTOPLUG2/` 或 `ur0:app/AUTOPLUG2/`。VitaShell 的 FTP 路径要写绝对形式：`/ux0:/app/AUTOPLUG2/`；
2. 把本仓库 `lua/` 目录下 18 个 lua 按同名相对路径覆盖进去，其中**必改的两个**：
   - `script.lua`（L2 Hook）
   - `scripts/psvita/plugins_online.lua`（L3 改道 + URL 镜像）
3. 其余 16 个是纯 URL 镜像文件，一并覆盖更彻底。

## 四、验证是否生效

1. 打开 AP2 → 进"在线插件"列表，能刷出列表即 L1 / L2 生效；
2. 进设置手动触发一次在线更新，退出重进，列表仍能刷新 → L3 生效；
3. FTP 查看 `ux0:app/AUTOPLUG2/scripts/psvita/autoplugin.lua` 的修改时间未被刷新 → 覆盖拦截生效；
4. 若第 1 步失败，说明镜像本身不可用，见下节换镜像重打。

## 五、边界与注意事项

| 场景 | 结果 |
|---|---|
| 在线列表 / 在线脚本更新（本文讨论的覆盖） | 已拦截，补丁不会被还原 |
| AP2 提示"本体有新版本"并执行升级 | 会整体替换 `app/AUTOPLUG2/`，补丁全部失效。升级后需用本补丁包重打；建议先在设置里关掉自动更新 |
| 在线语言包更新 | 只替换 `lang/` 文本，不含网络逻辑，不影响补丁 |
| 免费镜像关停 | 改 `tools/build_patch_v2.py` 顶部的 `MIRROR` 常量重新打包；或直接改 L2 Hook 里的 `__MIRROR` 字符串 |
| 掌机 TLS 兼容性 | 装后列表仍加载失败时，可用整机 Wi-Fi 代理指向电脑上的代理端口作为保底方案 |

**关于镜像可用性**：`gh-proxy.com`、`ghproxy.net` 在编写时可用；`ghfast.top`、`raw.gitmirror.com`、`cdn.jsdelivr.net` 实测直连不通。免费镜像随时可能关停，失效时按上表换前缀即可。

## 六、仓库结构

```text
.
├── lua/                     # 18 个已改写 lua，按 AP2 内部路径组织（FTP 覆盖用）
├── tools/
│   ├── build_patch_v2.py    # 可复现的 v2 构建脚本（含 L1/L2/L3），换镜像只改 MIRROR
│   └── patch_autoplugin2.py # v1 脚本（仅 L1 静态镜像，留作参考）
├── docs/
│   └── 补丁说明_v2防覆盖.md   # 详细技术说明与验证清单
└── README.md
```

## 七、自行构建

```bash
# 需要一份官方 AutoPlugin2 2.20 的 VPK 作为输入
python tools/build_patch_v2.py \
  --input  AutoPlugin2_2.20.vpk \
  --output AutoPlugin2_2.20_CN_v2.vpk \
  --lua-out lua/
```

脚本会解包 → 改写 lua → 按原条目的压缩类型与目录结构重打包 → 校验 zip 完整性。

## 八、出处与许可

- 原始程序 AutoPlugin II 由 **TheHeroeGAC** 开发，**Gdljjrod / DevDavisNunez** 设计，`script.lua` 头部声明遵循 **CC BY-SA 4.0**；
- 本项目为衍生补丁，同样遵循 **CC BY-SA 4.0**，版权归原作者所有，仅供个人自用与学习交流；
- 若上游作者认为不妥，请提 Issue，会立即下架。

## 九、免责声明

刷机、安装自制软件存在风险，请自行评估。因使用本补丁造成的设备异常、数据丢失，作者不承担责任。请支持原作者，有能力请访问上游项目。

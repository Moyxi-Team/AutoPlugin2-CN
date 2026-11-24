# -*- coding: utf-8 -*-
"""AutoPlugin II 国内网络补丁 v2 构建脚本

三层结构：
    L1 静态镜像   把内部全部 *.lua 中的 GitHub 域名 URL 前置镜像前缀
    L2 运行时Hook script.lua 最前端劫持 http.get / http.download，出口统一改写
    L3 覆盖拦截   plugins_online.lua 中官方"下载后覆盖本地脚本"的动作全部改道

用法：
    python build_patch_v2.py -i AutoPlugin2_2.20.vpk -o out/
    python build_patch_v2.py -i AP2.vpk -o out/ -m https://ghproxy.net/

注意：输入必须是官方 AutoPlugin II 2.20 的原始 VPK。
"""
import argparse
import os
import re
import zipfile

DEFAULT_MIRROR = "https://gh-proxy.com/"

HOSTPAT = re.compile(
    r'https?://(raw\.githubusercontent\.com|github\.com|api\.github\.com|'
    r'objects\.githubusercontent\.com|codeload\.github\.com)/'
)

HOOK = '''
--==== [CN-MIRROR-HOOK v2] 国内镜像自愈层：官方在线更新覆盖脚本后依然生效 ====
if not __CN_MIRROR_HOOK then
\t__CN_MIRROR_HOOK = true
\tlocal __MIRROR = "%(mirror)s"
\tlocal __PFX = {
\t\t"https://raw.githubusercontent.com/",
\t\t"https://github.com/",
\t\t"https://api.github.com/",
\t\t"https://objects.githubusercontent.com/",
\t\t"https://codeload.github.com/",
\t}
\tlocal function __cn_mirror_url(u)
\t\tif type(u) ~= "string" then return u end
\t\tif string.sub(u, 1, #__MIRROR) == __MIRROR then return u end
\t\tfor i = 1, #__PFX do
\t\t\tlocal p = __PFX[i]
\t\t\tif string.sub(u, 1, #p) == p then return __MIRROR .. u end
\t\tend
\t\treturn u
\tend
\tpcall(function()
\t\tif type(http) == "table" then
\t\t\tlocal _hget, _hdl = http.get, http.download
\t\t\tif _hget then http.get = function(u, ...) return _hget(__cn_mirror_url(u), ...) end end
\t\t\tif _hdl then http.download = function(u, ...) return _hdl(__cn_mirror_url(u), ...) end end
\t\tend
\tend)
end
--==== [/CN-MIRROR-HOOK v2] ====
'''

# L3：覆盖动作改道
REDIRECTS = [
    ('files.move(tmpdir.."autoplugin.lua","scripts/psvita/")',
     'files.delete(tmpdir.."autoplugin.lua")--CN: discard upstream download, keep local mirrored script'),
    ('dofile("scripts/psvita/autoplugin.lua")--Official',
     'dofile("scripts/psvita/autoplugin.lua")--LOCKED: always load local mirrored script'),
    ('files.move(tmpdir.."plugins.lua","plugins/")',
     'files.move(tmpdir.."plugins.lua","plugins/plugins_online_cache.lua")--CN: never overwrite plugins/plugins.lua'),
    ('dofile("plugins/plugins.lua")--Official',
     'dofile("plugins/plugins_online_cache.lua")--CN: load cached online list'),
]


def build(src, outdir, mirror, luadir=None):
    z = zipfile.ZipFile(src)
    files = {}
    log = []

    for it in z.infolist():
        if it.is_dir():
            continue
        files[it.filename] = z.read(it.filename)

    # ---- L1 静态 URL 镜像 ----
    n1 = 0
    for name in list(files):
        if not name.endswith(".lua"):
            continue
        try:
            txt = files[name].decode("utf-8")
        except UnicodeDecodeError:
            continue
        new, n = HOSTPAT.subn(lambda m: mirror + "https://" + m.group(1) + "/", txt)
        if n:
            files[name] = new.encode("utf-8")
            n1 += n
            log.append("L1 %-45s %d" % (name, n))

    # ---- L2 注入 hook ----
    s = files["script.lua"].decode("utf-8")
    anchor = 'dofile("git/shared.lua")'
    assert s.count(anchor) == 1, "anchor count %d" % s.count(anchor)
    s = s.replace(anchor, HOOK % {"mirror": mirror} + "\n" + anchor, 1)
    files["script.lua"] = s.encode("utf-8")
    log.append("L2 script.lua hook injected")

    # ---- L3 覆盖改道 ----
    po = files["scripts/psvita/plugins_online.lua"].decode("utf-8")
    for old, new in REDIRECTS:
        c = po.count(old)
        assert c == 1, "redirect pattern %r count=%d" % (old, c)
        po = po.replace(old, new, 1)
        log.append("L3 plugins_online.lua redirect: %s" % old[:40])
    files["scripts/psvita/plugins_online.lua"] = po.encode("utf-8")

    # ---- 指纹自检 ----
    for name in files:
        if name.endswith(".lua"):
            t = files[name].decode("utf-8", "ignore")
            assert "gh-proxy.com/https://gh-proxy.com" not in t, name
    assert "__CN_MIRROR_HOOK" in files["script.lua"].decode("utf-8")

    # ---- 重打包（保留原条目顺序、压缩类型、时间戳与属性）----
    os.makedirs(outdir, exist_ok=True)
    outvpk = os.path.join(outdir, "AutoPlugin2_2.20_CN_v2.vpk")
    with zipfile.ZipFile(outvpk, "w", zipfile.ZIP_DEFLATED) as zo:
        for it in z.infolist():
            zi = zipfile.ZipInfo(it.filename, date_time=it.date_time)
            zi.compress_type = it.compress_type
            zi.external_attr = it.external_attr
            zo.writestr(zi, b"" if it.is_dir() else files[it.filename])
    assert zipfile.ZipFile(outvpk).testzip() is None

    # ---- 导出改写后的 lua（按 AP2 内部路径）----
    if luadir:
        n = 0
        for name, data in files.items():
            if not name.endswith(".lua"):
                continue
            t = data.decode("utf-8", "ignore")
            if "gh-proxy.com" not in t and "__CN_MIRROR_HOOK" not in t:
                continue
            dst = os.path.join(luadir, *name.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "wb").write(data)
            n += 1

    print("\n".join(log))
    print("L1 total urls:", n1)
    print("vpk:", outvpk, os.path.getsize(outvpk))
    return outvpk


def main():
    ap = argparse.ArgumentParser(description="AutoPlugin II 2.20 国内网络补丁 v2 构建器")
    ap.add_argument("-i", "--input", required=True, help="官方 AutoPlugin2 2.20 原始 VPK")
    ap.add_argument("-o", "--output", default="dist", help="输出目录")
    ap.add_argument("-m", "--mirror", default=DEFAULT_MIRROR, help="镜像前缀，默认 " + DEFAULT_MIRROR)
    ap.add_argument("-l", "--lua-out", dest="lua_out", default=None, help="可选：导出改写后 lua 的目录")
    a = ap.parse_args()

    mirror = a.mirror
    if not mirror.endswith("/"):
        mirror += "/"

    build(a.input, a.output, mirror, a.lua_out)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
AutoPlugin II 国内网络镜像补丁工具
作用：把 VPK 内所有 lua 脚本中的 GitHub 域名前置到国内可用镜像前缀，
      使 AP2 的“在线插件列表 / 插件下载 / README 描述 / release 下载”走镜像。

用法示例：
  python patch_autoplugin2.py -i AutoPlugin2_2.20.vpk -o AutoPlugin2_2.20_CN.vpk
  python patch_autoplugin2.py -i AutoPlugin2_2.20.vpk --mirror https://ghproxy.net/
  python patch_autoplugin2.py -i AutoPlugin2_2.20.vpk --verify

镜像候选（2026-11 实测，直连/无VPN）：
  https://gh-proxy.com/    可用  ← 默认
  https://ghproxy.net/     可用
  https://ghfast.top/      直连不通
  raw.gitmirror.com        直连不通
"""
import argparse, os, re, sys, zipfile

HOSTPAT = re.compile(
    r'https?://(raw\.githubusercontent\.com|github\.com|api\.github\.com|'
    r'objects\.githubusercontent\.com|codeload\.github\.com)/'
)

def patch_text(text, mirror):
    """一次性替换，避免二次叠加前缀"""
    new, n = HOSTPAT.subn(lambda m: mirror + "https://" + m.group(1) + "/", text)
    return new, n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True, help="原始 VPK 路径")
    ap.add_argument("-o", "--output", default=None, help="输出 VPK 路径")
    ap.add_argument("-m", "--mirror", default="https://gh-proxy.com/", help="镜像前缀，需以 / 结尾")
    ap.add_argument("--lua-dir", default=None, help="同时导出改好的 lua 文件到该目录（供 FTP 覆盖）")
    ap.add_argument("--verify", action="store_true", help="仅统计将替换的数量，不写文件")
    a = ap.parse_args()

    mirror = a.mirror if a.mirror.endswith("/") else a.mirror + "/"
    src = a.input
    z = zipfile.ZipFile(src)
    changed, total = {}, 0

    for it in z.infolist():
        if not it.filename.endswith(".lua"):
            continue
        try:
            txt = z.read(it.filename).decode("utf-8")
        except UnicodeDecodeError:
            continue
        new, n = patch_text(txt, mirror)
        if n:
            changed[it.filename] = new.encode("utf-8")
            total += n
            print("[patch] %-45s %d 处" % (it.filename, n))

    print("共 %d 个文件，%d 处 URL" % (len(changed), total))
    if a.verify:
        return

    out = a.output or os.path.splitext(src)[0] + "_CN.vpk"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
        for it in z.infolist():
            data = changed.get(it.filename) or (b"" if it.is_dir() else z.read(it.filename))
            zi = zipfile.ZipInfo(it.filename, date_time=it.date_time)
            zi.compress_type = it.compress_type
            zi.external_attr = it.external_attr
            zo.writestr(zi, data)
    z.close()
    print("已输出 VPK: %s (%d 字节)" % (out, os.path.getsize(out)))
    assert zipfile.ZipFile(out).testzip() is None
    print("zip 完整性校验通过")

    if a.lua_dir:
        for f, b in changed.items():
            dst = os.path.join(a.lua_dir, *f.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as fh:
                fh.write(b)
        print("已导出 %d 个 lua 到 %s" % (len(changed), a.lua_dir))

if __name__ == "__main__":
    main()

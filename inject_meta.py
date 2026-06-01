"""
inject_meta.py
==============
在 Streamlit 啟動前執行，把社群分享預覽(OG meta tags)注入 Streamlit 的 index.html。
重點：用 streamlit 套件本身的位置動態找 index.html，不寫死路徑（寫死路徑在 Render 上會找不到）。

在 render.yaml 的 startCommand 改成先跑這支再啟動：
  python inject_meta.py && streamlit run wealth.py --server.port $PORT ...
"""

import os

# 你想顯示在分享卡片上的標題與描述（可自行修改）
CUSTOM_META = """
    <title>小資族理財 App - By Noreen</title>
    <meta name="description" content="專為個人量身打造的資產管理與台美股投資觀測工具，助你精準規劃財務進度。" />
    <meta property="og:title" content="小資族理財 App - By Noreen" />
    <meta property="og:description" content="專為個人量身打造的資產管理與台美股投資觀測工具，助你精準規劃財務進度。" />
    <meta property="og:type" content="website" />
    <meta name="twitter:card" content="summary" />
    <meta name="twitter:title" content="小資族理財 App - By Noreen" />
    <meta name="twitter:description" content="個人化資產管理與台美股投資觀測工具。" />
"""


def find_index_html():
    """動態定位 Streamlit 的 index.html，不寫死路徑。"""
    try:
        import streamlit
        p = os.path.join(os.path.dirname(streamlit.__file__), "static", "index.html")
        if os.path.exists(p):
            return p
    except Exception as e:
        print(f"[inject_meta] 透過 streamlit 套件定位失敗: {e}")
    # 後備：在常見的 site-packages 路徑下搜尋
    import glob
    for pattern in [
        "/opt/render/**/site-packages/streamlit/static/index.html",
        "/usr/**/site-packages/streamlit/static/index.html",
        os.path.expanduser("~") + "/**/site-packages/streamlit/static/index.html",
    ]:
        hits = glob.glob(pattern, recursive=True)
        if hits:
            return hits[0]
    return None


def main():
    path = find_index_html()
    if not path:
        print("[inject_meta] ❌ 找不到 Streamlit 的 index.html，跳過注入（App 仍可正常啟動）")
        return

    print(f"[inject_meta] 找到 index.html: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
    except Exception as e:
        print(f"[inject_meta] ❌ 讀取失敗: {e}")
        return

    if "og:title" in html:
        print("[inject_meta] ✓ 已注入過，略過")
        return

    # 移除原本的 <title>Streamlit</title>，再把自訂 meta 插進 <head>
    import re
    html = re.sub(r"<title>.*?</title>", "", html, count=1, flags=re.IGNORECASE | re.DOTALL)
    if "<head>" in html:
        html = html.replace("<head>", "<head>" + CUSTOM_META, 1)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            print("[inject_meta] ✅ 成功注入自訂 meta tags！")
        except Exception as e:
            print(f"[inject_meta] ❌ 寫入失敗（可能是唯讀檔案系統）: {e}")
    else:
        print("[inject_meta] ❌ index.html 裡找不到 <head>，跳過")


if __name__ == "__main__":
    main()

import os

# 找到 Streamlit 在雲端伺服器上的 index.html 實體路徑
st_path = os.path.dirname(os.__file__) + "/site-packages/streamlit/static/index.html"
if not os.path.exists(st_path):
    # 預備路徑（依據不同虛擬環境可能有所不同）
    st_path = "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/static/index.html"

if os.path.exists(st_path):
    with open(st_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 定義你想自訂的標題與敘述
    custom_meta = """
    <title>小資族理財 App ── Noreen 專屬訂製版</title>
    <meta property="og:title" content="小資族理財 App ── Noreen 專屬訂製版" />
    <meta property="og:description" content="專為個人量身打造的資產管理與台美股投資觀測工具，助你精準規劃財務進度。" />
    <meta property="og:type" content="website" />
    """
    
    # 將自訂的標籤強行注入到 HTML 的 <head> 之中
    if "<head>" in html and "og:title" not in html:
        html = html.replace("<head>", f"<head>{custom_meta}")
        with open(st_path, "w", encoding="utf-8") as f:
            f.write(html)
        print("Successfully injected custom meta tags!")

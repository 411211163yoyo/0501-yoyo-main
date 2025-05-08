import json
import requests
from bs4 import BeautifulSoup

import firebase_admin
from firebase_admin import credentials, firestore
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

from flask import Flask, render_template, request,make_response, jsonify
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

@app.route("/")
def index():
    homepage = "<h1>周攸晨Python網頁(時間+8)片名片長1</h1>"
    homepage += "<a href=/mis>MIS</a><br>"
    homepage += "<a href=/today>顯示日期時間</a><br>"
    homepage += "<a href=/welcome?nick=Yoyo&work=pu>傳送使用者暱稱</a><br>"
    homepage += "<a href=/account>網頁表單傳值</a><br>"
    homepage += "<a href=/about>簡介網頁</a><br>"
    homepage += "<br><a href=/read>讀取Firestore資料</a><br>"
    homepage += "<br><a href=/spider>爬取開演即將上映電影,存到資料庫</a><br>"
    homepage += "<br><a href=/Dispmovie>輸入關鍵字查詢電影</a><br>"
    homepage += "<br><a href=/accident>輸入關鍵字查詢114年2月台中十大易肇事路口</a><br>"
    homepage += "<br><a href=/webhook4>我的webhook</a><br>"
    return homepage

@app.route("/mis")
def course():
    return "<h1>資訊管理導論</h1>"

@app.route("/today")
def today():
    tz = timezone(timedelta(hours=+8))
    now = datetime.now(tz)
    return render_template("today.html", datetime=str(now))

@app.route("/about")
def me():
    return render_template("about.html")

@app.route("/welcome", methods=["GET"])
def welcome():
    user = request.values.get("nick")
    w = request.values.get("work")
    return render_template("welcome.html", name=user, work=w)

@app.route("/account", methods=["GET", "POST"])
def account():
    if request.method == "POST":
        user = request.form["user"]
        pwd = request.form["pwd"]
        result = "您輸入的帳號是：" + user + "; 密碼為：" + pwd
        return result
    else:
        return render_template("account.html")

@app.route("/read")
def read():
    Result = ""
    db = firestore.client()
    collection_ref = db.collection("靜宜資管")
    docs = collection_ref.order_by("mail").get()
    for doc in docs:
        Result += "文件內容：{}".format(doc.to_dict()) + "<br>"
    return Result

@app.route("/spider")
def spider():
    db = firestore.client()
    url = "http://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    result = sp.select(".filmListAllX li")

    for item in result:
        img = item.find("img")
        a = item.find("a")
        div = item.find(class_="runtime")

        if div.text.find("片長") > 0:
            FilmLen = div.text[21:]
        else:
            FilmLen = "無"

        doc = {
            "title": img.get("alt"),
            "hyperlink": "http://www.atmovies.com.tw" + a.get("href"),
            "picture": img.get("src"),
            "showDate": div.text[5:15],
            "ShowLength": FilmLen
        }

        doc_ref = db.collection("電影").document(a.get("href")[7:19])
        doc_ref.set(doc)

    return "資料庫已更新"

@app.route("/input", methods=["GET", "POST"])
def input():
    if request.method == "POST":
        keyword = request.form["MovieKeyword"]
        db = firestore.client()
        docs = db.collection("周攸晨").order_by("showDate").get()
        info = ""

        for item in docs:
            if keyword in item.to_dict()["title"]:
                info += "片名:<a href=" + item.to_dict()["hyperlink"] + ">" + item.to_dict()["title"] + "</a><br>"
                info += "介紹:" + item.to_dict()["hyperlink"] + "<br>"
                info += "海報:<img src=" + item.to_dict()["picture"] + "><br>"
                info += "片長:" + item.to_dict()["ShowLength"] + "<br>"
                info += "上映日期:" + item.to_dict()["showDate"] + "<br><br>"
        return info
    else:
        return render_template("movie.html")

# ✅ accident 已改：加上「查無資料」提示 + 顯示全部按鈕 + 隱藏功能
@app.route("/accident", methods=["GET", "POST"])
def accident():
    url = "https://datacenter.taichung.gov.tw/swagger/OpenData/1289c779-6efa-4e7c-bac8-aa6cbe84a58c"
    try:
        Data = requests.get(url, verify=False)
        JsonData = json.loads(Data.text)
    except Exception as e:
        return f"<h3>資料取得失敗：</h3>{str(e)}"

    keyword = ""
    info = ""
    result_html = ""
    found = False

    if request.method == "POST":
        keyword = request.form.get("RoadKeyword", "").strip()

        if keyword == "all":
            matched = JsonData
            info += f"<h2>📋 顯示所有事故路段：</h2><br>"
            found = True
        else:
            matched = [item for item in JsonData if keyword in item["路口名稱"]]
            if matched:
                info += f"<h2>🔍 查詢結果 - 包含「{keyword}」的路口：</h2><br>"
                found = True
            else:
                info += f"<h3>❌ 找不到包含「{keyword}」的路口</h3>"

        for item in matched:
            result_html += f"🚧 <b>事故路口：</b>{item['路口名稱']}<br>"
            result_html += f"📊 <b>發生件數：</b>{item['總件數']}<br>"
            result_html += f"💥 <b>主要肇因：</b>{item['主要肇因']}<br><br>"

    html = """
    <html>
    <head>
        <meta charset="utf-8">
        <title>台中事故路口查詢</title>
        <script>
            function toggleDisplay() {
                var resultDiv = document.getElementById("result");
                var btn = document.getElementById("toggleBtn");
                if (resultDiv.style.display === "none") {
                    resultDiv.style.display = "block";
                    btn.value = "👁️ 隱藏查詢結果";
                } else {
                    resultDiv.style.display = "none";
                    btn.value = "👁️ 顯示查詢結果";
                }
            }
        </script>
    </head>
    <body>
        <h1>🚦 台中市 114 年 2 月十大易肇事路口</h1>
        <form method='POST'>
            🔍 請輸入路口名稱關鍵字：<input type='text' name='RoadKeyword'>
            <input type='submit' value='查詢'>
        </form>

        <form method='POST' style='margin-top:10px;'>
            <input type='hidden' name='RoadKeyword' value='all'>
            <input type='submit' value='📋 顯示所有資料'>
        </form>
    """

    if info:
        html += """
        <br>
        <input type="button" id="toggleBtn" onclick="toggleDisplay()" value="👁️ 隱藏查詢結果">
        <div id="result" style="margin-top:10px;">
        """ + info + result_html + "</div>"

    html += "</body></html>"
    return html
@app.route("/rate")
def rate():
    url = "http://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    result=sp.select(".filmListAllX li")
    lastUpdate = sp.find(class_="smaller09").text[5:]

    for x in result:
        picture = x.find("img").get("src").replace(" ", "")
        title = x.find("img").get("alt")
        movie_id = x.find("div", class_="filmtitle").find("a").get("href").replace("/", "").replace("movie", "")
        hyperlink = "http://www.atmovies.com.tw" + x.find("a").get("href")

        t = x.find(class_="runtime").text
        showDate = t[5:15]

        showLength = ""
        if "片長" in t:
            t1 = t.find("片長")
            t2 = t.find("分")
            showLength = t[t1+3:t2]

        r = x.find(class_="runtime").find("img")
        rate = ""
        if r != None:
            rr = r.get("src").replace("/images/cer_", "").replace(".gif", "")
            if rr == "G":
                rate = "普遍級"
            elif rr == "P":
                rate = "保護級"
            elif rr == "F2":
                rate = "輔12級"
            elif rr == "F5":
                rate = "輔15級"
            else:
                rate = "限制級"

        doc = {
            "title": title,
            "picture": picture,
            "hyperlink": hyperlink,
            "showDate": showDate,
            "showLength": showLength,
            "rate": rate,
            "lastUpdate": lastUpdate
        }

        db = firestore.client()
        doc_ref = db.collection("電影含分級").document(movie_id)
        doc_ref.set(doc)
    return "近期上映電影已爬蟲及存檔完畢，網站最近更新日期為：" + lastUpdate

@app.route("/webhook4", methods=["POST"])
def webhook4():
    req = request.get_json(force=True)
    action =  req["queryResult"]["action"]
    if (action == "rateChoice"):

        rate = req.get("queryResult").get("parameters").get("rate")
        # 處理可能的輸入變化
        rate_mapping = {
            "普級": "普遍級", "普遍": "普遍級", "G級": "普遍級", "一般級": "普遍級",
            "護級": "保護級", "P級": "保護級",
            "輔12": "輔12級", "輔導12級": "輔12級", "輔導級": "輔12級", "F2級": "輔12級",
            "輔15": "輔15級", "輔導15級": "輔15級", "F5級": "輔15級",
            "限級": "限制級", "限制": "限制級", "R級": "限制級", "成人級": "限制級"
        }
        
        # 如果用戶輸入的是簡稱，轉換為完整名稱
        if rate in rate_mapping:
            rate = rate_mapping[rate]
            
        info = "您選擇的電影分級是:" + rate + ", 相關電影:\n"
        db = firestore.client()
        collection_ref = db.collection("電影含分級")
        docs = collection_ref.get()
        result = ""
        for doc in docs:
            dict = doc.to_dict()
            if rate in dict["rate"]:
                result += "片名:" + dict["title"] + "\n"
                result += "介紹:" + dict["hyperlink"] + "\n\n"

        if not result:
            info += "抱歉，查無此分級的電影"
        else:
            info += result


    elif (action == "MovieDetail"):
        question = req.get("queryResult").get("parameters").get("FilmQ")
        keyword = req.get("queryResult").get("parameters").get("any")
        info = "我是周攸晨開發的電影聊天機器人，您要查詢電影的" + question + "，關鍵字是：" + keyword + "\n\n"
    return make_response(jsonify({"fulfillmentText": info}))


if __name__ == "__main__":
    app.run(debug=True)
import os
from flask import Flask, request, redirect, url_for, send_from_directory, render_template
from werkzeug import secure_filename
import pymysql.cursors
import json
from watson_developer_cloud import VisualRecognitionV3
import requests

UPLOAD_FOLDER = 'static/images/'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)

# APIの設定
visual_recognition = VisualRecognitionV3(
    #The release date of the version of the API you want to use.
    '2018-03-19',
    iam_apikey='APIKEY')

# データベースに接続
connection = pymysql.connect(host='localhost',
     user='pi',
     password='raspberry',
     db='pi',
     charset='utf8',
     # Selectの結果をdictionary形式で受け取る
     cursorclass=pymysql.cursors.DictCursor)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

#画像解析
def analyze(fname):
    with open(fname, 'rb') as images_file:
        classes = visual_recognition.classify(
        images_file,
        threshold='0.6',
        classifier_ids=["CLASSIFIERID"]).get_result()
        #unicodeで返ってくるので、utf-8に変換する。
        result = json.dumps(classes, indent=2).encode('utf-8').decode('unicode_escape')
        #jsonを辞書型&リスト型にする
        result = json.loads(result)
        #認識結果のclass=認識・特定した物体の名前だけを抽出する。
        result = result['images'][0]['classifiers'][0]['classes'][0]['class']
    return result

# データベースを検索
def selectsql(name):
    with connection.cursor() as cursor:
        sql = "SELECT * FROM vegetable WHERE class=%s"
        cursor.execute(sql,name)
        #必要なカラムの内容だけ抽出 
        dbdata = cursor.fetchall()
        desc = dbdata[0]['description']
        return desc

#引数で指定した文字列を再生する
def talk(title, message, path="static/audio/"):
    audiofile = path+title+".wav"
    if not os.path.isfile(path+title+".wav"): # 既に音声ファイルがあるかどうかを確認する
        url = 'https://api.apigw.smt.docomo.ne.jp/crayon/v1/textToSpeech?APIKEY=YourAPIKEY'

        params = {
              "Command":"AP_Synth",
              "SpeakerID":"1",
              "StyleID":"1",
              "SpeechRate":"1.15",
              "AudioFileFormat":"2",
              "TextData":message
            }

        r = requests.post(url, data=json.dumps(params))
        if r.status_code == requests.codes.ok:
            wav = r.content
            with open(path+title+".wav","wb") as fout:
                fout.write(wav)
                return audiofile

    if os.path.isfile(path+title+".wav"): # APIでエラーが発生し、音声ファイルが生成されないときのため
        return audiofile

#メインルーチン
@app.route('/', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            img = UPLOAD_FOLDER + filename
            #img = filename
            print(filename)
            result = analyze(img)
            desc = selectsql(result)
            audiofile = talk(result, desc)
            return render_template('index.html', img=img, audiofile=audiofile, message=result, desc=desc) #変更
            #return redirect(url_for('uploaded_file', filename=filename))
    return '''
    <!doctype html>
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="http://code.jquery.com/jquery-1.11.1.min.js"></script>
    <link href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS" crossorigin="anonymous"></script>
    </head>
    <title>自己商品紹介</title>
    <h1>自己商品紹介</h1>
    <h3>Upload & Analyze new File</h3>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''


#@app.route('/<filename>')
#def uploaded_file(filename):
#    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)

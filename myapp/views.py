from django.shortcuts import render
import json
import random
from random import randrange
from urllib import request as url_request
from django.http import HttpResponse
from django.conf import settings
import logging

from django.template.defaulttags import do_if
from django.utils.lorem_ipsum import sentence

# settingsを使用してAPPIDを安全に取得
APPID = settings.YAHOO_APP_ID
URL = "https://jlp.yahooapis.jp/MAService/V2/parse"


def Analysis(request):
    """
    ユーザー入力を解析するためにYahooのMAService APIを呼び出す関数。
    :param request: DjangoのHTTPリクエストオブジェクト
    :return: APIのJSONレスポンスを辞書形式で返す
    """
    # フォームからユーザー入力を取得
    user_input = request.POST.get('text_input', '')

    # APIリクエストのヘッダーを設定
    headers = {
        "Content-Type": "application/json",
        "User-Agent": f"Yahoo AppID: {APPID}",
    }

    # APIリクエストのパラメータを設定
    param_dic = {
        "id": "1234-1",  # 任意のID
        "jsonrpc": "2.0",  # JSON-RPCのバージョン
        "method": "jlp.maservice.parse",  # メソッド名
        "params": {
            "q": user_input  # ユーザーの入力テキスト
        }
    }
    params = json.dumps(param_dic).encode()

    # APIリクエストを送信し、レスポンスを取得
    try:
        req = url_request.Request(URL, data=params, headers=headers)
        with url_request.urlopen(req) as res:
            body = res.read()

        # レスポンスをJSON形式にデコード
        response_text = body.decode()
        response_json = json.loads(response_text)
        return response_json
    except Exception as e:
        # エラー発生時にログを記録し、Noneを返す
        logging.error(f"APIリクエスト中のエラー: {e}")
        return None


class JsonHandler:
    """
    JSONレスポンスを処理しやすくするためのヘルパークラス。
    """

    def __init__(self, json_object):
        # トークン情報を初期化
        self.tokens = json_object.get("result", {}).get("tokens", [])

    def key(self, n):
        """
        トークンのn番目の要素を取得するヘルパーメソッド。
        :param n: トークンのインデックス
        :return: トークンのキー、または改行文字
        """
        if n < len(self.tokens):
            return self.tokens[n][0]
        return "\n"


def ModelGeneration(json_object):
    """
    マルコフ連鎖モデルを生成する関数。
    :param json_object: APIのJSONレスポンスオブジェクト
    :return: マルコフ連鎖モデルを辞書形式で返す
    """
    model = {}  # モデルを保持する辞書
    handler = JsonHandler(json_object)  # JsonHandlerクラスのインスタンスを作成

    n = 0
    while n < len(handler.tokens):
        word = handler.key(n)  # 現在のトークンのキーを取得
        if word == "\r":  # 改行の場合、次のトークンに進む
            n += 2
            continue

        # 次のトークンのキーを取得
        next_word = handler.key(n + 1)
        # モデルに現在の単語が無ければ追加する
        if word not in model:
            model[word] = {}

        # 次の単語が有効であればモデルに追加し、頻度をインクリメント
        if next_word and next_word != "\n":
            if next_word not in model[word]:
                model[word][next_word] = 0
            model[word][next_word] += 1

        n += 1  # 次のトークンに進む

    print(model)
    return model


def FindStart(json_object, num):#主語を探す
    noun = []
    for n in range(num):
        word = json_object["result"]["tokens"][n]
        if word[3] in "名詞" and word[4] in "普通名詞":
            noun.append(word[0])

    print(noun)
    return noun


def GenerationText(model, start):#続きを生成する
    #名詞の中から文頭を決める
    randam = randrange(len(start))
    sentence_start = start[randam]

    #テキストを生成する
    word = sentence_start
    text = [word]
    n = 0
    while True:
        if word not in model or not model[word]:
            break

        # 次の単語を選択するために重み付きランダム選択を行う
        next_word = random.choices(
            population=list(model[word].keys()),  # 選択肢（次の単語のリスト）
            weights=list(model[word].values())  # 出現頻度を重みとして使用
        )[0]

        text.append(next_word)  # 生成された単語を追加
        word = next_word  # 次の単語を現在の単語に設定

        # 終了条件: 改行または句点、または100単語を超えた場合
        if next_word == "\n" or next_word == "。":
            break
        if n > 100:
            break

        n += 1

    generate_text = "".join(text)

    print(generate_text)
    return generate_text

def home(request):
    """
    ホームページを表示し、POSTリクエストがあった場合は解析結果を表示するビュー関数。
    :param request: DjangoのHTTPリクエストオブジェクト
    :return: HttpResponseまたはレンダリングされたテンプレート
    """
    if request.method == 'POST':
        action = request.POST.get('action')  # どちらのボタンがクリックされたかを取得

        # ユーザーの入力を解析する
        json_response = Analysis(request)
        if not json_response:
            return HttpResponse("リクエストの処理中にエラーが発生しました。")

        # トークンの数を取得
        num = len(json_response.get("result", {}).get("tokens", []))

        if action == 'generateNew':
            # 新しいモデルを生成し、セッションに保存
            model = ModelGeneration(json_response)
            request.session['markov_model'] = json.dumps(model)  # JSON形式で保存

        elif action == 'useExisting':
            # 既存のモデルを使用
            if 'markov_model' in request.session:
                model = json.loads(request.session['markov_model'])
            else:
                return HttpResponse("既存のモデルが見つかりません。新しいモデルを生成してください。")

        # 名詞を探す
        norn = FindStart(json_response, num)

        # 文を生成
        text = GenerationText(model, norn)

        # 結果を表示
        return HttpResponse(f'{text}')

    # GETリクエストの場合、ホームページをレンダリング
    return render(request, 'home.html')

from django.shortcuts import render
import json
import random
from random import randrange
from urllib import request as url_request
from django.http import HttpResponse
from django.conf import settings
import logging

# settingsを使用してAPPIDを安全に取得
APPID = settings.YAHOO_APP_ID
URL = "https://jlp.yahooapis.jp/MAService/V2/parse"


def Analysis(request):
    """
    ユーザー入力を解析するためにYahooのMAService APIを呼び出す関数。
    """
    user_input = request.POST.get('text_input', '')

    headers = {
        "Content-Type": "application/json",
        "User-Agent": f"Yahoo AppID: {APPID}",
    }

    param_dic = {
        "id": "1234-1",  # 任意のID
        "jsonrpc": "2.0",  # JSON-RPCのバージョン
        "method": "jlp.maservice.parse",  # メソッド名
        "params": {
            "q": user_input  # ユーザーの入力テキスト
        }
    }
    params = json.dumps(param_dic).encode()

    try:
        req = url_request.Request(URL, data=params, headers=headers)
        with url_request.urlopen(req) as res:
            body = res.read()

        response_text = body.decode()
        response_json = json.loads(response_text)
        return response_json
    except Exception as e:
        logging.error(f"APIリクエスト中のエラー: {e}")
        return None


class JsonHandler:
    """
    JSONレスポンスを処理しやすくするためのヘルパークラス。
    """

    def __init__(self, json_object):
        self.tokens = json_object.get("result", {}).get("tokens", [])

    def key(self, n):
        if n < len(self.tokens):
            return self.tokens[n][0]
        return "\n"


def ModelGeneration(json_object):
    """
    マルコフ連鎖モデルを生成する関数。
    """
    model = {}
    handler = JsonHandler(json_object)

    n = 0
    while n < len(handler.tokens):
        word = handler.key(n)
        if word == "\r":
            n += 2
            continue

        next_word = handler.key(n + 1)
        if word not in model:
            model[word] = {}

        if next_word and next_word != "\n":
            if next_word not in model[word]:
                model[word][next_word] = 0
            model[word][next_word] += 1

        n += 1

    return model


def FindStart(json_object, num):
    """
    主語を探す関数。
    """
    noun = []
    for n in range(num):
        word = json_object["result"]["tokens"][n]
        if word[3] in "名詞" and word[4] in "普通名詞":
            noun.append(word[0])

    return noun


def GenerationText(model, start):
    """
    続きを生成する関数。
    """
    randam = randrange(len(start))
    sentence_start = start[randam]

    word = sentence_start
    text = [word]
    n = 0
    while True:
        if word not in model or not model[word]:
            break

        next_word = random.choices(
            population=list(model[word].keys()),
            weights=list(model[word].values())
        )[0]

        text.append(next_word)
        word = next_word

        if next_word == "\n" or next_word == "。":
            break
        if n > 100:
            break

        n += 1

    generate_text = "".join(text)
    return generate_text


def home(request):
    """
    ホーム画面のビュー関数。ユーザー入力を受け取って解析し、文を生成する。
    """
    if request.method == 'POST':
        action = request.POST.get('action')

        json_response = Analysis(request)
        if not json_response:
            return HttpResponse("リクエストの処理中にエラーが発生しました。")

        num = len(json_response.get("result", {}).get("tokens", []))

        if action == 'generateNew':
            # 新しいモデルを生成し、モデルを保存
            model = ModelGeneration(json_response)
            response = HttpResponse()  # 一時的なレスポンスを作成
            response.set_cookie('markov_model', json.dumps(model), max_age=3600)  # クッキーにモデルを保存

            # 生成したモデルを使ってテキストを生成
            norn = FindStart(json_response, num)
            text = GenerationText(model, norn)

            # 結果を表示
            response.content = f'新しいモデルを生成しました。\n生成された文: {text}'
            return response

        elif action == 'useExisting':
            # クッキーから既存のモデルを取得
            model_cookie = request.COOKIES.get('markov_model')
            if not model_cookie:
                return HttpResponse("既存のモデルが見つかりません。新しいモデルを生成してください。")

            # クッキーからモデルを読み込む
            model = json.loads(model_cookie)

        # 名詞を探す
        norn = FindStart(json_response, num)

        # 文を生成
        text = GenerationText(model, norn)

        # 結果を表示
        return HttpResponse(f'生成された文: {text}')

    return render(request, 'home.html')

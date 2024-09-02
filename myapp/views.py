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


def FindStart(model):
    """
    モデル内の名詞（文の開始候補）を探す関数。
    """
    # モデルのキー（単語）のリストから開始候補となる単語を探す
    noun = [word for word in model.keys() if len(word) > 1]  # 短すぎる単語を除外する
    return noun


def GenerationText(model, start):
    """
    続きを生成する関数。
    """
    if not start:
        return "モデルに開始できる名詞が見つかりませんでした。"

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

        if action == 'generateNew':
            # 新しいモデルを生成し、モデルを保存
            json_response = Analysis(request)
            if not json_response:
                return HttpResponse("リクエストの処理中にエラーが発生しました。")

            num = len(json_response.get("result", {}).get("tokens", []))
            model = ModelGeneration(json_response)
            response = HttpResponse()  # 一時的なレスポンスを作成
            # クッキーにモデルを保存（圧縮することを考慮）
            model_data = json.dumps(model)
            response.set_cookie('markov_model', model_data, max_age=3600, httponly=True)

            # 生成したモデルを使ってテキストを生成
            norn = FindStart(model)
            text = GenerationText(model, norn)

            # 結果を表示
            response.content = f'新しいモデルを生成しました。\n生成された文: {text}'
            return response

        elif action == 'useExisting':
            # クッキーから既存のモデルを取得
            model_cookie = request.COOKIES.get('markov_model')
            if not model_cookie:
                logging.info("既存のモデルがクッキーから見つかりません。")  # ログに出力
                return HttpResponse("既存のモデルが見つかりません。新しいモデルを生成してください。")

            # クッキーからモデルを読み込む（例外処理を追加）
            try:
                model = json.loads(model_cookie)
            except json.JSONDecodeError as e:
                logging.error(f"クッキーからモデルを読み込む際のエラー: {e}")
                return HttpResponse("モデルを読み込む際にエラーが発生しました。新しいモデルを生成してください。")

            # 名詞を探す
            norn = FindStart(model)

            # 文を生成
            text = GenerationText(model, norn)

            # 結果を表示
            return HttpResponse(f'生成された文: {text}')

    # クッキーをデバッグ用にログに出力
    logging.info(f"クッキー情報: {request.COOKIES}")

    return render(request, 'home.html')


#!/bin/bash

# Vercelが提供するPython環境をアクティベート
pip install -r requirements.txt

# Django管理コマンドを実行
python3.9 manage.py migrate  # マイグレーションを実行
python3.9 manage.py collectstatic --noinput  # 静的ファイルを収集

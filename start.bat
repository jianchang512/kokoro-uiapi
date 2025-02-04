@echo off
@chcp 65001

echo "启动中请稍等..."

call %cd%/runtime/python ./app.py

pause
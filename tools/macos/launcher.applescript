-- 双击启动三月七小助手 GUI（macOS / PlayCover iOS 版）
-- 程序自带单实例：已经在运行时新进程会激活已有窗口后退出
set projectDir to "/Users/luoxia/Workspace/GameScript/March7thAssistant"
do shell script "cd " & quoted form of projectDir & "; mkdir -p logs; /usr/bin/nohup " & quoted form of (projectDir & "/.venv/bin/python") & " app.py > logs/gui_launch.log 2>&1 < /dev/null &"

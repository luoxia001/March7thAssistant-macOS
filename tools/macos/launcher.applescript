-- 双击启动三月七小助手 GUI（macOS / PlayCover iOS 版）
-- 程序自带单实例：已经在运行时新进程会激活已有窗口后退出
-- 由 tools/macos/make_app.sh 替换为项目实际路径
set projectDir to "__PROJECT_DIR__"
do shell script "cd " & quoted form of projectDir & "; mkdir -p logs; /usr/bin/nohup " & quoted form of (projectDir & "/.venv/bin/python") & " app.py > logs/gui_launch.log 2>&1 < /dev/null &"

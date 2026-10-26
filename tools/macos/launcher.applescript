-- 双击启动三月七小助手 GUI（macOS / PlayCover iOS 版） 已经在运行时不重复启动
set projectDir to "/Users/luoxia/Workspace/GameScript/March7thAssistant"
set isRunning to (do shell script "pgrep -f 'March7thAssistant/.venv/bin/python app.py' >/dev/null && echo yes || echo no")
if isRunning is "yes" then
	display notification "三月七小助手已经在运行" with title "三月七小助手"
else
	do shell script "cd " & quoted form of projectDir & "; mkdir -p logs; /usr/bin/nohup " & quoted form of (projectDir & "/.venv/bin/python") & " app.py > logs/gui_launch.log 2>&1 < /dev/null &"
end if

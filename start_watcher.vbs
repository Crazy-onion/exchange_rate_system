' 汇率底稿自动更新 —— 静默启动器
' 作用：以无窗口方式启动 watcher.py（后台哨兵）
' 放在 Windows 启动目录 / 注册表 Run 项，实现「开机登录就自动接管」
Option Explicit

Dim ws, pythonw, workDir
Set ws = CreateObject("WScript.Shell")

workDir  = "C:\Users\rfuser\WorkBuddy\2026-07-24-15-41-07\exchange_rate_system"
pythonw  = "C:\Users\rfuser\.workbuddy\binaries\python\envs\default\Scripts\pythonw.exe"

ws.CurrentDirectory = workDir
ws.Run """" & pythonw & """ watcher.py", 0, False

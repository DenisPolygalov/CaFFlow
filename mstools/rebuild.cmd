@echo off

rmdir /s /q build\
rmdir /s /q dist\
pyinstaller -F pyinstaller.spec

rem pause

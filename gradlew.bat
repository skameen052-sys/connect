@echo off
pushd "%~dp0android"
call gradlew.bat %*
popd

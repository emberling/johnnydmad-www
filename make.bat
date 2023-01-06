@echo off
set targetpath=C:\Users\emberling\Documents\GitHub\emberling.github.io
rem generate.py
copy index.html %targetpath% /Y
copy johnnydmad.css %targetpath% /Y
xcopy core %targetpath%\core /I /Y
xcopy legacy %targetpath%\legacy /I /Y
xcopy tierboss %targetpath%\tierboss /I /Y
xcopy victory %targetpath%\victory /I /Y
xcopy sleep %targetpath%\sleep /I /Y
xcopy game_over %targetpath%\game_over /I /Y
xcopy static %targetpath%\static /I /Y
xcopy upcoming %targetpath%\upcoming /I /Y

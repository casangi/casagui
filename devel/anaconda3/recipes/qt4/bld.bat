set INCLUDE=%LIBRARY_INC%;%INCLUDE%
set LIB=%LIBRARY_LIB%;%LIB%

cd qt-everywhere-opensource-src-%PKG_VERSION%

echo y | configure.exe -prefix %LIBRARY_PREFIX%\qt4 ^
                       -libdir %LIBRARY_PREFIX%\qt4\lib ^
                       -bindir %LIBRARY_PREFIX%\qt4\bin ^
                       -headerdir %LIBRARY_PREFIX%\qt4\include ^
                       -datadir %LIBRARY_PREFIX%\qt4 ^
                       -release ^
                       -shared ^
                       -opensource ^
                       -fast ^
                       -no-qt3support ^
                       -nomake examples ^
                       -nomake demos ^
                       -nomake docs ^
                       -openssl ^
                       -webkit ^
                       -system-zlib ^
                       -system-libpng ^
                       -system-libtiff ^
                       -system-libjpeg

bin\qmake -r QT_BUILD_PARTS="libs tools"

jom -j%NUMBER_OF_PROCESSORS%
if errorlevel 1 exit 1
nmake install
if errorlevel 1 exit 1

rd /S /Q %LIBRARY_PREFIX%\qt4\phrasebooks
rd /S /Q %LIBRARY_PREFIX%\qt4\tests
del %LIBRARY_PREFIX%\qt4\q3porting.xml

:: These are here to map cl.exe version numbers, which we use to figure out which
:: compiler we are using, and which compiler consumers of Qt need to use, to MSVC
:: year numbers, which is how qt identifies MSVC versions.
:: Update this with any new MSVC compiler you might use.
echo @echo 15=2008 >> msvc_versions.bat
echo @echo 16=2010 >> msvc_versions.bat
echo @echo 17=2012 >> msvc_versions.bat
echo @echo 18=2013 >> msvc_versions.bat
echo @echo 19=2015 >> msvc_versions.bat

for /f "delims=" %%A in ('cl /? 2^>^&1 ^| findstr /C:"Version"') do set "CL_TEXT=%%A"
FOR /F "tokens=1,2 delims==" %%i IN ('msvc_versions.bat') DO echo %CL_TEXT% | findstr /C:"Version %%i" > nul && set VSTRING=%%j && goto FOUND
EXIT 1
:FOUND

mkdir %LIBRARY_PREFIX%\qt4\mkspecs\win32-msvc-default
copy %LIBRARY_PREFIX%\qt4\mkspecs\win32-msvc%VSTRING:~0,4%\* %LIBRARY_PREFIX%\qt4\mkspecs\win32-msvc-default\

copy "%RECIPE_DIR%\write_qtconf.bat" "%PREFIX%\Scripts\.qt4-post-link.bat"

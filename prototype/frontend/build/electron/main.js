"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var electron_1 = require("electron");
var path = require("path");
var isDev = require("electron-is-dev");
var electron_devtools_installer_1 = require("electron-devtools-installer");
var win = null;
function createWindow() {
    win = new electron_1.BrowserWindow({
        useContentSize: true,
        autoHideMenuBar: true,
        darkTheme: true,
        resizable: true,
        backgroundColor: '#282c34',
        webPreferences: {
            nodeIntegration: true
        }
    });
    if (isDev) {
        win.loadURL('http://localhost:3000/index.html');
    }
    else {
        // 'build/index.html'
        win.loadURL("file://" + __dirname + "/../index.html");
    }
    win.on('closed', function () { return win = null; });
    // Hot Reloading
    if (isDev) {
        // 'node_modules/.bin/electronPath'
        require('electron-reload')(__dirname, {
            electron: path.join(__dirname, '..', '..', 'node_modules', '.bin', 'electron'),
            forceHardReset: true,
            hardResetMethod: 'exit'
        });
    }
    // DevTools
    electron_devtools_installer_1.default(electron_devtools_installer_1.REACT_DEVELOPER_TOOLS)
        .then(function (name) { return console.log("Added Extension:  " + name); })
        .catch(function (err) { return console.log('An error occurred: ', err); });
    if (isDev) {
        //    win.webContents.openDevTools();
    }
}
electron_1.app.on('ready', createWindow);
electron_1.app.on('window-all-closed', function () {
    if (process.platform !== 'darwin') {
        electron_1.app.quit();
    }
});
electron_1.app.on('activate', function () {
    if (win === null) {
        createWindow();
    }
});
//# sourceMappingURL=main.js.map
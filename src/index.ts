import { app, BrowserWindow } from "electron"
import * as path from 'path';

let mainWindow
var root = path.dirname(path.resolve(__dirname))

function createWindow() {

    if (process.env.PYTHONPATH) {
        process.env.PYTHONPATH = `${root}/kernels/python:${process.env.PYTHONPATH}`
    } else {
        process.env.PYTHONPATH = `${root}/kernels/python`
    }
    console.info(`set PYTHONPATH to ${process.env.PYTHONPATH}`)

    mainWindow = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            nodeIntegration: true, // this line is very important as it allows us to use `require` syntax in our html file.
            contextIsolation: false,
        },
    })
    mainWindow.loadFile(`index.html`)
}

app.allowRendererProcessReuse = false
app.whenReady().then(createWindow)

import { app, BrowserWindow } from "electron"
import { JupyterKernel } from "./kernels";
const { v4: uuidv4 } = require('uuid');
import * as path from 'path';

let mainWindow: any
var root = path.dirname(path.resolve(__dirname))

var kernel: JupyterKernel = new JupyterKernel( )

function sendConnectionInfo( mw: any, kspec: any, type: string, type_count: number ) {
    let spec = { identity: uuidv4( ),                 // --- must have a unique identity
                 header: { session: uuidv4( ),
                           username: `${kspec.header.username}:${type}:${type_count}` },
                 config: kspec.config }
    mw.webContents.send('kernel-spec',spec)
}

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

    kernel.spawn( ).then( kspec => sendConnectionInfo(mainWindow,kspec,'plotants',1) )

    mainWindow.loadFile(`index.html`)
}

app.on('before-quit', event => {
    if ( kernel.get_state( ) != 'closed' ) {
        event.preventDefault()
        kernel.shutdown( ).then( result => { app.quit( ) } )
    }
} )

app.allowRendererProcessReuse = false
app.whenReady().then(createWindow)

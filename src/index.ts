import { app, BrowserWindow, globalShortcut, Menu, MenuItem, ipcMain } from "electron"
import { JupyterKernel } from "./kernels";
const { v4: uuidv4 } = require('uuid');
import * as path from 'path';
import { Dictionary } from "./utils";

// These windows variables need to be cleaned up and managed instead of
// being global variables, but for now...
// ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ----
let placeholderWindow: any
let plotlyDemo: any
let bokehDemo: any
// ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ----

let kernelSpec: Promise<any>
let devDisplayed = false
let devSubMenu = new Menu( )
var root = path.dirname(path.resolve(__dirname))

var kernel: JupyterKernel = new JupyterKernel( )

// Keep track of the number of renderer windows with the same name so that
// the name of each window can be unique, e.g. '<user-name>:<window-name>:<count>'
let connectionCounts: Dictionary = { }
// Keep track of the renderers using the jupyter kernel. In the future, this may
// be used to load balance work across a number of kernels.
var kernelRenderers: Array<{ spec: any, renderer: any}> = new Array<{ spec: any, renderer: any }>( )
function generateConnectionInfo( sender: any, kspec: any, args: { name: string } ) {
    if ( args.name in connectionCounts ) {
        connectionCounts[args.name] += 1
    } else {
        connectionCounts[args.name] = 1
    }
    let result = { identity: uuidv4( ),                 // --- must have a unique identity
                   header: { session: uuidv4( ),
                   username: `${kspec.header.username}:${args.name}:${connectionCounts[args.name]}` },
                   config: kspec.config }
    kernelRenderers.push({ spec: result, renderer: sender })
    return result
}
// renderers which use the jupyter kernel should send a release message when they exit
function registerKernelRelease( sender: any, args: { session: string } ) {
    kernelRenderers = kernelRenderers.filter( v => { v.spec.header.session != args.session })
}

function toggleDeveloperMenu( ) {
    let curMenu = Menu.getApplicationMenu( )
    if (curMenu) {
        let newMenu = new Menu( )
        if (devDisplayed === false) {
            curMenu.items.forEach( x => { newMenu.append(x) } )
            newMenu.append( new MenuItem({
                type: 'submenu',
                label: 'Develop',
                submenu: devSubMenu
            }))
            devDisplayed = true
        } else {
            curMenu.items.filter(x => x.label != 'Develop').forEach( x => { newMenu.append(x) })
            devDisplayed = false
        }
        Menu.setApplicationMenu(newMenu)
    }
}
function stripDevtools( devmenu: Menu ) {
    let curMenu = Menu.getApplicationMenu( )
    if ( curMenu ) {
        let newMenu = new Menu( )
        curMenu.items.forEach( x => {
            if (x.role?.toLowerCase() == 'viewmenu') {
                let newSubMenu = new Menu( )

                x.submenu?.items.forEach( y => {
                    if ( y.role?.toLowerCase() === 'toggledevtools' ) {
                        devmenu.append(y)
                    } else {
                        newSubMenu.append(y)
                    }
                })

                newMenu.append( new MenuItem({
                    type: x.type,
                    label: x.label,
                    submenu: newSubMenu
                }))
            } else {
                newMenu.append(x)
            }
        })
        Menu.setApplicationMenu(newMenu)
    }
}
function setupDevAndDemo( devmenu: Menu ) {
    devmenu.append(new MenuItem({
        label: 'Plotly Demo',
        click: ( ) => {
            plotlyDemo = new BrowserWindow({
                width: 800,
                height: 600,
                webPreferences: {
                    nodeIntegration: true, // this line is very important as it allows us to use `require` syntax in our html file.
                    contextIsolation: false,
                },
            })

            plotlyDemo.loadFile(`./dist/demo/plotly.html`)
        }
    }))
    devmenu.append(new MenuItem({
        label: 'Bokeh Demo',
        click: ( ) => {
            bokehDemo = new BrowserWindow({
                width: 800,
                height: 600,
                webPreferences: {
                    nodeIntegration: true, // this line is very important as it allows us to use `require` syntax in our html file.
                    contextIsolation: false,
                },
            })

            bokehDemo.loadFile(`./dist/demo/bokeh.html`)
        }
    }))

}
function initializeApp() {

    if (process.env.PYTHONPATH) {
        process.env.PYTHONPATH = `${root}/kernels/python:${process.env.PYTHONPATH}`
    } else {
        process.env.PYTHONPATH = `${root}/kernels/python`
    }
    console.info(`set PYTHONPATH to ${process.env.PYTHONPATH}`)

    stripDevtools(devSubMenu)
    setupDevAndDemo(devSubMenu)
    kernelSpec = kernel.spawn( )

    kernelSpec.then( spec => {
        ipcMain.on('kernel-request', (event,arg) => {
            event.sender.send('kernel-reply', generateConnectionInfo(event.sender, spec, arg))
        })
        ipcMain.on('kernel-release', (event,arg) => {
            registerKernelRelease(event.sender, arg)
        })
    })

    placeholderWindow = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            nodeIntegration: true, // this line is very important as it allows us to use `require` syntax in our html file.
            contextIsolation: false,
        },
    })

    placeholderWindow.loadFile(`./dist/placeholder.html`)
}

app.on('before-quit', event => {
    if ( kernel.get_state( ) != 'closed' ) {
        event.preventDefault()
        kernel.shutdown( ).then( result => { app.quit( ) } )
    }
} )

app.allowRendererProcessReuse = false
app.whenReady().then( ( ) => {
    globalShortcut.register('CommandOrControl+o',toggleDeveloperMenu)
    // The default behavior is that the electron app exits when the last renderer
    // is exits, but on macos typically the applications w/ menu bar
    // stays active until the user explicitly quits
    app.on('window-all-closed', function () {
        if (process.platform !== 'darwin') {
          app.quit()
        }
     } )
    initializeApp( )
} )

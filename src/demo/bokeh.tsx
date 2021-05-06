import * as path from 'path';
import React, { useState, useEffect } from "react"
import * as ReactDOM from "react-dom"
import PropTypes from 'prop-types';
import { parse } from 'node-html-parser';
import { ipcRenderer } from 'electron';
import { Dictionary } from "../utils";
import { JupyterKernel, message_type } from "../kernels";
import _, { map } from 'underscore';

var root = path.dirname(path.dirname(path.resolve(__dirname)))

var kernel: JupyterKernel = new JupyterKernel( )

const MIME_HTML = 'text/html'
const MIME_HOLO_JSON = 'application/vnd.holoviews_load.v0+json'
const MIME_JAVASCRIPT = 'application/javascript'

function splitScripts( output: any[] ): {html: string, scripts: string[]} {
    let html = ''
    let scripts = [] as string[]
    output.forEach( elem => {
        if ( elem.content !== undefined &&
             elem.content.data !== undefined &&
             elem.content.data[MIME_HTML] !== undefined ) {
            const root = parse(elem.content.data[MIME_HTML])
            const script_elements = root.querySelectorAll('script')
            scripts = script_elements.map(e => e.text)
            script_elements.map(e => e.remove( ))
            html = root.toString( )
        }
    } )
    return { html, scripts }
}


function Bokeh01( ) {
    const [html, setHtml] = useState('Loading plot...')
    const [scripts, setScripts] = useState([ ] as string[])
    const [javascript, setJavascript] = useState([ ] as string[])

    useEffect(( ) => {
        if ( scripts.length > 0 ) {
            scripts.map(s => { window.eval(s) } )
            setScripts([ ] as string[])
        }
    },[scripts])

    useEffect( ( ) => {
        if ( javascript.length > 0 ) {
            javascript.map(s => { window.eval(s) })
            setJavascript([ ] as string[])
        }
    },[javascript])

    useEffect(( ) => {
        const createPlot = async ( ) => {
            let code = `from casadesk.trybokeh import bokehdemo01
bokehdemo01( )`

            let result = await kernel.call( "execute_request" as message_type,
                                            { silent: true,
                                              code } ).then(
                                                  res => _.groupBy(res, x => x.content.type)
                                              )



            if ( result.html != undefined ) {
                let splithtml = splitScripts(result.html)
                setHtml(splithtml.html)
                setScripts(splithtml.scripts)
            }

            if ( result.javascript != undefined ) {
                setJavascript(_.map(result.javascript, js => js.content.data['application/javascript']))
            }
        }
        createPlot( )
    }, [])

    return <div>
               <div dangerouslySetInnerHTML={{ __html: html }} />
           </div>
}

async function initializeBokeh( spec: any  ) {
    // Bokeh must be initialized for notebook display...
    let code = `from bokeh.io import output_notebook
output_notebook( )`
    let result = await kernel.call( "execute_request" as message_type,
                                    { silent: true, code } ).then(
                                        res => _.groupBy(res, x => x.content.type)
                                    )
    if ( result.javascript != undefined ) {
        result.javascript.forEach( js => {
            window.eval(js.content.data['application/javascript'])
        } )
    }
                        
    if ( result.html != undefined ) {
        let splithtml = splitScripts(result.html)
        splithtml.scripts.forEach( script => {
            window.eval(script)
        })
    }
    return spec
}

ipcRenderer.send('kernel-request', { name: 'bokeh' })
ipcRenderer.once('kernel-reply', (ev,spec) => {
    console.info("received kernel info",spec)
    kernel.attach(spec).then(initializeBokeh).then( spec => {
        ReactDOM.render(<Bokeh01/>,document.getElementById("app"))
    } )
    window.onbeforeunload = (e: any) => {
        ipcRenderer.send('kernel-release', { session: spec.header.session } )
    }
} )

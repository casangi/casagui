import * as path from 'path';
import React, { useState, useEffect } from "react"
import * as ReactDOM from "react-dom"
import PropTypes from 'prop-types';
import { parse } from 'node-html-parser';
import { ipcRenderer } from 'electron';
import { JupyterKernel, message_type } from "../kernels";

var root = path.dirname(path.dirname(path.resolve(__dirname)))

var kernel: JupyterKernel = new JupyterKernel( )

function splitScripts( output: any[] ): {html: string, scripts: string[]} {
    let html = ''
    let scripts = [] as string[]
    output.forEach( elem => {
        if ( elem.content !== undefined &&
             elem.content.data !== undefined &&
             elem.content.data['text/html'] !== undefined ) {
            const root = parse(elem.content.data['text/html'])
            const script_elements = root.querySelectorAll('script')
            scripts = script_elements.map(e => e.text)
            script_elements.map(e => e.remove( ))
            html = root.toString( )
        }
    } )
    return { html, scripts }
}

function PlotAnts( ) {
    const [html, setHtml] = useState('Loading antenna plot...')
    const [scripts, setScripts] = useState([ ] as string[])
    const [coord, setCoord] = useState('polar')
    const [mspath, setPath] = useState({ path: `${root}/test/ic2233_1.ms` })

    useEffect(( ) => {
        if ( scripts.length > 0 ) {
            scripts.map(s => { window.eval(s) } )
            setScripts([ ] as string[])
        }
    },[scripts])

    useEffect(( ) => {
        const fetchData = async ( ) => {
            let code = `from casadesk import plotants
plotants("${mspath.path}",logpos=${coord === 'polar' ? 'True' : 'False'}).show( )`
            let result = await kernel.call( "execute_request" as message_type,
                                            { silent: false,
                                              code } ).then(splitScripts)
            console.info(result)
            setHtml(result.html)
            setScripts(result.scripts)
        }
        fetchData( )
    }, [coord])

    return <div>
               <div dangerouslySetInnerHTML={{ __html: html }} />
               <table>
                   <tbody>
                       <tr>
                           <td><input type="radio" name="cartesian" checked={coord === "cartesian"} value="cartesian" onChange={e => setCoord('cartesian')}/>cartesian</td>
                           <td><input type="radio" name="polar" checked={coord === "polar"} onChange={e => setCoord('polar')}/>polar</td>
                       </tr>
                   </tbody>
               </table>
           </div>
}

ipcRenderer.send('kernel-request', { name: 'plotants' })
ipcRenderer.once('kernel-reply', (ev,spec) => {
    console.info("received kernel info",spec)
    kernel.attach(spec).then( spec => {
        ReactDOM.render(<PlotAnts/>,document.getElementById("app"))
    } )
    window.onbeforeunload = (e: any) => {
        ipcRenderer.send('kernel-release', { session: spec.header.session } )
    }
} )

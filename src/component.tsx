import * as React from "react"
import * as ReactDOM from "react-dom"
import PropTypes from 'prop-types';
import { parse } from 'node-html-parser';

import { JupyterKernel, message_type } from "./kernels";
const kernel = new JupyterKernel( )

function to_console( output: any[] ): string {
    console.group('jupyter result')
    let result = ''
    let count = 1
    output.forEach( elem => {
        console.info(`(${count})\t`,elem )
        if ( elem.content !== undefined && elem.content.data !== undefined &&
             elem.content.data['text/html'] !== undefined ) {
            result = elem.content.data['text/html']
            console.info(result)
        }
        count += 1 } )
    console.groupEnd( )
    return result
}

async function render_app(func:(e: JSX.Element) => any) {
    let html_orig = await kernel.call( "execute_request" as message_type,
                                  { silent: false, code: `import plotly.graph_objects as go
fig = go.Figure( data=[go.Bar(y=[2, 1, 3])],
                 layout_title_text="A Figure Displayed with fig.show()" )
fig.show()`} ).then(to_console)
    
    if ( html_orig.length > 0 ) {
        const root = parse(html_orig)
        let script_elements = root.querySelectorAll('script')
        let scripts = script_elements.map(e => e.text)
        script_elements.map(e => e.remove( ))
        let danger = { __html: root.toString( ) }

        class RenderComponent extends React.Component {
            componentDidMount( ) {
                scripts.map(s => { window.eval(s) } )
            }
            render() {
                return <div dangerouslySetInnerHTML={{ __html: root.toString( )}} />
            }
        }
        console.info("setting dangerous HTML:",danger)
        func( React.createElement(RenderComponent) )
    } else {
        console.info("setting regular HTML")
        func( <h1>Hello, react!</h1> )
    }
}

//ReactDOM.render(<App />, document.getElementById("app"))
render_app( elem => {
    console.info("react render of", elem)
    ReactDOM.render(elem,document.getElementById("app"))
} )

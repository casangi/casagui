import * as path from 'path';
import * as React from "react"
import * as ReactDOM from "react-dom"
import PropTypes from 'prop-types';
import { parse } from 'node-html-parser';

import { JupyterKernel, message_type } from "./kernels";

var root = path.dirname(path.resolve(__dirname))

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

interface PAProps { }
interface PAState {
    coord?: string;
}

async function render_app(func:(e: JSX.Element) => any) {
//    let html_orig = await kernel.call( "execute_request" as message_type,
//                                  { silent: false, code: `import plotly.graph_objects as go
//fig = go.Figure( data=[go.Bar(y=[2, 1, 3])],
//                 layout_title_text="A Figure Displayed with fig.show()" )
//fig.show()`} ).then(to_console)
    let mspath = `${root}/test/ic2233_1.ms`
    let html_orig = await kernel.call( "execute_request" as message_type,
                                       { silent: false,
                                         code: `from casadesk import plotants
plotants("${mspath}",logpos=True).show( )`} ).then(to_console)

    if ( html_orig.length > 0 ) {
        const root = parse(html_orig)
        let script_elements = root.querySelectorAll('script')
        let scripts = script_elements.map(e => e.text)
        script_elements.map(e => e.remove( ))
        let danger = { __html: root.toString( ) }

        class RenderComponent extends React.Component<PAProps,PAState> {
            constructor(props: PAProps) {
                super(props)
                this.state = { coord: "polar" }
                this.onCartesianChange = this.onCartesianChange.bind(this)
                this.onPolarChange = this.onPolarChange.bind(this)
            }
            componentDidMount( ) {
                scripts.map(s => { window.eval(s) } )
            }
            onCartesianChange( e: any ) {
                this.setState({ coord: "cartesian" })
            }
            onPolarChange( e: any ) {
                this.setState({ coord: "polar" })
            }
            render() {
                return <div>
                           <div dangerouslySetInnerHTML={{ __html: root.toString( )}} />
                           <table>
                               <tbody>
                                   <tr>
                                       <td><input type="radio" name="cartesian" checked={this.state.coord === "cartesian"} value="cartesian" onChange={this.onCartesianChange}/>cartesian</td>
                                       <td><input type="radio" name="polar" checked={this.state.coord === "polar"} onChange={this.onPolarChange}/>polar</td>
                                   </tr>
                               </tbody>
                           </table>
                       </div>
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

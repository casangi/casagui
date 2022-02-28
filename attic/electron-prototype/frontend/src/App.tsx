import * as React from 'react';
import Plotter from './Plotter';
import './App.css';

import '../node_modules/@blueprintjs/core/lib/css/blueprint.css';
import '../node_modules/flexlayout-react/style/dark.css'
import {
  Layout, 
  Model, 
  TabNode, 
  IJsonModel
} from 'flexlayout-react';

import {
  Button,
  ControlGroup,
  ButtonGroup,
  FileInput,
  Navbar,
  Alignment,
  Text,
} from "@blueprintjs/core";


var json : IJsonModel= {
  global: {
    "splitterSize": 6,
		"tabEnableFloat": true
  },
  borders: [
		{
		  "type": "border",
			"location": "bottom",
			"children": [
				{
					"type": "tab",
					"enableClose":false,
					"name": "Menu",
					"component": "grid"
				},
			]
		},
	],
  layout: {
    "type": "row",
    "weight": 100,
    "children": [
      {
        "type": "tabset",
        "weight": 100,
        "selected": 0,
        "children": [
          {
            "type": "tab",
            "name": "One",
            "component": "button"
          }
        ]
      }
    ]
  }
};

type Props = {

}

type State = {
  model: Model;
};


export class App extends React.PureComponent <Props, State> {
  public state: State = {
    model: Model.fromJson(json),
  }


  nextGridIndex: number = 1;

  private onAddActiveClick = (event: React.MouseEvent) => {
    if (this.state.model!.getMaximizedTabset() == null) {
        (this.refs.layout as Layout).addTabToActiveTabSet({
            component: "channel-tab",
            name: "channel-" + this.nextGridIndex++
        });
    }
  }

  private handleClick(element:string):any {
    console.log(element);
  }

  private getData = async() =>{
    const response = await fetch('http://localhost:5000/channel')
    const data = await response.json();
    
    return data;
    
  }

  private getChannelData = async(id:string) =>{
    const response = await fetch('http://localhost:5000/channel/' + id)
    const data = await response.json();
    
    return data;
    
  }

  private factory = (node: TabNode) => {
    if(node.getComponent() === 'channel-tab'){
      return (
        <div className="bp3-dark">
          <div className="panel" id={'Channel: ' + node.getName()}>
          <Plotter channel={'Channel: ' + node.getName()} />
          </div>
        </div>
      );
    }

    return ( 
    <div className="bp3-dark">
      <div className="panel">
      <Text>
        Load file to begin interactive clean analysis ...
      </Text>
      </div>
    </div>
    );
  }
  
  public render(){
    return (
      <div className="app bp3-dark">
        <Navbar>
              <Navbar.Group align={Alignment.LEFT}>
              <Navbar.Heading>CASA</Navbar.Heading>
              <Navbar.Divider />
              
              <FileInput buttonText="File" text="Choose file ..."/>
              
              <Navbar.Divider />
            
              <ControlGroup fill={true} vertical={false}>
                <ButtonGroup>
                  <Button fill={false} icon='properties' onClick={this.getData}></Button>
                  <Button fill={false} icon='add' onClick={this.onAddActiveClick}></Button>
                </ButtonGroup>

              </ControlGroup>
              
              </Navbar.Group>
            </Navbar>
        
            <div className="toolbar">
            
            </div>
            <div className="contents">
              {<Layout 
              ref="layout" 
              model={this.state.model} 
              factory={this.factory}
              />}
            </div>
        
      </div>
    );
  }
}

export default App;

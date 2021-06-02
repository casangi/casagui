import * as React from 'react';
import Plot from 'react-plotly.js'
import {
    Button,
    ControlGroup,
    ButtonGroup,
    NumericInput,
    Label,
    Divider,
  } from "@blueprintjs/core";

const getData = async() =>{
    const response = await fetch('http://localhost:5000/channel/1');
    const data = await response.json();

    return data;
}

const Plotter = (props) => {    
    const [values, setValues] = React.useState([]);

    const handleSelected = (vals) => {
      console.log('Box> ' + vals.range.x[0] + " " + vals.range.x[1] + "\n" + vals.range.y[0] + " " + vals.range.y[1])
      // vals.points.forEach(function(pt.range) {
      //   console.log('(x, y) > ' + pt.x + " " pt.y);
      //  });
          
      
    };

    React.useEffect(async (props)=>{
        await fetch('http://localhost:5000/channel/1')
        .then(response=>response.json())
        .then(values=>setValues(values));
    }, []);
    return (
      <div className="panel">
        <Plot
            data={[
          {
            x: values.time,
            y: values.flux,
            type: 'scatter',
            mode: 'markers',
            marker: {color: 'red'},
          },
        
        ]}
        layout={
          {
              title: props.channel,
              autosize: true,
              hovermode: 'closest',
              responsive: true,
              dragmode: 'drawrect',
              margin: {
                  t: 50, //top margin
                  l: 50, //left margin
                  r: 50, //right margin
                  b: 50 //bottom margin
                  },
          }
        }
        style={
          {
              width: '100%', 
              height: '100%'
          }
        }
        useResizeHandler={true}
        onSelected={eventData=>{handleSelected(eventData)}}
    />
    
    <div className="toolbar">
      <ControlGroup fill={true} vertical={false}>
            <ButtonGroup>
                <Button fill={false} icon='new-grid-item'></Button>
                <Button fill={false} icon='eraser'></Button>
                <Button fill={false} icon='play'></Button>
                <Button fill={false} icon='step-forward'></Button>
                <Button fill={false} icon='stop'></Button>
                <Divider />
                <label class="bp3-inline">
                <NumericInput defaultValue={1}/>  
                </label>
              </ButtonGroup>


        </ControlGroup> <br></br>
      </div>
  </div>
  );
    
}

export default Plotter;
import * as React from "react";
import { 
    Alignment,
    Button,
    Navbar,
    NavbarDivider,
    NavbarGroup,
    NavbarHeading,
    Dialog,
    Classes,
    FileInput,
} from "@blueprintjs/core";
import '../node_modules/@blueprintjs/core/lib/css/blueprint.css';

type Props = {
    onInputChange: React.FormEventHandler<HTMLInputElement>
}

type State = {
    autoFocus: boolean
    canEscapeKeyClose: boolean;
    canOutsideClickClose: boolean;
    enforceFocus: boolean;
    hasBackdrop: boolean;
    isOpen: boolean;
    usePortal: boolean;
    useTallContent: boolean;
}

export class NavBar extends React.PureComponent<Props, State>{
    public state: State = {
        autoFocus: true,
        canEscapeKeyClose: true,
        canOutsideClickClose: true,
        enforceFocus: true,
        hasBackdrop: true,
        isOpen: false,
        usePortal: true,
        useTallContent: false,
    };

    private handleOpen = () => this.setState({isOpen: true});

    private handleClose = () => this.setState({isOpen: false});


    public render(){        
        return (
            <Navbar className="bp3-dark">
                <NavbarGroup align={Alignment.LEFT}>
                    <NavbarHeading>CASA</NavbarHeading>
                    <NavbarDivider />
                    <Button className="bp3-minimal bp3-dark" icon="home" text="Home" />
                    <Button className="bp3-minimal bp3-dark" icon="document" text="Files" onClick={this.handleOpen}/>
                    <Dialog className={Classes.DIALOG_BODY} icon='info-sign' title="Load CASA File" isOpen={this.state.isOpen} onClose={this.handleClose}>
                        <div className="bp3-dark load">
                            <>
                                <FileInput placeholder="choose file ..." buttonText="Load" onInputChange={this.props.onInputChange}/>
                            </>
                        </div>
                    </Dialog>
                </NavbarGroup>
            </Navbar>
        );
    }
}
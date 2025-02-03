import _ from "lodash";
import React from 'react';
import Container from 'react-bootstrap/Container';
import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Button from 'react-bootstrap/Button';
import SplitViewHorizontal from "./SplitView";
import Spinner from 'react-bootstrap/Spinner';
import Alert from 'react-bootstrap/Alert';
import { Action } from '../ActionHandlers/webcli_client';
import './App.css';

// Example of closing the connection after 10 seconds
// setTimeout(() => {
//     console.log("Closing WebSocket connection...");
//     socket.close();
// }, 10000);

/*******************************************************
 * In dev mode, when we have StrictMode at top level
 * A component may mount, then unmount, then mount
 * so we do not disconnect the web socket upon unmount
 * this is a dev behavior when StrictMode is used, 
 * In production mode (when StrictMode is not used), unmount won't happen
 * props
 *     configMap: a map for action handler configurations
 *                key is action handler name, value is the configuration
 */
class App extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            actionWrappers: [],
            command: "",

            alerts: [
            ]
        };
    }

    removeAlert = (alert) => {
        this.setState({
            alerts: this.state.alerts.filter(it => it.id === alert.id)
        })
    }

    addAlert = message => {
        const newAlert = {
            id: 1+_.min([0, ...this.state.alerts.map(alert => alert.id)]),
            message: message
        };
        this.setState({
            alerts: [...this.state.alerts, newAlert]
        })
    }


    /**********************************************************************************
     * Called when user hit "submit" button
     */
    sendAction = async () => {
        console.log("App.sendAction: enter");
        const command = this.state.command;
        console.log(`App.sendAction: command=${command}`);
        const [actionHandler, request] = this.props.webCLIClient.getActionRequestFromText(command);

        // if no action handler recognize the text, we will ignore it
        if (request === null) {
            // TODO: pop up some error message
            this.addAlert("Unrecognized command");
            console.log("App.sendAction: unrecognized command");
            console.log("App.sendAction: exit");
            return;
        }

        // TODO: "/actions" -- this need to be configurable
        const response = await fetch("/actions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(request),
        });
        console.log(`App.sendAction: send action to server`);

        if (!response.ok) {
            // TODO: pop up some error message
            this.addAlert(`Failed to send action to server, status: ${response.status}`);
            console.log("App.sendAction: error, ", response);
            return;
        }

        const actionResponse = await response.json();
        console.log("App.sendAction: server response: ", actionResponse.id);
        const newAction = new Action({
            id: actionResponse.id, 
            text: command, 
            request: request, 
            handlerName: actionHandler.getName()
        });
        await this.props.webCLIClient.addAction(newAction);
        console.log("App.sendAction: exit");
    }

    // after component is mounted
    componentDidMount() {
        console.log("App.componentDidMount: enter");
        this.props.webCLIClient.connect(
            async () => {
                this.setState({
                    actionWrappers: [...this.props.webCLIClient.actionWrappers]
                });
            },
            // use __, since I may use lodash which is imported as _
            __ => <Spinner animation="border" role="status">
                <span className="visually-hidden">Loading...</span>
            </Spinner>
        );
        console.log("App.componentDidMount: websocket is connected");
        console.log("App.componentDidMount: exit");
    }

    // after component state changes
    componentDidUpdate(prevProps, prevState) {
        // commented since it is called too often
        // console.log("App.componentDidUpdate: enter");
        // console.log("App.componentDidUpdate: exit");
    }

    // after component is unmounted
    componentWillUnmount() {
        console.log("App.componentWillUnmount: enter");
        // const notificationManager = this.props.notificationManager;
        // notificationManager.disconnect();
        // console.log("App.componentWillUnmount: websocket is disconnected");
        console.log("App.componentWillUnmount: exit");
    }

    render() {
        return (
            <div className='cli-page'>
                <SplitViewHorizontal>
                    <Container fluid className='h-100'>
                        <Row>
                            <Col>
                            {this.state.alerts.map(
                                alert => 
                                <Alert 
                                    key={alert.id} 
                                    variant="danger"
                                    dismissible
                                    onClose={() => this.removeAlert(alert)} 
                                >
                                    {alert.message}
                                </Alert>
                            )}
                            </Col>
                        </Row>
                        <Row className="answer-panel">
                            <Col>
                            {
                                this.state.actionWrappers.map(actionWrapper => {
                                    return <div key={actionWrapper.action.id} className="mb-2">
                                        {this.props.webCLIClient.renderAction(actionWrapper)}
                                    </div>
                                })
                            }
                            </Col>
                        </Row>
                    </Container>
                    <Container fluid className="question-panel">
                        <Row className="h-100 pt-2 pb-2">
                            <Col>
                                <Form.Control as="textarea" rows={6} 
                                    className='question-panel--question'
                                    value={this.state.command}
                                    onChange={async (event) => {
                                        this.setState({
                                            command: event.target.value
                                        });
                                    }}
                                    placeholder='Please input your command'
                                />
                            </Col>
                            <Col xs={1}>
                                <Button 
                                    variant="primary"
                                    size="sm"
                                    onClick={this.sendAction}
                                >Submit</Button>
                            </Col>
                        </Row>
                    </Container>
                </SplitViewHorizontal>
            </div>
        );
    }
}

export default App;

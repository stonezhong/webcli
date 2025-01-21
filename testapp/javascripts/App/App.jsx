import React from 'react';
import './App.css';
import {Action} from '../tools/webcli_client';

import pino from 'pino';
const logger = pino({
    level: 'debug',
    transport: {
        target: 'pino-pretty',
        options: { colorize: true },
    },
});

class App extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            command:"",
            actions: []
        };
    }

    /**********************************************************************************
     * Called when an action is completed
     */
    onActionCompleted = async (actionId, actionResponse) => {
        const newActions = this.state.actions.map(action => {
            if (action.id !== actionId) {
                return action;
            }
            action.response = actionResponse;
            return action;
        });
        this.setState({
            actions: newActions
        });
    }

    /**********************************************************************************
     * Called when user hit "send" button
     */
    sendAction = async () => {
        logger.info("App.sendAction: enter");
        const command = this.state.command;
        logger.info(`App.sendAction: command=${command}`);
        const [actionHandler, request] = this.props.webCLIClient.getActionRequestFromText(command);

        // if no action handler recognize the text, we will ignore it
        if (request === null) {
            logger.info("App.sendAction: unrecognized command");
            logger.info("App.sendAction: exit");
            return;
        }

        const response = await fetch("/actions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(request),
        });
        logger.info(`App.sendAction: send action to server`);

        if (!response.ok) {
            logger.info("App.sendAction: error, ", response);
            return;
        }

        const actionResponse = await response.json();
        logger.info("App.sendAction: server response: ", actionResponse.id);
        const newAction = new Action({
            id: actionResponse.id, 
            text: command, 
            request: request, 
            response: actionResponse,
            handlerName: actionHandler.getName()
        });
        this.setState({
            actions: [...this.state.actions, newAction]
        });
        logger.info("App.sendAction: exit");
    }

    // after component is mounted
    componentDidMount() {
        logger.info("App.componentDidMount: enter");
        this.props.webCLIClient.connect(this.onActionCompleted);
        logger.info("App.componentDidMount: websocket is connected");
        logger.info("App.componentDidMount: exit");
    }

    // after component state changes
    componentDidUpdate(prevProps, prevState) {
        // commented since it is called too often
        // logger.info("App.componentDidUpdate: enter");
        // logger.info("App.componentDidUpdate: exit");
    }

    // after component is unmounted
    componentWillUnmount() {
        // disconnect upon unmount does not work, when you put top component
        // under <StrictMode>, since it will mount your component, then unmount
        // then mount again
        // if user close the browser tab, the web socket will be closed then
        logger.info("App.componentWillUnmount: enter");
        logger.info("App.componentWillUnmount: exit");
    }
    
    render() {
        return (
            <>
                <div id="answers">
                    {this.state.actions.map(action => this.props.webCLIClient.renderAction(action))}
                </div>
                <div>
                    <textarea 
                        id="command" 
                        name="command" 
                        rows="4" 
                        cols="50" 
                        className="question-panel"
                        onChange={async (event) => {
                            this.setState({command: event.target.value})
                        }}
                        value={this.state.command}
                    >
                    </textarea>
                    <button type="button" onClick={this.sendAction}>Send</button>
                </div>
            </>
        );
    }
}

export default App;

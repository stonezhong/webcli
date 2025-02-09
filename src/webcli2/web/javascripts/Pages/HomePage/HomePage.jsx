import _ from "lodash";
import React from 'react';
import Container from 'react-bootstrap/Container';
import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Button from 'react-bootstrap/Button';
import { SplitViewHorizontal } from "@/Components/SplitView";
import Spinner from 'react-bootstrap/Spinner';
import Alert from 'react-bootstrap/Alert';
import pino from 'pino';
import Stack from 'react-bootstrap/Stack';

import { 
    get_thread, create_action, remove_action_from_thread, update_action_title,
    update_thread_action_show_question, update_thread_action_show_answer
} from '@/apis';

import {
    getNextValue, dropItemFromReactState, updateMatchingItemsFromReactState, updateMatchingItemsFromReactStateAsync
} from '@/algo';

import './HomePage.css';

const logger = pino({
    level: 'debug',
    transport: {
        target: 'pino-pretty',
        options: { colorize: true },
    },
});

// Example of closing the connection after 10 seconds
// setTimeout(() => {
//     console.log("Closing WebSocket connection...");
//     socket.close();
// }, 10000);


class ThreadActionWrapper {
    /*******************
     * Action with some UI related stateful data
    */
    constructor(threadAction) {
        this.threadAction = threadAction;
        this.editing_title = false;     // editing title?
    }
}

/*******************************************************
 * In dev mode, when we have StrictMode at top level
 * A component may mount, then unmount, then mount
 * so we do not disconnect the web socket upon unmount
 * this is a dev behavior when StrictMode is used, 
 * In production mode (when StrictMode is not used), unmount won't happen
 * props
 *     threadId     : int
 *     wsUrl        : websocket url
 *     clientId     : str
 * 
 * removeAlert                  dismiss a given alert
 * addAlert                     add an alert
 * renderAction                 Render a given action
 * renderPendingAction          Render an action that is still pending
 * sendAction                   Create a new action
 * getActionRequestFromText     Try to handle input text using registered action handlers
 * connect                      Connect to web socket
 * onActionCompleted            called when an action is completed
 * 
 * -------------------------------------------------------------------------------------------------------------------
 * update action title          It only update the action title (a single action), it does not resync the entire thread
 * create action                It only add the new action to the bottom, it does not resync the entire thread
 */
export class HomePage extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            threadActionWrappers: [],
            command: "",
            thread_title:"",
            alerts: []
        };
    }

    removeAlert = (alert) => {
        this.setState({
            alerts: this.state.alerts.filter(it => it.id !== alert.id)
        })
    }

    addAlert = message => {
        const newAlert = {
            id: getNextValue({values:this.state.alerts.map(alert => alert.id)}),
            message: message
        };
        this.setState({
            alerts: [...this.state.alerts, newAlert]
        })
    }

    /**
     * Remove an action specified by actionWrapper. Web UI does not re-sync the entire thread.
     */
    deleteAction = async (action) => {
        await remove_action_from_thread({thread_id:this.props.threadId, action_id:action.id});
        dropItemFromReactState({
            element:this, 
            stateFieldName:"threadActionWrappers",
            shouldRemove: threadActionWrapper => threadActionWrapper.threadAction.action.id === action.id
        });
    }

    setActionShowQuestion = async (threadAction, show_question) => {
        await update_thread_action_show_question({
            thread_id:this.props.threadId, 
            action_id:threadAction.action.id,
            show_question
        });
        updateMatchingItemsFromReactState({
            element: this,
            stateFieldName:"threadActionWrappers",
            shouldUpdate: threadActionWrapper => threadActionWrapper.threadAction.action.id === threadAction.action.id,
            doUpdate: threadActionWrapper => {
                threadActionWrapper.threadAction.show_question = show_question;
            }
        });
    }

    setActionShowAnswer = async (threadAction, show_answer) => {
        await update_thread_action_show_answer({
            thread_id:this.props.threadId, 
            action_id:threadAction.action.id,
            show_answer
        });
        updateMatchingItemsFromReactState({
            element: this,
            stateFieldName:"threadActionWrappers",
            shouldUpdate: threadActionWrapper => threadActionWrapper.threadAction.action.id === threadAction.action.id,
            doUpdate: threadActionWrapper => {
                threadActionWrapper.threadAction.show_answer = show_answer;
            }
        });
    }

    setActionTitle = async (action, title) => {
        updateMatchingItemsFromReactState({
            element: this,
            stateFieldName:"threadActionWrappers",
            shouldUpdate: threadActionWrapper => threadActionWrapper.threadAction.action.id === action.id,
            doUpdate: threadActionWrapper => {
                threadActionWrapper.threadAction.action.title = title;
            }
        });
    }

    setActionEditingTitle = async (threadActionWrapper, editing_title) => {
        if (!editing_title) {
            await update_action_title({
                action_id:threadActionWrapper.threadAction.action.id, 
                title:threadActionWrapper.threadAction.action.title
            });
        }
        updateMatchingItemsFromReactState({
            element: this,
            stateFieldName:"threadActionWrappers",
            shouldUpdate: xThreadActionWrapper => xThreadActionWrapper.threadAction.action.id === threadActionWrapper.threadAction.action.id,
            doUpdate: xThreadActionWrapper => {
                xThreadActionWrapper.editing_title = editing_title;
            }
        });
    }

    /**********************************************************************************
     * Render an action
     * action: Action
     * We let the action to render the request and response
     */
    renderAction(threadActionWrapper) {
        const threadAction = threadActionWrapper.threadAction;
        const action = threadAction.action;
        const actionHandler = this.props.actionHandlerMap.get(action.handler_name);
        return <div>
            <div>
                <div>
                    <Stack direction="horizontal" gap={3}>
                        <Button 
                            variant="primary" 
                            size="sm" 
                            className="me-2"
                            onClick={async event=>{
                                await this.deleteAction(action);
                            }}
                        >
                            Delete
                        </Button>
                        <Form.Control 
                            type="input" 
                            value={action.title} 
                            disabled={!threadActionWrapper.editing_title}
                            onChange={async event=>{
                                await this.setActionTitle(action, event.target.value);
                            }}
                        />
                    </Stack>
                </div>
                <Form.Check
                    inline
                    type="checkbox"
                    label="Show Question"
                    checked={threadAction.show_question}
                    onChange={async event => {
                        await this.setActionShowQuestion(threadAction, event.target.checked);
                    }}
                />
                <Form.Check
                    inline
                    type="checkbox"
                    label="Show Answer"
                    checked={threadAction.show_answer}
                    onChange={async event => {
                        await this.setActionShowAnswer(threadAction, event.target.checked);
                    }}
                />
                <Form.Check
                    inline
                    type="checkbox"
                    label="Edit Title"
                    checked={threadActionWrapper.editing_title}
                    onChange={async event => {
                        await this.setActionEditingTitle(threadActionWrapper, event.target.checked);
                    }}
                />
            </div>
            {
                (threadAction.show_question)?<pre>{action.raw_text}</pre>:null
            }
            {
                (threadAction.show_answer)?((action.response === null)?this.renderPendingAction():actionHandler.renderAction(action)):null
            }
        </div>;
    }

    renderPendingAction() {
        return <Spinner animation="border" role="status">
            <span className="visually-hidden">Loading...</span>
        </Spinner>
    }

    /******************************************************************************
     * Given a piece of text, try to find if an action handler can recognize it
     ******************************************************************************/
    getActionRequestFromText(text) {
        for (const actionHandler of this.props.actionHandlerMap.values()) {
            const request = actionHandler.getActionRequestFromText(text);
            if (request !== null) {
                return [actionHandler, request];
            }
        }
        return [null, null];
    }

    /**********************************************************************************
     * Called when user hit "submit" button
     */
    sendAction = async () => {
        logger.info("HomePage.sendAction: enter");
        const command = this.state.command;
        logger.info(`HomePage.sendAction: command=${command}`);
        const [actionHandler, request] = this.getActionRequestFromText(command);

        // if no action handler recognize the text, we will ignore it
        if (request === null) {
            // TODO: pop up some error message
            this.addAlert("Unrecognized command");
            logger.info("HomePage.sendAction: unrecognized command");
            logger.info("HomePage.sendAction: exit");
            return;
        }

        try {
            const threadAction = await create_action({thread_id:this.props.threadId, request, title:"question", raw_text:command});
            logger.info("HomePage.sendAction: server response: ", threadAction);
            this.setState({
                threadActionWrappers: [...this.state.threadActionWrappers, new ThreadActionWrapper(threadAction)]
            });
            logger.info("HomePage.sendAction: exit");
        } 
        catch(err) {
            // TODO: pop up some error message
            this.addAlert(err.message);
            logger.info("HomePage.sendAction: error, ", err.message);
            return;
        }

    }

    // after component is mounted
    async componentDidMount() {
        logger.info("HomePage.componentDidMount: enter");
        
        const thread = await get_thread(this.props.threadId);
        const threadActionWrappers = thread.thread_actions.map(threadAction => new ThreadActionWrapper(threadAction));
        this.setState({
            thread_title: thread.title,
            threadActionWrappers
        })

        this.connect();

        logger.info("HomePage.componentDidMount: websocket is connected");
        logger.info("HomePage.componentDidMount: exit");
    }

    // after component state changes
    componentDidUpdate(prevProps, prevState) {
        // commented since it is called too often
        // console.log("App.componentDidUpdate: enter");
        // console.log("App.componentDidUpdate: exit");
    }

    // after component is unmounted
    componentWillUnmount() {
        logger.info("HomePage.componentWillUnmount: enter");
        // const notificationManager = this.props.notificationManager;
        // notificationManager.disconnect();
        // console.log("App.componentWillUnmount: websocket is disconnected");
        logger.info("HomePage.componentWillUnmount: exit");
    }

    onActionCompleted = async (actionId, response) => {
        await updateMatchingItemsFromReactStateAsync({
            element: this,
            stateFieldName:"threadActionWrappers",
            shouldUpdate: async threadActionWrapper => threadActionWrapper.threadAction.action.id === actionId,
            doUpdate: async threadActionWrapper => {
                threadActionWrapper.threadAction.action.response = response;
            }
        });
    }

    /*******************
     * Connecto to web socket
     * onActionCompleted: called upon success
     * 
     */
    connect() {
        logger.info("HomePage.connect: enter");
        if (window.webcli_socket) {
            logger.info("HomePage.connect: WebSocket is already connected!");
            return;
        }

        window.webcli_socket = new WebSocket(this.props.wsUrl);

        // Event: Connection opened
        window.webcli_socket.addEventListener("open", () => {
            logger.info("websocket.open: enter");
            window.webcli_socket.send(JSON.stringify({ client_id: this.props.clientId }));
            logger.info("websocket.open: exit");
        });

        // Event: Connection closed
        window.webcli_socket.addEventListener("close", (event) => {
            logger.info("websocket.close: enter");
            logger.info(`websocket.close: connection closed (Code: ${event.code}, Reason: ${event.reason})`);
            window.webcli_socket = null;
            logger.info("websocket.close: exit");           
        });

        // Event: Error
        window.webcli_socket.addEventListener("error", (error) => {
            logger.info("websocket.error: enter");
            logger.info("websocket.error: ", error);
            // shall we consider ourself disconnected?
            logger.info("websocket.error: enter");
        });

        // Event: Message received
        window.webcli_socket.addEventListener("message", async (event) => {
            logger.info("websocket.message: enter");
            logger.info("websocket.message: received ", event.data);
            try {
                if (event.data == "ping") {
                    logger.info("websocket.message: ping from server, ignore");
                    logger.info("websocket.message: exit");
                    return;
                }
                const parsedData = JSON.parse(event.data);
                logger.info("websocket.message: parsed ", parsedData);

                await this.onActionCompleted(parsedData.action_id, parsedData.response);
            } catch (error) {
                error("websocket.message: parse JSON error ", error);
            }
            logger.info("websocket.message: exit");
        });
        logger.info("HomePage.connect: exit");
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
                                this.state.threadActionWrappers.map(threadActionWrapper => {
                                    return <div key={threadActionWrapper.threadAction.id} className="mb-2">
                                        {this.renderAction(threadActionWrapper)}
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

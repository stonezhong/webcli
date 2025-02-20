import _ from "lodash";
import React, { useEffect, useRef } from 'react';
import Container from 'react-bootstrap/Container';
import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Button from 'react-bootstrap/Button';
import { SplitViewHorizontal } from "@/Components/SplitView";
import Spinner from 'react-bootstrap/Spinner';
import Alert from 'react-bootstrap/Alert';
import pino from 'pino';
import { MdModeEdit, MdDelete } from "react-icons/md";
import { setStateAsync } from "@/tools.js";
import { PageHeader } from "@/Components/PageHeader";
import ReactMarkdown from "react-markdown";
import mermaid from 'mermaid';

import { 
    get_thread, create_action, remove_action_from_thread, update_action_title,
    update_thread_action_show_question, update_thread_action_show_answer,
    update_thread_title, update_thread_description
} from '@/apis';

import {
    getNextValue, dropItemFromReactState, updateMatchingItemsFromReactState, updateMatchingItemsFromReactStateAsync
} from '@/algo';

import '@/global.scss';
import './ThreadPage.scss';

const MermaidDiagram = ({ chart }) => {
    const ref = useRef(null);

    useEffect(() => {
        mermaid.initialize({ startOnLoad: true });
        mermaid.run();
    }, [chart]);

    return <div className="mermaid" ref={ref}>{chart}</div>;
};

/****************************************
 Page Layout

 div
    PageHeader
    div class="cli-page"
        SplitViewHorizontal
            Container (the container to display questions & answers)
                Row
                    Col
                        array of Alert (for showing error message)
                Row
                    Col
                        table
                            tr for thread title using <EditableText>
                            tr for thread description using <EditableText>
                <hr />

                Row
                    Col
                        div class="actions-panel"
                            array of divs, 
                                table
                                    tr for question title
                                div class="questio-wrapper"
                                div class="answer-wrapper"
                                

            Container (the container for user input text)
 */
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
        // this.editing_title = false;     // editing title?
    }
}

class EditableText extends React.Component {
    /*******************
     * props
     *     className:   (optional) extra classname for the tr element
     *     onSave:      (Must provide) callback, called when text is saved
     *     onError:     caller to display error message
    */
    constructor(props) {
        super(props);
        this.editor_ref = React.createRef();
        this.state = {
            text:this.props.text,
            saved_text:"",
            editing: false
        };
    }

    async componentDidUpdate(prevProps, prevState) {
        if (this.props.text !== prevProps.text) {
            await setStateAsync(this, {
                text: this.props.text,
            });
        }
    }

    render_editing_mode = () => {
        if (this.props.multiLine) {
            return <Form.Control
                ref={this.editor_ref}
                className="editable-text-text"
                as="textarea" rows={3}
                value={this.state.saved_text}
                onKeyDown={async event => {
                    if (event.key === "Escape") {
                        // user can hit Escape key to cancel the edit
                        await setStateAsync(this, {editing: false});
                    } else if (event.ctrlKey && event.key === "Enter") {
                        // user can hit enter to submit the change
                        try {
                            await this.props.onSave(this.state.saved_text);
                            await setStateAsync(this, {
                                editing: false,
                                text: this.state.saved_text   
                            });
                        }
                        catch (err) {
                            await this.props.onError(err);
                        }
                    }
                }}
                onChange={async event => {
                    await setStateAsync(this, {saved_text:event.target.value});
                }}
            />;
        } else {
            return <Form.Control
                ref={this.editor_ref}
                className="editable-text-text"
                value={this.state.saved_text}
                onKeyDown={async event => {
                    if (event.key === "Escape") {
                        // user can hit Escape key to cancel the edit
                        await setStateAsync(this, {editing: false});
                    } else if (event.key === "Enter") {
                        // user can hit enter to submit the change
                        try {
                            await this.props.onSave(this.state.saved_text);
                            await setStateAsync(this, {
                                editing: false,
                                text: this.state.saved_text   
                            });
                        }
                        catch (err) {
                            await this.props.onError(err);
                        }
                    }
                }}
                onChange={async event => {
                    await setStateAsync(this, {saved_text:event.target.value})
                }}
            />;
        }
    }
    
    render_non_editing_mode = () => {
        if (this.props.multiLine) {
            return <Form.Control
                ref={this.editor_ref}
                className="editable-text-text"
                as="textarea" rows={3}
                style={{
                    backgroundColor: 'transparent',
                    border: '1px transparent'
                }}
                disabled
                value={this.state.text}
            />
        } else {
            return <Form.Control
                ref={this.editor_ref}
                className="editable-text-text"
                style={{
                    backgroundColor: 'transparent',
                    border: '1px transparent'
                }}
                disabled
                value={this.state.text}
            />
        }
    }

    render() {
        return <tr className={`${this.props.className} editable-text`}>
            <td className="tools-column">
                {this.props.children}
                <MdModeEdit 
                    className="editable-text-icon"
                    onClick={async event => {
                        await setStateAsync(this, {editing: true, saved_text: this.state.text});
                        if (this.editor_ref.current) {
                            this.editor_ref.current.focus(); // Set focus to the editor
                        }
                    }}
                    style={{
                        display: this.state.editing?"none":"inline"
                    }}
                />
            </td>
            <td>
            {
                this.state.editing?this.render_editing_mode():this.render_non_editing_mode()
            }
            </td>
        </tr>;
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
  * 
 * -------------------------------------------------------------------------------------------------------------------
 * update action title          It only update the action title (a single action), it does not resync the entire thread
 * create action                It only add the new action to the bottom, it does not resync the entire thread
 */
export class ThreadPage extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            threadActionWrappers: [],
            command: "",
            thread_title:"",
            thread_description:"",
            alerts: [],
            editing_title: false,
        };
    }

    removeAlert = async alert => {
        await setStateAsync(this, {
            alerts: this.state.alerts.filter(it => it.id !== alert.id)
        })
    }

    addAlert = async message => {
        const newAlert = {
            id: getNextValue({values:this.state.alerts.map(alert => alert.id)}),
            message: message
        };
        await setStateAsync(this, {
            alerts: [...this.state.alerts, newAlert]
        });
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

    renderResponseChunk(action, response_chunk) {
        if (response_chunk.mime === "text/html") {
            return <div key={response_chunk.id} dangerouslySetInnerHTML={{ __html: response_chunk.text_content }} />;
        }
        if (response_chunk.mime === "text/markdown") {
            return <ReactMarkdown key={response_chunk.id}>{response_chunk.text_content}</ReactMarkdown>;
        }
        if (response_chunk.mime === "application/x-webcli-mermaid") {
            return <MermaidDiagram key={response_chunk.id} chart={response_chunk.text_content} />;
        }
        if (response_chunk.mime === "text/plain") {
            return <pre key={response_chunk.id}>{response_chunk.text_content}</pre>;
        }
        if (response_chunk.mime === "image/png") {
            const url = `/resources/${action.id}/${response_chunk.id}.png`
            return <img key={response_chunk.id} src={url}/>;
        }

        // for anything unknown, show text
        return <pre key={response_chunk.id}>{response_chunk.text_content}</pre>;
    }

    renderAnswer(action) {
        /*******************
         * action looks like this
         * {
         *     id: 2,
         *     is_completed: false,
         *     completed_at: null,
         *     created_at: "2025-02-17T08:38:14.632326",
         *     raw_text: "aaa",
         *     request: {},
         *     response_chunks: [
         *         {
         *             id: 1,
         *             action_id: 2,
         *             mime: "text/html",
         *             order: 1,
         *             text_content: "<h1>Hello</h1>",
         *             binary_content: null,
         *         }
         *     ],
         *     title: "aaa"
         * 
         * }
         */
        return [
            ...action.response_chunks.map(response_chunk => this.renderResponseChunk(action, response_chunk)),
            action.is_completed?null:<Spinner key="loading" animation="border" role="status">
                <span className="visually-hidden">Loading...</span>
            </Spinner>
        ];
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
        return <div key={threadActionWrapper.threadAction.id}>
            <table style={{width: "100%"}} className="question-table">
                <tbody>
                    <EditableText
                        className="action-title-editor"
                        multiLine={false}
                        text={action.title}
                        onError = {
                            async err => await this.addAlert(`Cannot change action title, error: ${err.message}`)
                        }
                        onSave = {async newText => {
                            await update_action_title({
                                action_id:threadActionWrapper.threadAction.action.id,
                                title:newText
                            });
                            await this.setActionTitle(action, newText);
                        }}
                    >
                        <Form.Check
                            inline
                            type="switch"
                            label="Q"
                            checked={threadAction.show_question}
                            onChange={async event => {
                                await this.setActionShowQuestion(threadAction, event.target.checked);
                            }}        
                        />
                        
                        <Form.Check
                            inline
                            type="switch"
                            label="A"
                            checked={threadAction.show_answer}
                            onChange={async event => {
                                await this.setActionShowAnswer(threadAction, event.target.checked);
                            }}
                        />
                        <MdDelete className="standard-icon clickable-icon"
                            onClick={async event=>{
                                await this.deleteAction(action);
                            }}
                        />
                    </EditableText>
                </tbody>
            </table>
            
            {
                (threadAction.show_question)?<div className="action-question-wrapper"><pre className="question-raw-text">{action.raw_text}</pre></div>:null
            }
            {
                (threadAction.show_answer)?(<div className="action-answer-wrapper">{this.renderAnswer(action)}</div>):null
            }
            
        </div>;
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
        logger.info("ThreadPage.sendAction: enter");
        const command = this.state.command;
        logger.info(`ThreadPage.sendAction: command=${command}`);
        const [actionHandler, request] = this.getActionRequestFromText(command);

        // if no action handler recognize the text, we will ignore it
        if (request === null) {
            // TODO: pop up some error message
            await this.addAlert("Unrecognized command");
            logger.info("ThreadPage.sendAction: unrecognized command");
            logger.info("ThreadPage.sendAction: exit");
            return;
        }

        try {
            const threadAction = await create_action({thread_id:this.props.threadId, request, title:"question", raw_text:command});
            logger.info("ThreadPage.sendAction: server response: ", threadAction);
            await setStateAsync(this, {
                threadActionWrappers: [...this.state.threadActionWrappers, new ThreadActionWrapper(threadAction)]
            });
            logger.info("ThreadPage.sendAction: exit");
        } 
        catch(err) {
            // TODO: pop up some error message
            await this.addAlert(err.message);
            logger.info("ThreadPage.sendAction: error, ", err.message);
            return;
        }

    }

    // after component is mounted
    async componentDidMount() {
        logger.info("ThreadPage.componentDidMount: enter");
        
        const thread = await get_thread(this.props.threadId);
        const threadActionWrappers = thread.thread_actions.map(threadAction => new ThreadActionWrapper(threadAction));
        await setStateAsync(this, {
            thread_title: thread.title,
            thread_description: thread.description,
            threadActionWrappers
        })

        this.connect();

        logger.info("ThreadPage.componentDidMount: websocket is connected");
        logger.info("ThreadPage.componentDidMount: exit");
    }

    // after component state changes
    componentDidUpdate(prevProps, prevState) {
        // commented since it is called too often
        // console.log("App.componentDidUpdate: enter");
        // console.log("App.componentDidUpdate: exit");
    }

    // after component is unmounted
    componentWillUnmount() {
        logger.info("ThreadPage.componentWillUnmount: enter");
        // const notificationManager = this.props.notificationManager;
        // notificationManager.disconnect();
        // console.log("App.componentWillUnmount: websocket is disconnected");
        logger.info("ThreadPage.componentWillUnmount: exit");
    }

    onThreadEvent = async threadEvent => {
        /******************************************
         * threadEvent looks like this
         * {
         *     action_id: 1
         *     mime: "text/plain",
         *     order: 6
         *     text_content: "blah",
         *     type: "action-response-chunk"
         * }
         */
        if (threadEvent.type === "action-response-chunk") {
            const action_id = threadEvent.action_id;
            const threadActionWrapper = _.find(
                this.state.threadActionWrappers, taw => taw.threadAction.action.id === action_id
            );
            if (_.isUndefined(threadActionWrapper)) {
                return;
            }
            const new_response_chunks1 = threadActionWrapper.threadAction.action.response_chunks.filter(response_chunk => response_chunk.order < threadEvent.order);
            const new_response_chunks2 = threadActionWrapper.threadAction.action.response_chunks.filter(response_chunk => response_chunk.order > threadEvent.order);
            const new_response_chunks = [
                ...new_response_chunks1,
                {
                    action_id: action_id,
                    binary_content: null,
                    id: threadEvent.id,
                    mime: threadEvent.mime,
                    text_content: threadEvent.text_content,
                    order: threadEvent.order
                },
                ...new_response_chunks2,
            ];
            threadActionWrapper.threadAction.action.response_chunks = new_response_chunks;
            this.setState({threadActionWrappers: this.state.threadActionWrappers});
            return;
        }

        if (threadEvent.type === "action-completed") {
            const action_id = threadEvent.action_id;
            const threadActionWrapper = _.find(
                this.state.threadActionWrappers, taw => taw.threadAction.action.id === action_id
            );
            if (_.isUndefined(threadActionWrapper)) {
                return;
            }
            threadActionWrapper.threadAction.action.is_completed = true;
            this.setState({threadActionWrappers: this.state.threadActionWrappers});
            return;
        }

    }

    connect() {
        logger.info("ThreadPage.connect: enter");
        if (window.webcli_socket) {
            logger.info("ThreadPage.connect: WebSocket is already connected!");
            return;
        }

        window.webcli_socket = new WebSocket(this.props.wsUrl);

        // Event: Connection opened
        window.webcli_socket.addEventListener("open", () => {
            logger.info("websocket.open: enter");
            window.webcli_socket.send(JSON.stringify({ 
                client_id: this.props.clientId,
                thread_id: this.props.threadId,
            }));
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

                await this.onThreadEvent(parsedData);
            } catch (error) {
                error("websocket.message: parse JSON error ", error);
            }
            logger.info("websocket.message: exit");
        });
        logger.info("ThreadPage.connect: exit");
    }


    render() {
        return (
            <div>
                <PageHeader />
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
                                        onClose={async () => await this.removeAlert(alert)} 
                                    >
                                        {alert.message}
                                    </Alert>
                                )}
                                </Col>
                            </Row>

                            <Row>
                                <Col>
                                    <table style={{width: "100%"}}>
                                        <tbody>
                                            <EditableText
                                                className="thread-title-editor"
                                                multiLine={false}
                                                text={this.state.thread_title}
                                                onError = {
                                                    async err => await this.addAlert(`Cannot change thread title, error: ${err.message}`)
                                                }
                                                onSave = {async newText => {
                                                    await update_thread_title({
                                                        thread_id:this.props.threadId,
                                                        title: newText
                                                    });
                                                    await setStateAsync(this, {
                                                        thread_title:newText
                                                    });
                                                }}
                                            />
                                            <EditableText
                                                className="description-editor"
                                                multiLine={true}
                                                text={this.state.thread_description}
                                                onError = {
                                                    async err => await this.addAlert(`Cannot change thread description, error: ${err.message}`)
                                                }
                                                onSave = {async newText => {
                                                    await update_thread_description({
                                                        thread_id:this.props.threadId,
                                                        description: newText
                                                    });
                                                    await setStateAsync(this, {
                                                        thread_description:newText
                                                    });
                                                }}
                                            />
                                        </tbody>
                                    </table>
                                </Col>
                            </Row>

                            <hr className="thin-spacebar" />

                            <Row>
                                <Col>
                                    <div className="actions-panel">
                                    {
                                        this.state.threadActionWrappers.map(threadActionWrapper => this.renderAction(threadActionWrapper))
                                    }
                                    </div>
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
                                            await setStateAsync(this, {
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
            </div>
        );
    }
}

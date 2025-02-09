import _ from "lodash";
import React from 'react';
import Container from 'react-bootstrap/Container';
import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Button from 'react-bootstrap/Button';
import { list_threads } from "@/apis";

import './ThreadsPage.css';

export class ThreadsPage extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            threads: []
        };
    }

    // after component is mounted
    async componentDidMount() {
        console.log("ThreadsPage.componentDidMount: enter");
        const threads = await list_threads();
        this.setState({threads:threads})
        console.log("ThreadsPage.componentDidMount: exit");
    }

    // after component state changes
    componentDidUpdate(prevProps, prevState) {
        // commented since it is called too often
        // console.log("App.componentDidUpdate: enter");
        // console.log("App.componentDidUpdate: exit");
    }

    // after component is unmounted
    componentWillUnmount() {
        console.log("ThreadsPage.componentWillUnmount: enter");
        // const notificationManager = this.props.notificationManager;
        // notificationManager.disconnect();
        // console.log("App.componentWillUnmount: websocket is disconnected");
        console.log("ThreadsPage.componentWillUnmount: exit");
    }

    render() {
        return (
            <Container fluid >
                <Row>
                    <Col>
                        <h1>Threads</h1>
                    </Col>
                </Row>
                <Row>
                    <Col>
                    {
                        this.state.threads.map(thread => 
                            <div key={thread.id}>
                                <a href={`/threads/${thread.id}`}>{thread.title}</a>
                            </div>
                        )
                    }
                    </Col>
                </Row>
            </Container>
        );
    }
}



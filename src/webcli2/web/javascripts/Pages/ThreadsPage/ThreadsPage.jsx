import _ from "lodash";
import React from 'react';
import Container from 'react-bootstrap/Container';
import Card from 'react-bootstrap/Card';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import { list_threads, create_thread, delete_thread } from "@/apis";
import Button from 'react-bootstrap/Button';
import { PageHeader } from "@/Components/PageHeader";

import '@/global.scss';
import './ThreadsPage.scss';

export class ThreadsPage extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            threads: []
        };
    }

    // after component is mounted
    async componentDidMount() {
        const threads = await list_threads();
        this.setState({threads:threads})
    }

    do_create_thread = async () => {
        await create_thread({title:"no title", description:"no description"});
        const threads = await list_threads();
        this.setState({threads:threads})
    };

    do_delete_thread = async id => {
        await delete_thread({id});
        const threads = await list_threads();
        this.setState({threads:threads})
    };

    render_thread(thread) {       
        const ret = <Col xs={3} key={thread.id}><Card data-purpose='thread'>
            <Card.Body>
                <Card.Title>
                    {thread.title}
                </Card.Title>
                <Card.Text>
                    {thread.description}
                </Card.Text>
                <Card.Link href={`/threads/${thread.id}`}>Open</Card.Link>
                <Card.Link href="#" onClick={async event=> {
                    await this.do_delete_thread(thread.id);
                }}>Delete</Card.Link>
            </Card.Body>
        </Card></Col>;
        return ret;
    }

    render_add_thread() {
        const ret = <Col xs={3}><Card data-purpose='thread'>
            <Card.Body>
                <Card.Title>
                </Card.Title>
                <Card.Text style={{textAlign: "center"}}>
                    <Button onClick={this.do_create_thread}>Create New Thread</Button>
                </Card.Text>
                <Card.Link style={{visibility: 'hidden'}} href="#">Open</Card.Link>
                <Card.Link style={{visibility: 'hidden'}} href="#">Delete</Card.Link>
            </Card.Body>
        </Card></Col>;
        return ret;
    }

    render() {
        return (
            <div>
                <PageHeader />
                <Container fluid >
                    <Row>
                        <Col>
                            <h1>Threads</h1>
                        </Col>
                    </Row>
                    <Row>
                        {
                            this.state.threads.map(thread => this.render_thread(thread))
                        }
                        { this.render_add_thread() }
                    </Row>
                </Container>
            </div>
        );
    }
}



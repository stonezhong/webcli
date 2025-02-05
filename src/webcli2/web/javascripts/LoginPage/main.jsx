import React from 'react';
import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Button from 'react-bootstrap/Button';

export class LoginPage extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            username: "",
            password: ""
        };
    }

    render() {
        return <div
            className="mt-2"
            style={{
                "marginLeft": "auto",
                "marginRight": "auto",
                width: "600px"
            }}
        >
            <Form onSubmit={this.onLogin} method="POST">
                <Form.Group as={Row} className="mb-3" controlId="login.username">
                    <Form.Label column sm="2">User name</Form.Label>
                    <Col sm="10">
                        <Form.Control 
                            type="input" 
                            value={this.state.username}
                            name="username"
                            onChange={event => {
                                this.setState({username: event.target.value})
                            }}
                        />
                    </Col>
                </Form.Group>
                <Form.Group as={Row} className="mb-3" controlId="login.password">
                    <Form.Label column sm="2">Password</Form.Label>
                    <Col sm="10">
                        <Form.Control
                            type="password" 
                            value={this.state.password}
                            name="password"
                            onChange={event => {
                                this.setState({password: event.target.value})
                            }}
                        />
                    </Col>
                </Form.Group>
                <Button variant="primary" type="submit">login</Button>
            </Form>
        </div>;
    }
}

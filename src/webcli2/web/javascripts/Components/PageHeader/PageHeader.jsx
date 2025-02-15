import React from 'react';
import Container from 'react-bootstrap/Container';
import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import Form from 'react-bootstrap/Form';
import Button from 'react-bootstrap/Button';
import './PageHeader.scss';

export class PageHeader extends React.Component {
    render() {
        return <Navbar sticky="top" className="page-header">
        <Container fluid>
          <Navbar.Toggle aria-controls="basic-navbar-nav" />
          <Navbar.Collapse id="basic-navbar-nav">
            <Nav className="me-auto">
              <Nav.Link href="/threads">Threads</Nav.Link>
            </Nav>
            <Nav className=".col-auto">
                <Form action="/logout" method="POST" >
                    <Button variant="link" type="submit">Logout</Button>
                </Form>
            </Nav>            
          </Navbar.Collapse>
        </Container>
      </Navbar>;
    }
}

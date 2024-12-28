import React, {useState} from 'react';
import './App.css';

import Container from 'react-bootstrap/Container';
import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Button from 'react-bootstrap/Button';


const App = () => {
  const [command, setCommand] = useState(''); // State to hold the textarea content
  const [answerComponents, setAnswerComponents] = useState([])

  const addAnswerComponent = (answerComponent) => {
    setAnswerComponents([...answerComponents, answerComponent]);
  };

  const onCommandChange = (event) => {
    setCommand(event.target.value);
  };

  // Give an answer -- a JSON object, return a ReactDOM element which renders the answer
  const renderAnswer = async (answer) => {
    if (answer.ui_type === "message") {
      return <pre>{answer.message}</pre>
    }

  }

  const fetchData = async (event) => {
    console.log("step 1");
    const response = await fetch('/test');
    if (!response.ok) {
      console.log(response);
    }
    const answer = await response.json();
    
    // for different result, we will use different UI component to render it
    // as a test, let's always put some funny string here
    const answerComponent = renderAnswer(answer);
    addAnswerComponent(answerComponent);

    console.log(result);
  }

  return (
    <div className='cli-page'>
      <Container fluid className="answer-panel">
        <div className="answer-inner-panel">
          {answerComponents.map((answerComponent, index) => (
            <div key={index}>{answerComponent}</div>
          ))}
        </div>
      </Container>
      <Container fluid className="question-panel">
        <div className='question-inner-panel'>
          <Row>
            <Col>
              <Form>
                <Form.Control as="textarea" rows={6} 
                  value={command}
                  onChange={onCommandChange}
                  placeholder='Please input your command'
                />
              </Form>
            </Col>
            <Col xs={1}>
              <Button 
                variant="primary"
                onClick={fetchData}
              >Submit</Button>
            </Col>
          </Row>
        </div>
      </Container>
    </div>
  );
};

export default App;

import React from 'react';

import { FaBeer } from 'react-icons/fa';
import { FaSpinner } from "react-icons/fa";
import ReactMarkdown from "react-markdown";
import { VictoryBar, VictoryChart, VictoryAxis, VictoryTheme } from "victory";

import './TestPage.css';


export class TestPage extends React.Component {
    render_react_icons() {
        return <div>
            <h1>React Icons</h1>
            <a href="https://react-icons.github.io/react-icons/">sdk document</a>
            <div>
                <FaBeer />
                <FaSpinner className="animate-spin"/>
            </div>
        </div>;
    }

    render_markdown() {
        return <div>
            <h1>React Markdown</h1>
            <ReactMarkdown>{"# Hello"}</ReactMarkdown>
        </div>;
    }

    render_victory() {
        const data = [
            { month: "2024-01", sales: 4000 },
            { month: "2024-02", sales: 3000 },
            { month: "2024-03", sales: 5000 },
            { month: "2024-04", sales: 4500 },
        ];
        return <div style={{height: "400px"}}>
            <a href="https://github.com/FormidableLabs/victory">Victory</a>
            <VictoryChart theme={VictoryTheme.material} domainPadding={20}>
                <VictoryAxis tickValues={["2024-01", "2024-02", "2024-03", "2024-04"]} />
                <VictoryAxis dependentAxis />
                <VictoryBar data={data} x="month" y="sales" />
            </VictoryChart>
        </div>;
    }

    render() {
        return <div>
            {this.render_react_icons()}
            {this.render_markdown()}
            {this.render_victory()}
        </div>;
    }
}

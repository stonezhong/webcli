import React, { useState } from "react";
import "./SplitView.css";

const SplitViewHorizontal = (props) => {
    const [dividerPosition, setDividerPosition] = useState(50); // Initial position in percentage

    const handleMouseDown = (e) => {
        e.preventDefault();
        const startY = e.clientY;
        const startDividerPosition = dividerPosition;

        const onMouseMove = (moveEvent) => {
            const deltaY = moveEvent.clientY - startY;
            const newDividerPosition = Math.min(
                Math.max(startDividerPosition + (deltaY / window.innerHeight) * 100, 10),
                90
            );
            setDividerPosition(newDividerPosition);
        };

        const onMouseUp = () => {
            window.removeEventListener("mousemove", onMouseMove);
            window.removeEventListener("mouseup", onMouseUp);
        };

        window.addEventListener("mousemove", onMouseMove);
        window.addEventListener("mouseup", onMouseUp);
    };

    return (
        <div className="split-view-horizontal">
            <div
                className="pane top-pane"
                style={{ height: `${dividerPosition}%` }}
            >
                {props.children[0]}
            </div>
            <div
                className="divider"
                onMouseDown={handleMouseDown}
                style={{ top: `${dividerPosition}%` }}
            ></div>
            <div
                className="pane bottom-pane"
                style={{ height: `${100 - dividerPosition}%` }}
            >
                {props.children[1]}
            </div>
        </div>
    );
};

export default SplitViewHorizontal;

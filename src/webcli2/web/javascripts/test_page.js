import React from 'react';
import { createRoot } from 'react-dom/client';
import { TestPage } from './Pages/TestPage';
import { StrictMode } from 'react';

const domNode = document.getElementById('webcli');
const root = createRoot(domNode);
root.render(
    <StrictMode>
        <TestPage />
    </StrictMode>
);


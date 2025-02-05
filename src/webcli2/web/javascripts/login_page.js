import React from 'react';
import { createRoot } from 'react-dom/client';
import { LoginPage } from './LoginPage';
import { StrictMode } from 'react';

const domNode = document.getElementById('webcli');
const root = createRoot(domNode);
root.render(
    <StrictMode>
        <LoginPage />
    </StrictMode>
);


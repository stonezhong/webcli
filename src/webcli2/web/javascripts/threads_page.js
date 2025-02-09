import React from 'react';
import { createRoot } from 'react-dom/client';
import { ThreadsPage } from '@/Pages/ThreadsPage';
import { StrictMode } from 'react';

const domNode = document.getElementById('webcli');
const root = createRoot(domNode);
root.render(
    <StrictMode>
        <ThreadsPage />
    </StrictMode>
);

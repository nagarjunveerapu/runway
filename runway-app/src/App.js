import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import RunwayApp from './RunwayApp';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import ProtectedRoute from './components/Auth/ProtectedRoute';
import { AppProvider } from './context/AppContext';
import { AuthProvider } from './context/AuthContext';
import CSVUpload from './components/Upload/CSVUpload';

export default function App(){
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/upload" element={
            <ProtectedRoute>
              <AppProvider>
                <CSVUpload onUploadComplete={() => window.location.href = '/'} />
              </AppProvider>
            </ProtectedRoute>
          } />
          <Route path="/" element={
            <ProtectedRoute>
              <AppProvider>
                <RunwayApp />
              </AppProvider>
            </ProtectedRoute>
          } />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
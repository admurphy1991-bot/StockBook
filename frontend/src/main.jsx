import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import SignPage from './SignPage.jsx'
import './index.css'

const signToken = new URLSearchParams(window.location.search).get('sign')

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {signToken ? <SignPage token={signToken} /> : <App />}
  </React.StrictMode>
)

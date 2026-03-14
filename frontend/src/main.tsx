import { createRoot } from "react-dom/client";
import { GoogleOAuthProvider } from '@react-oauth/google';
import App from "./App.tsx";
import "./index.css";

const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '622819446086-58hornf0c16j18ea49b1l90gslbd3res.apps.googleusercontent.com';

createRoot(document.getElementById("root")!).render(
  <GoogleOAuthProvider clientId={clientId}>
    <App />
  </GoogleOAuthProvider>
);

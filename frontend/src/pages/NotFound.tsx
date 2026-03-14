import { useLocation } from "react-router-dom";
import { useEffect } from "react";

const NotFound = () => {
    const location = useLocation();

    useEffect(() => {
        console.error("404 Error: User attempted to access non-existent route:", location.pathname);
    }, [location.pathname]);

    return (
        <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)', color: 'var(--text)', fontFamily: 'inherit' }}>
            <div style={{ textAlign: "center" }}>
                <h1 style={{ marginBottom: 16, fontSize: 48, fontWeight: 700, color: 'var(--green)' }}>404</h1>
                <p style={{ marginBottom: 16, fontSize: 20, color: 'var(--text3)' }}>Oops! Page not found</p>
                <a href="/" style={{ color: 'var(--text)', textDecoration: 'underline' }}>
                    Return to Home
                </a>
            </div>
        </div>
    );
};

export default NotFound;

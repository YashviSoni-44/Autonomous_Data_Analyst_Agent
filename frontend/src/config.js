// Central API configuration for frontend
// Default to port 8004 since port 8000 is occupied by an external service on this system
export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8004';

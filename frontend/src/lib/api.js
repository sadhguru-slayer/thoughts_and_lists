import axios from 'axios';

const api = axios.create({
    baseURL: 'http://127.0.0.1:8000',
});

// Add a request interceptor
api.interceptors.request.use(
    (config) => {
        const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Add a response interceptor
api.interceptors.response.use(
    (response) => response,
    (error) => {
        // Optionally handle 401 Unauthorized globally
        if (error.response && error.response.status === 401) {
            // e.g., clear token or redirect to login (best handled via AuthContext or Event)
            if (typeof window !== 'undefined') {
                // Custom event we can listen to in AuthProvider
                window.dispatchEvent(new Event('auth-unauthorized'));
            }
        }
        return Promise.reject(error);
    }
);

export default api;

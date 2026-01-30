import React, {useState, useEffect} from 'react';
import axios from 'axios';
import Icon from '@mdi/react';
import * as mdiIcons from '@mdi/js';

// Detect if running through Home Assistant ingress and adjust API base
const getApiBase = () => {
    // Check if we're running through HA ingress
    if (window.location.pathname.includes('/api/hassio_ingress/')) {
        // Use relative paths to stay within ingress context
        return '.';
    }
    // Use configured API URL or default to empty string for relative paths
    return import.meta.env.VITE_API_URL || '';
};

const API_BASE = getApiBase();

const getDisplayIcon = (iconString) => {
    if (!iconString?.startsWith('mdi:')) {
        return <Icon path={mdiIcons.mdiGauge} size={1.2}/>;
    }

    const iconName = 'mdi' + iconString
        .slice(4)
        .split('-')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join('');

    const iconPath = mdiIcons[iconName];
    return iconPath ? <Icon path={iconPath} size={1.2}/> : <Icon path={mdiIcons.mdiGauge} size={1.2}/>;
};

function App() {
    const [userEntities, setUserEntities] = useState([]);
    const [adminEntities, setAdminEntities] = useState([]);
    const [links, setLinks] = useState([]);
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showLogin, setShowLogin] = useState(false);
    const [showEntityManager, setShowEntityManager] = useState(false);
    const [showLinkManager, setShowLinkManager] = useState(false);

    useEffect(() => {
        fetchUserDashboard();
        fetchLinks();
        checkAuth();
        const interval = setInterval(() => {
            fetchUserDashboard();
            fetchLinks();
        }, 30000);
        return () => clearInterval(interval);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        if (user?.role === 'admin' || user?.role === 'superadmin') {
            fetchAdminDashboard();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [user]);

    const fetchUserDashboard = async () => {
        try {
            const response = await axios.get(`${API_BASE}/api/dashboard`);
            setUserEntities(response.data.entities);
            setError(null);
        } catch (err) {
            setError('Unable to fetch dashboard');
        } finally {
            setLoading(false);
        }
    };

    const fetchAdminDashboard = async () => {
        const token = localStorage.getItem('token');
        const axiosConfig = token ? {headers: {Authorization: `Bearer ${token}`}} : {};
        try {
            const response = await axios.get(`${API_BASE}/api/admin/dashboard`, axiosConfig);
            setAdminEntities(response.data.entities);
        } catch (err) {
            console.error('Failed to fetch admin dashboard');
        }
    };

    const fetchLinks = async () => {
        try {
            const response = await axios.get(`${API_BASE}/api/links`);
            setLinks(response.data.links);
        } catch (err) {
            console.error('Failed to fetch links');
        }
    };

    const checkAuth = async () => {
        const token = localStorage.getItem('token');
        const axiosConfig = token ? {headers: {Authorization: `Bearer ${token}`}} : {};
        try {
            const response = await axios.get(`${API_BASE}/api/me`, axiosConfig);
            if (response.data.authenticated) {
                setUser(response.data);
            } else {
                setUser(null);
            }
        } catch (err) {
            localStorage.removeItem('token');
            setUser(null);
        }
    };

    const login = async (username, password) => {
        try {
            const response = await axios.post(`${API_BASE}/api/login`, {username, password});
            localStorage.setItem('token', response.data.access_token);
            setShowLogin(false);
            await checkAuth();
            // Refresh dashboards after login
            await fetchUserDashboard();
        } catch (err) {
            alert('Login failed');
        }
    };

    const logout = () => {
        localStorage.removeItem('token');
        setUser(null);
        setAdminEntities([]);
        setShowLogin(false);
        setShowEntityManager(false);
    };

    const toggleEntity = async (entityId, action = 'toggle') => {
        const token = localStorage.getItem('token');
        const axiosConfig = token ? {headers: {Authorization: `Bearer ${token}`}} : {};
        try {
            await axios.post(`${API_BASE}/api/admin/toggle/${entityId}`,
                {action},
                axiosConfig
            );
            fetchAdminDashboard();
        } catch (err) {
            alert('Failed to control entity');
        }
    };

    const deleteEntity = async (entityId, dashboard) => {
        const token = localStorage.getItem('token');
        const axiosConfig = token ? {headers: {Authorization: `Bearer ${token}`}} : {};
        try {
            await axios.delete(
                `${API_BASE}/api/admin/entities/${entityId}?dashboard=${dashboard}`,
                axiosConfig
            );
            fetchUserDashboard();
            fetchAdminDashboard();
        } catch (err) {
            alert('Failed to delete entity');
        }
    };

    const deleteLink = async (linkIndex) => {
        const token = localStorage.getItem('token');
        const axiosConfig = token ? {headers: {Authorization: `Bearer ${token}`}} : {};
        try {
            await axios.delete(
                `${API_BASE}/api/admin/links/${linkIndex}`,
                axiosConfig
            );
            fetchLinks();
        } catch (err) {
            alert('Failed to delete link');
        }
    };

    if (loading) {
        return <div className="loading">Loading dashboard...</div>;
    }

    return (
        <div className="App">
            <header className="header">
                <h1>🏢 Public Dashboard</h1>
                {user ? (
                    <div className="user-info">
                        <span>{user.username} (role: {user.role})</span>
                        {user.role === 'superadmin' && (
                            <button onClick={() => setShowEntityManager(!showEntityManager)} className="btn-secondary">
                                {showEntityManager ? 'Close Manager' : 'Edit Cards'}
                            </button>
                        )}
                        {user.role === 'superadmin' && (
                            <button onClick={() => setShowLinkManager(!showLinkManager)} className="btn-secondary">
                                {showLinkManager ? 'Close Links' : 'Links'}
                            </button>
                        )}
                        <button onClick={logout} className="btn-secondary">Logout</button>
                    </div>
                ) : (
                    <div className="auth-buttons">
                        <button onClick={() => setShowLogin(!showLogin)} className="btn-primary">
                            {showLogin ? 'Cancel' : 'Login'}
                        </button>
                    </div>
                )}
            </header>

            {error && <div className="error">{error}</div>}

            {showLogin && !user && <LoginForm onLogin={login} onCancel={() => setShowLogin(false)}/>}

            {showEntityManager && user?.role === 'superadmin' && (
                <EntityManager
                    onClose={() => setShowEntityManager(false)}
                    onUpdate={() => {
                        fetchUserDashboard();
                        fetchAdminDashboard();
                    }}
                />
            )}

            {showLinkManager && user?.role === 'superadmin' && (
                <LinkManager
                    onClose={() => setShowLinkManager(false)}
                    onUpdate={fetchLinks}
                />
            )}

            <main className="dashboard">
                {userEntities.length > 0 && (
                    <div className="dashboard-section">
                        <h2>📊 User</h2>
                        <div className="entities-grid">
                            {userEntities.map(entity => (
                                <EntityCard
                                    key={entity.entity_id}
                                    entity={entity}
                                    showDelete={user?.role === 'superadmin'}
                                    onDelete={(entityId) => deleteEntity(entityId, 'user')}
                                />
                            ))}
                        </div>
                    </div>
                )}

                {(user?.role === 'admin' || user?.role === 'superadmin') && adminEntities.length > 0 && (
                    <div className="dashboard-section">
                        <h2>🔧 Admin</h2>
                        <div className="entities-grid">
                            {adminEntities.map(entity => (
                                <EntityCard
                                    key={entity.entity_id}
                                    entity={entity}
                                    onToggle={entity.controllable ? toggleEntity : null}
                                    showDelete={user?.role === 'superadmin'}
                                    onDelete={(entityId) => deleteEntity(entityId, 'admin')}
                                />
                            ))}
                        </div>
                    </div>
                )}

                {links.length > 0 && (
                    <div className="dashboard-section">
                        <h2>🔗 Links</h2>
                        <div className="links-grid">
                            {links.map((link, index) => (
                                <div key={index} className="link-card">
                                    {user?.role === 'superadmin' && (
                                        <button
                                            className="delete-btn"
                                            onClick={() => deleteLink(index)}
                                            title="Delete link"
                                        >
                                            ✕
                                        </button>
                                    )}
                                    <div className="link-text">{link.text}</div>
                                    {link.url && (
                                        <a href={link.url} target="_blank" rel="noopener noreferrer"
                                           className="link-button">
                                            Відкрити
                                        </a>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {userEntities.length === 0 && (!user || adminEntities.length === 0) && (
                    <div className="empty-state">
                        <h3>No entities configured</h3>
                        {user?.role === 'superadmin' ? (
                            <p>Click "Manage Entities" to add entities to the dashboard</p>
                        ) : (
                            <p>Contact your administrator to configure dashboard entities</p>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}

function LoginForm({onLogin, onCancel}) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        onLogin(username, password);
    };

    return (
        <div className="login-overlay">
            <form onSubmit={handleSubmit} className="login-form">
                <h3>Login for Admin Access</h3>
                <input
                    type="text"
                    placeholder="Username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                />
                <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                />
                <div className="login-buttons">
                    <button type="submit" className="btn-primary">Login</button>
                    <button type="button" onClick={onCancel} className="btn-secondary">Cancel</button>
                </div>
            </form>
        </div>
    );
}

function EntityCard({entity, onToggle, onDelete, showDelete}) {
    const getStateColor = (state, entityType) => {
        if (entityType === 'binary_sensor') {
            return state === 'on' ? '#4CAF50' : '#9E9E9E';
        }
        if (entityType === 'switch' || entityType === 'input_boolean' || entityType === 'light') {
            return state === 'on' ? '#4CAF50' : '#9E9E9E';
        }
        // Sensor states
        if (state === 'online' || state === 'available' || state === 'heating') return '#4CAF50';
        if (state === 'idle' || state === 'standby') return '#FF9800';
        if (state === 'offline' || state === 'unavailable') return '#F44336';
        return '#9E9E9E';
    };

    return (
        <div className="entity-card">
            {showDelete && (
                <button
                    className="delete-btn"
                    onClick={() => onDelete(entity.entity_id)}
                    title="Delete entity"
                >
                    ✕
                </button>
            )}
            <div className="entity-icon">{getDisplayIcon(entity.icon)}</div>
            <h3>{entity.display_name}</h3>
            <div
                className="entity-state"
                style={{color: getStateColor(entity.state, entity.entity_type)}}
            >
                {entity.state.toUpperCase()}
            </div>
            {onToggle && entity.controllable && (
                <div className="entity-controls">
                    <button
                        className={`btn-control ${entity.state === 'on' ? 'active' : ''}`}
                        onClick={() => onToggle(entity.entity_id, 'toggle')}
                    >
                        {entity.state === 'on' ? 'ON' : 'OFF'}
                    </button>
                </div>
            )}
        </div>
    );
}

function EntityManager({onClose, onUpdate}) {
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [loading, setLoading] = useState(false);

    const token = localStorage.getItem('token');
    const axiosConfig = {headers: {Authorization: `Bearer ${token}`}};


    const searchEntities = async () => {
        if (!searchQuery.trim()) return;

        setLoading(true);
        try {
            const response = await axios.get(
                `${API_BASE}/api/admin/entities/search?query=${searchQuery}`,
                axiosConfig
            );
            setSearchResults(response.data.entities);
        } catch (err) {
            alert('Failed to search entities');
        } finally {
            setLoading(false);
        }
    };

    const addEntity = async (entity, dashboard) => {
        try {
            await axios.post(
                `${API_BASE}/api/admin/entities/add`,
                {
                    entity_id: entity.entity_id,
                    display_name: entity.friendly_name,
                    dashboard: dashboard,
                    icon: entity.icon
                },
                axiosConfig
            );
            alert(`Entity added to ${dashboard} dashboard`);
            onUpdate();
        } catch (err) {
            alert('Failed to add entity');
        }
    };

    return (
        <div className="entity-manager-overlay">
            <div className="entity-manager">
                <div className="manager-header">
                    <h3>Manage Dashboard Entities</h3>
                    <button onClick={onClose} className="btn-secondary">Close</button>
                </div>

                <div className="search-section">
                    <div className="search-bar">
                        <input
                            type="text"
                            placeholder="Search entities..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && searchEntities()}
                        />
                        <button onClick={searchEntities} className="btn-primary" disabled={loading}>
                            {loading ? 'Searching...' : 'Search'}
                        </button>
                    </div>
                </div>

                <div className="search-results">
                    {searchResults.map(entity => (
                        <div key={entity.entity_id} className="search-result">
                            <div className="entity-info">
                <span className="entity-icon">
                  {getDisplayIcon(entity.icon)}
                </span>
                                <div>
                                    <div className="entity-name">{entity.friendly_name}</div>
                                    <div className="entity-id">{entity.entity_id}</div>
                                </div>
                            </div>
                            <div className="entity-actions">
                                <button
                                    onClick={() => addEntity(entity, 'user')}
                                    className="btn-small btn-primary"
                                >
                                    Add to User
                                </button>
                                <button
                                    onClick={() => addEntity(entity, 'admin')}
                                    className="btn-small btn-secondary"
                                >
                                    Add to Admin
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

function LinkManager({onClose, onUpdate}) {
    const [text, setText] = useState('');
    const [url, setUrl] = useState('');

    const token = localStorage.getItem('token');
    const axiosConfig = {headers: {Authorization: `Bearer ${token}`}};

    const addLink = async () => {
        if (!text.trim()) return;

        try {
            await axios.post(
                `${API_BASE}/api/admin/links/add`,
                {
                    text: text.trim(),
                    url: url.trim() || null
                },
                axiosConfig
            );
            setText('');
            setUrl('');
            onUpdate();
        } catch (err) {
            alert('Failed to add link');
        }
    };

    return (
        <div className="entity-manager-overlay">
            <div className="entity-manager">
                <div className="manager-header">
                    <h3>Керування посиланнями</h3>
                    <button onClick={onClose} className="btn-secondary">Close</button>
                </div>

                <div className="search-section">
                    <div className="link-form">
                        <input
                            type="text"
                            placeholder="Текст посилання..."
                            value={text}
                            onChange={(e) => setText(e.target.value)}
                        />
                        <input
                            type="url"
                            placeholder="URL (опціонально)..."
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                        />
                        <button onClick={addLink} className="btn-primary">
                            Додати
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default App;

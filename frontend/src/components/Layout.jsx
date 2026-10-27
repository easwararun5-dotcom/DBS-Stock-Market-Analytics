import { NavLink, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const navItems = [
  { to: '/',          icon: '📊', label: 'Dashboard' },
  { to: '/stocks',    icon: '📈', label: 'Stock Explorer' },
  { to: '/sectors',   icon: '🏢', label: 'Sectors' },
  { to: '/portfolio', icon: '💼', label: 'Portfolio' },
  { to: '/watchlist', icon: '⭐', label: 'Watchlist' },
  { to: '/ml',        icon: '🤖', label: 'ML Predictions' },
];

export default function Layout({ children }) {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <Link to="/" style={{ textDecoration: 'none' }}>
            <div className="brand-badge">DBMS PROJECT</div>
            <h1>Stock Market Analytics</h1>
            <div className="subtitle">Portfolio & Predictive Intelligence</div>
          </Link>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section-label">NAVIGATION</div>
          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-text">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-user-section">
          {isAuthenticated ? (
            <div className="user-profile-card">
              <div className="user-info">
                <div className="user-avatar">
                  {user.name ? user.name[0].toUpperCase() : 'U'}
                </div>
                <div className="user-details">
                  <div className="user-name" title={user.name}>{user.name}</div>
                  <div className="user-email" title={user.email}>{user.email}</div>
                </div>
              </div>
              <button
                className="btn-logout"
                onClick={handleLogout}
                title="Sign Out"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <div className="auth-buttons-group">
              <Link to="/login" className="btn btn-secondary btn-sm btn-block">
                Sign In
              </Link>
              <Link to="/register" className="btn btn-primary btn-sm btn-block">
                Create Account
              </Link>
            </div>
          )}
        </div>

        <div className="sidebar-footer">
          PostgreSQL &middot; TimescaleDB &middot; ML
        </div>
      </aside>

      <main className="main-content">
        {children}
      </main>
    </div>
  );
}

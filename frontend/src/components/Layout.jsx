import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/',          icon: '📊', label: 'Dashboard' },
  { to: '/stocks',    icon: '📈', label: 'Stock Explorer' },
  { to: '/sectors',   icon: '🏢', label: 'Sectors' },
  { to: '/portfolio', icon: '💼', label: 'Portfolio' },
  { to: '/watchlist', icon: '⭐', label: 'Watchlist' },
  { to: '/ml',        icon: '🤖', label: 'ML Predictions' },
]

export default function Layout({ children }) {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>DBS Stock Market Analytics</h1>
          <div className="subtitle">Portfolio Management System</div>
        </div>
        <nav className="sidebar-nav">
          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          DBS College Project &middot; DBMS
        </div>
      </aside>
      <main className="main-content">
        {children}
      </main>
    </div>
  )
}

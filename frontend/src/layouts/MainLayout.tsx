import { Outlet, Link } from "react-router-dom";
import "./MainLayout.css"; // We'll add some basic styles

export default function MainLayout() {
  return (
    <div className="layout">
      <header className="header">
        <div className="logo">
            <Link to="/">Social Deduction Engine</Link>
        </div>
        <nav>
          <Link to="/">Home</Link>
          <Link to="/create-game" className="btn-primary">Create Game</Link>
        </nav>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}

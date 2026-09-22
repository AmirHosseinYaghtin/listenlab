import { Headphones, Library, Plus } from 'lucide-react'
import { Link, NavLink, Outlet } from 'react-router-dom'

export default function Layout() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2.5 font-semibold text-slate-900">
            <span className="flex size-8 items-center justify-center rounded-lg bg-brand-600 text-white">
              <Headphones className="size-4.5" aria-hidden />
            </span>
            <span className="text-[15px] tracking-tight">
              Listen<span className="text-brand-600">Lab</span>
            </span>
          </Link>

          <nav className="flex items-center gap-1.5 sm:gap-2" aria-label="Main">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `btn-ghost ${isActive ? 'bg-slate-100 text-slate-900' : ''}`
              }
            >
              <Library className="size-4" aria-hidden />
              <span className="hidden sm:inline">Library</span>
            </NavLink>
            <Link to="/podcast/new" className="btn-primary">
              <Plus className="size-4" aria-hidden />
              <span>Add Podcast</span>
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 py-6">
        <p className="mx-auto max-w-6xl px-4 text-xs text-slate-400 sm:px-6">
          ListenLab — interactive podcast listening &amp; vocabulary practice for
          university English classes.
        </p>
      </footer>
    </div>
  )
}

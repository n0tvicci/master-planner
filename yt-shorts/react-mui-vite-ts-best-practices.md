# React + TypeScript + MUI (Vite) Best Practices Guide

A comprehensive guide based on the [karpolan/react-mui-vite-ts](https://github.com/karpolan/react-mui-vite-ts) boilerplate, covering project structure, theming, routing, state management, authentication, testing, and deployment patterns.

## Table of Contents

1. [Project Structure](#project-structure)
2. [Environment Configuration](#environment-configuration)
3. [TypeScript Standards](#typescript-standards)
4. [MUI Theming & Styling](#mui-theming--styling)
5. [Routing & Layouts](#routing--layouts)
6. [State Management (Context API)](#state-management-context-api)
7. [Authentication Pattern](#authentication-pattern)
8. [Component Standards](#component-standards)
9. [DRY Principle](#dry-principle-dont-repeat-yourself)
10. [Custom Hooks](#custom-hooks)
11. [Error Handling](#error-handling)
12. [Performance Optimization](#performance-optimization)
13. [Security Considerations](#security-considerations)
14. [Testing Strategies](#testing-strategies)
15. [Deployment Guidelines](#deployment-guidelines)
16. [Common Pitfalls and Solutions](#common-pitfalls-and-solutions)

---

## Project Structure

### Recommended Directory Layout

```
src/
├── assets/                   # Static files: images, fonts, icons, SVGs
├── components/               # Reusable, generic UI components (no business logic)
│   └── AppButton/
│       ├── AppButton.tsx
│       ├── AppButton.test.tsx
│       └── index.ts          # Barrel export
├── hooks/                    # Custom React hooks
│   ├── useAuth.ts
│   ├── useAppTheme.ts
│   └── useLocalStorage.ts
├── layouts/                  # Page layout wrappers
│   ├── PublicLayout/         # For unauthenticated pages
│   │   ├── PublicLayout.tsx
│   │   └── index.ts
│   └── PrivateLayout/        # For authenticated pages
│       ├── PrivateLayout.tsx
│       ├── Sidebar.tsx
│       ├── Topbar.tsx
│       └── index.ts
├── pages/                    # Route-level page components
│   ├── Home/
│   │   ├── Home.tsx
│   │   └── index.ts
│   ├── Login/
│   │   ├── Login.tsx
│   │   └── index.ts
│   └── NotFound/
│       ├── NotFound.tsx
│       └── index.ts
├── router/                   # React Router config and route guards
│   ├── index.tsx             # Route definitions
│   └── PrivateRoute.tsx      # Auth guard component
├── store/                    # Context API providers
│   ├── AuthContext.tsx
│   ├── ThemeContext.tsx
│   └── index.ts              # Combined provider export
├── theme/                    # MUI theme customization
│   ├── index.ts              # Exports final theme
│   ├── palette.ts            # Light and dark color palettes
│   └── typography.ts         # Font sizes, weights, families
├── types/                    # Shared TypeScript types and interfaces
│   ├── auth.types.ts
│   ├── api.types.ts
│   └── index.ts
├── utils/                    # Pure utility/helper functions
│   ├── formatDate.ts
│   ├── storage.ts
│   └── validators.ts
├── App.tsx                   # Root component
└── main.tsx                  # Entry point
```

### Key Principles

- **Component Co-location**: Every component lives in its own folder with an `index.ts` barrel export
- **Test Co-location**: Place `ComponentName.test.tsx` next to the component it tests
- **Single Responsibility**: No business logic inside `components/` — that belongs in `pages/` or `hooks/`
- **Feature Grouping**: Group files by feature, not by file type
- **Barrel Exports**: Always use `index.ts` to expose a clean public API for each folder

---

## Environment Configuration

### Environment Variable Strategy

Vite uses specific prefixing rules to control what is exposed to the client bundle:

```bash
# ✅ Server-only (no VITE_ prefix) - Never exposed to client bundle
API_SECRET_KEY=super-secret-key
DATABASE_URL=postgresql://user:pass@localhost:5432/mydb

# ✅ Client-safe (VITE_ prefix) - Exposed to the client bundle
VITE_APP_TITLE=My App
VITE_API_URL=https://api.example.com
VITE_SENTRY_DSN=https://...
```

### Environment File Hierarchy

```bash
# .env - Default values (safe to commit)
VITE_APP_TITLE=My App
VITE_API_URL=http://localhost:3000

# .env.local - Local overrides (never commit, in .gitignore)
VITE_API_URL=http://localhost:8080

# .env.production - Production values
VITE_API_URL=https://api.myapp.com
```

### Environment Validation

Always validate environment variables at startup using Zod:

```typescript
// src/config/env.ts
import { z } from "zod";

const envSchema = z.object({
  VITE_APP_TITLE: z.string().min(1),
  VITE_API_URL: z.string().url(),
});

export const env = envSchema.parse(import.meta.env);
```

### .env.example Template

Document all required variables in `.env.example`:

```bash
# .env.example
VITE_APP_TITLE=_TITLE_
VITE_API_URL=http://localhost:3000
VITE_LOG_LEVEL=DEBUG
```

---

## TypeScript Standards

### Strict Configuration

The boilerplate ships with strict mode enabled in `tsconfig.app.json`. Never disable it:

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true
  }
}
```

### Types vs Interfaces

- Use `interface` for object shapes (components, API responses, entities)
- Use `type` for unions, intersections, and aliases

```typescript
// ✅ Interface for object shapes
interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: UserRole;
}

// ✅ Type for unions
type UserRole = 'admin' | 'editor' | 'viewer';

// ✅ Type for function signatures
type ApiHandler<T> = (data: T) => Promise<ApiResponse<T>>;
```

### Generic API Response Type

Define a shared response wrapper in `src/types/api.types.ts`:

```typescript
// src/types/api.types.ts
export interface ApiResponse<T> {
  data: T | null;
  error: string | null;
  success: boolean;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  total: number;
  page: number;
  pageSize: number;
}
```

### No `any` Rule

Never use `any`. Use `unknown` with type guards for unsafe values:

```typescript
// ❌ Bad
const handleError = (error: any) => console.error(error.message);

// ✅ Good
const handleError = (error: unknown) => {
  if (error instanceof Error) {
    console.error(error.message);
  }
};
```

---

## MUI Theming & Styling

### Theme Structure

Organize your MUI theme into focused files:

```typescript
// src/theme/palette.ts
import { PaletteOptions } from '@mui/material/styles';

export const lightPalette: PaletteOptions = {
  mode: 'light',
  primary: { main: '#1976d2' },
  secondary: { main: '#9c27b0' },
  background: {
    default: '#f5f5f5',
    paper: '#ffffff',
  },
};

export const darkPalette: PaletteOptions = {
  mode: 'dark',
  primary: { main: '#90caf9' },
  secondary: { main: '#ce93d8' },
  background: {
    default: '#121212',
    paper: '#1e1e1e',
  },
};
```

```typescript
// src/theme/typography.ts
import { TypographyOptions } from '@mui/material/styles/createTypography';

export const typography: TypographyOptions = {
  fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  h1: { fontSize: '2.5rem', fontWeight: 700 },
  h2: { fontSize: '2rem', fontWeight: 600 },
  body1: { fontSize: '1rem', lineHeight: 1.6 },
};
```

```typescript
// src/theme/index.ts
import { createTheme, Theme } from '@mui/material/styles';
import { lightPalette, darkPalette } from './palette';
import { typography } from './typography';

export const createAppTheme = (mode: 'light' | 'dark'): Theme =>
  createTheme({
    palette: mode === 'light' ? lightPalette : darkPalette,
    typography,
    shape: { borderRadius: 8 },
    spacing: 8,
  });
```

### Styling Rules

Always use MUI's `sx` prop or `styled()` — never inline styles or plain CSS:

```typescript
// ✅ Use sx prop with theme tokens
<Box
  sx={{
    p: 2,
    mt: 1,
    bgcolor: 'background.paper',
    borderRadius: 1,
    boxShadow: 1,
  }}
>

// ✅ Use styled() for complex or reusable styles
const StyledCard = styled(Card)(({ theme }) => ({
  padding: theme.spacing(2),
  borderRadius: theme.shape.borderRadius,
  '&:hover': {
    boxShadow: theme.shadows[4],
  },
}));

// ❌ Never use inline styles
<Box style={{ padding: '16px', backgroundColor: '#fff' }}>

// ❌ Never hardcode values
<Box sx={{ padding: '16px', color: '#1976d2' }}>
```

### Dark/Light Mode Toggle

Use the `ThemeContext` (covered in State Management) to toggle themes:

```typescript
// Usage in any component
const { mode, toggleMode } = useAppTheme();

<IconButton onClick={toggleMode}>
  {mode === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}
</IconButton>
```

---

## Routing & Layouts

### Route Configuration

Define all routes in `src/router/index.tsx`:

```tsx
// src/router/index.tsx
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { PublicLayout } from '@/layouts/PublicLayout';
import { PrivateLayout } from '@/layouts/PrivateLayout';
import { PrivateRoute } from './PrivateRoute';
import { Home } from '@/pages/Home';
import { Login } from '@/pages/Login';
import { Dashboard } from '@/pages/Dashboard';
import { NotFound } from '@/pages/NotFound';

const router = createBrowserRouter([
  {
    element: <PublicLayout />,
    children: [
      { path: '/login', element: <Login /> },
    ],
  },
  {
    element: <PrivateRoute />,
    children: [
      {
        element: <PrivateLayout />,
        children: [
          { path: '/', element: <Home /> },
          { path: '/dashboard', element: <Dashboard /> },
        ],
      },
    ],
  },
  { path: '*', element: <NotFound /> },
]);

export const AppRouter = () => <RouterProvider router={router} />;
```

### Private Route Guard

```tsx
// src/router/PrivateRoute.tsx
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';

export const PrivateRoute = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <FullPageLoader />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return <Outlet />;
};
```

### Layout Pattern

Public and Private layouts wrap content via `<Outlet />`:

```tsx
// src/layouts/PrivateLayout/PrivateLayout.tsx
import { Outlet } from 'react-router-dom';
import { Box } from '@mui/material';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

export const PrivateLayout = () => (
  <Box sx={{ display: 'flex', minHeight: '100vh' }}>
    <Sidebar />
    <Box component="main" sx={{ flexGrow: 1, overflow: 'auto' }}>
      <Topbar />
      <Box sx={{ p: 3 }}>
        <Outlet />
      </Box>
    </Box>
  </Box>
);
```

---

## State Management (Context API)

### Context Pattern

Every context follows the same three-part structure: Context → Provider → Hook.

```typescript
// src/store/AuthContext.tsx
import { createContext, useContext, useState, FC, ReactNode } from 'react';
import { UserProfile } from '@/types';

interface AuthContextValue {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      // Call your API here
      const profile = await authApi.login(email, password);
      setUser(profile);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => setUser(null);

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated: !!user, isLoading, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// Always export a named hook — never consume context directly in components
export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
};
```

### Combining Providers

Avoid deeply nested providers by combining them in one place:

```tsx
// src/store/index.ts
import { FC, ReactNode } from 'react';
import { AuthProvider } from './AuthContext';
import { ThemeProvider } from './ThemeContext';

interface AppProvidersProps {
  children: ReactNode;
}

export const AppProviders: FC<AppProvidersProps> = ({ children }) => (
  <ThemeProvider>
    <AuthProvider>
      {children}
    </AuthProvider>
  </ThemeProvider>
);
```

```tsx
// src/main.tsx
import { AppProviders } from '@/store';

root.render(
  <StrictMode>
    <AppProviders>
      <AppRouter />
    </AppProviders>
  </StrictMode>
);
```

---

## Authentication Pattern

### Auth Hook Usage

The `useAuth` hook is the single entry point to auth state in any component:

```typescript
// In any component or page
const { user, isAuthenticated, login, logout } = useAuth();
```

### Login Page Pattern

```tsx
// src/pages/Login/Login.tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, TextField, Box, Alert } from '@mui/material';
import { useAuth } from '@/hooks/useAuth';

export const Login = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    const formData = new FormData(e.currentTarget);

    try {
      await login(
        formData.get('email') as string,
        formData.get('password') as string
      );
      navigate('/dashboard');
    } catch {
      setError('Invalid credentials. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ maxWidth: 400, mx: 'auto', mt: 8 }}>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      <TextField name="email" label="Email" type="email" fullWidth required sx={{ mb: 2 }} />
      <TextField name="password" label="Password" type="password" fullWidth required sx={{ mb: 3 }} />
      <Button type="submit" variant="contained" fullWidth loading={isLoading}>
        Sign In
      </Button>
    </Box>
  );
};
```

### Persisting Auth State

Use `localStorage` for token persistence with a dedicated utility:

```typescript
// src/utils/storage.ts
const AUTH_TOKEN_KEY = 'auth_token';

export const storage = {
  getToken: () => localStorage.getItem(AUTH_TOKEN_KEY),
  setToken: (token: string) => localStorage.setItem(AUTH_TOKEN_KEY, token),
  removeToken: () => localStorage.removeItem(AUTH_TOKEN_KEY),
};
```

---

## Component Standards

### Component Template

Every component follows this consistent pattern:

```tsx
// src/components/UserCard/UserCard.tsx
import { FC } from 'react';
import { Card, CardContent, Typography, Avatar, Box } from '@mui/material';
import { UserProfile } from '@/types';

interface UserCardProps {
  user: UserProfile;
  onClick?: (user: UserProfile) => void;
}

export const UserCard: FC<UserCardProps> = ({ user, onClick }) => {
  const handleClick = () => onClick?.(user);

  return (
    <Card
      onClick={handleClick}
      sx={{
        cursor: onClick ? 'pointer' : 'default',
        '&:hover': onClick ? { boxShadow: 4 } : undefined,
        transition: 'box-shadow 0.2s',
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Avatar src={user.avatar} alt={user.name} />
          <Box>
            <Typography variant="subtitle1" fontWeight={600}>{user.name}</Typography>
            <Typography variant="body2" color="text.secondary">{user.email}</Typography>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};
```

```typescript
// src/components/UserCard/index.ts
export { UserCard } from './UserCard';
export type { UserCardProps } from './UserCard'; // if you export the type
```

### Component Rules

- Use **named exports** for all components — except pages which can use default exports
- Keep components **under ~150 lines** — split if they grow beyond that
- **Props interface** is always defined directly above the component
- Use **optional chaining** for optional callback props (`onClick?.(value)`)
- Never put **API calls directly** in components — abstract into hooks

---

## DRY Principle (Don't Repeat Yourself)

DRY is a core rule of this codebase. Every piece of knowledge — a style, a calculation, a validation, a UI pattern — must have a **single authoritative source**. If you find yourself writing the same thing twice, stop and extract it.

### 1. Reusable Components — Never Duplicate UI

If the same UI pattern appears in two places, extract it into `src/components/`. Never copy-paste JSX between pages or components.

```tsx
// ❌ Bad — same card layout duplicated in two pages
// pages/Dashboard/Dashboard.tsx
<Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 1, boxShadow: 1 }}>
  <Typography variant="h6">{title}</Typography>
  <Typography color="text.secondary">{value}</Typography>
</Box>

// pages/Reports/Reports.tsx
<Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 1, boxShadow: 1 }}>
  <Typography variant="h6">{title}</Typography>
  <Typography color="text.secondary">{value}</Typography>
</Box>

// ✅ Good — extracted once into a shared component
// src/components/StatCard/StatCard.tsx
interface StatCardProps {
  title: string;
  value: string | number;
}

export const StatCard: FC<StatCardProps> = ({ title, value }) => (
  <Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 1, boxShadow: 1 }}>
    <Typography variant="h6">{title}</Typography>
    <Typography color="text.secondary">{value}</Typography>
  </Box>
);

// Used in both pages with one import
<StatCard title="Total Users" value={42} />
```

### 2. Shared Logic — Extract into Custom Hooks

If the same stateful logic appears in more than one component, move it to `src/hooks/`.

```typescript
// ❌ Bad — same fetch logic duplicated in two components
// ComponentA.tsx
const [users, setUsers] = useState([]);
const [isLoading, setIsLoading] = useState(false);
useEffect(() => {
  setIsLoading(true);
  fetchUsers().then(setUsers).finally(() => setIsLoading(false));
}, []);

// ComponentB.tsx — exact same block
const [users, setUsers] = useState([]);
const [isLoading, setIsLoading] = useState(false);
useEffect(() => { ... }, []);

// ✅ Good — extracted once into a hook
// src/hooks/useUsers.ts
export const useUsers = () => {
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setIsLoading(true);
    fetchUsers().then(setUsers).finally(() => setIsLoading(false));
  }, []);

  return { users, isLoading };
};

// Used in both components
const { users, isLoading } = useUsers();
```

### 3. Shared Types — Single Source in `src/types/`

Never redefine the same interface in two files. All shared types live in `src/types/` and are imported wherever needed.

```typescript
// ❌ Bad — UserProfile defined in two places
// components/UserCard/UserCard.tsx
interface UserProfile { id: string; name: string; email: string; }

// pages/Dashboard/Dashboard.tsx
interface UserProfile { id: string; name: string; email: string; } // duplicate!

// ✅ Good — defined once
// src/types/user.types.ts
export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: UserRole;
}

// Imported everywhere
import { UserProfile } from '@/types';
```

### 4. Shared Constants — Never Hardcode the Same Value Twice

Magic strings, numbers, and config values belong in `src/utils/constants.ts` or domain-specific constant files.

```typescript
// ❌ Bad — same string in multiple files
// api/users.ts
fetch('/api/v1/users')

// api/posts.ts
fetch('/api/v1/posts')    // if base URL changes, must update everywhere

// ✅ Good — single source of truth
// src/utils/constants.ts
export const API_BASE = import.meta.env.VITE_API_URL;
export const API_V1 = `${API_BASE}/api/v1`;

export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  DASHBOARD: '/dashboard',
  SETTINGS: '/settings',
} as const;

// Used consistently everywhere
fetch(`${API_V1}/users`)
navigate(ROUTES.DASHBOARD)
```

### 5. Shared Styles — Use Theme Tokens, Not Repeated `sx` Objects

If the same `sx` style block appears more than once, extract it as a `styled()` component or a shared style object.

```typescript
// ❌ Bad — same sx object copy-pasted
<Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2 }}>
<Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2 }}>

// ✅ Good — extract as a styled component or shared sx object
// src/theme/styles.ts
export const flexRowSx = {
  display: 'flex',
  alignItems: 'center',
  gap: 2,
  p: 2,
} as const;

// Or as a styled component
export const FlexRow = styled(Box)({
  display: 'flex',
  alignItems: 'center',
  gap: 2,
  padding: 2,
});
```

### 6. Shared Validation — One Schema Per Entity

Define Zod or validation schemas once in `src/utils/validators.ts` or alongside the type, and reuse them in forms, hooks, and API calls.

```typescript
// ❌ Bad — email validation written in every form
const isValidEmail = (email: string) => /\S+@\S+\.\S+/.test(email); // form A
const validateEmail = (v: string) => v.includes('@');                 // form B

// ✅ Good — defined once with Zod
// src/utils/validators.ts
import { z } from 'zod';

export const emailSchema = z.string().email('Invalid email address');

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

export const registerSchema = loginSchema.extend({
  name: z.string().min(1, 'Name is required'),
});
```

### 7. Shared API Calls — One Function Per Endpoint

Every API call is defined once in `src/hooks/` or a dedicated `src/api/` layer. Never call `fetch` directly inside a component.

```typescript
// ❌ Bad — fetch duplicated in two components
// ComponentA.tsx
const res = await fetch(`${API_V1}/users/${id}`);

// ComponentB.tsx
const res = await fetch(`${API_V1}/users/${id}`);  // duplicate

// ✅ Good — defined once in an API module
// src/api/users.ts
export const usersApi = {
  getById: (id: string) => apiRequest<UserProfile>(`/users/${id}`),
  getAll: () => apiRequest<UserProfile[]>('/users'),
  update: (id: string, data: UserUpdate) =>
    apiRequest<UserProfile>(`/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
};

// Used via a hook everywhere
const { data: user } = useQuery(() => usersApi.getById(id));
```

### DRY Checklist

Before committing, ask yourself:

- [ ] Is this component or JSX block used anywhere else? → Extract to `src/components/`
- [ ] Is this stateful logic duplicated? → Extract to `src/hooks/`
- [ ] Is this type or interface defined more than once? → Move to `src/types/`
- [ ] Is this string, number, or URL hardcoded in multiple files? → Move to constants
- [ ] Is this `sx` style block repeated? → Extract to `styled()` or a shared style object
- [ ] Is this validation logic duplicated? → Define once with Zod in `src/utils/validators.ts`
- [ ] Is this API call written more than once? → Move to `src/api/`

---

## Custom Hooks

### Hook Template

```typescript
// src/hooks/useLocalStorage.ts
import { useState, useEffect } from 'react';

export function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = localStorage.getItem(key);
      return item ? (JSON.parse(item) as T) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setValue = (value: T | ((prev: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error(`useLocalStorage error for key "${key}":`, error);
    }
  };

  return [storedValue, setValue] as const;
}
```

### Hook Rules

- Always prefix with `use` — e.g., `useWindowSize`, `useDebounce`
- One responsibility per hook — don't combine unrelated logic
- Return a `const` tuple `[value, setter] as const` or a named object `{ value, isLoading, error }`
- Handle loading and error states inside the hook, not the component

---

## Error Handling

### Global Error Boundary

Wrap the app with an error boundary to catch unhandled React errors:

```tsx
// src/components/ErrorBoundary/ErrorBoundary.tsx
import { Component, ErrorInfo, ReactNode } from 'react';
import { Box, Typography, Button } from '@mui/material';

interface Props { children: ReactNode; }
interface State { hasError: boolean; error: Error | null; }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Unhandled error:', error, info);
    // Send to your error tracking service (Sentry, etc.)
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box sx={{ textAlign: 'center', p: 6 }}>
          <Typography variant="h5" color="error" gutterBottom>
            Something went wrong
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 3 }}>
            {this.state.error?.message}
          </Typography>
          <Button variant="contained" onClick={() => window.location.reload()}>
            Reload Page
          </Button>
        </Box>
      );
    }
    return this.props.children;
  }
}
```

### API Error Handling Pattern

Wrap all API calls consistently:

```typescript
// src/utils/apiClient.ts
export async function apiRequest<T>(
  url: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}${url}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });

    if (!res.ok) {
      const message = await res.text();
      return { data: null, error: message || 'Request failed', success: false };
    }

    const data: T = await res.json();
    return { data, error: null, success: true };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Network error';
    return { data: null, error: message, success: false };
  }
}
```

---

## Performance Optimization

### Lazy Loading Routes

Use `React.lazy` for route-level code splitting:

```tsx
// src/router/index.tsx
import { lazy, Suspense } from 'react';
import { FullPageLoader } from '@/components/FullPageLoader';

const Dashboard = lazy(() => import('@/pages/Dashboard'));
const Settings = lazy(() => import('@/pages/Settings'));

// Wrap routes in Suspense
{
  path: '/dashboard',
  element: (
    <Suspense fallback={<FullPageLoader />}>
      <Dashboard />
    </Suspense>
  ),
}
```

### Memoization

Use `memo`, `useMemo`, and `useCallback` when re-renders are expensive:

```tsx
// Memoize expensive child components
export const UserList = memo(({ users }: { users: UserProfile[] }) => (
  <Stack spacing={2}>
    {users.map(user => <UserCard key={user.id} user={user} />)}
  </Stack>
));

// Memoize derived values
const sortedUsers = useMemo(
  () => [...users].sort((a, b) => a.name.localeCompare(b.name)),
  [users]
);

// Memoize callbacks passed to children
const handleUserClick = useCallback((user: UserProfile) => {
  navigate(`/users/${user.id}`);
}, [navigate]);
```

### MUI Bundle Size

Import MUI components individually to avoid importing the full bundle:

```typescript
// ✅ Good - tree-shakeable named import
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';

// ❌ Avoid - imports entire MUI barrel
import { Button, TextField } from '@mui/material';
```

---

## Security Considerations

### Never Expose Secrets to the Client

```typescript
// ✅ Safe - accessed only on server or in API calls
const secret = process.env.API_SECRET_KEY;

// ✅ Safe - prefixed VITE_ for client use
const appName = import.meta.env.VITE_APP_TITLE;

// ❌ Never put secrets in VITE_ vars
// VITE_SECRET_KEY=abc123  ← This is visible in the client bundle
```

### Input Sanitization

Validate all user inputs before sending to API:

```typescript
import { z } from 'zod';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

const handleSubmit = (formData: unknown) => {
  const result = loginSchema.safeParse(formData);
  if (!result.success) {
    setErrors(result.error.flatten().fieldErrors);
    return;
  }
  // Safe to use result.data here
};
```

### Token Security

Store tokens safely and clear them on logout:

```typescript
// ✅ Clear all auth data on logout
const logout = () => {
  storage.removeToken();
  setUser(null);
  navigate('/login');
};
```

---

## Testing Strategies

### Component Testing

Co-locate tests with the component file:

```typescript
// src/components/AppButton/AppButton.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { AppButton } from './AppButton';

describe('AppButton', () => {
  it('renders the label', () => {
    render(<AppButton label="Submit" />);
    expect(screen.getByRole('button', { name: /submit/i })).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<AppButton label="Submit" onClick={handleClick} />);
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledOnce();
  });

  it('does not call onClick when disabled', () => {
    const handleClick = vi.fn();
    render(<AppButton label="Submit" onClick={handleClick} disabled />);
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).not.toHaveBeenCalled();
  });
});
```

### Hook Testing

```typescript
// src/hooks/useLocalStorage.test.ts
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { useLocalStorage } from './useLocalStorage';

describe('useLocalStorage', () => {
  it('returns initial value when key does not exist', () => {
    const { result } = renderHook(() => useLocalStorage('testKey', 'default'));
    expect(result.current[0]).toBe('default');
  });

  it('stores and retrieves a value', () => {
    const { result } = renderHook(() => useLocalStorage('testKey', ''));
    act(() => result.current[1]('newValue'));
    expect(result.current[0]).toBe('newValue');
  });
});
```

### Test Rules

- Test **behavior**, not implementation details
- Query by **role, label, or visible text** — not by class names or IDs
- Mock API calls at the network level using `msw` (Mock Service Worker)
- Run tests before every commit: `npm test`

### Available Test Commands

```bash
npm test           # Run all tests in watch mode
npm run test:ci    # Run once (for CI/CD pipelines)
npm run coverage   # Run with coverage report
```

---

## Deployment Guidelines

### Build for Production

```bash
npm run build      # Outputs to /dist
npm run preview    # Preview the production build locally
```

### Docker Configuration

Use multi-stage builds to keep the final image lean:

```dockerfile
# Dockerfile
FROM node:20-alpine AS base

FROM base AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM base AS builder
WORKDIR /app
COPY . .
COPY --from=deps /app/node_modules ./node_modules
RUN npm run build

FROM nginx:alpine AS runner
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Nginx Configuration for SPA

Single-page apps need all routes to fallback to `index.html`:

```nginx
# nginx.conf
server {
  listen 80;
  root /usr/share/nginx/html;
  index index.html;

  # Handle client-side routing
  location / {
    try_files $uri $uri/ /index.html;
  }

  # Cache static assets
  location /assets {
    expires 1y;
    add_header Cache-Control "public, immutable";
  }
}
```

### Environment Variables at Runtime

For Docker deployments, inject env vars at runtime using a startup script:

```bash
#!/bin/sh
# docker-entrypoint.sh
# Replace placeholders in the built HTML with real env vars at runtime
sed -i "s|VITE_API_URL_PLACEHOLDER|${VITE_API_URL}|g" /usr/share/nginx/html/index.html
nginx -g "daemon off;"
```

---

## Common Pitfalls and Solutions

### 1. Context Not Available

**Problem**: `useAuth()` throws "must be used inside AuthProvider".

**Solution**: Ensure providers wrap the entire app in `main.tsx`:

```tsx
// ✅ Correct — providers wrap everything
root.render(
  <AppProviders>
    <AppRouter />
  </AppProviders>
);
```

### 2. Dark Mode Not Persisting on Refresh

**Problem**: Theme resets to light on page reload.

**Solution**: Initialize theme from `localStorage`:

```typescript
const [mode, setMode] = useLocalStorage<'light' | 'dark'>('theme-mode', 'light');
```

### 3. Private Route Flashing Login Page

**Problem**: Authenticated users briefly see the login page on refresh.

**Solution**: Show a loader while checking auth state:

```tsx
// PrivateRoute.tsx
if (isLoading) return <FullPageLoader />;
if (!isAuthenticated) return <Navigate to="/login" replace />;
return <Outlet />;
```

### 4. MUI Bundle Too Large

**Problem**: Slow load times due to large MUI bundle.

**Solution**: Use path imports instead of barrel imports:

```typescript
// ✅ Tree-shakeable
import Button from '@mui/material/Button';

// ❌ Imports entire library
import { Button } from '@mui/material';
```

### 5. TypeScript Errors on `import.meta.env`

**Problem**: TypeScript doesn't recognize custom env variables.

**Solution**: Declare them in `vite-env.d.ts`:

```typescript
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_TITLE: string;
  readonly VITE_API_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

### 6. Tests Failing Due to Missing MUI Theme

**Problem**: Components using `useTheme()` or MUI tokens fail in tests.

**Solution**: Wrap test renders with a theme provider:

```typescript
// src/utils/test-utils.tsx
import { render, RenderOptions } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import { createAppTheme } from '@/theme';

const AllProviders = ({ children }) => (
  <ThemeProvider theme={createAppTheme('light')}>
    {children}
  </ThemeProvider>
);

const customRender = (ui: ReactElement, options?: RenderOptions) =>
  render(ui, { wrapper: AllProviders, ...options });

export * from '@testing-library/react';
export { customRender as render };
```

---

## Conclusion

The `karpolan/react-mui-vite-ts` boilerplate provides a solid, production-ready foundation. Following these best practices will ensure your apps remain consistent, scalable, and maintainable. Key takeaways:

- Follow the folder structure strictly — consistency across projects saves time
- Never disable TypeScript strict mode
- Always use MUI theme tokens, never hardcoded values
- Keep business logic out of components — use hooks and pages
- Every context gets its own consumer hook — never use `useContext` directly
- Lazy-load routes for better performance
- Co-locate tests with components and run them before every commit
- Validate all environment variables at startup
- **Apply DRY everywhere** — if you write something twice, extract it: components → `src/components/`, logic → `src/hooks/`, types → `src/types/`, constants → `src/utils/constants.ts`, styles → `styled()`, validation → `src/utils/validators.ts`, API calls → `src/api/`

Remember to check the [official MUI docs](https://mui.com) and [React Router docs](https://reactrouter.com) as both libraries continue to evolve.

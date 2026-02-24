import { createContext, useContext, useState, useEffect } from "react";
import type { ReactNode } from "react";
import { API } from "../services/api";

type User = {
    id: number;
    username: string;
    email: string;
};

type AuthContextType = {
    user: User | null;
    loading: boolean;
    login: (username: string, password: string) => Promise<void>;
    signup: (username: string, email: string, password: string, passwordConfirm: string) => Promise<void>;
    logout: () => void;
};

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem("token");
        if (!token) {
            setLoading(false);
            return;
        }
        API.get("/auth/me/")
            .then((res) => setUser(res.data))
            .catch(() => {
                localStorage.removeItem("token");
            })
            .finally(() => setLoading(false));
    }, []);

    const login = async (username: string, password: string) => {
        const res = await API.post("/auth/login/", { username, password });
        localStorage.setItem("token", res.data.token);
        setUser(res.data.user);
    };

    const signup = async (username: string, email: string, password: string, passwordConfirm: string) => {
        const res = await API.post("/auth/signup/", {
            username,
            email,
            password,
            password_confirm: passwordConfirm,
        });
        localStorage.setItem("token", res.data.token);
        setUser(res.data.user);
    };

    const logout = () => {
        localStorage.removeItem("token");
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}

import { BrowserRouter, Routes, Route } from "react-router-dom";
import MainLayout from "./layouts/MainLayout";
import Home from "./pages/Home";
import GameEditor from "./pages/GameEditor";
import PlayGame from "./pages/PlayGame";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import LobbyLanding from "./pages/LobbyLanding";
import SessionLobby from "./pages/SessionLobby";
import ProtectedRoute from "./components/ProtectedRoute";

export default function AppRoutes() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<MainLayout />}>
                    <Route index element={<Home />} />
                    <Route path="login" element={<Login />} />
                    <Route path="signup" element={<Signup />} />
                    <Route element={<ProtectedRoute />}>
                        <Route path="play-game/:id" element={<PlayGame />} />
                        <Route path="multiplayer" element={<LobbyLanding />} />
                        <Route path="sessions/:sessionId" element={<SessionLobby />} />
                        <Route path="create-game" element={<GameEditor />} />
                        <Route path="edit-game/:id" element={<GameEditor />} />
                    </Route>
                </Route>
            </Routes>
        </BrowserRouter>
    );
}

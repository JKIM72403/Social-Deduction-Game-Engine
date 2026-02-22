import { BrowserRouter, Routes, Route } from "react-router-dom";
import MainLayout from "./layouts/MainLayout";
import Home from "./pages/Home";
import GameEditor from "./pages/GameEditor";
import PlayGame from "./pages/PlayGame";

export default function AppRoutes() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<MainLayout />}>
                    <Route index element={<Home />} />
                    <Route path="create-game" element={<GameEditor />} />
                    <Route path="edit-game/:id" element={<GameEditor />} />
                    <Route path="play-game/:id" element={<PlayGame />} />
                </Route>
            </Routes>
        </BrowserRouter>
    );
}

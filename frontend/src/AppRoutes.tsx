import { BrowserRouter, Routes, Route } from "react-router-dom";
import MainLayout from "./layouts/MainLayout";
import Home from "./pages/Home";
import GameEditor from "./pages/GameEditor";

export default function AppRoutes() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<MainLayout />}>
                    <Route index element={<Home />} />
                </Route>
                <Route path="create-game" element={<GameEditor />} />
                <Route path="edit-game/:id" element={<GameEditor />} />
            </Routes>
        </BrowserRouter>
    );
}

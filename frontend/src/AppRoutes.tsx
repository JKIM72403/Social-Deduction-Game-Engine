import { BrowserRouter, Routes, Route } from "react-router-dom";
import MainLayout from "./layouts/MainLayout";
import Home from "./pages/Home";
import GameCreator from "./pages/GameCreator/index";

export default function AppRoutes() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<MainLayout />}>
                    <Route index element={<Home />} />
                    <Route path="create-game" element={<GameCreator />} />
                </Route>
            </Routes>
        </BrowserRouter>
    );
}

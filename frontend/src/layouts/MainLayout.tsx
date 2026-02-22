import { Outlet } from "react-router-dom";
import { Box } from "@mui/material";
import Navbar from "../components/navbar";

export default function MainLayout() {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: 'background.default' }}>
      <Navbar />
      <Box component="main" sx={{ flexGrow: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
        <Outlet />
      </Box>
    </Box>
  );
}

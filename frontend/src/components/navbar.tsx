import { Link as RouterLink, useNavigate } from 'react-router-dom';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import { useAuth } from '../contexts/AuthContext';

const Navbar = () => {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    return (
        <AppBar position="static" elevation={0} sx={{ 
            bgcolor: 'rgba(15, 23, 42, 0.85)', 
            backdropFilter: 'blur(12px)',
            borderBottom: '1px solid rgba(255,255,255,0.05)'
        }}>
            <Toolbar>
                <Typography
                    variant="h5"
                    component={RouterLink}
                    to="/"
                    sx={{ flexGrow: 1, textDecoration: 'none', color: 'white', fontWeight: 800, letterSpacing: 1 }}
                >
                    SDE
                </Typography>
                <Box sx={{ display: 'flex', gap: { xs: 1, md: 3 }, alignItems: 'center' }}>
                    {user ? (
                        <>
                            <Button component={RouterLink} to="/multiplayer" sx={{ color: 'rgba(255,255,255,0.8)', fontWeight: 600 }}>
                                Multiplayer
                            </Button>
                            <Button variant="outlined" component={RouterLink} to="/create-game" size="small" sx={{ borderColor: 'rgba(255,255,255,0.2)', color: 'white', borderRadius: 2 }}>
                                Create Game
                            </Button>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, ml: { xs: 0, md: 2 } }}>
                                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: 1 }}>
                                    {user.username}
                                </Typography>
                                <Button size="small" onClick={handleLogout} sx={{ color: 'rgba(255,255,255,0.4)', minWidth: 'auto', p: 1 }}>
                                    Logout
                                </Button>
                            </Box>
                        </>
                    ) : (
                        <>
                            <Button component={RouterLink} to="/login" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                                Log In
                            </Button>
                            <Button variant="contained" color="primary" component={RouterLink} to="/signup" sx={{ borderRadius: 2 }}>
                                Sign Up
                            </Button>
                        </>
                    )}
                </Box>
            </Toolbar>
        </AppBar>
    );
};

export default Navbar;

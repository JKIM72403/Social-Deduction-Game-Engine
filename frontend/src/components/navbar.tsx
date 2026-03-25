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
        navigate('/');
    };

    return (
        <AppBar position="static" elevation={1}>
            <Toolbar>
                <Typography
                    variant="h6"
                    component={RouterLink}
                    to="/"
                    sx={{ flexGrow: 1, textDecoration: 'none', color: 'inherit', fontWeight: 'bold' }}
                >
                    Social Deduction Engine
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                    <Button color="inherit" component={RouterLink} to="/">
                        Home
                    </Button>
                    {user ? (
                        <>
                            <Button color="inherit" component={RouterLink} to="/multiplayer">
                                Join Lobby
                            </Button>
                            <Button variant="contained" color="secondary" component={RouterLink} to="/create-game">
                                Create Game
                            </Button>
                            <Typography variant="body2" color="inherit" sx={{ fontWeight: 600 }}>
                                {user.username}
                            </Typography>
                            <Button color="inherit" onClick={handleLogout}>
                                Log Out
                            </Button>
                        </>
                    ) : (
                        <>
                            <Button color="inherit" component={RouterLink} to="/login">
                                Log In
                            </Button>
                            <Button variant="contained" color="secondary" component={RouterLink} to="/signup">
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

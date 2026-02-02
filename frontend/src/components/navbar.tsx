import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';

const Navbar = () => {
    const menuItems = ['File', 'Edit', 'Help'];

    return (
        <AppBar position="static" elevation={0} sx={{ 
            borderBottom: '1px solid', 
            borderColor: 'divider',
            bgcolor: 'background.paper',
            height: 48, // Dense toolbar height
            justifyContent: 'center'
        }}>
            <Toolbar variant="dense" sx={{ minHeight: 48 }}>
                <Box sx={{ display: 'flex', gap: 1 }}>
                    {menuItems.map((item) => (
                        <Button
                            key={item}
                            color="inherit"
                            sx={{
                                color: 'text.secondary',
                                fontWeight: 500,
                                minWidth: 'auto',
                                px: 1,
                                '&:hover': {
                                    color: 'text.primary',
                                    backgroundColor: 'action.hover',
                                },
                            }}
                        >
                            {item}
                        </Button>
                    ))}
                </Box>
            </Toolbar>
        </AppBar>
    );
};

export default Navbar;

import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Navbar from '../components/navbar';
import Sidebar from '../components/sidebar';
import EditPanel from '../components/edit-panel';

const HomePage = () => {
    return (
        <Box sx={{ 
            height: '100vh', 
            display: 'flex', 
            flexDirection: 'column',
            overflow: 'hidden',
            bgcolor: 'background.default'
        }}>
            <Navbar />
            <Box sx={{ 
                flex: 1, 
                display: 'flex', 
                overflow: 'hidden' 
            }}>
                <Sidebar />
                
                <Box component="main" sx={{ 
                    flex: 1, 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                    position: 'relative',
                    background: 'radial-gradient(circle at center, #1e293b 0%, #0f172a 100%)'
                }}>
                    <Box sx={{ textAlign: 'center' }}>
                        <Typography variant="h5" color="text.primary" fontWeight={500}>
                            Game View
                        </Typography>
                        <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
                            (can be empty for now)
                        </Typography>
                    </Box>
                </Box>

                <EditPanel />
            </Box>
        </Box>
    );
};

export default HomePage;

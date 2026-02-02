import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';

const EditPanel = () => {
    return (
        <Box sx={{
            width: 280,
            bgcolor: 'background.paper',
            borderLeft: '1px solid',
            borderColor: 'divider',
            p: 3,
            display: 'flex',
            flexDirection: 'column',
            overflowY: 'auto'
        }}>
            <Box sx={{ 
                borderBottom: '2px solid', 
                borderColor: 'primary.main', 
                pb: 1, 
                mb: 3, 
                alignSelf: 'center' 
            }}>
                <Typography variant="h6">Edit Panel</Typography>
            </Box>

            <Paper variant="outlined" sx={{ 
                p: 2, 
                bgcolor: 'rgba(255,255,255,0.05)', 
                borderStyle: 'dashed',
                mb: 4
            }}>
                <Typography variant="body2" color="text.secondary">
                    (This is where you edit or create a new role, phase, class etc. 
                    Basically just a big menu with dropdowns and text boxes for each thing)
                </Typography>
            </Paper>
            
            {/* Mock input fields */}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, opacity: 0.5 }}>
                 <Box sx={{ height: 30, bgcolor: 'action.hover', borderRadius: 1 }} />
                 <Box sx={{ height: 30, bgcolor: 'action.hover', borderRadius: 1 }} />
                 <Box sx={{ height: 80, bgcolor: 'action.hover', borderRadius: 1 }} />
            </Box>
        </Box>
    );
};

export default EditPanel;

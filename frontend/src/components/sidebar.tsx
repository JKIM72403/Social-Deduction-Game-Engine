import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Link from '@mui/material/Link';
import CircleIcon from '@mui/icons-material/Circle';
import AddIcon from '@mui/icons-material/Add';

interface SidebarSectionProps {
    title: string;
    items: string[];
}

const SidebarSection = ({ title, items }: SidebarSectionProps) => (
    <Box sx={{ mb: 3 }}>
        <Box sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            mb: 1,
            border: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
            px: 1,
            py: 0.5,
            borderRadius: 1
        }}>
            <Typography variant="subtitle2" fontWeight={600}>
                {title}
            </Typography>
            <IconButton size="small" sx={{ p: 0.5 }}>
                <AddIcon fontSize="small" />
            </IconButton>
        </Box>
        <List disablePadding>
            {items.map((item, index) => (
                <ListItem key={index} disablePadding sx={{ mb: 0.5 }}>
                    <CircleIcon sx={{ fontSize: 6, color: 'text.secondary', mr: 1 }} />
                    <ListItemText 
                        primary={item} 
                        primaryTypographyProps={{ variant: 'body2', fontSize: '0.9rem' }} 
                    />
                    <Link href="#" underline="hover" sx={{ fontSize: '0.8rem', color: 'text.secondary' }}>
                        [edit]
                    </Link>
                </ListItem>
            ))}
        </List>
    </Box>
);

const Sidebar = () => {
    return (
        <Box sx={{
            width: 260,
            bgcolor: 'background.default',
            borderRight: '1px solid',
            borderColor: 'divider',
            p: 2,
            display: 'flex',
            flexDirection: 'column',
            overflowY: 'auto'
        }}>
            <Button 
                variant="contained" 
                color="primary" 
                fullWidth 
                sx={{ mb: 3, fontWeight: 'bold' }}
            >
                Play Game
            </Button>

            <SidebarSection
                title="Roles"
                items={['Murderer', 'Sheriff', 'Citizen', 'Baker']}
            />
            
            <SidebarSection
                title="Phases"
                items={['Daytime', 'Nighttime', 'Voting']}
            />

            <SidebarSection
                title="Win Conditions"
                items={['Killer wins', 'Citizen wins']}
            />
        </Box>
    );
};

export default Sidebar;

import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import AddIcon from '@mui/icons-material/Add';
import CircleIcon from '@mui/icons-material/Circle';
import type { GameData } from '../types';

interface SidebarProps {
    gameData: GameData;
    onSelect: (type: 'GAME_SETTINGS' | 'ROLE', id?: number) => void;
    onAddRole: () => void;
}

interface SidebarSectionProps {
    title: string;
    items: { label: string; id?: number }[];
    onItemClick: (id?: number) => void;
    onAdd?: () => void;
}

const SidebarSection = ({ title, items, onItemClick, onAdd }: SidebarSectionProps) => (
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
            {onAdd && (
                <IconButton size="small" sx={{ p: 0.5 }} onClick={(e) => { e.stopPropagation(); onAdd(); }}>
                    <AddIcon fontSize="small" />
                </IconButton>
            )}
        </Box>
        <List disablePadding>
            {items.map((item, index) => (
                <ListItem
                    key={index}
                    disablePadding
                    sx={{
                        mb: 0.5,
                        cursor: 'pointer',
                        '&:hover': { bgcolor: 'action.hover' }
                    }}
                    onClick={() => onItemClick(item.id)}
                >
                    <CircleIcon sx={{ fontSize: 6, color: 'text.secondary', mr: 1, ml: 1 }} />
                    <ListItemText
                        primary={item.label}
                        primaryTypographyProps={{ variant: 'body2', fontSize: '0.9rem' }}
                    />
                </ListItem>
            ))}
            {items.length === 0 && (
                <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                    No items
                </Typography>
            )}
        </List>
    </Box>
);

const Sidebar = ({ gameData, onSelect, onAddRole }: SidebarProps) => {
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
                onClick={() => onSelect('GAME_SETTINGS')}
            >
                Game Settings
            </Button>

            <SidebarSection
                title="Roles"
                items={gameData.role_slots.map(slot => ({ label: `${slot.roleName} (x${slot.count})`, id: slot.roleId }))}
                onItemClick={(id) => onSelect('ROLE', id)}
                onAdd={onAddRole}
            />

            <SidebarSection
                title="Phases"
                items={[{ label: 'Day', id: 1 }, { label: 'Night', id: 2 }]} // Placeholder
                onItemClick={() => { }}
            />
        </Box>
    );
};

export default Sidebar;

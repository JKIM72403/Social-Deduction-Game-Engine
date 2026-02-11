import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import RoleEditor from './RoleEditor';
import type { GameData } from '../types';

interface EditPanelProps {
    selection: { type: 'GAME_SETTINGS' } | { type: 'ROLE', roleId: number } | { type: 'NEW_ROLE' } | { type: 'EDIT_ROLE_DETAILS', roleId: number } | null;
    gameData: GameData;
    onUpdateGame: (data: Partial<GameData>) => void;
    onSaveRole: (role: any) => void;
    onCancel: () => void;
    onEditRoleDetails: (roleId: number) => void;
}

const EditPanel = ({ selection, gameData, onUpdateGame, onSaveRole, onCancel, onEditRoleDetails }: EditPanelProps) => {
    if (!selection) {
        return (
            <Box sx={{ width: 350, p: 3, textAlign: 'center', color: 'text.secondary' }}>
                <Typography>Select an item to edit</Typography>
            </Box>
        );
    }

    if (selection.type === 'NEW_ROLE') {
        return (
            <Box sx={{ width: 400, bgcolor: 'background.paper', borderLeft: '1px solid', borderColor: 'divider', p: 3, overflowY: 'auto' }}>
                <RoleEditor onSave={onSaveRole} onCancel={onCancel} />
            </Box>
        );
    }

    if (selection.type === 'EDIT_ROLE_DETAILS') {
        return (
            <Box sx={{ width: 400, bgcolor: 'background.paper', borderLeft: '1px solid', borderColor: 'divider', p: 3, overflowY: 'auto' }}>
                <RoleEditor
                    roleId={selection.roleId}
                    onSave={(updatedRole) => {
                        onSaveRole(updatedRole);
                    }}
                    onCancel={onCancel}
                />
            </Box>
        );
    }

    if (selection.type === 'GAME_SETTINGS') {
        return (
            <Box sx={{ width: 350, bgcolor: 'background.paper', borderLeft: '1px solid', borderColor: 'divider', p: 3 }}>
                <Typography variant="h6" sx={{ mb: 3 }}>Game Settings</Typography>

                <TextField
                    fullWidth
                    label="Game Name"
                    value={gameData.name}
                    onChange={(e) => onUpdateGame({ name: e.target.value })}
                    sx={{ mb: 2 }}
                />

                <Box sx={{ display: 'flex', gap: 2 }}>
                    <TextField
                        type="number"
                        label="Min Players"
                        value={gameData.min_players}
                        onChange={(e) => onUpdateGame({ min_players: parseInt(e.target.value) })}
                    />
                    <TextField
                        type="number"
                        label="Max Players"
                        value={gameData.max_players}
                        onChange={(e) => onUpdateGame({ max_players: parseInt(e.target.value) })}
                    />
                </Box>
            </Box>
        );
    }

    if (selection.type === 'ROLE') {
        const slot = gameData.role_slots.find(s => s.roleId === selection.roleId);
        if (!slot) return null;

        return (
            <Box sx={{ width: 350, bgcolor: 'background.paper', borderLeft: '1px solid', borderColor: 'divider', p: 3 }}>
                <Typography variant="h6" sx={{ mb: 3 }}>Edit Role Slot</Typography>

                <Typography variant="subtitle1" sx={{ mb: 2 }}>
                    {slot.roleName}
                </Typography>

                <TextField
                    type="number"
                    label="Count"
                    value={slot.count}
                    onChange={(e) => {
                        const val = e.target.value;
                        const newCount = val === '' ? 0 : parseInt(val);
                        if (!isNaN(newCount) && newCount >= 0) {
                            const newSlots = gameData.role_slots.map(s =>
                                s.roleId === slot.roleId ? { ...s, count: newCount } : s
                            );
                            onUpdateGame({ role_slots: newSlots });
                        }
                    }}
                    fullWidth
                    sx={{ mb: 3 }}
                />

                <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => onEditRoleDetails(selection.roleId)}
                >
                    Edit Role Details
                </Button>
            </Box>
        );
    }

    return null;
};

export default EditPanel;

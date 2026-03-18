import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Switch from '@mui/material/Switch';
import FormControlLabel from '@mui/material/FormControlLabel';
import RoleEditor from './RoleEditor';
import AbilityEditor from './AbilityEditor';
import type { GameData } from '../types';

interface GameValidationState {
    errors: string[];
    totalRoleSlots: number;
    minPlayersError?: string;
    maxPlayersError?: string;
    roleSlotErrors: Record<number, string>;
}

interface EditPanelProps {
    selection: { type: 'GAME_SETTINGS' } | { type: 'ROLE', roleId: number } | { type: 'NEW_ROLE' } | { type: 'EDIT_ROLE_DETAILS', roleId: number } |
    { type: 'NEW_ABILITY' } | { type: 'EDIT_ABILITY_DETAILS', roleId: number } | null;
    gameData: GameData;
    validationState: GameValidationState;
    onUpdateGame: (data: Partial<GameData>) => void;
    onSaveRole: (role: any) => void;
    onSaveAbility?: (ability: any) => void;
    onDeleteAbility?: (abilityId: number) => void;
    onCancel: () => void;
    onEditRoleDetails: (roleId: number) => void;
}

const EditPanel = ({ selection, gameData, validationState, onUpdateGame, onSaveRole, onSaveAbility, onDeleteAbility, onCancel, onEditRoleDetails }: EditPanelProps) => {
    if (!selection) {
        return (
            <Box sx={{ width: 350, p: 3, textAlign: 'center', color: 'text.secondary' }}>
                <Typography>Select an item to edit</Typography>
            </Box>
        );
    }

    if (selection.type === 'NEW_ABILITY') {
        return (
            <Box sx={{ width: 400, bgcolor: 'background.paper', borderLeft: '1px solid', borderColor: 'divider', p: 3, overflowY: 'auto' }}>
                <AbilityEditor onSave={onSaveAbility!} onCancel={onCancel} />
            </Box>
        );
    }

    if (selection.type === 'EDIT_ABILITY_DETAILS') {
        return (
            <Box sx={{ width: 400, bgcolor: 'background.paper', borderLeft: '1px solid', borderColor: 'divider', p: 3, overflowY: 'auto' }}>
                <AbilityEditor
                    abilityId={selection.roleId} // 'roleId' holds the generic selection ID here
                    onSave={(updatedAbility) => {
                        onSaveAbility!(updatedAbility);
                    }}
                    onDelete={() => {
                        if (onDeleteAbility) onDeleteAbility(selection.roleId);
                    }}
                    onCancel={onCancel}
                />
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

                <Box sx={{ mb: 2, transform: 'translateZ(0)', willChange: 'transform' }}>
                    <FormControlLabel
                        control={
                            <Switch
                                checked={gameData.is_public !== false}
                                onChange={(e) => onUpdateGame({ is_public: e.target.checked })}
                            />
                        }
                        label="Public Game (visible to all)"
                    />
                </Box>

                <Box sx={{ display: 'flex', gap: 2 }}>
                    <TextField
                        type="number"
                        label="Min Players"
                        value={gameData.min_players}
                        onChange={(e) => onUpdateGame({ min_players: parseInt(e.target.value) })}
                        error={Boolean(validationState.minPlayersError)}
                        helperText={validationState.minPlayersError || `Total role slots: ${validationState.totalRoleSlots}`}
                    />
                    <TextField
                        type="number"
                        label="Max Players"
                        value={gameData.max_players}
                        onChange={(e) => onUpdateGame({ max_players: parseInt(e.target.value) })}
                        error={Boolean(validationState.maxPlayersError)}
                        helperText={validationState.maxPlayersError || "Set the upper player limit for this template."}
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
                    error={Boolean(validationState.roleSlotErrors[slot.roleId])}
                    helperText={validationState.roleSlotErrors[slot.roleId] || `Total role slots: ${validationState.totalRoleSlots}`}
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

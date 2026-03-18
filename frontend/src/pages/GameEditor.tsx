import { useState, useEffect } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import Sidebar from '../components/sidebar';
import EditPanel from '../components/edit-panel';
import { API } from '../services/api';
import type { GameData, RoleSlot } from '../types';
import { useNavigate, useParams } from 'react-router-dom';

type Selection = { type: 'GAME_SETTINGS' } | { type: 'ROLE', roleId: number } | { type: 'NEW_ROLE' } |
{ type: 'EDIT_ROLE_DETAILS', roleId: number } | { type: 'NEW_ABILITY' } | { type: 'EDIT_ABILITY_DETAILS', roleId: number } | null;

type GameValidationState = {
    errors: string[];
    totalRoleSlots: number;
    minPlayersError?: string;
    maxPlayersError?: string;
    roleSlotErrors: Record<number, string>;
};

function getGameValidationState(gameData: GameData): GameValidationState {
    const errors: string[] = [];
    const { min_players, max_players, role_slots } = gameData;
    const roleSlotErrors: Record<number, string> = {};

    const minIsValid = Number.isInteger(min_players) && min_players >= 1;
    const maxIsValid = Number.isInteger(max_players) && max_players >= 1;
    const totalRoleSlots = role_slots.reduce((sum, slot) => sum + (Number.isFinite(slot.count) ? slot.count : 0), 0);
    let minPlayersError: string | undefined;
    let maxPlayersError: string | undefined;

    if (!minIsValid) {
        minPlayersError = "Enter a whole number of at least 1.";
        errors.push("Min Players must be a whole number of at least 1.");
    }

    if (!maxIsValid) {
        maxPlayersError = "Enter a whole number of at least 1.";
        errors.push("Max Players must be a whole number of at least 1.");
    }

    if (minIsValid && maxIsValid && min_players > max_players) {
        minPlayersError = "Min Players cannot be greater than Max Players.";
        maxPlayersError = "Max Players must be at least Min Players.";
        errors.push("Min Players cannot be greater than Max Players.");
    }

    if (role_slots.length === 0) {
        errors.push("Add at least one role slot before saving.");
    }

    const invalidSlots = role_slots.filter(
        (slot) => !Number.isInteger(slot.count) || slot.count <= 0
    );

    if (invalidSlots.length > 0) {
        invalidSlots.forEach((slot) => {
            roleSlotErrors[slot.roleId] = "Count must be a positive whole number.";
        });
        const slotNames = invalidSlots.map((slot) => slot.roleName).join(", ");
        errors.push(`All role slot counts must be positive whole numbers. Fix: ${slotNames}.`);
    }

    if (minIsValid && invalidSlots.length === 0 && totalRoleSlots < min_players) {
        minPlayersError = `Total role slots (${totalRoleSlots}) is below Min Players (${min_players}).`;
        errors.push(`Total role slots (${totalRoleSlots}) must be at least Min Players (${min_players}).`);
    }

    if (maxIsValid && invalidSlots.length === 0 && totalRoleSlots > max_players) {
        maxPlayersError = `Total role slots (${totalRoleSlots}) exceeds Max Players (${max_players}).`;
        errors.push(`Total role slots (${totalRoleSlots}) cannot exceed Max Players (${max_players}).`);
    }

    return {
        errors,
        totalRoleSlots,
        minPlayersError,
        maxPlayersError,
        roleSlotErrors,
    };
}

const GameEditor = () => {
    const navigate = useNavigate();
    const { id } = useParams();
    const [gameData, setGameData] = useState<GameData>({
        name: "New Game",
        min_players: 4,
        max_players: 10,
        is_public: true,
        role_slots: []
    });
    // This state variable key forces the Sidebar to remount/re-fetch abilities when an ability is saved
    const [abilityUpdateKey, setAbilityUpdateKey] = useState(0);
    const [selection, setSelection] = useState<Selection>({ type: 'GAME_SETTINGS' });
    const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const validationState = getGameValidationState(gameData);
    const validationErrors = validationState.errors;
    const hasValidationErrors = validationErrors.length > 0;
    const totalRoleSlots = validationState.totalRoleSlots;

    useEffect(() => {
        if (id) {
            API.get(`/game-templates/${id}/`)
                .then(res => {
                    const data = res.data;
                    // Transform API response to internal GameData format
                    const role_slots = data.role_slots.map((s: any) => ({
                        roleId: s.role,
                        roleName: s.role_details ? s.role_details.name : "Unknown Role",
                        count: s.count
                    }));
                    setGameData({
                        name: data.name,
                        min_players: data.min_players,
                        max_players: data.max_players,
                        is_public: data.is_public !== undefined ? data.is_public : true,
                        role_slots: role_slots
                    });
                })
                .catch(err => {
                    console.error("Failed to fetch game", err);
                    alert("Could not load game details.");
                    navigate("/");
                });
        }
    }, [id, navigate]);

    const handleUpdateGame = (data: Partial<GameData>) => {
        setGameData(prev => ({ ...prev, ...data }));
    };

    const handleRoleSaved = (role: any) => {
        // If it's a new role (not in slots), add it.
        // If it's an existing role, just update name in slots if needed.
        setGameData(prev => {
            const existingSlotIndex = prev.role_slots.findIndex(s => s.roleId === role.id);
            if (existingSlotIndex >= 0) {
                // Update name if changed
                const newSlots = [...prev.role_slots];
                newSlots[existingSlotIndex] = { ...newSlots[existingSlotIndex], roleName: role.name };
                return { ...prev, role_slots: newSlots };
            } else {
                // Add new role slot
                const newSlot: RoleSlot = {
                    roleId: role.id,
                    roleName: role.name,
                    count: 1
                };
                return { ...prev, role_slots: [...prev.role_slots, newSlot] };
            }
        });

        // Go back to the role slot view
        setSelection({ type: 'ROLE', roleId: role.id });
    };

    const handleAbilitySaved = (ability: any) => {
        setAbilityUpdateKey(prev => prev + 1); // trigger sidebar re-fetch
        setSelection({ type: 'EDIT_ABILITY_DETAILS', roleId: ability.id }); // Using roleId as a loosely 
        // structured generic ID here based on the Selection type definition
    };

    const handleDeleteAbility = () => {
        setAbilityUpdateKey(prev => prev + 1); // trigger sidebar re-fetch
        setSelection({ type: 'GAME_SETTINGS' });
    };

    const handleSnackbarClose = () => {
        setSnackbar(prev => ({ ...prev, open: false }));
    };

    const handleSaveGame = async () => {
        if (hasValidationErrors) {
            setSnackbar({ open: true, message: "Fix validation errors before saving.", severity: 'error' });
            return;
        }

        try {
            const payload = {
                name: gameData.name,
                min_players: gameData.min_players,
                max_players: gameData.max_players,
                is_public: gameData.is_public,
                role_slots: gameData.role_slots.map(slot => ({
                    role: slot.roleId,
                    count: slot.count
                }))
            };

            if (id) {
                await API.put(`/game-templates/${id}/`, payload);
                setSnackbar({ open: true, message: "Game Updated Successfully!", severity: 'success' });
            } else {
                await API.post("/game-templates/", payload);
                setSnackbar({ open: true, message: "Game Created Successfully!", severity: 'success' });
            }
            // Navigate after a short delay so the user can see the snackbar
            setTimeout(() => {
                navigate("/");
            }, 1000);
        } catch (e) {
            console.error(e);
            setSnackbar({ open: true, message: "Failed to save game.", severity: 'error' });
        }
    };

    const confirmDeleteGame = async () => {
        if (!id) return;
        try {
            await API.delete(`/game-templates/${id}/`);
            setSnackbar({ open: true, message: "Game Deleted Successfully!", severity: 'success' });
            setTimeout(() => {
                navigate("/");
            }, 1000);
        } catch (e) {
            console.error(e);
            setSnackbar({ open: true, message: "Failed to delete game.", severity: 'error' });
        } finally {
            setDeleteDialogOpen(false);
        }
    };

    return (
        <Box sx={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            bgcolor: 'background.default',
            flexGrow: 1
        }}>
            <Box sx={{
                flex: 1,
                display: 'flex',
                overflow: 'hidden'
            }}>
                <Sidebar
                    key={abilityUpdateKey}
                    gameData={gameData}
                    onSelect={(type, roleId) => setSelection((type === 'ROLE' || type === 'EDIT_ABILITY_DETAILS') &&
                        roleId ? { type, roleId: roleId } : { type: type as any })}
                    onAddRole={() => setSelection({ type: 'NEW_ROLE' })}
                    onAddAbility={() => setSelection({ type: 'NEW_ABILITY' })}
                />

                <Box component="main" sx={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    position: 'relative',
                    background: 'radial-gradient(circle at center, #1e293b 0%, #0f172a 100%)',
                    flexDirection: 'column',
                    gap: 2
                }}>
                    <Box sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="text.primary" fontWeight={600}>
                            {gameData.name}
                        </Typography>
                        <Typography variant="subtitle1" color="text.secondary">
                            {gameData.min_players} - {gameData.max_players} Players
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                            {gameData.role_slots.length} Roles Configured
                        </Typography>
                        <Typography
                            variant="body2"
                            color={hasValidationErrors ? 'error.main' : 'text.secondary'}
                            sx={{ mt: 0.5 }}
                        >
                            Total Role Slots: {totalRoleSlots}
                        </Typography>
                    </Box>

                    {hasValidationErrors && (
                        <Alert severity="error" sx={{ width: '100%', maxWidth: 640 }}>
                            <Typography variant="subtitle2" sx={{ mb: 1 }}>
                                Fix these issues before saving:
                            </Typography>
                            <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
                                {validationErrors.map((error, idx) => (
                                    <Box component="li" key={idx} sx={{ mb: 0.5 }}>
                                        <Typography variant="body2">{error}</Typography>
                                    </Box>
                                ))}
                            </Box>
                        </Alert>
                    )}

                    <Box sx={{ display: 'flex', gap: 2 }}>
                        {id && (
                            <Button variant="outlined" color="error" onClick={() => setDeleteDialogOpen(true)} size="large">
                                Delete Game
                            </Button>
                        )}
                        <Button
                            variant="contained"
                            color="primary"
                            onClick={handleSaveGame}
                            size="large"
                            disabled={hasValidationErrors}
                        >
                            Save Game
                        </Button>
                    </Box>
                </Box>

                <EditPanel
                    selection={selection}
                    gameData={gameData}
                    validationState={validationState}
                    onUpdateGame={handleUpdateGame}
                    onSaveRole={handleRoleSaved}
                    onSaveAbility={handleAbilitySaved}
                    onDeleteAbility={handleDeleteAbility}
                    onCancel={() => setSelection({ type: 'GAME_SETTINGS' })}
                    onEditRoleDetails={(roleId) => setSelection({ type: 'EDIT_ROLE_DETAILS', roleId })}
                />
            </Box>

            <Snackbar
                open={snackbar.open}
                autoHideDuration={6000}
                onClose={handleSnackbarClose}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
            >
                <Alert onClose={handleSnackbarClose} severity={snackbar.severity} sx={{ width: '100%' }}>
                    {snackbar.message}
                </Alert>
            </Snackbar>

            <Dialog
                open={deleteDialogOpen}
                onClose={() => setDeleteDialogOpen(false)}
            >
                <DialogTitle>Delete Game?</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        Are you sure you want to permanently delete "{gameData.name}"? This action cannot be undone.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDeleteDialogOpen(false)} color="secondary">Cancel</Button>
                    <Button onClick={confirmDeleteGame} color="error" variant="contained">Delete</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default GameEditor;

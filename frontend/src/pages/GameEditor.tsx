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
import type { GameData, Phase, WinCondition, RoleSlot, RoleTemplate } from '../types';
import type { Selection } from '../components/edit-panel';
import { useNavigate, useParams } from 'react-router-dom';
import bgImage from '../assets/mafia_bg.png';

type GameTemplateAPIResponse = {
    id: number;
    name: string;
    min_players: number;
    max_players: number;
    is_public: boolean;
    role_slots: Array<{
        role: number;
        count: number;
        role_details?: RoleTemplate;
    }>;
    phases: Phase[];
    win_conditions: WinCondition[];
};

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
        role_slots: [],
        phases: [
            { name: "Night (default)", phase_type: "NIGHT", order: 0 },
            { name: "Day (default)", phase_type: "DAY", order: 1 },
            { name: "Voting (default)", phase_type: "VOTING", order: 2 }
        ],
        win_conditions: [
            {
                name: "Town Victory (default)",
                winner_alignment: 1, // Placeholder for Town
                order: 0,
                criteria: [{ type: "ALIGNMENT_COUNT", target: "MAFIA", count: 0 }]
            },
            {
                name: "Mafia Victory (default)",
                winner_alignment: 2, // Placeholder for Mafia
                order: 1,
                criteria: [{ type: "ALIGNMENT_COUNT", target: "TOWN", count: 0 }]
            }
        ]
    });

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
                    const data = res.data as GameTemplateAPIResponse;
                    // Transform API response to internal GameData format
                    const role_slots = data.role_slots.map((s) => ({
                        roleId: s.role,
                        roleName: s.role_details ? s.role_details.name : "Unknown Role",
                        count: s.count,
                        isDefault: s.role_details ? s.role_details.is_default : false
                    }));
                    setGameData({
                        id: data.id,
                        name: data.name,
                        min_players: data.min_players,
                        max_players: data.max_players,
                        is_public: data.is_public !== undefined ? data.is_public : true,
                        role_slots: role_slots,
                        phases: data.phases || [],
                        win_conditions: data.win_conditions || [],
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

    const handleRoleSaved = (role: RoleTemplate, originalId?: number) => {
        setGameData(prev => {
            // Match against originalId if provided (handles cloning), else use the new role.id
            const searchId = originalId ?? role.id;
            const existingSlotIndex = prev.role_slots.findIndex(s => s.roleId === searchId);
            
            if (existingSlotIndex >= 0) {
                const newSlots = [...prev.role_slots];
                newSlots[existingSlotIndex] = {
                    ...newSlots[existingSlotIndex],
                    roleId: role.id as number, // Update to the new ID (if cloned)
                    roleName: role.name,
                    isDefault: role.is_default
                };
                return { ...prev, role_slots: newSlots };
            } else {
                const newSlot: RoleSlot = {
                    roleId: role.id as number,
                    roleName: role.name,
                    count: 1,
                    isDefault: role.is_default
                };
                return { ...prev, role_slots: [...prev.role_slots, newSlot] };
            }
        });
        setSelection({ type: 'ROLE', id: role.id as number });
    };

    const handleDeleteRole = (id: number) => {
        setGameData(prev => ({
            ...prev,
            role_slots: prev.role_slots.filter(s => s.roleId !== id)
        }));
        setSelection({ type: 'GAME_SETTINGS' });
    };

    const handlePhaseSaved = (phase: Phase, index?: number) => {
        setGameData(prev => {
            const newPhases = [...prev.phases];
            if (index !== undefined && index >= 0) {
                newPhases[index] = phase;
            } else {
                newPhases.push(phase);
            }
            return { ...prev, phases: newPhases.sort((a, b) => (a.order ?? 0) - (b.order ?? 0)) };
        });
        setSelection({ type: 'GAME_SETTINGS' }); // Reset selection after save for simplicity or find new index
    };

    const handleDeletePhase = (id?: number, index?: number) => {
        setGameData(prev => {
            const newPhases = prev.phases.filter((p, i) => {
                if (id !== undefined && id !== null && p.id === id) return false;
                if (index !== undefined && i === index) return false;
                return true;
            });
            return { ...prev, phases: newPhases };
        });
        setSelection({ type: 'GAME_SETTINGS' });
    };

    const handleWinConditionSaved = (wc: WinCondition, index?: number) => {
        setGameData(prev => {
            const newWcs = [...prev.win_conditions];
            if (index !== undefined && index >= 0) {
                newWcs[index] = wc;
            } else {
                newWcs.push(wc);
            }
            return { ...prev, win_conditions: newWcs };
        });
        setSelection({ type: 'GAME_SETTINGS' });
    };

    const handleDeleteWinCondition = (id?: number, index?: number) => {
        setGameData(prev => {
            const newWcs = prev.win_conditions.filter((w, i) => {
                if (id !== undefined && id !== null && w.id === id) return false;
                if (index !== undefined && i === index) return false;
                return true;
            });
            return { ...prev, win_conditions: newWcs };
        });
        setSelection({ type: 'GAME_SETTINGS' });
    };

    const handleReorderPhases = async (newPhases: Phase[]) => {
        setGameData(prev => ({ ...prev, phases: newPhases }));
        const orders = newPhases.map(p => ({ id: p.id, order: p.order })).filter(o => o.id !== undefined);
        if (orders.length === 0) return;

        try {
            await API.post('/phases/reorder/', { orders });
        } catch (e) {
            console.error("Failed to persist phase order", e);
        }
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
                })),
                phases: gameData.phases.map(p => ({
                    name: p.name,
                    phase_type: p.phase_type,
                    order: p.order
                })),
                win_conditions: gameData.win_conditions.map(wc => ({
                    name: wc.name,
                    winner_alignment: wc.winner_alignment,
                    criteria: wc.criteria,
                    order: wc.order
                }))
            };

            let res;
            if (id) {
                res = await API.put(`/game-templates/${id}/`, payload);
                setSnackbar({ open: true, message: "Game Updated Successfully!", severity: 'success' });
            } else {
                res = await API.post("/game-templates/", payload);
                setSnackbar({ open: true, message: "Game Created Successfully! Default phases and win conditions added.", severity: 'success' });
                // Update navigation and state with the new ID
                navigate(`/edit-game/${res.data.id}`, { replace: true });
            }

            // Sync state with backend response (includes generated IDs and defaults)
            const data = res.data as GameTemplateAPIResponse;
            setGameData({
                id: data.id,
                name: data.name,
                min_players: data.min_players,
                max_players: data.max_players,
                is_public: data.is_public !== undefined ? data.is_public : true,
                role_slots: data.role_slots.map((s) => ({
                    roleId: s.role,
                    roleName: s.role_details?.name || 'Unknown',
                    count: s.count
                })),
                phases: data.phases || [],
                win_conditions: data.win_conditions || []
            });

        } catch (e: unknown) {
            console.error(e);
            let errMsg = "Failed to save game.";
            if (typeof e === 'object' && e !== null && 'response' in e) {
                const err = e as { response?: { data?: unknown } };
                if (err.response?.data) {
                    if (typeof err.response.data === 'string') errMsg = err.response.data;
                    else if (typeof err.response.data === 'object' && 'detail' in err.response.data) {
                        errMsg = String(err.response.data.detail);
                    } else {
                        errMsg = JSON.stringify(err.response.data);
                    }
                }
            }
            setSnackbar({ open: true, message: errMsg, severity: 'error' });
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
            height: '100vh',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            backgroundImage: `url(${bgImage})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            position: 'relative',
            '&::before': {
                content: '""',
                position: 'absolute',    
                top: 0, left: 0, right: 0, bottom: 0,
                backgroundColor: 'rgba(10, 15, 25, 0.55)', 
                zIndex: 0
            }
        }}>
            <Box sx={{
                flex: 1,
                display: 'flex',
                overflow: 'hidden',
                position: 'relative',
                zIndex: 1
            }}>
                <Sidebar
                    gameData={gameData}
                    onSelect={(type, id, index) => {
                        if (type === 'ROLE' && id !== undefined) {
                            setSelection({ type: 'ROLE', id });
                        } else if (type === 'PHASE' && index !== undefined) {
                            setSelection({ type: 'PHASE', id, index });
                        } else if (type === 'WIN_CONDITION' && index !== undefined) {
                            setSelection({ type: 'WIN_CONDITION', id, index });
                        } else if ((type as string) === 'ALIGNMENT_MANAGER') {
                            setSelection({ type: 'ALIGNMENT_MANAGER' });
                        } else {
                            setSelection({ type: 'GAME_SETTINGS' });
                        }
                    }}
                    onAddRole={() => setSelection({ type: 'NEW_ROLE' })}
                    onAddPhase={() => setSelection({ type: 'NEW_PHASE' })}
                    onAddWinCondition={() => setSelection({ type: 'NEW_WIN_CONDITION' })}
                    onReorderPhases={handleReorderPhases}
                />

                <Box component="main" sx={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    position: 'relative',
                    flexDirection: 'column',
                    gap: 2,
                    color: 'white'
                }}>
                    <Box sx={{ textAlign: 'center', bgcolor: 'rgba(30, 41, 59, 0.6)', backdropFilter: 'blur(12px)', p: 4, borderRadius: 3, border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)' }}>
                        <Typography variant="h3" fontWeight={800} sx={{ 
                            background: 'linear-gradient(45deg, #f3f4f6, #9ca3af)',
                            WebkitBackgroundClip: 'text',
                            WebkitTextFillColor: 'transparent',
                            mb: 2
                        }}>
                            {gameData.name}
                        </Typography>
                        <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                            {gameData.min_players} - {gameData.max_players} Players
                        </Typography>
                        <Typography variant="body2" sx={{ mt: 1, color: 'rgba(255,255,255,0.6)' }}>
                            {gameData.role_slots.length} Roles Configured
                        </Typography>
                        <Typography
                            variant="body2"
                            sx={{ mt: 0.5, color: hasValidationErrors ? '#ef4444' : 'rgba(255,255,255,0.6)' }}
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
                    onSavePhase={handlePhaseSaved}
                    onDeletePhase={handleDeletePhase}
                    onSaveWinCondition={handleWinConditionSaved}
                    onDeleteWinCondition={handleDeleteWinCondition}
                    onCancel={() => setSelection({ type: 'GAME_SETTINGS' })}
                    onEditRoleDetails={(id: number) => setSelection({ type: 'EDIT_ROLE_DETAILS', id })}
                    onSwitchToCustomRoleEditor={() => setSelection({ type: 'CREATE_CUSTOM_ROLE' })}
                    onDeleteRole={handleDeleteRole}
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

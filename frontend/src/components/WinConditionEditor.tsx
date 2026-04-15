import { useEffect, useState } from "react";
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import IconButton from '@mui/material/IconButton';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import Divider from '@mui/material/Divider';
import Paper from '@mui/material/Paper';
import { API } from "../services/api";
import type { WinCondition, RoleSlot, Criterion } from "../types";

interface Props {
    gameId?: number;
    winConditionId?: number;
    initialData?: WinCondition;
    roleSlots: RoleSlot[];
    onSave: (wc: WinCondition) => void;
    onCancel: () => void;
    onDelete?: () => void;
}

export default function WinConditionEditor({ gameId, winConditionId, initialData, roleSlots, onSave, onCancel, onDelete }: Props) {
    const [alignments, setAlignments] = useState<any[]>([]);
    const [wc, setWc] = useState<WinCondition>(initialData || {
        name: "",
        winner_alignment: 0,
        criteria: [{ type: 'ALIGNMENT_COUNT', target: 'MAFIA', count: 0 }],
        order: 0
    });
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

    useEffect(() => {
        const params = gameId ? { game_template: gameId } : undefined;
        API.get("/alignments/", { params }).then(res => {
            setAlignments(res.data);
            if (!initialData && !winConditionId && res.data.length > 0) {
                const town = res.data.find((a: any) => a.name.toUpperCase() === 'TOWN');
                const townName = town ? town.name.toUpperCase() : res.data[0].name.toUpperCase();
                setWc(prev => ({
                    ...prev,
                    winner_alignment: town ? town.id : res.data[0].id,
                    criteria: [{ type: 'ALIGNMENT_COUNT', target: townName, count: 0 }]
                }));
            }
        });

        if (initialData) {
            setWc(initialData);
        } else if (winConditionId) {
            API.get(`/win-conditions/${winConditionId}/`).then(res => {
                setWc(res.data);
            });
        }
    }, [gameId, winConditionId, initialData]);

    const submit = async () => {
        if (!gameId) {
            // Local-only save
            onSave(wc);
            return;
        }

        try {
            const payload = { ...wc, game_template: gameId };
            let res;
            if (winConditionId) {
                res = await API.put(`/win-conditions/${winConditionId}/`, payload);
            } else {
                res = await API.post("/win-conditions/", payload);
            }
            onSave(res.data);
        } catch (e) {
            console.error(e);
            alert("Failed to save win condition");
        }
    };

    const confirmDelete = async () => {
        if (!gameId || !winConditionId) {
            if (onDelete) onDelete();
            setDeleteDialogOpen(false);
            return;
        }

        try {
            await API.delete(`/win-conditions/${winConditionId}/`);
            if (onDelete) onDelete();
        } catch (e) {
            console.error(e);
            alert("Failed to delete win condition");
        } finally {
            setDeleteDialogOpen(false);
        }
    };

    const addCriterion = () => {
        setWc({
            ...wc,
            criteria: [...wc.criteria, { type: 'ROLE_COUNT', target: roleSlots[0]?.roleName || '', count: 0 }]
        });
    };

    const removeCriterion = (index: number) => {
        const newCriteria = wc.criteria.filter((_, i) => i !== index);
        setWc({ ...wc, criteria: newCriteria });
    };

    const updateCriterion = (index: number, updates: Partial<Criterion>) => {
        const newCriteria = [...wc.criteria];
        newCriteria[index] = { ...newCriteria[index], ...updates };
        setWc({ ...wc, criteria: newCriteria });
    };

    return (
        <Box>
            <Typography variant="h6" sx={{ mb: 3 }}>
                {(winConditionId || initialData) ? "Edit Win Condition" : "Create Win Condition"}
            </Typography>

            <TextField
                fullWidth
                label="Condition Name"
                value={wc.name}
                placeholder="e.g., Town Victory"
                onChange={e => setWc({ ...wc, name: e.target.value })}
                sx={{ mb: 3 }}
            />

            <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel>Winner Alignment</InputLabel>
                <Select
                    value={wc.winner_alignment}
                    label="Winner Alignment"
                    onChange={e => setWc({ ...wc, winner_alignment: e.target.value as any })}
                >
                    {alignments.map(a => (
                        <MenuItem key={a.id} value={a.id}>{a.name} Wins</MenuItem>
                    ))}
                </Select>
            </FormControl>

            <Divider sx={{ my: 2 }} />

            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>Requirements (AND)</Typography>
                <Button startIcon={<AddIcon />} onClick={addCriterion} size="small">Add Rule</Button>
            </Box>

            {wc.criteria.map((c, index) => (
                <Paper key={index} variant="outlined" sx={{ p: 2, mb: 2, position: 'relative' }}>
                    <IconButton
                        size="small"
                        color="error"
                        onClick={() => removeCriterion(index)}
                        sx={{ position: 'absolute', top: 4, right: 4 }}
                    >
                        <DeleteIcon fontSize="small" />
                    </IconButton>

                    <FormControl fullWidth size="small" sx={{ mb: 2, mt: 1 }}>
                        <InputLabel>Rule Type</InputLabel>
                        <Select
                            value={c.type}
                            label="Rule Type"
                            onChange={e => updateCriterion(index, { type: e.target.value as any, target: e.target.value === 'ROLE_COUNT' ? (roleSlots[0]?.roleName || '') : (alignments[0]?.name.toUpperCase() || 'MAFIA') })}
                        >
                            <MenuItem value="ROLE_COUNT">Specific Role Count</MenuItem>
                            <MenuItem value="ALIGNMENT_COUNT">Alignment Count</MenuItem>
                            <MenuItem value="SURVIVAL">Nights Survived</MenuItem>
                        </Select>
                    </FormControl>

                    <Box sx={{ display: 'flex', gap: 2 }}>
                        {c.type === 'ROLE_COUNT' && (
                            <FormControl fullWidth size="small">
                                <InputLabel>Role</InputLabel>
                                <Select
                                    value={c.target}
                                    label="Role"
                                    onChange={e => updateCriterion(index, { target: e.target.value })}
                                >
                                    {roleSlots.map(slot => (
                                        <MenuItem key={slot.roleId} value={slot.roleName}>{slot.roleName}</MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        )}

                        {c.type === 'ALIGNMENT_COUNT' && (
                            <FormControl fullWidth size="small">
                                <InputLabel>Alignment</InputLabel>
                                <Select
                                    value={c.target}
                                    label="Alignment"
                                    onChange={e => updateCriterion(index, { target: e.target.value })}
                                >
                                    {alignments.map(a => (
                                        <MenuItem key={a.id} value={a.name.toUpperCase()}>{a.name}</MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        )}

                        {c.type === 'SURVIVAL' && (
                            <TextField
                                disabled
                                fullWidth
                                size="small"
                                label="Target"
                                value="Nights"
                            />
                        )}

                        <TextField
                            size="small"
                            type="number"
                            label="Count"
                            value={c.count}
                            onChange={e => updateCriterion(index, { count: parseInt(e.target.value) || 0 })}
                            sx={{ width: 100 }}
                        />
                    </Box>
                </Paper>
            ))}

            <Box sx={{ display: 'flex', justifyContent: (winConditionId || initialData) ? 'space-between' : 'flex-end', alignItems: 'center', mt: 4 }}>
                {(winConditionId || initialData) && (
                    <Button onClick={() => setDeleteDialogOpen(true)} variant="outlined" color="error">
                        Delete
                    </Button>
                )}
                <Box sx={{ display: 'flex', gap: 2 }}>
                    <Button onClick={onCancel} variant="outlined" color="secondary">
                        Cancel
                    </Button>
                    <Button onClick={submit} variant="contained" color="primary">
                        {(winConditionId || initialData) ? "Update" : "Save"}
                    </Button>
                </Box>
            </Box>

            <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
                <DialogTitle>Delete Win Condition?</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        Are you sure you want to permanently delete "{wc.name}"?
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDeleteDialogOpen(false)} color="secondary">Cancel</Button>
                    <Button onClick={confirmDelete} color="error" variant="contained">Delete</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}
